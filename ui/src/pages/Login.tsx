import { type FormEvent, useState } from "react";
import { api } from "../lib/api";

interface Props {
  onLogin: () => void;
}

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.login(username, password);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.wrapper}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <h1 style={styles.title}>Webhook Gateway</h1>
        <p style={styles.subtitle}>Sign in to manage your routes</p>

        {error && <div style={styles.error}>{error}</div>}

        <label style={styles.label}>
          Username
          <input
            style={styles.input}
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </label>

        <label style={styles.label}>
          Password
          <input
            style={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <button type="submit" style={styles.button} disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    background: "#f5f5f7",
  },
  card: {
    background: "#fff",
    borderRadius: 16,
    padding: "48px 40px",
    width: "100%",
    maxWidth: 420,
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  title: {
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif",
    fontSize: 28,
    fontWeight: 600,
    color: "#1d1d1f",
    textAlign: "center" as const,
    margin: 0,
    letterSpacing: -0.5,
  },
  subtitle: {
    color: "#86868b",
    textAlign: "center" as const,
    fontSize: 15,
    margin: 0,
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
    fontSize: 16,
    outline: "none",
    transition: "border-color 0.2s",
  },
  button: {
    padding: "12px 0",
    background: "#0071e3",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    fontSize: 16,
    fontWeight: 500,
    marginTop: 4,
  },
  error: {
    background: "#fff2f2",
    color: "#ff3b30",
    padding: "10px 14px",
    borderRadius: 10,
    fontSize: 14,
    textAlign: "center" as const,
  },
};
