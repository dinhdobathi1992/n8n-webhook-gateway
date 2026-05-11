import type { Delivery } from "../lib/api";

interface Props {
  deliveries: Delivery[];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function DeliveryLog({ deliveries }: Props) {
  return (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Time</th>
            <th style={styles.th}>Method</th>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Response</th>
            <th style={styles.th}>Latency</th>
          </tr>
        </thead>
        <tbody>
          {deliveries.map((d) => (
            <tr key={d.id} style={styles.tr}>
              <td style={styles.td}>{formatDate(d.created_at)}</td>
              <td style={styles.td}>
                <code style={styles.method}>{d.method}</code>
              </td>
              <td style={styles.td}>
                <span
                  style={{
                    ...styles.badge,
                    background:
                      d.status === "success" ? "#e8f8ed" : "#fff2f2",
                    color:
                      d.status === "success" ? "#34c759" : "#ff3b30",
                  }}
                >
                  {d.status}
                </span>
              </td>
              <td style={styles.td}>
                {d.response_status != null ? d.response_status : "-"}
              </td>
              <td style={styles.td}>
                {d.latency_ms != null ? `${d.latency_ms}ms` : "-"}
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
    padding: "10px 16px",
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
    padding: "10px 16px",
    fontSize: 14,
    verticalAlign: "middle" as const,
  },
  method: {
    fontSize: 13,
    fontFamily: "ui-monospace, Consolas, monospace",
    background: "#f5f5f7",
    padding: "2px 6px",
    borderRadius: 4,
  },
  badge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 500,
  },
};
