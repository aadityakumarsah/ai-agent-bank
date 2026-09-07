import { REPO_URL } from "../content/registry";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p>
          <strong>AI Agent Bank</strong> — a programmable financial permission layer
          for AI agents. Built in 10 parts for a hackathon.
        </p>
        <nav aria-label="Footer">
          <a href={`${REPO_URL}`} target="_blank" rel="noreferrer">GitHub</a>
          <a href="http://localhost:8000/api/v1/status" target="_blank" rel="noreferrer">API status</a>
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">Dashboard</a>
        </nav>
        <p className="footer-note">
          Documentation reflects the current build. Simulated money is always
          labelled — AI Agent Bank never pretends mock is real.
        </p>
      </div>
    </footer>
  );
}