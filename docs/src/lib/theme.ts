export type ThemePreference = "light" | "dark" | "system";

const STORAGE_KEY = "aibank-docs-theme";

export function resolveTheme(pref: ThemePreference): "light" | "dark" {
  if (pref === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return pref;
}

export function getStoredPreference(): ThemePreference {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* ignore */
  }
  return "system";
}

export function setTheme(pref: ThemePreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    /* ignore */
  }
  document.documentElement.setAttribute("data-theme", resolveTheme(pref));
}

export function initTheme(): void {
  setTheme(getStoredPreference());
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      if (getStoredPreference() === "system") {
        document.documentElement.setAttribute("data-theme", resolveTheme("system"));
      }
    });
}

export function nextPreference(cur: ThemePreference): ThemePreference {
  if (cur === "system") return "light";
  if (cur === "light") return "dark";
  return "system";
}