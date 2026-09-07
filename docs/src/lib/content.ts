const modules = import.meta.glob(
  "../content/pages/**/*.md",
  { query: "?raw", import: "default", eager: true }
) as Record<string, string>;

export function getContent(group: string, slug: string): string | undefined {
  return modules[`../content/pages/${group}/${slug}.md`];
}

export function contentKeys(): string[] {
  return Object.keys(modules);
}