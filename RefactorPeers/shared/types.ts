// Unique ID for each Claude Code instance (generated on registration)
export type PeerId = string;

// Hierarchy role types
export type PeerRole = "worker" | "boss" | "super_boss";

export interface Peer {
  id: PeerId;
  pid: number;
  cwd: string;
  git_root: string | null;
  tty: string | null;
  summary: string;
  registered_at: string; // ISO timestamp
  last_seen: string; // ISO timestamp
  role: PeerRole; // NEW: hierarchical role
  parent_id?: PeerId; // NEW: reference to parent boss (null for top-level)
  hierarchy_level: number; // NEW: 0 = super_boss, 1 = boss, 2+ = workers
}

export interface Message {
  id: number;
  from_id: PeerId;
  to_id: PeerId;
  text: string;
  sent_at: string; // ISO timestamp
  delivered: boolean;
  priority?: "normal" | "high"; // NEW: for hierarchical routing
}

// --- Broker API types ---

export interface RegisterRequest {
  pid: number;
  cwd: string;
  git_root: string | null;
  tty: string | null;
  summary: string;
  role: PeerRole; // NEW: specify role on registration
  parent_id?: PeerId; // NEW: parent boss ID if not top-level
}

export interface RegisterResponse {
  id: PeerId;
  hierarchy_level: number;
}

export interface HeartbeatRequest {
  id: PeerId;
}

export interface SetSummaryRequest {
  id: PeerId;
  summary: string;
}

export interface ListPeersRequest {
  scope: "machine" | "directory" | "repo" | "hierarchy"; // NEW: hierarchy scope
  // The requesting peer's context (used for filtering)
  cwd: string;
  git_root: string | null;
  exclude_id?: PeerId;
  role_filter?: PeerRole; // NEW: filter by role
  parent_id?: PeerId; // NEW: filter by parent (for hierarchy scope)
}

export interface SendMessageRequest {
  from_id: PeerId;
  to_id: PeerId;
  text: string;
  priority?: "normal" | "high"; // NEW: message priority
}

export interface PollMessagesRequest {
  id: PeerId;
}

export interface PollMessagesResponse {
  messages: Message[];
}

// NEW: Hierarchical query types
export interface GetHierarchyRequest {
  id: PeerId;
}

export interface HierarchyNode {
  peer: Peer;
  children: HierarchyNode[];
}

export interface GetHierarchyResponse {
  hierarchy: HierarchyNode;
}

export interface BroadcastMessageRequest {
  from_id: PeerId;
  text: string;
  scope: "subordinates" | "superiors" | "peers"; // NEW: broadcast scope
  priority?: "normal" | "high";
}
