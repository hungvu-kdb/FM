# Hierarchical Claude-Peers Setup Example

This guide walks through setting up a complete hierarchical organization with 1 super_boss, 2 bosses, and 5 workers.

## Prerequisites

- Bun installed
- Claude Code v2.1.80+
- claude.ai login

## Step 1: Install and Register

```bash
# Copy to your preferred location
cp -r RefactorPeers ~/claude-peers-hierarchical
cd ~/claude-peers-hierarchical

# Install dependencies
bun install

# Register with Claude
claude mcp add --scope user --transport stdio claude-peers-hierarchical -- bun ~/claude-peers-hierarchical/server-hierarchical.ts

# Create alias for convenience
alias claudepeers-hier='claude --dangerously-load-development-channels server:claude-peers-hierarchical'
```

## Step 2: Start Super Boss (Terminal 1)

```bash
# Terminal 1
claudepeers-hier
```

In Claude, run these commands:

```
Call set_role with role="super_boss"
Call set_summary with "I am the top-level coordinator for the engineering team"
Call list_peers with scope="machine"
```

**Note the super_boss ID** (e.g., `abc12345`)

## Step 3: Start Boss A (Terminal 2)

```bash
# Terminal 2
claudepeers-hier
```

In Claude:

```
Call list_peers with scope="machine"
# Copy the super_boss ID from the output
Call set_role with role="boss", parent_id="<super_boss_id>"
Call set_summary with "I manage the backend team"
Call list_peers with scope="hierarchy"
```

**Note the boss A ID** (e.g., `def67890`)

## Step 4: Start Boss B (Terminal 3)

```bash
# Terminal 3
claudepeers-hier
```

In Claude:

```
Call list_peers with scope="machine"
Call set_role with role="boss", parent_id="<super_boss_id>"
Call set_summary with "I manage the frontend team"
```

**Note the boss B ID** (e.g., `ghi11111`)

## Step 5: Start Workers (Terminals 4-8)

### Worker 1 (Terminal 4)
```bash
claudepeers-hier
```

In Claude:
```
Call list_peers with scope="machine"
Call set_role with role="worker", parent_id="<boss_a_id>"
Call set_summary with "Working on API authentication"
```

### Worker 2 (Terminal 5)
```bash
claudepeers-hier
```

In Claude:
```
Call list_peers with scope="machine"
Call set_role with role="worker", parent_id="<boss_a_id>"
Call set_summary with "Working on database optimization"
```

### Worker 3 (Terminal 6)
```bash
claudepeers-hier
```

In Claude:
```
Call list_peers with scope="machine"
Call set_role with role="worker", parent_id="<boss_a_id>"
Call set_summary with "Working on API documentation"
```

### Worker 4 (Terminal 7)
```bash
claudepeers-hier
```

In Claude:
```
Call list_peers with scope="machine"
Call set_role with role="worker", parent_id="<boss_b_id>"
Call set_summary with "Working on React components"
```

### Worker 5 (Terminal 8)
```bash
claudepeers-hier
```

In Claude:
```
Call list_peers with scope="machine"
Call set_role with role="worker", parent_id="<boss_b_id>"
Call set_summary with "Working on UI styling"
```

## Step 6: View the Hierarchy

From any terminal, run:

```
Call get_hierarchy
```

You should see:

```
Organizational Hierarchy:

SUPER_BOSS (abc12345): I am the top-level coordinator for the engineering team
  BOSS (def67890): I manage the backend team
    WORKER (jkl22222): Working on API authentication
    WORKER (mno33333): Working on database optimization
    WORKER (pqr44444): Working on API documentation
  BOSS (ghi11111): I manage the frontend team
    WORKER (stu55555): Working on React components
    WORKER (vwx66666): Working on UI styling
```

## Step 7: Test Messaging

### Super Boss broadcasts to all subordinates

From Terminal 1 (Super Boss):
```
Call broadcast_message with scope="subordinates", message="Great work everyone! Let's sync up in 30 minutes for a team meeting."
```

All bosses and workers receive this message.

### Boss A broadcasts to their team

