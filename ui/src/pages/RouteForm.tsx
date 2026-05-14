import { type FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";

export default function RouteForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [slug, setSlug] = useState("");
  const [destinationUrl, setDestinationUrl] = useState("");
  const [description, setDescription] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [signingSecret, setSigningSecret] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  const [authHeaderName, setAuthHeaderName] = useState("");
  const [authHeaderValue, setAuthHeaderValue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (id) {
      api
        .getRoute(Number(id))
        .then((r) => {
          setSlug(r.slug);
          setDestinationUrl(r.destination_url);
          setDescription(r.description || "");
          if (r.signing_secret_set) setShowSecret(true);
          if (r.auth_header_set) {
            setShowAuth(true);
            if (r.auth_header_name) setAuthHeaderName(r.auth_header_name);
          }
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
        const data: Record<string, string> = { destination_url: destinationUrl };
        if (description) data.description = description;
        if (signingSecret) data.signing_secret = signingSecret;
        if (authHeaderName) data.auth_header_name = authHeaderName;
        if (authHeaderValue) data.auth_header_value = authHeaderValue;
        await api.updateRoute(Number(id), data);
      } else {
        await api.createRoute({
          slug,
          destination_url: destinationUrl,
          description: description || undefined,
          signing_secret: signingSecret,
          auth_header_name: authHeaderName || undefined,
          auth_header_value: authHeaderValue || undefined,
        });
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.wrapper}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <h1 style={styles.title}>{isEdit ? "Edit Route" : "Create Route"}</h1>

        {error && <div style={styles.error}>{error}</div>}

        <label style={styles.label}>
          Slug
          <input
            style={styles.input}
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            disabled={isEdit}
            placeholder="my-webhook"
            required
          />
          {!isEdit && (
            <span style={styles.hint}>
              Webhook URL will be: /{slug || "..."}/webhook
            </span>
          )}
        </label>

        <label style={styles.label}>
          Destination URL
          <input
            style={styles.input}
            type="url"
            value={destinationUrl}
            onChange={(e) => setDestinationUrl(e.target.value)}
            placeholder="https://n8n.example.com/webhook/..."
            required
          />
        </label>

        <label style={styles.label}>
          Description
          <input
            style={styles.input}
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
          />
        </label>

        {isEdit ? (
          <>
            <div style={styles.toggleRow}>
              <label style={styles.toggleLabel}>
                <input
                  type="checkbox"
                  checked={showSecret}
                  onChange={(e) => setShowSecret(e.target.checked)}
                />
                Update signing secret
              </label>
            </div>
            {showSecret && (
              <>
                <span style={styles.hint}>Signing secret is set. Enter new value to update.</span>
                <label style={styles.label}>
                  Signing Secret
                  <input
                    style={styles.input}
                    type="password"
                    value={signingSecret}
                    onChange={(e) => setSigningSecret(e.target.value)}
                    placeholder="••••••••  (enter to change)"
                  />
                </label>
              </>
            )}
          </>
        ) : (
          <label style={styles.label}>
            Slack Signing Secret (required)
            <input
              style={styles.input}
              type="password"
              value={signingSecret}
              onChange={(e) => setSigningSecret(e.target.value)}
              placeholder="From Slack App → Basic Information → Signing Secret"
              required
            />
          </label>
        )}

        <div style={styles.toggleRow}>
          <label style={styles.toggleLabel}>
            <input
              type="checkbox"
              checked={showAuth}
              onChange={(e) => setShowAuth(e.target.checked)}
            />
            {isEdit ? "Update destination auth header" : "Set destination auth header"}
          </label>
        </div>

        {showAuth && (
          <>
            {isEdit && (
              <span style={styles.hint}>Auth header is set. Enter new values to update.</span>
            )}
            <label style={styles.label}>
              Header Name
              <input
                style={styles.input}
                type="text"
                value={authHeaderName}
                onChange={(e) => setAuthHeaderName(e.target.value)}
                placeholder="e.g. api_key"
              />
            </label>
            <label style={styles.label}>
              Header Value
              <input
                style={styles.input}
                type="password"
                value={authHeaderValue}
                onChange={(e) => setAuthHeaderValue(e.target.value)}
                placeholder={isEdit && !authHeaderValue ? "••••••••  (enter to change)" : "secret value"}
              />
            </label>
          </>
        )}

        <div style={styles.buttonRow}>
          <button
            type="button"
            onClick={() => navigate("/")}
            style={styles.cancelBtn}
          >
            Cancel
          </button>
          <button type="submit" style={styles.submitBtn} disabled={loading}>
            {loading ? "Saving..." : isEdit ? "Update" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    justifyContent: "center",
    padding: "60px 24px",
    minHeight: "100vh",
    background: "#f5f5f7",
  },
  card: {
    background: "#fff",
    borderRadius: 16,
    padding: "40px 36px",
    width: "100%",
    maxWidth: 500,
    height: "fit-content",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: 18,
  },
  title: {
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif",
    fontSize: 24,
    fontWeight: 600,
    color: "#1d1d1f",
    margin: 0,
    letterSpacing: -0.3,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontSize: 14,
    fontWeight: 500,
    color: "#1d1d1f",
  },
  input: {
    padding: "10px 14px",
    border: "1px solid #e0e0e0",
    borderRadius: 10,
    fontSize: 15,
    outline: "none",
  },
  hint: {
    fontSize: 13,
    color: "#86868b",
  },
  toggleRow: {
    display: "flex",
    alignItems: "center",
  },
  toggleLabel: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 14,
    color: "#1d1d1f",
    cursor: "pointer",
  },
  buttonRow: {
    display: "flex",
    gap: 12,
    marginTop: 8,
  },
  cancelBtn: {
    flex: 1,
    padding: "10px 0",
    background: "transparent",
    color: "#86868b",
    border: "1px solid #e0e0e0",
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 500,
  },
  submitBtn: {
    flex: 1,
    padding: "10px 0",
    background: "#0071e3",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 500,
  },
  error: {
    background: "#fff2f2",
    color: "#ff3b30",
    padding: "10px 14px",
    borderRadius: 10,
    fontSize: 14,
  },
};
