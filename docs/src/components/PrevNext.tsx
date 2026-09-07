import { Link } from "react-router-dom";

interface Props {
  prev?: { to: string; title: string };
  next?: { to: string; title: string };
}

export default function PrevNext({ prev, next }: Props) {
  return (
    <nav className="prevnext" aria-label="Page navigation">
      {prev ? (
        <Link className="prevnext-card prev" to={prev.to}>
          <span className="prevnext-label">← Previous</span>
          <span className="prevnext-title">{prev.title}</span>
        </Link>
      ) : (
        <span />
      )}
      {next ? (
        <Link className="prevnext-card next" to={next.to}>
          <span className="prevnext-label">Next →</span>
          <span className="prevnext-title">{next.title}</span>
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}