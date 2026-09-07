import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { REPO_URL } from "../content/registry";
import SearchModal from "./SearchModal";
import ThemeToggle from "./ThemeToggle";

export default function TopNav() {
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setSearchOpen(false);
  }, [location.pathname]);

  const toggleNav = () => {
    const open = document.body.classList.toggle("nav-open");
    const hamburger = document.getElementById("nav-toggle");
    if (hamburger) hamburger.setAttribute("aria-expanded", String(open));
  };

  const closeNav = () => {
    document.body.classList.remove("nav-open");
    const hamburger = document.getElementById("nav-toggle");
    if (hamburger) hamburger.setAttribute("aria-expanded", "false");
  };

  return (
    <>
      <header className="topnav">
        <div className="topnav-inner">
          <button
            type="button"
            id="nav-toggle"
            className="btn-open-menu"
            aria-label="Toggle navigation menu"
            aria-expanded="false"
            onClick={toggleNav}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>

          <Link className="brand" to="/" onClick={closeNav}>
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3 10h18M8 22V5" />
              </svg>
            </span>
            <span className="brand-name">
              AI&nbsp;Agent&nbsp;Bank <span className="brand-sub">docs</span>
            </span>
          </Link>

          <button
            type="button"
            className="search-trigger"
            onClick={() => setSearchOpen(true)}
            aria-label="Search documentation"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <span className="search-trigger-text">Search…</span>
            <kbd>⌘K</kbd>
          </button>

          <button
            type="button"
            className="search-trigger search-trigger-mobile"
            onClick={() => setSearchOpen(true)}
            aria-label="Search documentation"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
          </button>

          <nav className="topnav-links" aria-label="Primary">
            <a href={`${REPO_URL}`} target="_blank" rel="noreferrer">GitHub</a>
            <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="topnav-cta">
              Launch dashboard
            </a>
          </nav>

          <ThemeToggle />
        </div>
      </header>

      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}