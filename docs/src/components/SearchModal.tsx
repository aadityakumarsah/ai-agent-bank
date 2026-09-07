import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { search, SearchHit } from "../lib/search";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function SearchModal({ open, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const navigate = useNavigate();

  const results = search(query);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const go = useCallback(
    (to: string) => {
      onClose();
      navigate(to);
    },
    [onClose, navigate]
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((a) => Math.min(a + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const hit = results[active];
        if (hit) go(hit.to);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, results, active, go, onClose]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  return (
    <div className="search-backdrop" role="dialog" aria-modal="true" aria-label="Search documentation">
      <div className="search-panel" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-row">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search docs, guides, API endpoints…"
            aria-label="Search"
          />
          <button className="search-esc" onClick={onClose} aria-label="Close search">
            Esc
          </button>
        </div>

        <div className="search-results-wrap">
          {query.trim() === "" ? (
            <p className="search-empty">Start typing to search every page, guide, and API endpoint.</p>
          ) : results.length === 0 ? (
            <p className="search-empty">No results for “{query}”.</p>
          ) : (
            <ul className="search-results" ref={listRef}>
              {results.map((hit: SearchHit, i) => (
                <li key={hit.to}>
                  <button
                    type="button"
                    data-index={i}
                    className={`search-result ${i === active ? "is-active" : ""}`}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(hit.to)}
                  >
                    <span className="search-result-title">{hit.title}</span>
                    <span className="search-result-desc">{hit.description}</span>
                    <span className="search-result-group">{hit.group}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="search-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> to navigate</span>
          <span><kbd>↵</kbd> to open</span>
          <span><kbd>esc</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}