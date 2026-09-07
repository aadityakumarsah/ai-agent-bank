import { useEffect, useState } from "react";
import {
  ThemePreference,
  getStoredPreference,
  nextPreference,
  resolveTheme,
  setTheme,
} from "../lib/theme";

export function useTheme() {
  const [pref, setPref] = useState<ThemePreference>(getStoredPreference);

  useEffect(() => {
    setTheme(pref);
  }, [pref]);

  const cycle = () => setPref((p) => nextPreference(p));
  const resolved = resolveTheme(pref);

  return { pref, resolved, cycle };
}