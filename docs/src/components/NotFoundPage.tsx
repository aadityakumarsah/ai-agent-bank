import { useEffect } from "react";
import { Link } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import Footer from "./Footer";

export default function NotFoundPage() {
  useEffect(() => {
    document.title = "Page not found — AI Agent Bank Docs";
  }, []);

  return (
    <div className="app">
      <TopNav />
      <div className="layout">
        <Sidebar />
        <main className="content">
          <div className="notfound">
            <p className="notfound-code">404</p>
            <h1>Page not found</h1>
            <p>
              That page doesn't exist or hasn't been written yet. Try the search,
              or jump back into the docs.
            </p>
            <div className="notfound-links">
              <Link to="/" className="btn-primary">
                Home
              </Link>
              <Link to="/get-started/quickstart" className="btn-secondary">
                Quickstart
              </Link>
              <Link to="/api/overview" className="btn-secondary">
                API overview
              </Link>
            </div>
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}