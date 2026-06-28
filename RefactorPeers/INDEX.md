# Claude-Peers Hierarchical - Complete Index

## 📚 Documentation Files

### Getting Started
- **[README.md](README.md)** - Main documentation with features, installation, and API reference
- **[OVERVIEW.md](OVERVIEW.md)** - Visual overview with diagrams and architecture
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference for daily use

### Setup & Examples
- **[SETUP_EXAMPLE.md](SETUP_EXAMPLE.md)** - Step-by-step setup with 8-terminal example
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep dive into system design
- **[SUMMARY.md](SUMMARY.md)** - Project summary and feature comparison

### This File
- **[INDEX.md](INDEX.md)** - Complete index (you are here)

## 🔧 Implementation Files

### Core System
- **[broker-hierarchical.ts](broker-hierarchical.ts)** - Broker daemon (450+ lines)
  - HTTP server on localhost:7899
  - SQLite database management
  - Hierarchy tree building
  - Message routing and broadcasting
  
- **[server-hierarchical.ts](server-hierarchical.ts)** - MCP server (550+ lines)
  - Stdio-based MCP communication
  - Tool implementations
  - Message polling and channel notifications
  - Automatic broker startup

### Shared Code
- **[shared/types.ts](shared/types.ts)** - Type definitions (150+ lines)
  - Peer, Message, HierarchyNode types
  - Request/Response types
  - Broadcast types

### Configuration
- **[package.json](package.json)** - Dependencies and scripts
- **[tsconfig.json](tsconfig.json)** - TypeScript configuration
- **[.gitignore](.gitignore)** - Git ignore rules

## 📖 Reading Guide

### For First-Time Users
1. Start with [OVERVIEW.md](OVERVIEW.md) for visual understanding
2. Read [README.md](README.md) for features and API
3. Follow [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) for setup
4. Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for daily work

### For Developers
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Study [broker-hierarchical.ts](broker-hierarchical.ts) for backend
3. Study [server-hierarchical.ts](server-hierarchical.ts) for MCP integration
4. Review [shared/types.ts](shared/types.ts) for data structures
5. Check [SUMMARY.md](SUMMARY.md) for project overview

