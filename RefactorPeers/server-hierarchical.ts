#!/usr/bin/env bun
/**
 * claude-peers hierarchical MCP server
 *
 * Extended version with support for hierarchical peer relationships.
 * Spawned by Claude Code as a stdio MCP server (one per instance).
 * Connects to the shared broker daemon for peer discovery and messaging.
 *
 * Usage:
 *   claude --dangerously-load-development-channels server:claude-peers-hierarchical
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import type {
  PeerId,
  Peer,
  PeerRole,
  RegisterResponse,
  PollMessagesResponse,
  Message,
  GetHierarchyResponse,
  HierarchyNode,
} from "./shared/types.ts";

// --- Configuration ---

const BROKER_PORT = parseInt(process.env.CLAUDE_PEERS_PORT ?? "7899", 10);
const BROKER_URL = `http://127.0.0.1:${BROKER_PORT}`;
const POLL_INTERVAL_MS = 1000;
const HEARTBEAT_INTERVAL_MS = 15_000;
const BROKER_SCRIPT = new URL("./broker-hierarchical.ts", import.meta.url).pathname;

// --- Broker communication ---

async function brokerFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BROKER_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Broker error (${path}): ${res.status} ${err}`);
  }
  return res.json() as Promise<T>;
}

async function isBrokerAlive(): Promise<boolean> {
  try {
    const res = await fetch(`${BROKER_URL}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureBroker(): Promise<void> {
  if (await isBrokerAlive()) {
    log("Broker already running");
    return;
  }

  log("Starting hierarchical broker daemon...");
  const proc = Bun.spawn(["bun", BROKER_SCRIPT], {
    stdio: ["ignore", "ignore", "inherit"],
  });

  proc.unref();

  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 200));
    if (await isBrokerAlive()) {
      log("Broker started");
      return;
    }
  }
  throw new Error("Failed to start broker daemon after 6 seconds");
}

// --- Utility ---

function log(msg: string) {
  console.error(`[claude-peers-hierarchical] ${msg}`);
}

async function getGitRoot(cwd: string): Promise<string | null> {
  try {
    const proc = Bun.spawn(["git", "rev-parse", "--show-toplevel"], {
      cwd,
      stdout: "pipe",
      stderr: "ignore",
    });
    const text = await new Response(proc.stdout).text();
    const code = await proc.exited;
    if (code === 0) {
      return text.trim();
    }
  } catch {
    // not a git repo
  }
  return null;
}

function getTty(): string | null {
  try {
    const ppid = process.ppid;
    if (ppid) {
      const proc = Bun.spawnSync(["ps", "-o", "tty=", "-p", String(ppid)]);
      const tty = new TextDecoder().decode(proc.stdout).trim();
      if (tty && tty !== "?" && tty !== "??") {
        return tty;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

// --- State ---

let myId: PeerId | null = null;
let myRole: PeerRole = "worker";
let myParentId: PeerId | undefined;
let myCwd = process.cwd();
let myGitRoot: string | null = null;

// --- MCP Server ---

const mcp = new Server(
  { name: "claude-peers-hierarchical", version: "0.1.0" },
  {
    capabilities: {
      experimental: { "claude/channel": {} },
      tools: {},
    },
    instructions: `You are connected to the claude-peers hierarchical network. You have a role in the organization:
- super_boss: Top-level coordinator
- boss: Middle management
- worker: Individual contributor

When you receive a <channel source="claude-peers" ...> message, RESPOND IMMEDIATELY. Pause what you are doing, reply using send_message, then resume.

Available tools:
- list_peers: Discover other Claude Code instances (with hierarchy support)
- send_message: Send a message to another instance by ID
- broadcast_message: Send a message to all subordinates, superiors, or peers
- set_summary: Set a summary of what you're working on
- get_hierarchy: View the organizational hierarchy
- check_messages: Manually check for new messages

When you start, call set_role to establish your position in the hierarchy, then set_summary to describe your work.`,
  }
);

// --- Tool definitions ---

const TOOLS = [
  {
    name: "set_role",
    description:
      "Set your role in the hierarchical organization. Must be called during initialization.",
    inputSchema: {
      type: "object" as const,
      properties: {
        role: {
          type: "string" as const,
          enum: ["super_boss", "boss", "worker"],
          description: "Your role in the hierarchy",
        },
        parent_id: {
          type: "string" as const,
          description:
            "The peer ID of your boss (required for boss and worker roles, leave empty for super_boss)",
        },
      },
      required: ["role"],
    },
  },
  {
    name: "list_peers",
    description:
      "List other Claude Code instances. Can filter by scope, role, or hierarchy.",
    inputSchema: {
      type: "object" as const,
      properties: {
        scope: {
          type: "string" as const,
          enum: ["machine", "directory", "repo", "hierarchy"],
          description:
            'Scope of discovery. "hierarchy" shows your direct reports if you\'re a boss.',
        },
        role_filter: {
          type: "string" as const,
          enum: ["super_boss", "boss", "worker"],
          description: "Filter results by role",
        },
      },
      required: ["scope"],
    },
  },
  {
    name: "send_message",
    description: "Send a message to another Claude Code instance by peer ID.",
    inputSchema: {
      type: "object" as const,
      properties: {
        to_id: {
          type: "string" as const,
          description: "The peer ID of the target",
        },
        message: {
          type: "string" as const,
          description: "The message to send",
        },
        priority: {
          type: "string" as const,
          enum: ["normal", "high"],
          description: "Message priority (high priority messages are delivered first)",
        },
      },
      required: ["to_id", "message"],
    },
  },
  {
    name: "broadcast_message",
    description:
      "Send a message to all subordinates, superiors, or peers at your level.",
    inputSchema: {
      type: "object" as const,
      properties: {
        scope: {
          type: "string" as const,
          enum: ["subordinates", "superiors", "peers"],
          description:
            "Who to send to: subordinates (your reports), superiors (your chain of command), or peers (same level)",
        },
        message: {
          type: "string" as const,
          description: "The message to broadcast",
        },
        priority: {
          type: "string" as const,
          enum: ["normal", "high"],
          description: "Message priority",
        },
      },
      required: ["scope", "message"],
    },
  },
  {
    name: "get_hierarchy",
    description: "View the complete organizational hierarchy starting from the top.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
  {
    name: "set_summary",
    description: "Set a brief summary of what you are currently working on.",
    inputSchema: {
      type: "object" as const,
      properties: {
        summary: {
          type: "string" as const,
          description: "A 1-2 sentence summary of your current work",
        },
      },
      required: ["summary"],
    },
  },
  {
    name: "check_messages",
    description: "Manually check for new messages from other peers.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
];

// --- Tool handlers ---

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;

  switch (name) {
    case "set_role": {
      const { role, parent_id } = args as { role: PeerRole; parent_id?: string };

      if (role !== "super_boss" && !parent_id) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error: parent_id is required for ${role} role`,
            },
          ],
          isError: true,
        };
      }

      myRole = role;
      myParentId = parent_id;

      if (!myId) {
        return {
          content: [
            {
              type: "text" as const,
              text: "Not registered with broker yet",
            },
          ],
          isError: true,
        };
      }

      // Re-register with new role
      try {
        const result = await brokerFetch<RegisterResponse>("/register", {
          pid: process.pid,
          cwd: myCwd,
          git_root: myGitRoot,
          tty: getTty(),
          summary: "",
          role,
          parent_id,
        });

        myId = result.id;
        log(`Role set to ${role} (hierarchy level: ${result.hierarchy_level})`);

        return {
          content: [
            {
              type: "text" as const,
              text: `Role set to ${role} at hierarchy level ${result.hierarchy_level}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error setting role: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "list_peers": {
      const { scope, role_filter } = args as { scope: string; role_filter?: PeerRole };
      try {
        const peers = await brokerFetch<Peer[]>("/list-peers", {
          scope,
          cwd: myCwd,
          git_root: myGitRoot,
          exclude_id: myId,
          role_filter,
          parent_id: myId, // For hierarchy scope
        });

        if (peers.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `No peers found (scope: ${scope}${role_filter ? `, role: ${role_filter}` : ""}).`,
              },
            ],
          };
        }

        const lines = peers.map((p) => {
          const parts = [
            `ID: ${p.id}`,
            `Role: ${p.role}`,
            `Level: ${p.hierarchy_level}`,
            `CWD: ${p.cwd}`,
          ];
          if (p.parent_id) parts.push(`Reports to: ${p.parent_id}`);
          if (p.git_root) parts.push(`Repo: ${p.git_root}`);
          if (p.summary) parts.push(`Summary: ${p.summary}`);
          return parts.join("\n  ");
        });

        return {
          content: [
            {
              type: "text" as const,
              text: `Found ${peers.length} peer(s):\n\n${lines.join("\n\n")}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error listing peers: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "send_message": {
      const { to_id, message, priority } = args as {
        to_id: string;
        message: string;
        priority?: "normal" | "high";
      };
      if (!myId) {
        return {
          content: [{ type: "text" as const, text: "Not registered with broker yet" }],
          isError: true,
        };
      }
      try {
        const result = await brokerFetch<{ ok: boolean; error?: string }>("/send-message", {
          from_id: myId,
          to_id,
          text: message,
          priority,
        });
        if (!result.ok) {
          return {
            content: [{ type: "text" as const, text: `Failed to send: ${result.error}` }],
            isError: true,
          };
        }
        return {
          content: [
            {
              type: "text" as const,
              text: `Message sent to peer ${to_id}${priority === "high" ? " (high priority)" : ""}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error sending message: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "broadcast_message": {
      const { scope, message, priority } = args as {
        scope: "subordinates" | "superiors" | "peers";
        message: string;
        priority?: "normal" | "high";
      };
      if (!myId) {
        return {
          content: [{ type: "text" as const, text: "Not registered with broker yet" }],
          isError: true,
        };
      }
      try {
        const result = await brokerFetch<{ ok: boolean; count: number }>("/broadcast-message", {
          from_id: myId,
          text: message,
          scope,
          priority,
        });
        return {
          content: [
            {
              type: "text" as const,
              text: `Broadcast to ${result.count} ${scope}${priority === "high" ? " (high priority)" : ""}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error broadcasting: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "get_hierarchy": {
      if (!myId) {
        return {
          content: [{ type: "text" as const, text: "Not registered with broker yet" }],
          isError: true,
        };
      }
      try {
        const result = await brokerFetch<GetHierarchyResponse>("/get-hierarchy", { id: myId });

        function formatNode(node: HierarchyNode, indent = 0): string {
          const prefix = "  ".repeat(indent);
          const lines = [
            `${prefix}${node.peer.role.toUpperCase()} (${node.peer.id}): ${node.peer.summary || "(no summary)"}`,
          ];
          for (const child of node.children) {
            lines.push(formatNode(child, indent + 1));
          }
          return lines.join("\n");
        }

        return {
          content: [
            {
              type: "text" as const,
              text: `Organizational Hierarchy:\n\n${formatNode(result.hierarchy)}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error fetching hierarchy: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "set_summary": {
      const { summary } = args as { summary: string };
      if (!myId) {
        return {
          content: [{ type: "text" as const, text: "Not registered with broker yet" }],
          isError: true,
        };
      }
      try {
        await brokerFetch("/set-summary", { id: myId, summary });
        return {
          content: [{ type: "text" as const, text: `Summary updated: "${summary}"` }],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error setting summary: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    case "check_messages": {
      if (!myId) {
        return {
          content: [{ type: "text" as const, text: "Not registered with broker yet" }],
          isError: true,
        };
      }
      try {
        const result = await brokerFetch<PollMessagesResponse>("/poll-messages", { id: myId });
        if (result.messages.length === 0) {
          return {
            content: [{ type: "text" as const, text: "No new messages." }],
          };
        }
        const lines = result.messages.map(
          (m) => `From ${m.from_id} (${m.priority || "normal"} priority, ${m.sent_at}):\n${m.text}`
        );
        return {
          content: [
            {
              type: "text" as const,
              text: `${result.messages.length} new message(s):\n\n${lines.join("\n\n---\n\n")}`,
            },
          ],
        };
      } catch (e) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error checking messages: ${e instanceof Error ? e.message : String(e)}`,
            },
          ],
          isError: true,
        };
      }
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// --- Polling loop for inbound messages ---

async function pollAndPushMessages() {
  if (!myId) return;

  try {
    const result = await brokerFetch<PollMessagesResponse>("/poll-messages", { id: myId });

    for (const msg of result.messages) {
      let fromSummary = "";
      let fromCwd = "";
      let fromRole = "";
      try {
        const peers = await brokerFetch<Peer[]>("/list-peers", {
          scope: "machine",
          cwd: myCwd,
          git_root: myGitRoot,
        });
        const sender = peers.find((p) => p.id === msg.from_id);
        if (sender) {
          fromSummary = sender.summary;
          fromCwd = sender.cwd;
          fromRole = sender.role;
        }
      } catch {
        // Non-critical
      }

      await mcp.notification({
        method: "notifications/claude/channel",
        params: {
          content: msg.text,
          meta: {
            from_id: msg.from_id,
            from_role: fromRole,
            from_summary: fromSummary,
            from_cwd: fromCwd,
            priority: msg.priority || "normal",
            sent_at: msg.sent_at,
          },
        },
      });

      log(
        `Pushed message from ${msg.from_id} (${fromRole}): ${msg.text.slice(0, 80)}`
      );
    }
  } catch (e) {
    log(`Poll error: ${e instanceof Error ? e.message : String(e)}`);
  }
}

// --- Startup ---

async function main() {
  await ensureBroker();

  myCwd = process.cwd();
  myGitRoot = await getGitRoot(myCwd);
  const tty = getTty();

  log(`CWD: ${myCwd}`);
  log(`Git root: ${myGitRoot ?? "(none)"}`);
  log(`TTY: ${tty ?? "(unknown)"}`);

  // Register as worker by default (can be changed with set_role)
  const reg = await brokerFetch<RegisterResponse>("/register", {
    pid: process.pid,
    cwd: myCwd,
    git_root: myGitRoot,
    tty,
    summary: "",
    role: "worker",
  });
  myId = reg.id;
  log(`Registered as peer ${myId} (hierarchy level: ${reg.hierarchy_level})`);

  await mcp.connect(new StdioServerTransport());
  log("MCP connected");

  const pollTimer = setInterval(pollAndPushMessages, POLL_INTERVAL_MS);

  const heartbeatTimer = setInterval(async () => {
    if (myId) {
      try {
        await brokerFetch("/heartbeat", { id: myId });
      } catch {
        // Non-critical
      }
    }
  }, HEARTBEAT_INTERVAL_MS);

  const cleanup = async () => {
    clearInterval(pollTimer);
    clearInterval(heartbeatTimer);
    if (myId) {
      try {
        await brokerFetch("/unregister", { id: myId });
        log("Unregistered from broker");
      } catch {
        // Best effort
      }
    }
    process.exit(0);
  };

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
}

main().catch((e) => {
  log(`Fatal: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});
