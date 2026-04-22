import type { Period } from "../types";

export const PERIODS: { label: string; value: Period }[] = [
  { label: "1D", value: "1D" },
  { label: "1W", value: "1W" },
  { label: "1M", value: "1M" },
  { label: "3M", value: "3M" },
  { label: "6M", value: "6M" },
  { label: "YTD", value: "YTD" },
  { label: "1Y", value: "1Y" },
  { label: "ALL", value: "ALL" },
];

export const CHART_GREEN = "#4CAF50";
export const CHART_GREEN_LIGHT = "rgba(76,175,80,0.15)";
export const CHART_RED = "#EF5350";
export const CHART_RED_LIGHT = "rgba(239,83,80,0.15)";

export const CHART_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16",
];

export const CHART_BLUE = "#64748B";
