import { type FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { ChannelRule } from "../lib/api";

export default function RouteForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [slug, setSlug] = useState("");
  const [destinationUrl, setDestinationUrl] = useState("");
  const [workflowUrl, setWorkflowUrl] = useState("");
  const [description, setDescription] = useState("");
  const [sourceType, setSourceType] = useState("slack");
  const [showSecret, setShowSecret] = useState(false);
  const [signingSecret, setSigningSecret] = useState("");
  const [secretHeaderName, setSecretHeaderName] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  const [authHeaderName, setAuthHeaderName] = useState("");
  const [authHeaderValue, setAuthHeaderValue] = useState("");
  const [channelId, setChannelId] = useState("");
  const [existingRules, setExistingRules] = useState<ChannelRule[]>([]);
  const [newChannelId, setNewChannelId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (id) {
      api
        .getRoute(Number(id))
        .then((r) => {
          setSlug(r.slug);
          setDestinationUrl(r.destination_url);
          setWorkflowUrl(r.workflow_url || "");
          setDescription(r.description || "");
          setSourceType(r.source_type || "slack");
          if (r.secret_header_name) setSecretHeaderName(r.secret_header_name);
          if (r.signing_secret_set) setShowSecret(true);
          if (r.auth_header_set) {
            setShowAuth(true);
            if (r.auth_header_name) setAuthHeaderName(r.auth_header_name);
          }
          if (r.channel_rules) setExistingRules(r.channel_rules);
        })
        .catch((err) =>
          setError(err instanceof Error ? err.message : "Failed to load route")
        );
    }
  }, [id]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isEdit) {
        const data: Record<string, string | undefined> = { destination_url: destinationUrl };
        if (workflowUrl) data.workflow_url = workflowUrl;
        if (description) data.description = description;
        if (signingSecret) data.signing_secret = signingSecret;
        if (sourceType === "generic" && secretHeaderName) data.secret_header_name = secretHeaderName;
        if (authHeaderName) data.auth_header_name = authHeaderName;
        if (authHeaderValue) data.auth_header_value = authHeaderValue;
        await api.updateRoute(Number(id), data);
      } else {
        const route = await api.createRoute({
          slug,
          destination_url: destinationUrl,
          source_type: sourceType,
          description: description || undefined,
          workflow_url: workflowUrl || undefined,
          signing_secret: sourceType !== "gchat" ? signingSecret : undefined,
          secret_header_name: sourceType === "generic" ? secretHeaderName : undefined,
          auth_header_name: authHeaderName || undefined,
          auth_header_value: authHeaderValue || undefined,
        });
        if (channelId && sourceType === "slack") {
          await api.createChannelRule(route.id, {
            channel_id: channelId,
            destination_url: destinationUrl,
            workflow_url: workflowUrl || undefined,
            description: description || undefined,
          });
        }
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full px-4 py-3 bg-bg/60 border border-border rounded-lg text-[15px] text-text-primary outline-none transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/20 placeholder:text-text-muted disabled:opacity-50 disabled:cursor-not-allowed";
  const labelClass = "flex flex-col gap-2 text-sm font-medium text-text-secondary";

  return (
    <div className="flex justify-center px-4 sm:px-6 py-10 sm:py-14 min-h-screen">
      <div className="w-full max-w-[520px] animate-fade-in">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="inline-flex items-center gap-1.5 text-text-secondary hover:text-accent text-sm font-medium bg-transparent border-none cursor-pointer transition-colors mb-6"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back
        </button>

        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-border rounded-xl overflow-hidden"
        >
          <div className="px-6 sm:px-8 py-6 border-b border-border">
            <h1 className="text-xl font-semibold text-text-primary tracking-tight">
              {isEdit ? "Edit Route" : "Create Route"}
            </h1>
            {!isEdit && (
              <p className="text-sm text-text-muted mt-1">Configure a new webhook proxy route.</p>
            )}
          </div>

          <div className="px-6 sm:px-8 py-6 flex flex-col gap-5">
            {error && (
              <div className="bg-error-bg border border-error/20 text-error px-4 py-3 rounded-lg text-sm animate-fade-in">
                {error}
              </div>
            )}

            {/* Basic fields */}
            <div className="flex flex-col gap-5">
              <label className={labelClass}>
                Slug
                <input
                  className={inputClass}
                  type="text"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  disabled={isEdit}
                  placeholder="my-webhook"
                  required
                />
                {!isEdit && slug && (
                  <span className="text-xs text-text-muted font-mono bg-bg/60 px-2.5 py-1 rounded-lg border border-border/50 w-fit">
                    /{slug}/webhook
                  </span>
                )}
              </label>

              <label className={labelClass}>
                N8N Webhook URL
                <input
                  className={inputClass}
                  type="url"
                  value={destinationUrl}
                  onChange={(e) => setDestinationUrl(e.target.value)}
                  placeholder="https://n8n.example.com/webhook/..."
                  required
                />
              </label>

              <label className={labelClass}>
                N8N Workflow URL
                <input
                  className={inputClass}
                  type="url"
                  value={workflowUrl}
                  onChange={(e) => setWorkflowUrl(e.target.value)}
                  placeholder="https://n8n.example.com/workflow/123"
                />
              </label>

              <label className={labelClass}>
                Description
                <input
                  className={inputClass}
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </label>
            </div>

            {/* Source type section */}
            <div className="border-t border-border pt-5 flex flex-col gap-5">
              <div className="flex items-center gap-2 mb-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Verification</span>
              </div>

              <label className={labelClass}>
                Source Type
                <select
                  className={inputClass}
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  disabled={isEdit}
                >
                  <option value="slack">Slack</option>
                  <option value="gchat">Google Chat</option>
                  <option value="generic">Generic (header-based)</option>
                </select>
                {isEdit && (
                  <span className="text-xs text-text-muted">Source type cannot be changed after creation</span>
                )}
              </label>

              {sourceType === "slack" && (
                isEdit ? (
                  <>
                    <label className="flex items-center gap-2.5 text-sm text-text-secondary cursor-pointer select-none group">
                      <input
                        type="checkbox"
                        checked={showSecret}
                        onChange={(e) => setShowSecret(e.target.checked)}
                        className="accent-accent w-4 h-4"
                      />
                      <span className="group-hover:text-text-primary transition-colors">Update signing secret</span>
                    </label>
                    {showSecret && (
                      <div className="animate-fade-in">
                        <span className="text-xs text-text-muted block mb-2">Signing secret is set. Enter new value to update.</span>
                        <label className={labelClass}>
                          Signing Secret
                          <input
                            className={inputClass}
                            type="password"
                            value={signingSecret}
                            onChange={(e) => setSigningSecret(e.target.value)}
                            placeholder="Enter to change"
                          />
                        </label>
                      </div>
                    )}

                    {/* Channel Rules for edit mode */}
                    <div className="border-t border-border/60 pt-4 mt-2">
                      <div className="flex items-center gap-2 mb-3">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
                          <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
                        </svg>
                        <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Channel Rules</span>
                      </div>
                      <span className="text-xs text-text-muted block mb-3">Only forward events from these channels. Uses the Webhook/Workflow URLs above.</span>

                      {existingRules.length > 0 && (
                        <div className="flex flex-col gap-2 mb-3">
                          {existingRules.map((rule) => (
                            <div key={rule.id} className="flex items-center justify-between bg-bg/40 border border-border/60 rounded-lg px-3 py-2">
                              <span className="text-sm font-mono text-text-primary">{rule.channel_id}</span>
                              <button
                                type="button"
                                onClick={async () => {
                                  if (!confirm("Remove this channel rule?")) return;
                                  try {
                                    await api.deleteChannelRule(Number(id), rule.id);
                                    setExistingRules(existingRules.filter((r) => r.id !== rule.id));
                                  } catch (err) {
                                    alert(err instanceof Error ? err.message : "Delete failed");
                                  }
                                }}
                                className="text-text-muted hover:text-error text-xs bg-transparent border-none cursor-pointer transition-colors"
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <input
                          className={inputClass}
                          type="text"
                          value={newChannelId}
                          onChange={(e) => setNewChannelId(e.target.value)}
                          placeholder="Channel ID (e.g. C0B3WDWKESH)"
                        />
                        <button
                          type="button"
                          disabled={!newChannelId}
                          onClick={async () => {
                            try {
                              const rule = await api.createChannelRule(Number(id), {
                                channel_id: newChannelId,
                                destination_url: destinationUrl,
                                workflow_url: workflowUrl || undefined,
                                description: description || undefined,
                              });
                              setExistingRules([...existingRules, rule]);
                              setNewChannelId("");
                            } catch (err) {
                              alert(err instanceof Error ? err.message : "Failed to add rule");
                            }
                          }}
                          className="shrink-0 px-3 py-3 bg-accent hover:bg-accent-hover text-accent-text rounded-lg text-[13px] font-semibold transition-colors disabled:opacity-50 disabled:pointer-events-none"
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <label className={labelClass}>
                      Slack Signing Secret
                      <input
                        className={inputClass}
                        type="password"
                        value={signingSecret}
                        onChange={(e) => setSigningSecret(e.target.value)}
                        placeholder="From Slack App > Basic Information"
                        required
                      />
                      <span className="text-xs text-text-muted">Required for HMAC-SHA256 verification</span>
                    </label>
                    <label className={labelClass}>
                      Channel ID
                      <input
                        className={inputClass}
                        type="text"
                        value={channelId}
                        onChange={(e) => setChannelId(e.target.value)}
                        placeholder="C0B3WDWKESH"
                      />
                      <span className="text-xs text-text-muted">Only forward events from this channel. Leave empty to forward all.</span>
                    </label>
                  </>
                )
              )}

              {sourceType === "gchat" && (
                <div className="bg-[#f0b90b]/8 border border-[#f0b90b]/20 text-[#f0b90b] px-4 py-3 rounded-lg text-sm flex items-start gap-2.5">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                  Google Chat webhooks are verified via JWT — no signing secret needed.
                </div>
              )}

              {sourceType === "generic" && (
                <>
                  <label className={labelClass}>
                    Secret Header Name
                    <input
                      className={inputClass}
                      type="text"
                      value={secretHeaderName}
                      onChange={(e) => setSecretHeaderName(e.target.value)}
                      placeholder="e.g. X-Telegram-Bot-Api-Secret-Token"
                      required
                      disabled={isEdit}
                    />
                    <span className="text-xs text-text-muted">
                      Header name the source sends with the secret value
                    </span>
                  </label>
                  {isEdit ? (
                    <>
                      <label className="flex items-center gap-2.5 text-sm text-text-secondary cursor-pointer select-none group">
                        <input
                          type="checkbox"
                          checked={showSecret}
                          onChange={(e) => setShowSecret(e.target.checked)}
                          className="accent-accent w-4 h-4"
                        />
                        <span className="group-hover:text-text-primary transition-colors">Update secret value</span>
                      </label>
                      {showSecret && (
                        <label className={`${labelClass} animate-fade-in`}>
                          Secret Value
                          <input
                            className={inputClass}
                            type="password"
                            value={signingSecret}
                            onChange={(e) => setSigningSecret(e.target.value)}
                            placeholder="Enter to change"
                          />
                        </label>
                      )}
                    </>
                  ) : (
                    <label className={labelClass}>
                      Secret Value
                      <input
                        className={inputClass}
                        type="password"
                        value={signingSecret}
                        onChange={(e) => setSigningSecret(e.target.value)}
                        placeholder="The secret value to match against"
                        required
                      />
                    </label>
                  )}
                </>
              )}
            </div>

            {/* Auth header section */}
            <div className="border-t border-border pt-5 flex flex-col gap-5">
              <div className="flex items-center gap-2 mb-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
                </svg>
                <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Destination Auth</span>
              </div>

              <label className="flex items-center gap-2.5 text-sm text-text-secondary cursor-pointer select-none group">
                <input
                  type="checkbox"
                  checked={showAuth}
                  onChange={(e) => setShowAuth(e.target.checked)}
                  className="accent-accent w-4 h-4"
                />
                <span className="group-hover:text-text-primary transition-colors">
                  {isEdit ? "Update destination auth header" : "Add auth header to forwarded requests"}
                </span>
              </label>

              {showAuth && (
                <div className="flex flex-col gap-4 animate-fade-in">
                  {isEdit && (
                    <span className="text-xs text-text-muted">Auth header is set. Enter new values to update.</span>
                  )}
                  <label className={labelClass}>
                    Header Name
                    <input
                      className={inputClass}
                      type="text"
                      value={authHeaderName}
                      onChange={(e) => setAuthHeaderName(e.target.value)}
                      placeholder="e.g. api_key"
                    />
                  </label>
                  <label className={labelClass}>
                    Header Value
                    <input
                      className={inputClass}
                      type="password"
                      value={authHeaderValue}
                      onChange={(e) => setAuthHeaderValue(e.target.value)}
                      placeholder={isEdit && !authHeaderValue ? "Enter to change" : "secret value"}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>

          <div className="px-6 sm:px-8 py-5 border-t border-border bg-bg/30 flex gap-3">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="flex-1 py-3 bg-transparent text-text-muted border border-border hover:border-border-hover hover:text-text-secondary rounded-md text-[15px] font-medium transition-all duration-200 active:scale-[0.98]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 bg-accent hover:bg-accent-hover active:scale-[0.98] text-accent-text border-none rounded-md text-[15px] font-semibold transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none"
              disabled={loading}
            >
              {loading ? "Saving..." : isEdit ? "Update" : "Create Route"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
