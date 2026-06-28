# Claude-Peers Hierarchical Refactor

A refactored version of claude-peers with support for hierarchical peer relationships. Enables organizing Claude Code instances in a boss-worker structure with multi-level management.

## Architecture

```
                    ┌─────────────────────┐
                    │   SUPER_BOSS (L0)   │
                    │   Coordinator       │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────▼────┐  ┌──────▼────┐  ┌──────▼────┐
         │  BOSS (L1)│  │  BOSS (L1)│  │  BOSS (L1)│
         │ Manager A │  │ Manager B │  │ Manager C │
         └──────┬────┘  └──────┬────┘  └──────┬────┘
                │              │              │
         ┌──────┴──────┐       │       ┌──────┴──────┐
         │             │       │       │             │
    ┌────▼──┐  ┌──────▼──┐ ┌──▼────┐ ┌▼────┐  ┌────▼──┐
    │Worker │  │ Worker  │ │Worker │ │Work │  │Worker │
    │  (L2) │  │  (L2)   │ │ (L2)  │ │ (L2)│  │ (L2)  │
    └───────┘  └─────────┘ └───────┘ └─────┘  └───────┘
```

## Key Features

### 1. Hierarchical Roles
- **super_boss** (Level 0): Top-level coordinator
- **boss** (Level 1): Middle management, reports to super_boss
- **worker** (Level 2+): Individual contributors, report to boss

### 2. Enhanced Messaging
- **Direct messaging**: Send to specific peer by ID
- **Broadcast messaging**: Send to all subordinates, superiors, or peers
- **Priority levels**: Normal or high-priority messages (high priority delivered first)

### 3. Hierarchy Queries
- **get_hierarchy**: View complete organizational structure
- **list_peers**: Filter by role, scope, or hierarchy level
- **Subordinate tracking**: Automatically track all direct and indirect reports

### 4. Database Schema
Extended SQLite schema with hierarchy support:
```sql
peers table:
  - role: TEXT (worker, boss, super_boss)
  - parent_id: TEXT (reference to parent boss)
  - hierarchy_level: INTEGER (0=super_boss, 1=boss, 2+=workers)

messages table:
  - priority: TEXT (normal, high)
```

## Installation

### 1. Clone/Copy the RefactorPeers folder

```bash
cp -r RefactorPeers ~/claude-peers-hierarchical
cd ~/claude-peers-hierarchical
```

### 2. Install dependencies

```bash
bun install
```

### 3. Register the MCP server

```bash
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts
```

### 4. Create an alias (optional)

```bash
alias claudepeers-hier='claude --dangerously-load-development-channels server:claude-peers-hierarchical'
```

## Usage

### Setup: Establish Hierarchy

**Terminal 1 - Super Boss:**
```bash
claudepeers-hier
```
In Claude:
```
Call set_role with role="super_boss"
Call set_summary with "I am the top-level coordinator"
```

**Terminal 2 - Boss A:**
```bash
claudepeers-hier
```
In Claude:
```
Call list_peers with scope="machine"
# Find super_boss ID (e.g., "abc12345")
Call set_role with role="boss", parent_id="abc12345"
Call set_summary with "I manage team A"
```

**Terminal 3 - Boss B:**
```bash
claudepeers-hier
```
In Claude:
```
Call set_role with role="boss", parent_id="abc12345"
Call set_summary with "I manage team B"
```

**Terminals 4-8 - Workers:**
```bash
claudepeers-hier
```
In Claude:
```
Call list_peers with scope="machine"
# Find boss ID (e.g., "def67890")
Call set_role with role="worker", parent_id="def67890"
Call set_summary with "Working on feature X"
```

### View Hierarchy

From any instance:
```
Call get_hierarchy
```

Output:
```
Organizational Hierarchy:

SUPER_BOSS (abc12345): I am the top-level coordinator
  BOSS (def67890): I manage team A
    WORKER (ghi11111): Working on feature X
    WORKER (jkl22222): Working on feature Y
  BOSS (mno33333): I manage team B
    WORKER (pqr44444): Working on feature Z
```

### Send Messages

**Direct message to specific peer:**
```
Call send_message with to_id="ghi11111", message="How's feature X going?"
```

**Broadcast to all subordinates:**
```
Call broadcast_message with scope="subordinates", message="Daily standup in 5 minutes"
```

**Broadcast to superiors (chain of command):**
```
Call broadcast_message with scope="superiors", message="Blocker: need approval on design"
```

**Broadcast to peers (same level):**
```
Call broadcast_message with scope="peers", message="Anyone free to pair on this?"
```

### List Peers with Filters

**All peers on machine:**
```
Call list_peers with scope="machine"
```

**Only bosses:**
```
Call list_peers with scope="machine", role_filter="boss"
```

