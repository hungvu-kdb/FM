# Claude-Peers Hierarchical - Quick Reference

## Installation (One-time)

```bash
cp -r RefactorPeers ~/claude-peers-hierarchical
cd ~/claude-peers-hierarchical
bun install
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts
alias claudepeers-hier='claude --dangerously-load-development-channels server:claude-peers-hierarchical'
```

## Starting a Session

```bash
claudepeers-hier
```

## Essential Commands

### 1. Establish Your Role (Do this first!)

```
# If you're the top boss
Call set_role with role="super_boss"

# If you report to someone
Call list_peers with scope="machine"
# Find your boss's ID, then:
Call set_role with role="boss", parent_id="<boss_id>"
# or
Call set_role with role="worker", parent_id="<boss_id>"
```

### 2. Set Your Status

```
Call set_summary with "What you're working on"
```

### 3. Discover Others

```
# Everyone on this machine
Call list_peers with scope="machine"

# Only bosses
Call list_peers with scope="machine", role_filter="boss"

# Your direct reports (if you're a boss)
Call list_peers with scope="hierarchy"

# Same git repo
Call list_peers with scope="repo"
```

### 4. Send Messages

```
# Direct message
Call send_message with to_id="<peer_id>", message="Your message"

# High priority
Call send_message with to_id="<peer_id>", message="URGENT", priority="high"

# Broadcast to all your reports
Call broadcast_message with scope="subordinates", message="Your message"

# Broadcast to your boss and their boss
Call broadcast_message with scope="superiors", message="Your message"

# Broadcast to peers at your level
Call broadcast_message with scope="peers", message="Your message"
```

### 5. View Organization

```
Call get_hierarchy
```

### 6. Check Messages

```
Call check_messages
```

## Hierarchy Levels

| Role | Level | Reports To | Can Have |
|------|-------|-----------|----------|
| super_boss | 0 | Nobody | Bosses |
| boss | 1 | super_boss | Workers & Bosses |
| worker | 2+ | boss | Nobody |

## Message Priority

- `priority="normal"` (default): Delivered in order
- `priority="high"`: Delivered first, useful for blockers/urgent items

## Scopes

### For list_peers:
- `machine`: All peers on this computer
- `directory`: Peers in same working directory
- `repo`: Peers in same git repository
- `hierarchy`: Your direct reports (if you're a boss)

### For broadcast_message:
- `subordinates`: All your direct and indirect reports
- `superiors`: Your boss and their chain of command
- `peers`: Others at your same level with same parent

## Common Workflows

### Daily Standup

1. Super Boss: `broadcast_message(scope="subordinates", message="Standup time!")`
2. Bosses: `broadcast_message(scope="subordinates", message="Team standup")`
3. Workers: `send_message(to_id=boss_id, message="Status: ...")`
4. Bosses: `send_message(to_id=super_boss_id, message="Team status: ...")`

### Report a Blocker

```
Call send_message with to_id="<boss_id>", message="BLOCKER: ...", priority="high"
```

### Ask Peers for Help

```
Call broadcast_message with scope="peers", message="Anyone available to help with ...?"
```

### Escalate Issue

```
Call broadcast_message with scope="superiors", message="URGENT: Need approval on ..."
```

### Team Announcement

```
Call broadcast_message with scope="subordinates", message="Important announcement: ..."
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Parent peer not found" | Run `list_peers` to get correct ID |
| Messages not arriving | Check recipient is still running with `list_peers` |
| Hierarchy looks wrong | Verify parent_id with `list_peers` |
| Broker won't start | `pkill -f "broker-hierarchical.ts"` then retry |

## Database

- Location: `~/.claude-peers.db`
- Type: SQLite
- Auto-created on first run
- Survives broker restarts

## Environment Variables

```bash
# Custom broker port (default: 7899)
export CLAUDE_PEERS_PORT=7900

# Custom database location (default: ~/.claude-peers.db)
export CLAUDE_PEERS_DB=/path/to/db

# Then start Claude
claudepeers-hier
```

## File Structure

```
RefactorPeers/
├── broker-hierarchical.ts    # Broker daemon
├── server-hierarchical.ts    # MCP server
├── shared/types.ts           # Type definitions
├── package.json              # Dependencies
├── README.md                 # Full documentation
├── SETUP_EXAMPLE.md          # Step-by-step setup
└── QUICK_REFERENCE.md        # This file
```

## Key Differences from Original claude-peers

| Feature | Original | Hierarchical |
|---------|----------|--------------|
| Roles | None | super_boss, boss, worker |
| Parent tracking | No | Yes |
| Broadcast | No | Yes |
| Priority | No | Yes |
| Hierarchy view | No | Yes |
| Role filtering | No | Yes |

## Tips & Tricks

### Get your peer ID
```
Call list_peers with scope="machine"
# Your ID is shown in the output
```

### Find your boss's ID
```
Call list_peers with scope="machine", role_filter="boss"
```

### See who reports to you
```
Call list_peers with scope="hierarchy"
```

### Update your status in real-time
```
Call set_summary with "New status"
```

### Send urgent message
```
Call send_message with to_id="<id>", message="URGENT: ...", priority="high"
```

### Broadcast to entire organization
```
# From super_boss:
Call broadcast_message with scope="subordinates", message="All hands: ..."
```

### Check if someone is online
```
Call list_peers with scope="machine"
# If they're in the list, they're online
```

## Performance Notes

- Messages delivered within 1 second (polling interval)
- Hierarchy queries are fast (indexed by parent_id)
- Database auto-cleans stale peers every 30 seconds
- Supports 100+ peers without issues

## Security Notes

- All communication is localhost-only (127.0.0.1:7899)
- No encryption (add if needed for production)
- Database is local SQLite (no remote access)
- Process validation prevents ghost peers

## Next Steps

1. Read `SETUP_EXAMPLE.md` for a complete walkthrough
2. Read `README.md` for detailed documentation
3. Start with `QUICK_REFERENCE.md` (this file) for daily use
