import { Link } from "react-router-dom";

export default function Breadcrumbs({ group, title }: { group: string; title: string }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol>
        <li>
          <Link to="/">Docs</Link>
        </li>
        <li aria-hidden="true">/</li>
        <li>{group}</li>
        <li aria-hidden="true">/</li>
        <li aria-current="page">{title}</li>
      </ol>
    </nav>
  );
}