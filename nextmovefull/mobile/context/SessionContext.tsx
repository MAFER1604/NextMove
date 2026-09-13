import React, { createContext, useContext } from "react";
import { useSession, UseSessionReturn } from "../hooks/useSession";

const SessionContext = createContext<UseSessionReturn | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useSessionContext(): UseSessionReturn {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessionContext must be used within a SessionProvider");
  return ctx;
}
