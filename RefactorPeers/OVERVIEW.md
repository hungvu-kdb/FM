# Claude-Peers Hierarchical - Visual Overview

## Project Structure

```
RefactorPeers/
├── 📄 README.md                    # Main documentation
├── 📄 QUICK_REFERENCE.md           # Daily command reference
├── 📄 SETUP_EXAMPLE.md             # Step-by-step setup guide
├── 📄 ARCHITECTURE.md              # Technical deep dive
├── 📄 SUMMARY.md                   # Project summary
├── 📄 OVERVIEW.md                  # This file
├── 📄 package.json                 # Dependencies
├── 📄 tsconfig.json                # TypeScript config
├── 📄 .gitignore                   # Git ignore rules
├── 🔧 broker-hierarchical.ts       # Broker daemon (450+ lines)
├── 🔧 server-hierarchical.ts       # MCP server (550+ lines)
└── 📁 shared/
    └── 📄 types.ts                 # Type definitions (150+ lines)
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Instances                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Terminal 1  │  │  Terminal 2  │  │  Terminal N  │       │
│  │  (Super Boss)│  │   (Boss A)   │  │  (Worker)    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│  ┌──────▼─────────────────▼─────────────────▼──────┐        │
│  │         MCP Server (server-hierarchical.ts)     │        │
│  │  - Registers with broker                        │        │
│  │  - Exposes hierarchy tools                      │        │
│  │  - Polls for messages                           │        │
│  │  - Pushes via channel notifications             │        │
│  └──────┬──────────────────────────────────────────┘        │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │ HTTP (localhost:7899)
          │
┌─────────▼────────────────────────────────────────────────────┐
│         Broker Daemon (broker-hierarchical.ts)               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  HTTP Server (127.0.0.1:7899)                         │  │
│  │  - /register          - Register peer                 │  │
│  │  - /send-message      - Route direct message          │  │
│  │  - /broadcast-message - Route broadcast message       │  │
│  │  - /get-hierarchy     - Build hierarchy tree          │  │
│  │  - /list-peers        - Query peers with filters      │  │
│  │  - /poll-messages     - Deliver messages              │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  SQLite Database (~/.claude-peers.db)                 │  │
│  │  ┌──────────────────┐  ┌──────────────────┐           │  │
│  │  │ peers table      │  │ messages table   │           │  │
│  │  │ - id             │  │ - id             │           │  │
│  │  │ - pid            │  │ - from_id        │           │  │
│  │  │ - role           │  │ - to_id          │           │  │
│  │  │ - parent_id      │  │ - text           │           │  │
│  │  │ - hierarchy_level│  │ - priority       │           │  │
│  │  │ - summary        │  │ - delivered      │           │  │
│  │  │ - last_seen      │  │ - sent_at        │           │  │
│  │  └──────────────────┘  └──────────────────┘           │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Hierarchy Structure

```
                    ┌─────────────────────┐
                    │   SUPER_BOSS (L0)   │
                    │   Coordinator       │
                    │   abc12345          │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────▼────┐  ┌──────▼────┐  ┌──────▼────┐
         │  BOSS (L1)│  │  BOSS (L1)│  │  BOSS (L1)│
         │ Manager A │  │ Manager B │  │ Manager C │
         │ def67890  │  │ ghi11111  │  │ jkl22222  │
         └──────┬────┘  └──────┬────┘  └──────┬────┘
                │              │              │
         ┌──────┴──────┐       │       ┌──────┴──────┐
         │             │       │       │             │
    ┌────▼──┐  ┌──────▼──┐ ┌──▼────┐ ┌▼────┐  ┌────▼──┐
    │Worker │  │ Worker  │ │Worker │ │Work │  │Worker │
    │  (L2) │  │  (L2)   │ │ (L2)  │ │ (L2)│  │ (L2)  │
    │mno333 │  │ pqr444  │ │stu555 │ │vwx6 │  │yz1111 │
    └───────┘  └─────────┘ └───────┘ └─────┘  └───────┘
```

## Message Flow

### Direct Message
```
Worker (mno333)
    ↓
send_message(to_id="def67890", message="Status update")
    ↓
MCP Server
    ↓
POST /send-message
    ↓
Broker validates recipient
    ↓
INSERT into messages table
    ↓
Boss (def67890) polls
    ↓
Message delivered via channel
    ↓
Boss receives notification
```

### Broadcast to Subordinates
```
Boss (def67890)
    ↓
broadcast_message(scope="subordinates", message="Team meeting")
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
Workers poll
    ↓
Messages delivered via channel
    ↓
All workers receive notification
```

### Broadcast to Superiors
```
Worker (mno333)
    ↓
broadcast_message(scope="superiors", message="BLOCKER")
    ↓
MCP Server
    ↓
POST /broadcast-message
    ↓
Broker queries chain of command
    ↓
INSERT to Boss (def67890)
INSERT to Super Boss (abc12345)
    ↓
Boss and Super Boss poll
    ↓
Messages delivered via channel
    ↓
