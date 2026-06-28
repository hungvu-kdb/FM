# Claude-Peers Hierarchical Architecture

## Overview

Claude-Peers Hierarchical extends the original claude-peers system with organizational hierarchy support. It enables Claude Code instances to organize themselves in a boss-worker structure with multi-level management.

## System Components

### 1. Broker Daemon (`broker-hierarchical.ts`)

**Purpose:** Central coordination server that manages peer registration, message routing, and hierarchy tracking.

**Responsibilities:**
- Register new peers with role and parent information
- Maintain SQLite database of peers and messages
- Route messages between peers
- Build and query hierarchy trees
- Clean up stale/dead peers
- Handle broadcast messages to subordinates/superiors/peers

**Key Functions:**
- `handleRegister()`: Register peer with role and parent_id
- `handleListPeers()`: Query peers with hierarchy filtering
- `handleSendMessage()`: Route direct messages
- `handleBroadcastMessage()`: Route broadcast messages
- `handleGetHierarchy()`: Build and return hierarchy tree
- `buildHierarchyTree()`: Recursively build tree structure
- `getAllSubordinates()`: Get all direct and indirect reports
- `getAllSuperiors()`: Get chain of command

**Database Schema:**

```sql
peers table:
  id (TEXT PRIMARY KEY)
  pid (INTEGER) - process ID
  cwd (TEXT) - working directory
  git_root (TEXT) - git repository root
  tty (TEXT) - terminal
  summary (TEXT) - current work summary
  role (TEXT) - super_boss, boss, or worker
  parent_id (TEXT) - reference to parent boss
  hierarchy_level (INTEGER) - 0=super_boss, 1=boss, 2+=workers
  registered_at (TEXT) - ISO timestamp
  last_seen (TEXT) - ISO timestamp

messages table:
  id (INTEGER PRIMARY KEY AUTOINCREMENT)
  from_id (TEXT) - sender peer ID
  to_id (TEXT) - recipient peer ID
  text (TEXT) - message content
  priority (TEXT) - normal or high
  sent_at (TEXT) - ISO timestamp
  delivered (INTEGER) - 0 or 1
```

**Indexes:**
- `idx_parent_id`: Fast hierarchy queries
- `idx_role`: Fast role filtering
- `idx_hierarchy_level`: Fast level filtering

### 2. MCP Server (`server-hierarchical.ts`)

**Purpose:** Stdio-based MCP server that runs in each Claude Code instance and communicates with the broker.

**Responsibilities:**
- Register with broker on startup
- Expose hierarchy-aware tools to Claude
- Poll for inbound messages
- Push messages via channel notifications
- Send heartbeats to broker
- Clean up on shutdown

**Key Functions:**
- `ensureBroker()`: Start broker if not running
- `pollAndPushMessages()`: Poll for messages and push via channel
- Tool handlers for all MCP tools

**Tools Exposed:**
1. `set_role` - Establish position in hierarchy
2. `list_peers` - Discover other instances
3. `send_message` - Send direct message
4. `broadcast_message` - Send to subordinates/superiors/peers
5. `get_hierarchy` - View organizational structure
6. `set_summary` - Update work status
7. `check_messages` - Manually poll messages

### 3. Shared Types (`shared/types.ts`)

**Purpose:** TypeScript type definitions used by both broker and server.

**Key Types:**
- `Peer` - Extended with role, parent_id, hierarchy_level
- `Message` - Extended with priority
- `RegisterRequest/Response` - Extended with role info
- `ListPeersRequest` - Extended with hierarchy scope
- `HierarchyNode` - Tree structure for hierarchy
- `BroadcastMessageRequest` - New type for broadcasts

## Data Flow

### Registration Flow

```
Claude Instance
    ↓
MCP Server (server-hierarchical.ts)
    ↓
POST /register
    ↓
Broker (broker-hierarchical.ts)
    ↓
SQLite Database
    ↓
RegisterResponse (id, hierarchy_level)
    ↓
MCP Server stores myId
```

### Message Sending Flow

```
Claude Instance
    ↓
send_message tool
    ↓
MCP Server
    ↓
POST /send-message
    ↓
Broker validates recipient
    ↓
SQLite: INSERT into messages
    ↓
Response: ok=true
```

### Message Receiving Flow

```
Broker (every 1 second)
    ↓
Poll undelivered messages
    ↓
Mark as delivered
    ↓
MCP Server
    ↓
Push via channel notification
    ↓
Claude receives message
```

### Broadcast Flow

```
Claude Instance (boss)
    ↓
broadcast_message(scope="subordinates")
    ↓
MCP Server
    ↓
POST /broadcast-message
    ↓
Broker queries all subordinates
    ↓
For each subordinate:
  INSERT message
    ↓
Response: ok=true, count=N
```

### Hierarchy Query Flow

```
Claude Instance
    ↓
get_hierarchy tool
    ↓
MCP Server
    ↓
POST /get-hierarchy
    ↓
Broker buildHierarchyTree()
    ↓
Recursively fetch children
    ↓
Return HierarchyNode tree
    ↓
MCP Server formats and returns
```

## Hierarchy Levels

