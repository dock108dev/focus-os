import type { WatchItem } from "./types";

export function listText(values: string[]) {
  return values.length ? values.join(", ") : "None configured";
}

export function splitList(value: string) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function normalizeSymbol(value: string) {
  return value.trim().replace(/^\$/, "").toUpperCase();
}

export function parseSymbolNotes(value: string) {
  return value
    .split(/\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((acc, line) => {
      const [rawSymbol, ...noteParts] = line.split(":");
      const symbol = normalizeSymbol(rawSymbol);
      const note = noteParts.join(":").trim();
      if (symbol && note) acc[symbol] = note;
      return acc;
    }, {});
}

export function symbolNotesText(watch: WatchItem) {
  const notes = watch.personal_context.manual_facts?.symbol_notes ?? {};
  return Object.entries(notes)
    .map(([symbol, value]) => {
      const note = typeof value === "string" ? value : value.note || value.thesis || "";
      const position = typeof value === "string" ? "" : value.position || "";
      const detail = [position, note].filter(Boolean).join(" - ");
      return detail ? `${symbol}: ${detail}` : symbol;
    })
    .join("\n");
}

export function trackedSymbolsText(watch: WatchItem) {
  return (watch.personal_context.manual_facts?.tracked_symbols ?? []).join(", ");
}

export function watchKindLabel(kind: WatchItem["watch_kind"]) {
  if (kind === "external_monitor") return "External Monitor";
  if (kind === "hybrid") return "Hybrid";
  return "Personal Tracker";
}

export function watchPriorityLabel(priority: WatchItem["priority"]) {
  if (priority === "primary_allowed") return "Primary allowed";
  if (priority === "quiet_by_default") return "Quiet by default";
  return "Watch only";
}

export function thresholdText(values: Record<string, number>) {
  const entries = Object.entries(values);
  if (!entries.length) return "";
  return entries
    .map(([key, value]) => `${key.replace(/_/g, " ")} ${Math.round(value * 100)}%`)
    .join(", ");
}

export function formatSourceWatchLabel(value: string) {
  if (value === "system:manual-or-topic-import") return "System/manual import";
  if (value.startsWith("system:")) return value.replace("system:", "System: ").replace(/-/g, " ");
  if (value.startsWith("watch:")) return value.replace("watch:", "").replace(/-/g, " ");
  return value;
}