From Terminal 2 (Boss A):
```
Call broadcast_message with scope="subordinates", message="Backend team: please review the API design doc by EOD"
```

Workers 1, 2, 3 receive this message.

### Worker 1 sends high-priority message to Boss A

From Terminal 4 (Worker 1):
```
Call send_message with to_id="<boss_a_id>", message="BLOCKER: Authentication service is down, need immediate help", priority="high"
```

Boss A receives this high-priority message immediately.

### Boss A escalates to Super Boss

From Terminal 2 (Boss A):
```
Call send_message with to_id="<super_boss_id>", message="URGENT: Backend authentication service is down. Worker 1 is blocked. Need to investigate immediately.", priority="high"
```

### Worker 4 asks peers for help

From Terminal 7 (Worker 4):
```
Call broadcast_message with scope="peers", message="Anyone familiar with Tailwind CSS? Need help with responsive design"
```

Worker 5 receives this message.

## Step 8: Advanced Queries

### List only bosses

From any terminal:
```
Call list_peers with scope="machine", role_filter="boss"
```

### List only workers

```
Call list_peers with scope="machine", role_filter="worker"
```

### Boss A sees their direct reports

From Terminal 2 (Boss A):
```
Call list_peers with scope="hierarchy"
```

Shows only Workers 1, 2, 3.

## Step 9: Update Summaries

Workers can update their status in real-time:

From Terminal 4 (Worker 1):
```
Call set_summary with "Completed API authentication, now working on rate limiting"
```

From Terminal 2 (Boss A):
```
Call list_peers with scope="hierarchy"
```

The updated summary is immediately visible.

## Workflow Example: Daily Standup

### 9:00 AM - Super Boss initiates standup

Terminal 1:
```
Call broadcast_message with scope="subordinates", message="Daily standup starting! Please provide status updates."
```

### 9:05 AM - Bosses gather team status

Terminal 2 (Boss A):
```
Call broadcast_message with scope="subordinates", message="Team standup: please share what you're working on and any blockers"
```

Terminal 3 (Boss B):
```
Call broadcast_message with scope="subordinates", message="Team standup: please share what you're working on and any blockers"
```

### 9:10 AM - Workers respond

Terminal 4 (Worker 1):
```
Call send_message with to_id="<boss_a_id>", message="Completed auth service, now on rate limiting. No blockers."
```

Terminal 5 (Worker 2):
```
Call send_message with to_id="<boss_a_id>", message="DB optimization in progress. Waiting on performance metrics from ops."
```

Terminal 7 (Worker 4):
```
Call send_message with to_id="<boss_b_id>", message="React components 80% done. Need design review on new modal."
```

### 9:15 AM - Bosses report to Super Boss

Terminal 2 (Boss A):
```
Call send_message with to_id="<super_boss_id>", message="Backend team status: Auth complete, DB optimization in progress (waiting on metrics), docs on track. No critical blockers."
```

Terminal 3 (Boss B):
```
Call send_message with to_id="<super_boss_id>", message="Frontend team status: Components 80% done (need design review), styling on track. No blockers."
```

### 9:20 AM - Super Boss reviews

Terminal 1 (Super Boss):
```
Call get_hierarchy
```

See complete status of all teams.

## Cleanup

To stop all instances:

```bash
# Kill all Claude processes
pkill -f "claude --dangerously-load-development-channels"

# Kill broker
pkill -f "broker-hierarchical.ts"

# Optional: reset database
rm ~/.claude-peers.db
```

## Troubleshooting

### "Parent peer not found" error

Make sure you're using the correct parent_id. Run `list_peers` to get the current IDs.

### Messages not arriving

Check that the recipient is still running:
```
Call list_peers with scope="machine"
```

If the peer is missing, they may have crashed. Restart them.

### Hierarchy shows incorrectly

Verify parent_id assignments:
```
Call list_peers with scope="machine"
```

Check the "Reports to" field for each peer.

### Database locked error

The broker may be using the database. Wait a moment and retry, or restart the broker:
```bash
pkill -f "broker-hierarchical.ts"
```

The broker will auto-restart on the next message.
