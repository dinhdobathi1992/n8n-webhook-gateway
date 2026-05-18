import { Link } from "react-router-dom";
import type { Route } from "../lib/api";
import CopyButton from "./CopyButton";

interface Props {
  routes: Route[];
  onToggle: (id: number, enabled: boolean) => void;
  onDelete: (id: number) => void;
}

function truncate(str: string, max: number) {
  return str.length > max ? str.slice(0, max) + "..." : str;
}

const sourceBadge: Record<string, string> = {
  slack: "bg-info-bg text-info border-info/20",
  gchat: "bg-[#f0b90b]/8 text-[#f0b90b] border-[#f0b90b]/20",
  generic: "bg-[#8b5cf6]/8 text-[#8b5cf6] border-[#8b5cf6]/20",
};

export default function RouteTable({ routes, onToggle, onDelete }: Props) {
  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto border border-border rounded-xl bg-surface">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-surface-elevated/50">
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Slug</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Source</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">N8N Webhook URL</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Status</th>
              <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Webhook URL</th>
              <th className="text-right px-5 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((r, i) => (
              <tr
                key={r.id}
                className="border-b border-border/40 last:border-b-0 hover:bg-surface-elevated/60 transition-colors duration-150"
                style={{ animationDelay: `${i * 30}ms` }}
              >
                <td className="px-5 py-4 text-sm align-middle">
                  <Link to={`/routes/${r.id}`} className="text-accent hover:text-accent-hover font-medium no-underline transition-colors">
                    {r.slug}
                  </Link>
                </td>
                <td className="px-5 py-4 text-sm align-middle">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${sourceBadge[r.source_type] || sourceBadge.generic}`}>
                    {r.source_type}
                  </span>
                </td>
                <td className="px-5 py-4 text-sm align-middle">
                  <span className="text-text-secondary text-[13px]" title={r.destination_url}>
                    {truncate(r.destination_url, 45)}
                  </span>
                </td>
                <td className="px-5 py-4 text-sm align-middle">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold ${
                    r.enabled
                      ? "bg-success/8 text-success border border-success/20"
                      : "bg-surface-elevated text-text-muted border border-border"
                  }`}>
                    {r.enabled && <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />}
                    {r.enabled ? "Active" : "Disabled"}
                  </span>
                </td>
                <td className="px-5 py-4 text-sm align-middle">
                  <div className="flex items-center gap-2">
                    <code className="text-[12px] font-mono text-text-muted bg-bg/60 px-2.5 py-1 rounded-md border border-border/50">
                      {truncate(r.webhook_url, 36)}
                    </code>
                    <CopyButton text={r.webhook_url} />
                  </div>
                </td>
                <td className="px-5 py-4 text-sm align-middle text-right">
                  <div className="flex gap-1 justify-end items-center">
                    <Link to={`/routes/${r.id}`} className="px-2.5 py-1 text-text-secondary hover:text-accent text-[13px] font-medium no-underline transition-all duration-150 rounded-md">
                      View
                    </Link>
                    <Link to={`/routes/${r.id}/edit`} className="px-2.5 py-1 text-text-secondary hover:text-accent text-[13px] font-medium no-underline transition-all duration-150 rounded-md">
                      Edit
                    </Link>
                    <button
                      onClick={() => onToggle(r.id, !r.enabled)}
                      className={`px-2.5 py-1 bg-transparent border-none text-[13px] font-medium cursor-pointer transition-all duration-150 rounded-md ${
                        r.enabled
                          ? "text-text-secondary hover:text-warning hover:bg-warning/8"
                          : "text-text-secondary hover:text-success hover:bg-success/8"
                      }`}
                    >
                      {r.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => onDelete(r.id)}
                      className="px-2.5 py-1 bg-transparent border-none text-text-secondary hover:text-error hover:bg-error-bg text-[13px] font-medium cursor-pointer transition-all duration-150 rounded-md"
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

      {/* Mobile card view */}
      <div className="md:hidden flex flex-col gap-3">
        {routes.map((r) => (
          <Link
            key={r.id}
            to={`/routes/${r.id}`}
            className="block bg-surface border border-border rounded-xl p-4 no-underline transition-all duration-150 hover:border-border-hover active:scale-[0.99]"
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium text-accent">{r.slug}</span>
                <span className="text-xs text-text-muted">{truncate(r.destination_url, 40)}</span>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold shrink-0 ${
                r.enabled
                  ? "bg-success/8 text-success border border-success/20"
                  : "bg-surface-elevated text-text-muted border border-border"
              }`}>
                {r.enabled && <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />}
                {r.enabled ? "Active" : "Off"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${sourceBadge[r.source_type] || sourceBadge.generic}`}>
                {r.source_type}
              </span>
              <div className="flex gap-2 items-center">
                <CopyButton text={r.webhook_url} />
                <Link
                  to={`/routes/${r.id}/edit`}
                  onClick={(e) => e.stopPropagation()}
                  className="px-2 py-1 text-text-muted hover:text-text-primary text-xs no-underline transition-colors"
                >
                  Edit
                </Link>
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggle(r.id, !r.enabled); }}
                  className={`px-2 py-1 bg-transparent border-none text-xs cursor-pointer transition-colors ${
                    r.enabled ? "text-text-muted hover:text-warning" : "text-text-muted hover:text-success"
                  }`}
                >
                  {r.enabled ? "Disable" : "Enable"}
                </button>
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(r.id); }}
                  className="px-2 py-1 bg-transparent border-none text-text-muted hover:text-error text-xs cursor-pointer transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
