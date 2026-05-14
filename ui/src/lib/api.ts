const BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    let msg = `HTTP ${resp.status}`;
    if (typeof body.detail === "string") {
      msg = body.detail;
    } else if (Array.isArray(body.detail)) {
      msg = body.detail.map((e: { loc?: string[]; msg?: string }) =>
        `${(e.loc || []).slice(-1).join(".")}: ${e.msg || "invalid"}`
      ).join(", ");
    }
    throw new Error(msg);
  }
  return resp.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ ok: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  listRoutes: () => request<Route[]>("/api/webhooks"),
  getRoute: (id: number) => request<Route>(`/api/webhooks/${id}`),
  createRoute: (data: RouteCreate) =>
    request<Route>("/api/webhooks", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateRoute: (id: number, data: Partial<RouteCreate>) =>
    request<Route>(`/api/webhooks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteRoute: (id: number) =>
    request<{ ok: boolean }>(`/api/webhooks/${id}`, { method: "DELETE" }),
  getDeliveries: (id: number, limit = 50, offset = 0) =>
    request<Delivery[]>(
      `/api/webhooks/${id}/deliveries?limit=${limit}&offset=${offset}`
    ),
};

export interface Route {
  id: number;
  slug: string;
  destination_url: string;
  enabled: boolean;
  source_type: string;
  signing_secret_set: boolean;
  auth_header_set: boolean;
  auth_header_name: string | null;
  secret_header_name: string | null;
  description: string | null;
  webhook_url: string;
  created_at: string;
}

export interface RouteCreate {
  slug: string;
  destination_url: string;
  source_type?: string;
  signing_secret?: string;
  secret_header_name?: string;
  auth_header_name?: string;
  auth_header_value?: string;
  description?: string;
}

export interface Delivery {
  id: number;
  route_id: number;
  source_event_id: string | null;
  method: string;
  status: string;
  attempt_count: number;
  response_status: number | null;
  response_body_excerpt: string | null;
  error: string | null;
  latency_ms: number | null;
  created_at: string;
}