Both receive notification
```

## Tool Ecosystem

```
┌─────────────────────────────────────────────────────────┐
│              MCP Tools (7 total)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Organization Setup:                                   │
│  ├─ set_role(role, parent_id)                         │
│  │  └─ Establish position in hierarchy                │
│  │                                                     │
│  Discovery:                                            │
│  ├─ list_peers(scope, role_filter)                    │
│  │  └─ Find other instances                           │
│  ├─ get_hierarchy()                                   │
│  │  └─ View org structure                             │
│  │                                                     │
│  Communication:                                        │
│  ├─ send_message(to_id, message, priority)           │
│  │  └─ Direct message to peer                         │
│  ├─ broadcast_message(scope, message, priority)      │
│  │  └─ Send to subordinates/superiors/peers          │
│  │                                                     │
│  Status & Monitoring:                                 │
│  ├─ set_summary(summary)                             │
│  │  └─ Update work status                            │
│  ├─ check_messages()                                 │
│  │  └─ Manually poll messages                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Data Model

### Peer Object
```typescript
interface Peer {
  id: string                    // Unique peer ID
  pid: number                   // Process ID
  cwd: string                   // Working directory
  git_root: string | null       // Git repository root
  tty: string | null            // Terminal
  summary: string               // Current work summary
  role: "super_boss" | "boss" | "worker"  // Role
  parent_id?: string            // Boss's ID (if not super_boss)
  hierarchy_level: number       // 0=super_boss, 1=boss, 2+=workers
  registered_at: string         // ISO timestamp
  last_seen: string             // ISO timestamp
}
```

### Message Object
```typescript
interface Message {
  id: number                    // Message ID
  from_id: string               // Sender peer ID
  to_id: string                 // Recipient peer ID
  text: string                  // Message content
  priority: "normal" | "high"   // Message priority
  sent_at: string               // ISO timestamp
  delivered: boolean            // Delivery status
}
```

### Hierarchy Node
```typescript
interface HierarchyNode {
  peer: Peer                    // Peer information
  children: HierarchyNode[]     // Direct reports
}
```

## Workflow Examples

### Daily Standup
```
9:00 AM
  Super Boss: broadcast_message(scope="subordinates", "Standup time!")
  
9:05 AM
  Boss A: broadcast_message(scope="subordinates", "Team standup")
  Boss B: broadcast_message(scope="subordinates", "Team standup")
  
9:10 AM
  Worker 1: send_message(to_id=boss_a, "Status: ...")
  Worker 2: send_message(to_id=boss_a, "Status: ...")
  Worker 4: send_message(to_id=boss_b, "Status: ...")
  
9:15 AM
  Boss A: send_message(to_id=super_boss, "Team A status: ...")
  Boss B: send_message(to_id=super_boss, "Team B status: ...")
  
9:20 AM
  Super Boss: get_hierarchy() → See complete status
```

### Escalation
```
Worker encounters blocker
  ↓
send_message(to_id=boss, message="BLOCKER", priority="high")
  ↓
Boss receives high-priority message
  ↓
Boss assesses and escalates if needed
  ↓
send_message(to_id=super_boss, message="URGENT", priority="high")
  ↓
Super Boss receives and acts
```

### Team Coordination
```
Boss A needs help from Boss B's team
  ↓
send_message(to_id=boss_b, message="Can you spare someone for X?")
  ↓
Boss B responds
  ↓
Boss B: broadcast_message(scope="subordinates", "Who can help Boss A?")
  ↓
Worker volunteers
  ↓
Worker: send_message(to_id=boss_a, "I can help")
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Lines of Code | 1200+ |
| Broker Code | 450+ lines |
| Server Code | 550+ lines |
| Type Definitions | 150+ lines |
| Documentation | 1500+ lines |
| Supported Peers | 100+ |
| Message Latency | ~1 second |
| Database | SQLite |
| Roles | 3 (super_boss, boss, worker) |
| Broadcast Scopes | 3 (subordinates, superiors, peers) |
| Message Priorities | 2 (normal, high) |
| Tools | 7 |

## Installation Summary

```bash
# 1. Copy project
cp -r RefactorPeers ~/claude-peers-hierarchical

# 2. Install dependencies
cd ~/claude-peers-hierarchical
bun install

# 3. Register with Claude
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts

# 4. Create alias
alias claudepeers-hier='claude --dangerously-load-development-channels server:claude-peers-hierarchical'

# 5. Start using
claudepeers-hier
```

## Documentation Map

```
START HERE
    ↓
README.md (Overview & Features)
    ↓
    ├─→ SETUP_EXAMPLE.md (Step-by-step setup)
    │       ↓
    │   QUICK_REFERENCE.md (Daily commands)
    │
    └─→ ARCHITECTURE.md (Technical details)
            ↓
        SUMMARY.md (Project overview)
```

## Quick Start

1. **Install:** Follow installation summary above
2. **Setup:** Follow SETUP_EXAMPLE.md
3. **Use:** Reference QUICK_REFERENCE.md
4. **Learn:** Read ARCHITECTURE.md

## Support Resources

- **README.md** - Features and API
- **QUICK_REFERENCE.md** - Commands and workflows
- **SETUP_EXAMPLE.md** - Step-by-step guide
- **ARCHITECTURE.md** - Technical details
- **SUMMARY.md** - Project overview
- **OVERVIEW.md** - This file

## Next Steps

1. Read README.md for complete overview
2. Follow SETUP_EXAMPLE.md to set up your hierarchy
3. Use QUICK_REFERENCE.md for daily work
4. Refer to ARCHITECTURE.md for advanced topics
5. Extend with custom features as needed
