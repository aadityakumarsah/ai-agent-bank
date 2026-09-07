import { useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import DocPage from "./components/DocPage";
import NotFoundPage from "./components/NotFoundPage";

function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [pathname, hash]);
  return null;
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Navigate to="/get-started/welcome" replace />} />
        <Route path="/:group/:slug" element={<DocPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  );
}