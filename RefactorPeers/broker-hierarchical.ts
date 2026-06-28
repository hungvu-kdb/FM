#!/usr/bin/env bun
/**
 * claude-peers hierarchical broker daemon
 *
 * Extended version with support for hierarchical peer relationships:
 * - super_boss (level 0): top-level coordinator
 * - boss (level 1): middle management, reports to super_boss
 * - worker (level 2+): reports to boss
 *
 * A singleton HTTP server on localhost:7899 backed by SQLite.
 * Tracks all registered Claude Code peers with hierarchy and routes messages between them.
 *
 * Auto-launched by the MCP server if not already running.
 * Run directly: bun broker-hierarchical.ts
 */

import { Database } from "bun:sqlite";
import type {
  RegisterRequest,
  RegisterResponse,
  HeartbeatRequest,
  SetSummaryRequest,
  ListPeersRequest,
  SendMessageRequest,
  PollMessagesRequest,
  PollMessagesResponse,
  Peer,
  Message,
  GetHierarchyRequest,
  GetHierarchyResponse,
  HierarchyNode,
  BroadcastMessageRequest,
} from "./shared/types.ts";

const PORT = parseInt(process.env.CLAUDE_PEERS_PORT ?? "7899", 10);
const DB_PATH = process.env.CLAUDE_PEERS_DB ?? `${process.env.HOME}/.claude-peers.db`;

// --- Database setup ---

const db = new Database(DB_PATH);
db.run("PRAGMA journal_mode = WAL");
db.run("PRAGMA busy_timeout = 3000");

db.run(`
  CREATE TABLE IF NOT EXISTS peers (
    id TEXT PRIMARY KEY,
    pid INTEGER NOT NULL,
    cwd TEXT NOT NULL,
    git_root TEXT,
    tty TEXT,
    summary TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'worker',
    parent_id TEXT,
    hierarchy_level INTEGER NOT NULL DEFAULT 2,
    registered_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES peers(id)
  )
`);

db.run(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    text TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    sent_at TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (from_id) REFERENCES peers(id),
    FOREIGN KEY (to_id) REFERENCES peers(id)
  )
`);

// Create index for faster hierarchy queries
db.run(`CREATE INDEX IF NOT EXISTS idx_parent_id ON peers(parent_id)`);
db.run(`CREATE INDEX IF NOT EXISTS idx_role ON peers(role)`);
db.run(`CREATE INDEX IF NOT EXISTS idx_hierarchy_level ON peers(hierarchy_level)`);

// Clean up stale peers (PIDs that no longer exist) on startup
function cleanStalePeers() {
  const peers = db.query("SELECT id, pid FROM peers").all() as { id: string; pid: number }[];
  for (const peer of peers) {
    try {
      process.kill(peer.pid, 0);
    } catch {
      db.run("DELETE FROM peers WHERE id = ?", [peer.id]);
      db.run("DELETE FROM messages WHERE to_id = ? AND delivered = 0", [peer.id]);
    }
  }
}

cleanStalePeers();
setInterval(cleanStalePeers, 30_000);

// --- Prepared statements ---

const insertPeer = db.prepare(`
  INSERT INTO peers (id, pid, cwd, git_root, tty, summary, role, parent_id, hierarchy_level, registered_at, last_seen)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

const updateLastSeen = db.prepare(`
  UPDATE peers SET last_seen = ? WHERE id = ?
`);

const updateSummary = db.prepare(`
  UPDATE peers SET summary = ? WHERE id = ?
`);

const deletePeer = db.prepare(`
  DELETE FROM peers WHERE id = ?
`);

const selectAllPeers = db.prepare(`
  SELECT * FROM peers
`);

const selectPeersByDirectory = db.prepare(`
  SELECT * FROM peers WHERE cwd = ?
`);

const selectPeersByGitRoot = db.prepare(`
  SELECT * FROM peers WHERE git_root = ?
`);

const selectPeersByParent = db.prepare(`
  SELECT * FROM peers WHERE parent_id = ?
`);

const selectPeerById = db.prepare(`
  SELECT * FROM peers WHERE id = ?
`);

