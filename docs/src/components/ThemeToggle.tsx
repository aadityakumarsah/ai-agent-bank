import { useTheme } from "../hooks/useTheme";

export default function ThemeToggle() {
  const { pref, cycle } = useTheme();
  const label =
    pref === "dark" ? "Switch to light theme" : pref === "light" ? "Switch to dark theme" : "Switch theme (system)";

  return (
    <button
      type="button"
      className="icon-btn"
      onClick={cycle}
      aria-label={label}
      title={label}
    >
      <span className="theme-icon theme-icon-sun" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </svg>
      </span>
      <span className="theme-icon theme-icon-moon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </span>
    </button>
  );
}