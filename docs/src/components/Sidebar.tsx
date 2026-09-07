import { NavLink } from "react-router-dom";
import { GROUPS, pageRoute } from "../content/registry";

export default function Sidebar() {
  const closeDrawer = () => {
    document.body.classList.remove("nav-open");
    const hamburger = document.getElementById("nav-toggle");
    if (hamburger) hamburger.setAttribute("aria-expanded", "false");
  };

  return (
    <div className="sidebar-wrap">
      <button
        type="button"
        className="sidebar-backdrop"
        aria-label="Close navigation"
        onClick={closeDrawer}
        tabIndex={-1}
      />
      <aside className="sidebar" aria-label="Documentation navigation">
        <div className="sidebar-head">
          <button type="button" className="sidebar-close" onClick={closeDrawer} aria-label="Close navigation">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <nav className="sidebar-nav">
          {GROUPS.map((group) => (
            <div className="sidebar-group" key={group.id}>
              <h3 className="sidebar-group-label">
                <span>{group.label}</span>
              </h3>
              <ul>
                {group.pages.map((page) => (
                  <li key={page.slug}>
                    <NavLink
                      to={pageRoute(group.id, page.slug)}
                      onClick={closeDrawer}
                      className={({ isActive }) =>
                        `sidebar-link${isActive ? " is-active" : ""}`
                      }
                    >
                      {page.title}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span>AI Agent Bank documentation</span>
          <span className="sidebar-version">Part 10 / 10</span>
        </div>
      </aside>
    </div>
  );
}