import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Route } from "../lib/api";
import RouteTable from "../components/RouteTable";

interface Props {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: Props) {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchRoutes() {
    try {
      const data = await api.listRoutes();
      setRoutes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load routes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchRoutes(); }, []);

  async function handleDelete(id: number) {
    if (!confirm("Disable this route?")) return;
    try {
      await api.deleteRoute(id);
      await fetchRoutes();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function handleLogout() {
    try { await api.logout(); } catch { /* ignore */ }
    onLogout();
  }

  const activeCount = routes.filter((r) => r.enabled).length;

  return (
    <div className="min-h-screen">
      <nav className="accent-bar border-b border-border bg-bg">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img src="/logo.svg" alt="" aria-hidden="true" className="h-8 w-8 shrink-0" />
            <span className="text-accent font-bold text-sm sm:text-base tracking-tight">
              <span className="hidden sm:inline">n8n Webhook Gateway</span>
              <span className="sm:hidden">n8n Gateway</span>
            </span>
          </div>
          <div className="flex gap-2 items-center">
            <Link
              to="/routes/new"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent-hover text-accent-text rounded-md text-[13px] font-semibold no-underline transition-colors"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              New Route
            </Link>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-surface-elevated text-text-secondary border border-border-hover hover:bg-surface-hover hover:text-text-primary rounded-md text-[13px] font-medium transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8">
        {!loading && !error && routes.length > 0 && (
          <div className="flex items-center gap-4 pt-5 pb-3 animate-fade-in text-[13px] text-text-muted">
            <span><span className="text-text-primary font-semibold">{routes.length}</span> routes</span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />
              <span className="text-text-primary font-semibold">{activeCount}</span> active
            </span>
          </div>
        )}

        <main className="py-4 animate-fade-in">
          {loading && (
            <div className="flex flex-col items-center py-24 gap-3">
              <div className="w-5 h-5 border-2 border-border border-t-accent rounded-full animate-spin" />
              <p className="text-text-muted text-[13px]">Loading routes...</p>
            </div>
          )}
          {error && <p className="text-error text-[13px] text-center py-24">{error}</p>}
          {!loading && !error && routes.length === 0 && (
            <div className="flex flex-col items-center py-24 gap-4 text-center">
              <p className="text-text-secondary text-sm font-medium">No routes yet</p>
              <p className="text-text-muted text-[13px]">Create your first webhook route to get started.</p>
              <Link
                to="/routes/new"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-accent hover:bg-accent-hover text-accent-text rounded-md text-[13px] font-semibold no-underline transition-colors mt-1"
              >
                Create Route
              </Link>
            </div>
          )}
          {!loading && routes.length > 0 && (
            <RouteTable routes={routes} onDelete={handleDelete} />
          )}
        </main>
      </div>
    </div>
  );
}
