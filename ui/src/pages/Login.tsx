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
    <div className="flex items-center justify-center min-h-screen bg-bg px-4">
      <div className="animate-fade-in w-full max-w-[380px]">
        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-border rounded-xl p-8 flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-3 mb-1">
            <img src="/logo.svg" alt="" aria-hidden="true" className="h-16 w-16" />
            <span className="text-accent text-2xl font-bold tracking-tight">n8n Webhook Gateway</span>
            <p className="text-text-muted text-[13px]">Sign in to manage your routes</p>
          </div>

          {error && (
            <div className="bg-error-bg border border-error/20 text-error px-3 py-2.5 rounded-md text-[13px] text-center animate-fade-in">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5 text-[13px] font-medium text-text-muted">
              Username
              <input
                className="px-4 py-2.5 bg-surface-elevated border border-border rounded-lg text-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent/30 placeholder:text-text-muted"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium text-text-muted">
              Password
              <input
                className="px-4 py-2.5 bg-surface-elevated border border-border rounded-lg text-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent/30 placeholder:text-text-muted"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
          </div>

          <button
            type="submit"
            className="py-3 bg-accent hover:bg-accent-hover text-accent-text font-semibold rounded-md text-sm transition-colors disabled:opacity-40 disabled:pointer-events-none"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