### For DevOps/Deployment
1. Read [README.md](README.md) configuration section
2. Check [ARCHITECTURE.md](ARCHITECTURE.md) security section
3. Review [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) for deployment
4. Monitor using health checks in [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

## 🎯 Quick Navigation

### By Task

#### "I want to set up the system"
→ [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md)

#### "I need a command reference"
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

#### "I want to understand the architecture"
→ [ARCHITECTURE.md](ARCHITECTURE.md)

#### "I need to troubleshoot an issue"
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md#troubleshooting) or [README.md](README.md#troubleshooting)

#### "I want to extend the system"
→ [ARCHITECTURE.md](ARCHITECTURE.md#extension-points)

#### "I need API documentation"
→ [README.md](README.md#api-endpoints)

#### "I want to see a workflow example"
→ [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md#workflow-example-daily-standup)

#### "I need to understand the data model"
→ [ARCHITECTURE.md](ARCHITECTURE.md#database-schema) or [OVERVIEW.md](OVERVIEW.md#data-model)

## 📋 File Descriptions

### Documentation

| File | Lines | Purpose |
|------|-------|---------|
| README.md | 400+ | Main documentation with features and API |
| OVERVIEW.md | 300+ | Visual diagrams and architecture overview |
| QUICK_REFERENCE.md | 200+ | Quick command reference |
| SETUP_EXAMPLE.md | 300+ | Step-by-step setup guide |
| ARCHITECTURE.md | 400+ | Technical deep dive |
| SUMMARY.md | 300+ | Project summary |
| INDEX.md | 200+ | This file |

### Implementation

| File | Lines | Purpose |
|------|-------|---------|
| broker-hierarchical.ts | 450+ | Broker daemon |
| server-hierarchical.ts | 550+ | MCP server |
| shared/types.ts | 150+ | Type definitions |
| package.json | 20 | Dependencies |
| tsconfig.json | 20 | TypeScript config |
| .gitignore | 30 | Git ignore rules |

## 🔑 Key Concepts

### Roles
- **super_boss** (Level 0) - Top-level coordinator
- **boss** (Level 1) - Middle management
- **worker** (Level 2+) - Individual contributors

### Scopes
- **machine** - All peers on this computer
- **directory** - Peers in same working directory
- **repo** - Peers in same git repository
- **hierarchy** - Direct reports (if you're a boss)

### Broadcast Scopes
- **subordinates** - All direct and indirect reports
- **superiors** - Chain of command (boss and their boss)
- **peers** - Others at same level with same parent

### Message Priority
- **normal** - Delivered in FIFO order (default)
- **high** - Delivered before normal messages

## 🛠️ Tools Available

1. **set_role** - Establish position in hierarchy
2. **list_peers** - Discover other instances
3. **send_message** - Send direct message
4. **broadcast_message** - Send to subordinates/superiors/peers
5. **get_hierarchy** - View organizational structure
6. **set_summary** - Update work status
7. **check_messages** - Manually poll messages

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Total Lines of Code | 1200+ |
| Total Documentation | 1500+ |
| Number of Files | 11 |
| Supported Peers | 100+ |
| Message Latency | ~1 second |
| Database Type | SQLite |
| Roles | 3 |
| Tools | 7 |
| Broadcast Scopes | 3 |
| Message Priorities | 2 |

## 🚀 Quick Start

```bash
# 1. Install
cp -r RefactorPeers ~/claude-peers-hierarchical
cd ~/claude-peers-hierarchical
bun install

# 2. Register
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts

# 3. Create alias
alias claudepeers-hier='claude --dangerously-load-development-channels server:claude-peers-hierarchical'

# 4. Start
claudepeers-hier
```

## 📞 Support

### Documentation
- [README.md](README.md) - Features and API
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Commands
- [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) - Setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details

### Troubleshooting
- [QUICK_REFERENCE.md#troubleshooting](QUICK_REFERENCE.md#troubleshooting)
- [README.md#troubleshooting](README.md#troubleshooting)

### Examples
- [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) - Complete setup
- [OVERVIEW.md#workflow-examples](OVERVIEW.md#workflow-examples)

## 🔄 Workflow

```
README.md (Overview)
    ↓
SETUP_EXAMPLE.md (Setup)
    ↓
QUICK_REFERENCE.md (Daily Use)
    ↓
ARCHITECTURE.md (Deep Dive)
    ↓
Extend/Customize
```

## 📝 File Organization

```
RefactorPeers/
├── 📖 Documentation
│   ├── README.md
│   ├── OVERVIEW.md
│   ├── QUICK_REFERENCE.md
│   ├── SETUP_EXAMPLE.md
│   ├── ARCHITECTURE.md
│   ├── SUMMARY.md
│   └── INDEX.md (this file)
│
├── 🔧 Implementation
│   ├── broker-hierarchical.ts
│   ├── server-hierarchical.ts
│   └── shared/
│       └── types.ts
│
└── ⚙️ Configuration
    ├── package.json
    ├── tsconfig.json
    └── .gitignore
```

## 🎓 Learning Path

### Beginner
1. [OVERVIEW.md](OVERVIEW.md) - Visual understanding
2. [README.md](README.md) - Features overview
3. [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) - Hands-on setup

### Intermediate
1. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
2. [README.md](README.md) - API documentation
3. [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) - Workflow examples

### Advanced
1. [ARCHITECTURE.md](ARCHITECTURE.md) - System design
2. [broker-hierarchical.ts](broker-hierarchical.ts) - Backend code
3. [server-hierarchical.ts](server-hierarchical.ts) - MCP integration
4. [shared/types.ts](shared/types.ts) - Data structures

## 🔗 Cross-References

### From README.md
- See [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) for step-by-step setup
- See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command reference
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details

### From SETUP_EXAMPLE.md
- See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command reference
- See [README.md](README.md) for API documentation
- See [ARCHITECTURE.md](ARCHITECTURE.md) for troubleshooting

### From QUICK_REFERENCE.md
- See [README.md](README.md) for detailed API
- See [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) for setup
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details

### From ARCHITECTURE.md
- See [README.md](README.md) for user-facing features
- See [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md) for usage examples
- See [broker-hierarchical.ts](broker-hierarchical.ts) for implementation

## 📌 Important Notes

1. **Localhost Only** - Communication is restricted to 127.0.0.1:7899
2. **No Authentication** - Assumes trusted environment
3. **SQLite Database** - Located at ~/.claude-peers.db
4. **Auto-Cleanup** - Stale peers removed every 30 seconds
5. **Message Latency** - ~1 second due to polling interval

## 🎯 Next Steps

1. **First Time?** → Start with [OVERVIEW.md](OVERVIEW.md)
2. **Ready to Setup?** → Follow [SETUP_EXAMPLE.md](SETUP_EXAMPLE.md)
3. **Need Commands?** → Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. **Want Details?** → Read [ARCHITECTURE.md](ARCHITECTURE.md)
5. **Troubleshooting?** → See [QUICK_REFERENCE.md#troubleshooting](QUICK_REFERENCE.md#troubleshooting)

---

**Last Updated:** April 2026
**Version:** 0.2.0
**Status:** Production Ready
