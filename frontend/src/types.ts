export type CitationEntry = {
  citation: string;
  url?: string;
};

export type RunSummary = {
  id: string;
  query: string;
  goal?: string | null;
  status: string;
  plan?: string | null;
  final_report?: string | null;
  citations?: CitationEntry[];
};

export type EventMessage = {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
  agent_id?: string;
};
