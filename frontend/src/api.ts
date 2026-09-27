export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const form = data instanceof FormData;
  const r = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "X-Requested-With": "swm",
      ...(!form && data ? { "Content-Type": "application/json" } : {}),
    },
    body: data ? (form ? data : JSON.stringify(data)) : undefined,
  });
  if (!r.ok) {
    const payload = await r
      .json()
      .catch(() => ({ detail: "Service unavailable. Please try again." }));
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : payload.detail?.map((x: { msg: string }) => x.msg).join("; ") ||
            "Request failed",
    );
  }
  return r.json();
}
export type User = {
  id: number;
  name: string;
  email: string;
  role: string;
  ward_id: number | null;
  active: boolean;
  available: boolean;
};
export type Complaint = {
  id: number;
  reference: string;
  description: string;
  address: string;
  status: string;
  priority: string;
  waste_stream: string;
  ward_id: number;
  category_id: number;
  collector_id: number | null;
  latitude: number;
  longitude: number;
  created_at: string;
  deadline: string;
  resolved_at: string | null;
  closed_at: string | null;
  overdue: boolean;
  version: number;
  cycle: number;
  reopen_count: number;
  possible_duplicates?: number;
  history?: { status: string; reason: string; created_at: string }[];
  evidence?: { id: number; stage: string; cycle: number; sha256: string }[];
  assignments?: { collector_id: number; reason: string; created_at: string }[];
};
export type Config = {
  demo?: boolean;
  wards: { id: number; name: string; zone: string }[];
  categories: { id: number; name: string }[];
  sla: { priority: string; hours: number }[];
};
export type Notice = {
  id: number;
  complaint_id: number;
  message: string;
  read: boolean;
  created_at: string;
};
export type Analytics = {
  total: number;
  open: number;
  closed: number;
  overdue: number;
  approaching: number;
  reopened: number;
  escalated: number;
  sla_compliance: number | null;
  average_resolution_hours: number | null;
  median_resolution_hours: number | null;
  status: Record<string, number>;
  wards: Record<string, number>;
  categories: Record<string, number>;
  streams: Record<string, number>;
  priorities: Record<string, number>;
  trend: Record<string, number>;
  hotspots: {
    latitude: number;
    longitude: number;
    count: number;
    open: number;
  }[];
  collectors: { collector_id: number; assigned: number; resolved: number }[];
};
