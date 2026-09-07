"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConfigStatus } from "@/lib/types";

export function useConfigStatus() {
  const [status, setStatus] = useState<ConfigStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getStatus()
      .then(setStatus)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return { status, error };
}