import type { WatchItem } from "./types";

export type AppView = "briefing" | "archive" | "watch-admin" | "appendix";

export type WatchPreset = {
  label: string;
  text: string;
};

export type GuidedWatchDraft = {
  title: string;
  watch_kind: WatchItem["watch_kind"];
  priority: WatchItem["priority"];
  cadence: "daily" | "weekly" | "event_driven";
  why_i_care: string;
  accounts: string;
  interests: string;
  symbols: string;
  symbol_notes: string;
  connected_sources: string;
  manual_inputs: string;
  surface_when: string;
  suppress_when: string;
  primary_focus_allowed: boolean;
  daily_prompt_override: string;
};

export type Provenance = {
  source_watch_ids: string[];
  triggered_surface_rule: string;
  suppressed_by: string | null;
  why_today: string;
};

export const WATCH_PRESETS: WatchPreset[] = [
  {
    label: "Markets",
    text: "Bitcoin range\nWatch price moves, threshold breaks, and material market context."
  },
  {
    label: "Sports",
    text: "Yankees and Rutgers\nWatch game timing, schedule changes, injuries, and results worth remembering."
  },
  {
    label: "Travel",
    text: "Upcoming travel\nWatch weather, airport timing, parking, hotel changes, and itinerary updates."
  },
  {
    label: "Family",
    text: "Family date\nWatch timing, location changes, gift deadlines, and planning blockers."
  },
  {
    label: "Home",
    text: "Home maintenance\nWatch due dates, weather risk, contractor timing, and small tasks becoming expensive."
  },
  {
    label: "Pets",
    text: "Bogey care\nWatch appointments, food, boarding, medication, and coverage gaps."
  },
  {
    label: "Health",
    text: "Health admin\nWatch appointment windows, insurance paperwork, refills, and scheduling deadlines."
  },
  {
    label: "Work",
    text: "Work migration\nWatch blocked teams, deadline movement, adoption gaps, and decisions needed this week."
  },
  {
    label: "Projects",
    text: "Side project\nWatch validation, costs, progress stalls, and ship-or-stop signals."
  },
  {
    label: "Tech",
    text: "WWDC and coding tools\nWatch developer tooling, API changes, pricing, and workflow changes."
  }
];

export const EMPTY_GUIDED_WATCH: GuidedWatchDraft = {
  title: "",
  watch_kind: "hybrid",
  priority: "watch_only",
  cadence: "daily",
  why_i_care: "",
  accounts: "",
  interests: "",
  symbols: "",
  symbol_notes: "",
  connected_sources: "",
  manual_inputs: "",
  surface_when: "",
  suppress_when: "",
  primary_focus_allowed: false,
  daily_prompt_override: ""
};
