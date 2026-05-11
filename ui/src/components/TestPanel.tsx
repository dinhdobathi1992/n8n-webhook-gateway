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
    <div style={styles.panel}>
      <textarea
        style={styles.textarea}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
        placeholder='{"test": true}'
      />
      <button onClick={handleSend} style={styles.sendBtn} disabled={sending}>
        {sending ? "Sending..." : "Send Test Request"}
      </button>

      {result && (
        <div
          style={{
            ...styles.result,
            borderColor: result.status < 400 ? "#34c759" : "#ff3b30",
          }}
        >
          <span style={styles.resultStatus}>Status: {result.status}</span>
          <pre style={styles.resultBody}>{result.body}</pre>
        </div>
      )}

      {error && <div style={styles.error}>{error}</div>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    maxWidth: 600,
  },
  textarea: {
    padding: "12px 14px",
    border: "1px solid #e0e0e0",
    borderRadius: 10,
    fontSize: 14,
    fontFamily: "ui-monospace, Consolas, monospace",
    resize: "vertical",
    outline: "none",
  },
  sendBtn: {
    padding: "10px 24px",
    background: "#0071e3",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 500,
    width: "fit-content",
  },
  result: {
    borderLeft: "3px solid",
    padding: "12px 16px",
    borderRadius: 8,
    background: "#f5f5f7",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  resultStatus: {
    fontSize: 14,
    fontWeight: 600,
    color: "#1d1d1f",
  },
  resultBody: {
    fontSize: 13,
    fontFamily: "ui-monospace, Consolas, monospace",
    color: "#1d1d1f",
    margin: 0,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-all" as const,
    maxHeight: 200,
    overflow: "auto",
  },
  error: {
    color: "#ff3b30",
    fontSize: 14,
  },
};