**Direct reports (if you're a boss):**
```
Call list_peers with scope="hierarchy"
```

**Same git repo:**
```
Call list_peers with scope="repo"
```

## API Endpoints

### New Endpoints

#### GET /get-hierarchy
Get the complete organizational hierarchy.

**Request:**
```json
{
  "id": "peer_id"
}
```

**Response:**
```json
{
  "hierarchy": {
    "peer": { /* Peer object */ },
    "children": [ /* HierarchyNode array */ ]
  }
}
```

#### POST /broadcast-message
Send a message to all subordinates, superiors, or peers.

**Request:**
```json
{
  "from_id": "peer_id",
  "text": "message content",
  "scope": "subordinates|superiors|peers",
  "priority": "normal|high"
}
```

**Response:**
```json
{
  "ok": true,
  "count": 5
}
```

### Enhanced Endpoints

#### POST /register
Now includes role and parent_id.

**Request:**
```json
{
  "pid": 12345,
  "cwd": "/path/to/project",
  "git_root": "/path/to/repo",
  "tty": "pts/0",
  "summary": "Working on auth",
  "role": "worker|boss|super_boss",
  "parent_id": "boss_peer_id"
}
```

**Response:**
```json
{
  "id": "new_peer_id",
  "hierarchy_level": 2
}
```

#### POST /list-peers
Now supports hierarchy scope and role filtering.

**Request:**
```json
{
  "scope": "machine|directory|repo|hierarchy",
  "cwd": "/path/to/project",
  "git_root": "/path/to/repo",
  "exclude_id": "peer_id",
  "role_filter": "worker|boss|super_boss",
  "parent_id": "boss_id"
}
```

#### POST /send-message
Now supports priority levels.

**Request:**
```json
{
  "from_id": "sender_id",
  "to_id": "recipient_id",
  "text": "message",
  "priority": "normal|high"
}
```

## Tools Available in MCP Server

### set_role
Establish your position in the hierarchy.

```
set_role(role: "super_boss"|"boss"|"worker", parent_id?: string)
```

### list_peers
Discover other instances with hierarchy support.

```
list_peers(scope: "machine"|"directory"|"repo"|"hierarchy", role_filter?: string)
```

### send_message
Send a direct message to another peer.

```
send_message(to_id: string, message: string, priority?: "normal"|"high")
```

### broadcast_message
Send a message to all subordinates, superiors, or peers.

```
broadcast_message(scope: "subordinates"|"superiors"|"peers", message: string, priority?: "normal"|"high")
```

### get_hierarchy
View the complete organizational structure.

```
get_hierarchy()
```

### set_summary
Set a summary of your current work.

```
set_summary(summary: string)
```

### check_messages
Manually check for new messages.

```
check_messages()
```

## Configuration

| Environment Variable | Default              | Description                           |
| -------------------- | -------------------- | ------------------------------------- |
| `CLAUDE_PEERS_PORT`  | `7899`               | Broker port                           |
| `CLAUDE_PEERS_DB`    | `~/.claude-peers.db` | SQLite database path                  |

## File Structure

```
RefactorPeers/
├── shared/
│   └── types.ts                 # Shared type definitions with hierarchy support
├── broker-hierarchical.ts       # Broker daemon with hierarchy logic
├── server-hierarchical.ts       # MCP server with hierarchy tools
├── package.json                 # Dependencies
└── README.md                    # This file
```

## Differences from Original claude-peers

| Feature | Original | Hierarchical |
| --- | --- | --- |
| Peer roles | None | super_boss, boss, worker |
| Parent tracking | No | Yes (parent_id) |
| Hierarchy level | No | Yes (0-N) |
| Broadcast messaging | No | Yes (subordinates/superiors/peers) |
| Message priority | No | Yes (normal/high) |
| Hierarchy queries | No | Yes (get_hierarchy) |
| Scope filtering | machine/directory/repo | + hierarchy |
| Role filtering | No | Yes |

## Example Workflow

### Scenario: Daily Standup

1. **Super Boss** calls `broadcast_message(scope="subordinates", message="Daily standup starting in 5 minutes")`
   - All bosses and workers receive the message

2. **Each Boss** calls `broadcast_message(scope="subordinates", message="Team standup in 3 minutes")`
   - Their direct reports receive the message

3. **Workers** respond with `send_message(to_id=boss_id, message="I'm working on feature X, no blockers")`

4. **Bosses** aggregate responses and call `send_message(to_id=super_boss_id, message="Team A status: all on track")`

5. **Super Boss** calls `get_hierarchy` to see complete status

## Troubleshooting

### Broker won't start
```bash
# Check if port 7899 is in use
lsof -i :7899

# Kill existing broker
pkill -f "broker-hierarchical.ts"

# Check database
ls -la ~/.claude-peers.db
```

### Messages not arriving
```bash
# Check broker health
curl http://127.0.0.1:7899/health

# Manually poll messages
bun cli.ts poll <peer_id>
```

### Hierarchy not showing correctly
```bash
# Verify parent_id is set correctly
bun cli.ts peers

# Check database directly
sqlite3 ~/.claude-peers.db "SELECT id, role, parent_id, hierarchy_level FROM peers;"
```

## Future Enhancements

- [ ] Delegation workflows (assign tasks down the hierarchy)
- [ ] Status aggregation (automatic rollup from workers to bosses)
- [ ] Escalation rules (auto-escalate high-priority messages)
- [ ] Team channels (group messaging within a team)
- [ ] Audit logging (track all messages and hierarchy changes)
- [ ] Web dashboard (visualize hierarchy and message flow)
