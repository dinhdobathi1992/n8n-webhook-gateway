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
    <>
      {/* Desktop table */}
      <div className="hidden sm:block overflow-x-auto border border-border rounded-xl bg-surface">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-surface-elevated/50">
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Time</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Method</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Status</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Response</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Latency</th>
            </tr>
          </thead>
          <tbody>
            {deliveries.map((d) => (
              <tr key={d.id} className="border-b border-border/40 last:border-b-0 hover:bg-surface-elevated/60 transition-colors duration-150">
                <td className="px-5 py-3 text-[13px] text-text-secondary align-middle whitespace-nowrap">
                  {formatDate(d.created_at)}
                </td>
                <td className="px-5 py-3 text-sm align-middle">
                  <code className="text-[11px] font-mono bg-bg/60 text-text-muted px-2 py-0.5 rounded-md border border-border/50">
                    {d.method}
                  </code>
                </td>
                <td className="px-5 py-3 text-sm align-middle">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${
                    d.status === "success"
                      ? "bg-success/8 text-success border-success/20"
                      : "bg-error/8 text-error border-error/20"
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${d.status === "success" ? "bg-success" : "bg-error"}`} />
                    {d.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-[13px] text-text-secondary align-middle font-mono">
                  {d.response_status != null ? d.response_status : "—"}
                </td>
                <td className="px-5 py-3 text-[13px] text-text-secondary align-middle font-mono">
                  {d.latency_ms != null ? `${d.latency_ms}ms` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile card view */}
      <div className="sm:hidden flex flex-col gap-2">
        {deliveries.map((d) => (
          <div key={d.id} className="bg-surface border border-border rounded-xl px-4 py-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted">{formatDate(d.created_at)}</span>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${
                d.status === "success"
                  ? "bg-success/8 text-success border-success/20"
                  : "bg-error/8 text-error border-error/20"
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${d.status === "success" ? "bg-success" : "bg-error"}`} />
                {d.status}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-text-secondary">
              <code className="font-mono bg-bg/60 px-1.5 py-0.5 rounded border border-border/50 text-text-muted">{d.method}</code>
              <span className="font-mono">{d.response_status ?? "—"}</span>
              <span className="font-mono ml-auto">{d.latency_ms != null ? `${d.latency_ms}ms` : "—"}</span>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
