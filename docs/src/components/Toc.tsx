import { useEffect, useRef, useState } from "react";
import type { HeadingRef } from "./Markdown";

export default function Toc({ headings }: { headings: HeadingRef[] }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const ticking = useRef(false);

  useEffect(() => {
    if (headings.length === 0) return;
    const onScroll = () => {
      if (ticking.current) return;
      ticking.current = true;
      requestAnimationFrame(() => {
        ticking.current = false;
        let current: string | null = null;
        for (const h of headings) {
          const el = document.getElementById(h.id);
          if (el && el.getBoundingClientRect().top <= 96) current = h.id;
        }
        if (!current && headings[0]) {
          current = headings[0].id;
        }
        setActiveId(current);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [headings]);

  if (headings.length === 0) return null;

  return (
    <nav className="toc" aria-label="On this page">
      <h4 className="toc-title">On this page</h4>
      <ul>
        {headings.map((h) => (
          <li
            key={h.id}
            className={`toc-item toc-level-${h.level} ${
              activeId === h.id ? "is-active" : ""
            }`}
          >
            <a
              href={`#${h.id}`}
              onClick={(e) => {
                e.preventDefault();
                document
                  .getElementById(h.id)
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}