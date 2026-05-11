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

  useEffect(() => {
    fetchRoutes();
  }, []);

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
    try {
      await api.logout();
    } catch {
      // ignore
    }
    onLogout();
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Webhook Gateway</h1>
        <div style={styles.actions}>
          <Link to="/routes/new" style={styles.createBtn}>
            Create Route
          </Link>
          <button onClick={handleLogout} style={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </header>

      <main style={styles.main}>
        {loading && <p style={styles.muted}>Loading...</p>}
        {error && <p style={styles.error}>{error}</p>}
        {!loading && !error && routes.length === 0 && (
          <p style={styles.muted}>
            No routes yet.{" "}
            <Link to="/routes/new">Create your first route</Link>.
          </p>
        )}
        {!loading && routes.length > 0 && (
          <RouteTable routes={routes} onDelete={handleDelete} />
        )}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "0 24px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "32px 0 24px",
    borderBottom: "1px solid #e0e0e0",
  },
  title: {
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif",
    fontSize: 28,
    fontWeight: 600,
    color: "#1d1d1f",
    margin: 0,
    letterSpacing: -0.5,
  },
  actions: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },
  createBtn: {
    padding: "8px 20px",
    background: "#0071e3",
    color: "#fff",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    textDecoration: "none",
    display: "inline-block",
  },
  logoutBtn: {
    padding: "8px 20px",
    background: "transparent",
    color: "#86868b",
    border: "1px solid #e0e0e0",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
  },
  main: {
    padding: "24px 0",
  },
  muted: {
    color: "#86868b",
    textAlign: "center" as const,
    padding: "40px 0",
  },
  error: {
    color: "#ff3b30",
    textAlign: "center" as const,
    padding: "40px 0",
  },
};
