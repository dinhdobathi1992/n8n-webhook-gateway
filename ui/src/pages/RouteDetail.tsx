import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Delivery, Route } from "../lib/api";
import CopyButton from "../components/CopyButton";
import DeliveryLog from "../components/DeliveryLog";
import TestPanel from "../components/TestPanel";

export default function RouteDetail() {
  const { id } = useParams<{ id: string }>();
  const [route, setRoute] = useState<Route | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    const routeId = Number(id);
    api
      .getRoute(routeId)
      .then(setRoute)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load route")
      );
    api
      .getDeliveries(routeId)
      .then(setDeliveries)
      .catch(() => {});
  }, [id]);

  function refreshDeliveries() {
    if (!id) return;
    api.getDeliveries(Number(id)).then(setDeliveries).catch(() => {});
  }

  if (error) {
    return (
      <div style={styles.page}>
        <p style={styles.error}>{error}</p>
        <Link to="/">Back to Dashboard</Link>
      </div>
    );
  }

  if (!route) {
    return (
      <div style={styles.page}>
        <p style={styles.muted}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.headerRow}>
        <Link to="/" style={styles.backLink}>
          &larr; Dashboard
        </Link>
        <Link to={`/routes/${route.id}/edit`} style={styles.editLink}>
          Edit
        </Link>
      </div>

      <div style={styles.infoCard}>
        <h1 style={styles.title}>{route.slug}</h1>

        <div style={styles.grid}>
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Destination</span>
            <span style={styles.fieldValue}>{route.destination_url}</span>
          </div>
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Status</span>
            <span
              style={{
                ...styles.badge,
                background: route.enabled ? "#e8f8ed" : "#f2f2f2",
                color: route.enabled ? "#34c759" : "#86868b",
              }}
            >
              {route.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Source</span>
            <span
              style={{
                ...styles.badge,
                background: "#e8f4fd",
                color: "#0071e3",
              }}
            >
              {route.source_type.toUpperCase()}
            </span>
          </div>
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Signing Secret</span>
            <span style={styles.fieldValue}>
              {route.signing_secret_set ? "Configured" : "Not set"}
            </span>
          </div>
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Created</span>
            <span style={styles.fieldValue}>
              {new Date(route.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        <div style={styles.webhookRow}>
          <span style={styles.fieldLabel}>Webhook URL</span>
          <div style={styles.urlRow}>
            <code style={styles.codeUrl}>{route.webhook_url}</code>
            <CopyButton text={route.webhook_url} />
          </div>
        </div>

        {route.description && (
          <div style={styles.field}>
            <span style={styles.fieldLabel}>Description</span>
            <span style={styles.fieldValue}>{route.description}</span>
          </div>
        )}
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Test Webhook</h2>
        <TestPanel webhookUrl={route.webhook_url} onSent={refreshDeliveries} />
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Delivery Log</h2>
        {deliveries.length === 0 ? (
          <p style={styles.muted}>No deliveries yet.</p>
        ) : (
          <DeliveryLog deliveries={deliveries} />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "24px",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  backLink: {
    color: "#0071e3",
    fontSize: 15,
    textDecoration: "none",
  },
  editLink: {
    color: "#0071e3",
    fontSize: 15,
    textDecoration: "none",
  },
  infoCard: {
    background: "#fff",
    borderRadius: 16,
    padding: "28px 32px",
    border: "1px solid #e0e0e0",
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  title: {
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif",
    fontSize: 24,
    fontWeight: 600,
    color: "#1d1d1f",
    margin: 0,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 16,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: "#86868b",
    textTransform: "uppercase" as const,
    letterSpacing: 0.5,
  },
  fieldValue: {
    fontSize: 15,
    color: "#1d1d1f",
    wordBreak: "break-all" as const,
  },
  badge: {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 500,
    width: "fit-content",
  },
  webhookRow: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  urlRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  codeUrl: {
    background: "#f5f5f7",
    padding: "8px 12px",
    borderRadius: 8,
    fontSize: 14,
    fontFamily: "ui-monospace, Consolas, monospace",
    flex: 1,
    wordBreak: "break-all" as const,
  },
  section: {
    marginTop: 32,
  },
  sectionTitle: {
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif",
    fontSize: 20,
    fontWeight: 600,
    color: "#1d1d1f",
    marginBottom: 16,
  },
  muted: {
    color: "#86868b",
    textAlign: "center" as const,
    padding: "24px 0",
  },
  error: {
    color: "#ff3b30",
    textAlign: "center" as const,
    padding: "40px 0",
  },
};
