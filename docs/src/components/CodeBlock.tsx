import { useEffect, useRef, useState } from "react";
import Prism from "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-python";
import "prismjs/components/prism-typescript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-markdown";
import "prismjs/components/prism-http";

const ALIASES: Record<string, string> = {
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  py: "python",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  http: "http",
};

const SUPPORTED = new Set(["bash", "python", "typescript", "json", "markdown", "http", "javascript"]);

function normalizeLang(raw: string): string {
  const base = raw.toLowerCase();
  const alias = ALIASES[base] ?? base;
  return SUPPORTED.has(alias) ? alias : "text";
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function highlight(code: string, lang: string): string {
  if (lang === "text") {
    return escapeHtml(code);
  }
  const grammar = Prism.languages[lang];
  if (!grammar) return escapeHtml(code);
  return Prism.highlight(code, grammar, lang);
}

function copyText(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      resolve();
    } catch (e) {
      reject(e);
    } finally {
      document.body.removeChild(ta);
    }
  });
}

export default function CodeBlock({ code, language }: { code: string; language: string }) {
  const lang = normalizeLang(language);
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);
  const [html, setHtml] = useState(() => highlight(code, lang));

  useEffect(() => {
    setHtml(highlight(code, lang));
  }, [code, lang]);

  useEffect(() => {
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, []);

  const onCopy = () => {
    copyText(code).then(() => {
      setCopied(true);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="codeblock">
      <div className="codeblock-head">
        <span className="codeblock-lang">{lang === "text" ? "plain text" : lang}</span>
        <button type="button" className="codeblock-copy" onClick={onCopy} aria-label="Copy code">
          {copied ? (
            <span className="codeblock-copied">Copied ✓</span>
          ) : (
            <span className="codeblock-copy-label">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy
            </span>
          )}
        </button>
      </div>
      <pre className={`language-${lang}`} tabIndex={-1}>
        <code
          className={`language-${lang}`}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </pre>
    </div>
  );
}