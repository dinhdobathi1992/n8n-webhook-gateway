import { useState } from "react";

interface Props {
  text: string;
}

export default function CopyButton({ text }: Props) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      style={{
        padding: "3px 10px",
        background: copied ? "#e8f8ed" : "#f5f5f7",
        border: "1px solid #e0e0e0",
        borderRadius: 6,
        fontSize: 12,
        color: copied ? "#34c759" : "#1d1d1f",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "background 0.2s, color 0.2s",
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}
