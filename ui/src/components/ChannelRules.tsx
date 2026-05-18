import { useState } from "react";
import { api } from "../lib/api";
import type { ChannelRule } from "../lib/api";

interface Props {
  routeId: number;
  rules: ChannelRule[];
  onUpdate: () => void;
}

export default function ChannelRules({ routeId, rules, onUpdate }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [channelId, setChannelId] = useState("");
  const [destinationUrl, setDestinationUrl] = useState("");
  const [workflowUrl, setWorkflowUrl] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAdd() {
    if (!channelId || !destinationUrl) return;
    setError("");
    setLoading(true);
    try {
      await api.createChannelRule(routeId, {
        channel_id: channelId,
        destination_url: destinationUrl,
        workflow_url: workflowUrl || undefined,
        description: description || undefined,
      });
      setChannelId("");
      setDestinationUrl("");
      setWorkflowUrl("");
      setDescription("");
      setShowForm(false);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add rule");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(ruleId: number) {
    if (!confirm("Remove this channel rule?")) return;
    try {
      await api.deleteChannelRule(routeId, ruleId);
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  }

  const inputClass =
    "w-full px-3 py-2 bg-bg/60 border border-border rounded-lg text-sm text-text-primary outline-none transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/20 placeholder:text-text-muted";

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
            <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
          </svg>
          <h2 className="text-lg font-semibold text-text-primary">Channel Rules</h2>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-hover text-accent-text rounded-md text-[13px] font-semibold transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Rule
        </button>
      </div>

      {rules.length === 0 && !showForm && (
        <div className="bg-surface border border-border rounded-xl py-8 text-center">
          <p className="text-text-muted text-sm">No channel rules. All events forward to the default destination.</p>
        </div>
      )}

      {showForm && (
        <div className="bg-surface border border-border rounded-xl p-5 mb-4 animate-fade-in">
          {error && (
            <div className="bg-error-bg border border-error/20 text-error px-3 py-2 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-text-secondary">Channel ID</label>
              <input
                className={inputClass}
                type="text"
                value={channelId}
                onChange={(e) => setChannelId(e.target.value)}
                placeholder="C0B3WDWKESH"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-text-secondary">N8N Webhook URL</label>
              <input
                className={inputClass}
                type="url"
                value={destinationUrl}
                onChange={(e) => setDestinationUrl(e.target.value)}
                placeholder="https://n8n.example.com/webhook/..."
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-text-secondary">N8N Workflow URL</label>
              <input
                className={inputClass}
                type="url"
                value={workflowUrl}
                onChange={(e) => setWorkflowUrl(e.target.value)}
                placeholder="https://n8n.example.com/workflow/123"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-text-secondary">Description</label>
              <input
                className={inputClass}
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 bg-transparent text-text-muted border border-border hover:border-border-hover rounded-md text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={loading || !channelId || !destinationUrl}
              className="px-3 py-1.5 bg-accent hover:bg-accent-hover text-accent-text rounded-md text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading ? "Adding..." : "Add"}
            </button>
          </div>
        </div>
      )}

      {rules.length > 0 && (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface-elevated/50">
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Channel ID</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Destination</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Workflow</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Description</th>
                <th className="text-right px-4 py-3 text-[11px] font-semibold text-text-muted uppercase tracking-widest border-b border-border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id} className="border-b border-border/40 last:border-b-0 hover:bg-surface-elevated/60 transition-colors">
                  <td className="px-4 py-3 text-sm font-mono text-text-primary">{rule.channel_id}</td>
                  <td className="px-4 py-3 text-sm text-text-secondary break-all">{rule.destination_url}</td>
                  <td className="px-4 py-3 text-sm">
                    {rule.workflow_url ? (
                      <a href={rule.workflow_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-hover transition-colors">
                        Open
                      </a>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-text-muted">{rule.description || "—"}</td>
                  <td className="px-4 py-3 text-sm text-right">
                    <button
                      onClick={() => handleDelete(rule.id)}
                      className="px-2 py-1 bg-transparent border-none text-text-secondary hover:text-error hover:bg-error-bg text-[13px] font-medium cursor-pointer transition-all rounded-md"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
