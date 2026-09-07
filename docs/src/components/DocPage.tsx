import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import { findPage, prevNext } from "../content/registry";
import { getContent } from "../lib/content";
import TopNav from "./TopNav";
import Sidebar from "./Sidebar";
import Breadcrumbs from "./Breadcrumbs";
import Markdown, { extractHeadings } from "./Markdown";
import Toc from "./Toc";
import PrevNext from "./PrevNext";
import Footer from "./Footer";
import NotFoundPage from "./NotFoundPage";

export default function DocPage() {
  const { group = "", slug = "" } = useParams();
  const entry = findPage(group, slug);
  const md = entry ? getContent(entry.group.id, entry.page.slug) : undefined;
  const path = `${group}/${slug}`;

  const headings = useMemo(() => (md ? extractHeadings(md) : []), [md]);
  const nav = useMemo(
    () => (entry ? prevNext(entry.group.id, entry.page.slug) : {}),
    [entry]
  );

  useEffect(() => {
    if (entry) {
      document.title = `${entry.page.title} — AI Agent Bank Docs`;
      let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!meta) {
        meta = document.createElement("meta");
        meta.name = "description";
        document.head.appendChild(meta);
      }
      meta.content = entry.page.description;
    }
  }, [entry]);

  useEffect(() => {
    if (entry) window.scrollTo({ top: 0, behavior: "auto" });
  }, [path, entry]);

  if (!entry || md === undefined) {
    return <NotFoundPage />;
  }

  return (
    <div className="app">
      <TopNav />
      <div className="layout">
        <Sidebar />
        <main className="content">
          <Breadcrumbs group={entry.group.label} title={entry.page.title} />
          <article className="article">
            <header className="doc-header">
              <h1>{entry.page.title}</h1>
              <p className="doc-description">{entry.page.description}</p>
            </header>
            <Markdown md={md} />
          </article>
          <PrevNext prev={nav.prev} next={nav.next} />
          <Footer />
        </main>
        <div className="sidebar-right">
          <Toc headings={headings} />
        </div>
      </div>
    </div>
  );
}