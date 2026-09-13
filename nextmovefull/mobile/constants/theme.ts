export const colors = {
  navy: "#0F172A",
  primary: "#2563EB",
  primarySoft: "#DBEAFE",
  green: "#10B981",
  greenSoft: "#D1FAE5",
  red: "#EF4444",
  redSoft: "#FEE2E2",
  amber: "#F59E0B",
  amberSoft: "#FEF3C7",
  background: "#F8FAFC",
  card: "#FFFFFF",
  textPrimary: "#0F172A",
  textSecondary: "#64748B",
  border: "#E2E8F0",

  // roles de ruta (sección 9 del brief)
  routeToPickup: "#2563EB",
  routeToDropoff: "#10B981",
  routeToDestination: "#0F172A",
  routeDirect: "#CBD5E1",
  routeBlocked: "#EF4444",
  routeCompleted: "#94A3B8",
};

export const radius = { sm: 10, md: 16, lg: 24, pill: 999 };

export const shadow = {
  card: {
    shadowColor: "#0F172A", shadowOpacity: 0.08, shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 }, elevation: 3,
  },
  floating: {
    shadowColor: "#0F172A", shadowOpacity: 0.16, shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 }, elevation: 8,
  },
};

export const typography = {
  display: { fontSize: 30, fontWeight: "800" as const, color: colors.textPrimary, letterSpacing: -0.5 },
  h1: { fontSize: 22, fontWeight: "700" as const, color: colors.textPrimary },
  h2: { fontSize: 17, fontWeight: "700" as const, color: colors.textPrimary },
  body: { fontSize: 15, color: colors.textPrimary, lineHeight: 21 },
  bodyMuted: { fontSize: 14, color: colors.textSecondary, lineHeight: 20 },
  caption: { fontSize: 12.5, color: colors.textSecondary },
  metricValue: { fontSize: 24, fontWeight: "800" as const, color: colors.textPrimary },
  metricLabel: { fontSize: 12, color: colors.textSecondary, fontWeight: "600" as const },
};

export const spacing = (n: number) => n * 8;
