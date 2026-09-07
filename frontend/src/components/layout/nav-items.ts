import {
  LayoutGrid,
  Bot,
  ArrowLeftRight,
  Shield,
  Inbox,
  Activity,
  Settings2,
  Store,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutGrid, exact: true },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/marketplace", label: "Marketplace", icon: Store },
  { href: "/policies", label: "Policies", icon: Shield },
  { href: "/approvals", label: "Approvals", icon: Inbox },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings2 },
];