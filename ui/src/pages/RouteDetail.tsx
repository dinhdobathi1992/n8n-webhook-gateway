import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Delivery, Route } from "../lib/api";
import CopyButton from "../components/CopyButton";
import DeliveryLog from "../components/DeliveryLog";
import TestPanel from "../components/TestPanel";

const sourceBadge: Record<string, string> = {
  slack: "bg-info-bg text-info border-info/20",
  gchat: "bg-[#f0b90b]/8 text-[#f0b90b] border-[#f0b90b]/20",
  generic: "bg-[#8b5cf6]/8 text-[#8b5cf6] border-[#8b5cf6]/20",
};

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
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <div className="bg-error-bg border border-error/20 text-error px-4 py-3 rounded-lg text-sm text-center">
          {error}
        </div>
        <Link to="/" className="text-accent hover:text-accent-hover text-sm transition-colors mt-4 inline-block">
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!route) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="w-6 h-6 border-2 border-border border-t-accent rounded-full animate-spin" />
          <p className="text-text-muted text-sm">Loading route...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 animate-fade-in">
      <div className="flex justify-between items-center mb-6">
        <Link to="/" className="inline-flex items-center gap-1.5 text-text-secondary hover:text-accent text-sm no-underline transition-colors font-medium">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Dashboard
        </Link>
        <Link
          to={`/routes/${route.id}/edit`}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-surface-elevated border border-border-hover hover:bg-surface-hover text-text-primary rounded-md text-sm font-medium no-underline transition-all duration-150"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          Edit
        </Link>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-6 sm:px-8 py-6 border-b border-border">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
            <h1 className="text-xl sm:text-2xl font-semibold text-text-primary tracking-tight">
              {route.slug}
            </h1>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${
                route.enabled
                  ? "bg-success/8 text-success border-success/20"
                  : "bg-surface-elevated text-text-muted border-border"
              }`}>
                {route.enabled && <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />}
                {route.enabled ? "Active" : "Disabled"}
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${sourceBadge[route.source_type] || sourceBadge.generic}`}>
                {route.source_type.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        <div className="px-6 sm:px-8 py-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="flex flex-col gap-1.5">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-widest">Destination</span>
            <span className="text-sm text-text-primary break-all leading-relaxed">{route.destination_url}</span>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-widest">Signing Secret</span>
            <span className="text-sm text-text-secondary">
              {route.signing_secret_set ? (
                <span className="inline-flex items-center gap-1.5">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="text-success">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Configured
                </span>
              ) : "Not set"}
            </span>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-widest">Created</span>
            <span className="text-sm text-text-secondary">
              {new Date(route.created_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        </div>

        <div className="px-6 sm:px-8 py-5 border-t border-border bg-bg/30">
          <span className="text-[11px] font-semibold text-text-muted uppercase tracking-widest block mb-2">Webhook URL</span>
          <div className="flex items-center gap-2">
            <code className="bg-bg/60 border border-border/60 px-4 py-2.5 rounded-lg text-sm font-mono text-text-primary flex-1 break-all">
              {route.webhook_url}
            </code>
            <CopyButton text={route.webhook_url} />
          </div>
        </div>

        {route.description && (
          <div className="px-6 sm:px-8 py-5 border-t border-border">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-widest block mb-1.5">Description</span>
            <span className="text-sm text-text-secondary leading-relaxed">{route.description}</span>
          </div>
        )}
      </div>

      <div className="mt-10">
        <div className="flex items-center gap-2 mb-4">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          <h2 className="text-lg font-semibold text-text-primary">Test Webhook</h2>
        </div>
        <TestPanel webhookUrl={route.webhook_url} onSent={refreshDeliveries} />
      </div>

      <div className="mt-10 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <h2 className="text-lg font-semibold text-text-primary">Delivery Log</h2>
          </div>
          {deliveries.length > 0 && (
            <span className="text-xs text-text-muted bg-surface px-2.5 py-1 rounded-lg border border-border">
              {deliveries.length} {deliveries.length === 1 ? "delivery" : "deliveries"}
            </span>
          )}
        </div>
        {deliveries.length === 0 ? (
          <div className="bg-surface border border-border rounded-xl py-10 text-center">
            <p className="text-text-muted text-sm">No deliveries yet. Send a test request above.</p>
          </div>
        ) : (
          <DeliveryLog deliveries={deliveries} />
        )}
      </div>
    </div>
  );
}
