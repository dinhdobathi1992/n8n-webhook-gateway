import { Link } from "react-router-dom";
import type { Route } from "../lib/api";
import CopyButton from "./CopyButton";

interface Props {
  routes: Route[];
  onDelete: (id: number) => void;
}

function truncate(str: string, max: number) {
  return str.length > max ? str.slice(0, max) + "..." : str;
}

export default function RouteTable({ routes, onDelete }: Props) {
  return (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Slug</th>
            <th style={styles.th}>Source</th>
            <th style={styles.th}>Destination</th>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Webhook URL</th>
            <th style={{ ...styles.th, textAlign: "right" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((r) => (
            <tr key={r.id} style={styles.tr}>
              <td style={styles.td}>
                <Link to={`/routes/${r.id}`} style={styles.slugLink}>
                  {r.slug}
                </Link>
              </td>
              <td style={styles.td}>
                <span style={styles.sourceBadge}>
                  {r.source_type === "gchat" ? "Google Chat" : r.source_type === "generic" ? "Generic" : "Slack"}
                </span>
              </td>
              <td style={styles.td}>
                <span style={styles.dest} title={r.destination_url}>
                  {truncate(r.destination_url, 50)}
                </span>
              </td>
              <td style={styles.td}>
                <span
                  style={{
                    ...styles.badge,
                    background: r.enabled ? "#e8f8ed" : "#f2f2f2",
                    color: r.enabled ? "#34c759" : "#86868b",
                  }}
                >
                  {r.enabled ? "Active" : "Disabled"}
                </span>
              </td>
              <td style={styles.td}>
                <div style={styles.urlCell}>
                  <code style={styles.urlCode}>
                    {truncate(r.webhook_url, 40)}
                  </code>
                  <CopyButton text={r.webhook_url} />
                </div>
              </td>
              <td style={{ ...styles.td, textAlign: "right" }}>
                <div style={styles.actionRow}>
                  <Link to={`/routes/${r.id}`} style={styles.actionLink}>
                    View
                  </Link>
                  <Link to={`/routes/${r.id}/edit`} style={styles.actionLink}>
                    Edit
                  </Link>
                  <button
                    onClick={() => onDelete(r.id)}
                    style={styles.deleteBtn}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  tableWrap: {
    overflowX: "auto",
    border: "1px solid #e0e0e0",
    borderRadius: 12,
    background: "#fff",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  th: {
    textAlign: "left",
    padding: "12px 16px",
    fontSize: 13,
    fontWeight: 500,
    color: "#86868b",
    textTransform: "uppercase" as const,
    letterSpacing: 0.5,
    borderBottom: "1px solid #e0e0e0",
    whiteSpace: "nowrap" as const,
  },
  tr: {
    borderBottom: "1px solid #f0f0f0",
  },
  td: {
    padding: "14px 16px",
    fontSize: 15,
    verticalAlign: "middle" as const,
  },
  slugLink: {
    color: "#0071e3",
    fontWeight: 500,
    textDecoration: "none",
  },
  sourceBadge: {
    fontSize: 13,
    fontWeight: 500,
    color: "#1d1d1f",
  },
  dest: {
    color: "#1d1d1f",
    fontSize: 14,
  },
  badge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 500,
  },
  urlCell: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  urlCode: {
    fontSize: 13,
    fontFamily: "ui-monospace, Consolas, monospace",
    color: "#1d1d1f",
    background: "#f5f5f7",
    padding: "2px 8px",
    borderRadius: 6,
  },
  actionRow: {
    display: "flex",
    gap: 12,
    justifyContent: "flex-end",
    alignItems: "center",
  },
  actionLink: {
    color: "#0071e3",
    fontSize: 14,
    textDecoration: "none",
  },
  deleteBtn: {
    background: "none",
    border: "none",
    color: "#ff3b30",
    fontSize: 14,
    padding: 0,
    cursor: "pointer",
  },
};
