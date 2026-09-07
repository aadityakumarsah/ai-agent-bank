import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Link } from "react-router-dom";
import CodeBlock from "./CodeBlock";

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "");
}

export interface HeadingRef {
  id: string;
  level: number;
  text: string;
}

export function extractHeadings(md: string): HeadingRef[] {
  const out: HeadingRef[] = [];
  for (const line of md.split("\n")) {
    const m = /^(#{2,3})\s+(.+?)\s*#*\s*$/.exec(line);
    if (m) {
      const text = m[2].replace(/[*_`]/g, "").trim();
      out.push({ id: slugify(text), level: m[1].length, text });
    }
  }
  return out;
}

type CalloutType = "note" | "info" | "tip" | "warning" | "danger" | "important";

function calloutType(children: React.ReactNode): CalloutType | null {
  const find = (n: React.ReactNode): string | null => {
    if (typeof n === "string") return n;
    if (Array.isArray(n)) {
      for (const item of n) {
        const r = find(item);
        if (r) return r;
      }
    }
    if (React.isValidElement(n)) {
      const p = (n.props as { children?: React.ReactNode })?.children;
      if (p != null) {
        const r = find(p);
        if (r) return r;
      }
    }
    return null;
  };
  const text = find(children) ?? "";
  const m = /^\[\s*!(NOTE|INFO|TIP|WARNING|DANGER|IMPORTANT)\s*\]/.exec(text.trim());
  if (!m) return null;
  return m[1].toLowerCase() as CalloutType;
}

const CALLOUT_LABELS: Record<CalloutType, string> = {
  note: "Note",
  info: "Info",
  tip: "Tip",
  warning: "Warning",
  danger: "Danger",
  important: "Important",
};

function stripFirstBadge(children: React.ReactNode): React.ReactNode {
  const strip = (n: React.ReactNode): React.ReactNode => {
    if (typeof n === "string") {
      return n.replace(/^\s*\[\s*!(NOTE|INFO|TIP|WARNING|DANGER|IMPORTANT)\s*\]\s*/i, "");
    }
    if (Array.isArray(n)) return n.map(strip);
    if (React.isValidElement(n)) {
      const p = (n.props as { children?: React.ReactNode })?.children;
      return React.cloneElement(n, undefined, p != null ? strip(p) : undefined);
    }
    return n;
  };
  return strip(children);
}

function headingId(children: React.ReactNode): string {
  const collect = (n: React.ReactNode): string =>
    typeof n === "string"
      ? n
      : Array.isArray(n)
      ? n.map(collect).join("")
      : React.isValidElement(n)
      ? collect((n.props as { children?: React.ReactNode })?.children)
      : "";
  return slugify(collect(children));
}

interface HeadingProps {
  level: 1 | 2 | 3;
  children?: React.ReactNode;
}

function Heading({ level, children }: HeadingProps) {
  const id = headingId(children);
  const Tag = `h${level}` as "h2" | "h3";
  return (
    <Tag id={id} tabIndex={-1} className="doc-heading">
      {level > 1 && (
        <a href={`#${id}`} className="heading-anchor" aria-label="Link to section" onClick={(e) => {
          e.preventDefault();
          const el = document.getElementById(id);
          el?.scrollIntoView({ behavior: "smooth", block: "start" });
        }}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
        </a>
      )}
      {children}
    </Tag>
  );
}

export default function Markdown({ md }: { md: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={{
        h1: ({ children }) => <Heading level={1}>{children}</Heading>,
        h2: ({ children }) => <Heading level={2}>{children}</Heading>,
        h3: ({ children }) => <Heading level={3}>{children}</Heading>,
        code(props) {
          const { className, children } = props;
          const langMatch = /language-([\w-]+)/.exec(className || "");
          if (!langMatch) {
            return <code className="inline-code">{children}</code>;
          }
          const raw = String(children);
          return (
            <CodeBlock
              code={raw.replace(/\n$/, "")}
              language={langMatch[1] || "text"}
            />
          );
        },
        blockquote({ children }) {
          const type = calloutType(children);
          if (!type) {
            return <blockquote className="plain-quote">{children}</blockquote>;
          }
          return (
            <div className={`callout callout-${type}`} role="note">
              <div className="callout-title">{CALLOUT_LABELS[type]}</div>
              <div className="callout-body">{stripFirstBadge(children)}</div>
            </div>
          );
        },
        a({ href, children, ...rest }) {
          const h = href ?? "";
          const internal = h.startsWith("/");
          const anchor = h.startsWith("#");
          if (anchor) {
            return (
              <a href={h} onClick={(e) => {
                e.preventDefault();
                document.getElementById(h.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}>
                {children}
              </a>
            );
          }
          if (internal) {
            if (h.endsWith(".md")) {
              const path = h.replace(/\.md$/, "").replace(/^\/docs/, "");
              return <Link to={path || "/"}>{children}</Link>;
            }
            return <Link to={h}>{children}</Link>;
          }
          return (
            <a href={h} target="_blank" rel="noopener noreferrer" {...rest}>
              {children}
            </a>
          );
        },
        mark: ({ children }) => <mark>{children}</mark>,
        del: ({ children }) => <del>{children}</del>,
      }}
    >
      {md}
    </ReactMarkdown>
  );
}