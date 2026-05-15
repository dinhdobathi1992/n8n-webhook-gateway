import { useState } from "react";

interface Props {
  webhookUrl: string;
  onSent?: () => void;
}

export default function TestPanel({ webhookUrl, onSent }: Props) {
  const [body, setBody] = useState('{"test": true}');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{
    status: number;
    body: string;
  } | null>(null);
  const [error, setError] = useState("");

  async function handleSend() {
    setError("");
    setResult(null);
    setSending(true);
    try {
      const resp = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const text = await resp.text();
      setResult({ status: resp.status, body: text });
      onSent?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 max-w-2xl">
      <div className="relative">
        <textarea
          className="w-full px-4 py-3 bg-bg/60 border border-border rounded-lg text-sm font-mono text-text-primary resize-y outline-none transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/20 placeholder:text-text-muted min-h-[100px]"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          placeholder='{"test": true}'
        />
        <span className="absolute top-2 right-3 text-[10px] text-text-muted/50 font-mono">JSON</span>
      </div>
      <button
        onClick={handleSend}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover active:scale-[0.97] text-accent-text border-none rounded-md text-sm font-semibold w-fit transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none"
        disabled={sending}
      >
        {sending ? (
          <>
            <div className="w-3.5 h-3.5 border-2 border-accent-text/30 border-t-accent-text rounded-full animate-spin" />
            Sending...
          </>
        ) : (
          <>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
            Send Test
          </>
        )}
      </button>

      {result && (
        <div className={`border-l-[3px] px-4 py-3 rounded-lg bg-surface flex flex-col gap-2 animate-fade-in ${
          result.status < 400 ? "border-l-success" : "border-l-error"
        }`}>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${result.status < 400 ? "text-success" : "text-error"}`}>
              {result.status}
            </span>
            <span className="text-xs text-text-muted">
              {result.status < 400 ? "OK" : "Error"}
            </span>
          </div>
          <pre className="text-xs font-mono text-text-secondary m-0 whitespace-pre-wrap break-all max-h-[200px] overflow-auto p-3 bg-bg/60 rounded-lg border border-border/50">
            {result.body}
          </pre>
        </div>
      )}

      {error && (
        <div className="bg-error-bg border border-error/20 text-error text-sm px-4 py-3 rounded-lg animate-fade-in">
          {error}
        </div>
      )}
    </div>
  );
}