const insertMessage = db.prepare(`
  INSERT INTO messages (from_id, to_id, text, priority, sent_at, delivered)
  VALUES (?, ?, ?, ?, ?, 0)
`);

const selectUndelivered = db.prepare(`
  SELECT * FROM messages WHERE to_id = ? AND delivered = 0 ORDER BY priority DESC, sent_at ASC
`);

const markDelivered = db.prepare(`
  UPDATE messages SET delivered = 1 WHERE id = ?
`);

// --- Utility functions ---

function generateId(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let id = "";
  for (let i = 0; i < 8; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

function calculateHierarchyLevel(role: string, parentLevel?: number): number {
  if (role === "super_boss") return 0;
  if (role === "boss") return 1;
  if (parentLevel !== undefined) return parentLevel + 1;
  return 2; // default worker level
}

function buildHierarchyTree(peerId: string): HierarchyNode | null {
  const peer = selectPeerById.get(peerId) as Peer | null;
  if (!peer) return null;

  const children = (selectPeersByParent.all(peerId) as Peer[]).map((child) => {
    const childTree = buildHierarchyTree(child.id);
    return childTree!;
  });

  return { peer, children };
}

function getAllSubordinates(peerId: string): Peer[] {
  const subordinates: Peer[] = [];
  const directReports = selectPeersByParent.all(peerId) as Peer[];

  for (const report of directReports) {
    subordinates.push(report);
    subordinates.push(...getAllSubordinates(report.id));
  }

  return subordinates;
}

function getAllSuperiors(peerId: string): Peer[] {
  const superiors: Peer[] = [];
  const peer = selectPeerById.get(peerId) as Peer | null;

  if (peer && peer.parent_id) {
    const parent = selectPeerById.get(peer.parent_id) as Peer | null;
    if (parent) {
      superiors.push(parent);
      superiors.push(...getAllSuperiors(parent.id));
    }
  }

  return superiors;
}

// --- Request handlers ---

function handleRegister(body: RegisterRequest): RegisterResponse {
  const id = generateId();
  const now = new Date().toISOString();

  // Validate parent exists if specified
  if (body.parent_id) {
    const parent = selectPeerById.get(body.parent_id) as Peer | null;
    if (!parent) {
      throw new Error(`Parent peer ${body.parent_id} not found`);
    }
  }

  // Remove any existing registration for this PID
  const existing = db.query("SELECT id FROM peers WHERE pid = ?").get(body.pid) as { id: string } | null;
  if (existing) {
    deletePeer.run(existing.id);
  }

  const hierarchyLevel = calculateHierarchyLevel(body.role, body.parent_id ? 1 : undefined);

  insertPeer.run(
    id,
    body.pid,
    body.cwd,
    body.git_root,
    body.tty,
    body.summary,
    body.role,
    body.parent_id || null,
    hierarchyLevel,
    now,
    now
  );

  return { id, hierarchy_level: hierarchyLevel };
}

function handleHeartbeat(body: HeartbeatRequest): void {
  updateLastSeen.run(new Date().toISOString(), body.id);
}

function handleSetSummary(body: SetSummaryRequest): void {
  updateSummary.run(body.summary, body.id);
}

function handleListPeers(body: ListPeersRequest): Peer[] {
  let peers: Peer[];

  switch (body.scope) {
    case "machine":
      peers = selectAllPeers.all() as Peer[];
      break;
    case "directory":
      peers = selectPeersByDirectory.all(body.cwd) as Peer[];
      break;
    case "repo":
      if (body.git_root) {
        peers = selectPeersByGitRoot.all(body.git_root) as Peer[];
      } else {
        peers = selectPeersByDirectory.all(body.cwd) as Peer[];
      }
      break;
    case "hierarchy":
      // Return direct reports if parent_id specified, otherwise all at same level
      if (body.parent_id) {
        peers = selectPeersByParent.all(body.parent_id) as Peer[];
      } else {
        peers = selectAllPeers.all() as Peer[];
      }
      break;
    default:
      peers = selectAllPeers.all() as Peer[];
  }

  // Apply role filter if specified
  if (body.role_filter) {
    peers = peers.filter((p) => p.role === body.role_filter);
  }

  // Exclude the requesting peer
  if (body.exclude_id) {
    peers = peers.filter((p) => p.id !== body.exclude_id);
  }

  // Verify each peer's process is still alive
  return peers.filter((p) => {
    try {
      process.kill(p.pid, 0);
      return true;
    } catch {
      deletePeer.run(p.id);
      return false;
    }
  });
}

function handleSendMessage(body: SendMessageRequest): { ok: boolean; error?: string } {
  const target = selectPeerById.get(body.to_id) as Peer | null;
  if (!target) {
    return { ok: false, error: `Peer ${body.to_id} not found` };
  }

  insertMessage.run(
    body.from_id,
    body.to_id,
    body.text,
    body.priority || "normal",
    new Date().toISOString()
  );
  return { ok: true };
}

function handlePollMessages(body: PollMessagesRequest): PollMessagesResponse {
  const messages = selectUndelivered.all(body.id) as Message[];

  for (const msg of messages) {
    markDelivered.run(msg.id);
  }

  return { messages };
}

function handleGetHierarchy(body: GetHierarchyRequest): GetHierarchyResponse {
  const peer = selectPeerById.get(body.id) as Peer | null;
  if (!peer) {
    throw new Error(`Peer ${body.id} not found`);
  }

  // Find the root of the hierarchy
  let root = peer;
  while (root.parent_id) {
    const parent = selectPeerById.get(root.parent_id) as Peer | null;
    if (!parent) break;
    root = parent;
  }

  const hierarchy = buildHierarchyTree(root.id);
  if (!hierarchy) {
    throw new Error("Failed to build hierarchy tree");
  }

  return { hierarchy };
}

function handleBroadcastMessage(body: BroadcastMessageRequest): { ok: boolean; count: number } {
  const sender = selectPeerById.get(body.from_id) as Peer | null;
  if (!sender) {
    throw new Error(`Sender ${body.from_id} not found`);
  }

  let recipients: Peer[] = [];

  switch (body.scope) {
    case "subordinates":
      recipients = getAllSubordinates(body.from_id);
      break;
    case "superiors":
      recipients = getAllSuperiors(body.from_id);
      break;
    case "peers":
      // Same hierarchy level and same parent
      recipients = (selectPeersByParent.all(sender.parent_id || "") as Peer[]).filter(
        (p) => p.id !== body.from_id
      );
      break;
  }

  const now = new Date().toISOString();
  for (const recipient of recipients) {
    insertMessage.run(
      body.from_id,
      recipient.id,
      body.text,
      body.priority || "normal",
      now
    );
  }

  return { ok: true, count: recipients.length };
}

function handleUnregister(body: { id: string }): void {
  deletePeer.run(body.id);
}

// --- HTTP Server ---

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  async fetch(req) {
    const url = new URL(req.url);
    const path = url.pathname;

    if (req.method !== "POST") {
      if (path === "/health") {
        return Response.json({ status: "ok", peers: (selectAllPeers.all() as Peer[]).length });
      }
      return new Response("claude-peers hierarchical broker", { status: 200 });
    }

    try {
      const body = await req.json();

      switch (path) {
        case "/register":
          return Response.json(handleRegister(body as RegisterRequest));
        case "/heartbeat":
          handleHeartbeat(body as HeartbeatRequest);
          return Response.json({ ok: true });
        case "/set-summary":
          handleSetSummary(body as SetSummaryRequest);
          return Response.json({ ok: true });
        case "/list-peers":
          return Response.json(handleListPeers(body as ListPeersRequest));
        case "/send-message":
          return Response.json(handleSendMessage(body as SendMessageRequest));
        case "/poll-messages":
          return Response.json(handlePollMessages(body as PollMessagesRequest));
        case "/get-hierarchy":
          return Response.json(handleGetHierarchy(body as GetHierarchyRequest));
        case "/broadcast-message":
          return Response.json(handleBroadcastMessage(body as BroadcastMessageRequest));
        case "/unregister":
          handleUnregister(body as { id: string });
          return Response.json({ ok: true });
        default:
          return Response.json({ error: "not found" }, { status: 404 });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      return Response.json({ error: msg }, { status: 500 });
    }
  },
});

console.error(`[claude-peers hierarchical broker] listening on 127.0.0.1:${PORT} (db: ${DB_PATH})`);