```
Level 0: super_boss
  ├─ Level 1: boss
  │   ├─ Level 2: worker
  │   ├─ Level 2: worker
  │   └─ Level 2: worker
  └─ Level 1: boss
      ├─ Level 2: worker
      └─ Level 2: worker
```

**Rules:**
- Only one super_boss per organization
- Bosses report to super_boss or other bosses
- Workers report to bosses
- Hierarchy level = 0 for super_boss, 1 for boss, 2+ for workers
- Parent_id must reference an existing peer

## Message Priority

**Normal Priority:**
- Delivered in FIFO order
- Used for regular communication
- Default if not specified

**High Priority:**
- Delivered before normal messages
- Used for blockers, urgent issues
- Sorted first in poll results

**Database Query:**
```sql
SELECT * FROM messages 
WHERE to_id = ? AND delivered = 0 
ORDER BY priority DESC, sent_at ASC
```

## Broadcast Scopes

### Subordinates
- All direct reports
- All indirect reports (recursive)
- Used by bosses to communicate down

**Query:**
```
getAllSubordinates(peer_id):
  - Get direct reports (parent_id = peer_id)
  - For each report, recursively get their subordinates
  - Return flattened list
```

### Superiors
- Direct boss
- Boss's boss (recursive)
- Used by workers to escalate

**Query:**
```
getAllSuperiors(peer_id):
  - Get parent (parent_id)
  - If parent exists, recursively get their superiors
  - Return flattened list
```

### Peers
- Same hierarchy level
- Same parent
- Used for lateral communication

**Query:**
```
selectPeersByParent(parent_id):
  - Get all peers with same parent_id
  - Exclude self
```

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Register peer | O(1) | Direct insert |
| Send message | O(1) | Direct insert |
| List peers | O(n) | n = total peers |
| Get hierarchy | O(n) | n = total peers (recursive) |
| Broadcast | O(n) | n = subordinates/superiors |
| Poll messages | O(m) | m = undelivered messages |

### Space Complexity

| Data | Complexity | Notes |
|------|-----------|-------|
| Peers | O(n) | n = total peers |
| Messages | O(m) | m = undelivered messages |
| Hierarchy tree | O(n) | n = total peers |

### Scalability

- **Tested with:** 100+ peers
- **Message latency:** ~1 second (polling interval)
- **Database:** SQLite with WAL mode for concurrent access
- **Indexes:** Optimized for common queries

## Security Considerations

### Current Implementation

- **Localhost only:** 127.0.0.1:7899
- **No authentication:** Assumes trusted environment
- **No encryption:** Messages in plaintext
- **Process validation:** Checks PID still exists

### Production Recommendations

- [ ] Add TLS/SSL for remote communication
- [ ] Implement authentication (API keys, OAuth)
- [ ] Add message encryption
- [ ] Implement audit logging
- [ ] Add rate limiting
- [ ] Validate message content
- [ ] Implement access control lists

## Extension Points

### Adding New Broadcast Scopes

1. Add scope to `BroadcastMessageRequest` enum
2. Implement query function in broker
3. Add case in `handleBroadcastMessage()`
4. Update MCP tool schema

### Adding New Message Types

1. Extend `Message` interface
2. Update database schema
3. Update broker handlers
4. Update MCP tools

### Adding Persistence Features

1. Extend `Peer` interface with new fields
2. Add columns to peers table
3. Update insert/update statements
4. Add migration logic

### Adding Delegation/Tasks

1. Create new `tasks` table
2. Add task assignment endpoints
3. Add task status tracking
4. Add task completion notifications

## Testing Strategy

### Unit Tests

- Hierarchy tree building
- Subordinate/superior queries
- Message routing logic
- Priority sorting

### Integration Tests

- Full registration flow
- Message send/receive
- Broadcast to multiple recipients
- Hierarchy updates

### Load Tests

- 100+ peers
- 1000+ messages
- Concurrent registrations
- Hierarchy queries under load

## Deployment

### Single Machine

```bash
# Install
bun install

# Register MCP
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts

# Run
claude --dangerously-load-development-channels server:claude-peers-hierarchical
```

### Multiple Machines (Future)

- Broker on central server
- MCP servers connect to remote broker
- Requires TLS and authentication
- Requires network configuration

## Monitoring

### Health Checks

```bash
curl http://127.0.0.1:7899/health
# Returns: { "status": "ok", "peers": 5 }
```

### Database Inspection

```bash
sqlite3 ~/.claude-peers.db
SELECT * FROM peers;
SELECT * FROM messages WHERE delivered = 0;
```

### Logs

- Broker: stderr output
- MCP Server: stderr output (prefixed with [claude-peers-hierarchical])

## Future Enhancements

1. **Web Dashboard**
   - Visualize hierarchy
   - Monitor message flow
   - View peer status

2. **Delegation System**
   - Assign tasks down hierarchy
   - Track task status
   - Automatic escalation

3. **Status Aggregation**
   - Automatic rollup from workers to bosses
   - Team-level metrics
   - Organization-wide dashboards

4. **Advanced Routing**
   - Message filtering
   - Conditional routing
   - Message templates

5. **Persistence**
   - Message history
   - Audit logs
   - Replay capability

6. **Integration**
   - Slack/Discord webhooks
   - Email notifications
   - Calendar integration
