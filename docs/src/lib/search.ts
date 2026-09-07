import { searchIndex } from "../content/registry";

export interface SearchHit {
  to: string;
  group: string;
  title: string;
  description: string;
}

interface Source extends SearchHit {
  keywords: string[];
}

interface Scored {
  item: Source;
  score: number;
}

export function search(query: string, limit = 12): SearchHit[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const all: Source[] = searchIndex();
  const scored: Scored[] = [];
  for (const item of all) {
    const title = item.title.toLowerCase();
    const desc = item.description.toLowerCase();
    const kw = item.keywords.join(" ").toLowerCase();
    const group = item.group.toLowerCase();
    let score = 0;
    if (title === q) score = 100;
    else if (title.startsWith(q)) score = 80;
    else if (title.includes(q)) score = 60;
    else if (group.startsWith(q)) score = 40;
    else if (desc.includes(q)) score = 30;
    else if (kw.includes(q)) score = 20;
    if (score === 0) continue;
    if (title.split(" ").some((w) => w.startsWith(q))) score += 5;
    scored.push({ item, score });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map((s) => ({
    to: s.item.to,
    group: s.item.group,
    title: s.item.title,
    description: s.item.description,
  }));
}