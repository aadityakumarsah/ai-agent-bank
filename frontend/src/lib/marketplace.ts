import type { LucideIcon } from "lucide-react";
import {
  ServerCog,
  Search,
  BarChart3,
  Sparkles,
  Database,
  Bot,
} from "lucide-react";
import type { ServiceCategory } from "@/lib/types";

export const CATEGORY_META: Record<
  ServiceCategory,
  { label: string; icon: LucideIcon; description: string }
> = {
  api: { label: "API", icon: Search, description: "Web & knowledge APIs" },
  compute: { label: "Compute", icon: ServerCog, description: "RPC & compute providers" },
  data: { label: "Data", icon: BarChart3, description: "Market & analytics data" },
  ai_model: { label: "AI Model", icon: Sparkles, description: "Model inference & generation" },
  storage: { label: "Storage", icon: Database, description: "Vector & object storage" },
  other_agent: { label: "Other Agent", icon: Bot, description: "Peer agent services" },
};

export const CATEGORY_ORDER: ServiceCategory[] = [
  "api",
  "compute",
  "data",
  "ai_model",
  "storage",
  "other_agent",
];

export const RISK_TONES: Record<
  string,
  "success" | "warning" | "destructive" | "neutral" | "info"
> = {
  low: "success",
  medium: "warning",
  high: "destructive",
};

export function categoryLabel(c: string): string {
  return CATEGORY_META[c as ServiceCategory]?.label ?? c;
}

export function categoryIcon(c: string): LucideIcon {
  return CATEGORY_META[c as ServiceCategory]?.icon ?? Search;
}