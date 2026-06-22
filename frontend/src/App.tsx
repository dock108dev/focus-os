import { Archive, Check, ClipboardList, FileText, ListChecks, Pencil, Plus, RefreshCw, Save, Trash2, Upload, X } from "lucide-react";
import { ChangeEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { requestJson, sourceFromFile } from "./api";
import type { AssistantBriefing, AssistantBriefingItem, Briefing, RecommendationDetail, WatchItem, WatchListResponse } from "./types";

type AppView = "briefing" | "archive" | "watch-admin" | "appendix";

type WatchPreset = {
  label: string;
  text: string;
};

type GuidedWatchDraft = {
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

type Provenance = {
  source_watch_ids: string[];
  triggered_surface_rule: string;
  suppressed_by: string | null;
  why_today: string;
};

const WATCH_PRESETS: WatchPreset[] = [
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

const EMPTY_GUIDED_WATCH: GuidedWatchDraft = {
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

function BriefingHeader({
  activeView,
  briefingDate,
  attentionCount,
  onViewChange,
  onRefresh,
  onImport,
  loading,
  importing,
  readOnly
}: {
  activeView: AppView;
  briefingDate: string;
  attentionCount: number | null;
  onViewChange: (view: AppView) => void;
  onRefresh: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
  loading: boolean;
  importing: boolean;
  readOnly: boolean;
}) {
  const sectionTitle =
    activeView === "watch-admin"
      ? "Watch Admin"
      : activeView === "archive"
        ? "Archive"
        : activeView === "appendix"
          ? "Appendix"
          : "Morning Briefing";

  return (
    <header className="masthead">
      <div className="mastheadCopy">
        <h1>FocusOS</h1>
        <p className="sectionTitle">{sectionTitle}</p>
        <p className="briefingMeta">
          {briefingDate}
          {attentionCount !== null && activeView === "briefing" ? ` · ${attentionCount} outputs` : ""}
          {readOnly && activeView === "archive" ? " · archived snapshot" : ""}
        </p>
        <nav className="viewNav" aria-label="FocusOS sections">
          <button type="button" className={activeView === "briefing" ? "selected" : ""} onClick={() => onViewChange("briefing")}>
            <ListChecks size={16} />
            Briefing
          </button>
          <button type="button" className={activeView === "archive" ? "selected" : ""} onClick={() => onViewChange("archive")}>
            <Archive size={16} />
            Archive
          </button>
          <button type="button" className={activeView === "watch-admin" ? "selected" : ""} onClick={() => onViewChange("watch-admin")}>
            <ClipboardList size={16} />
            Watch Admin
          </button>
          <button type="button" className={activeView === "appendix" ? "selected" : ""} onClick={() => onViewChange("appendix")}>
            <FileText size={16} />
            Appendix
          </button>
        </nav>
      </div>
      <div className="actions">
        {activeView === "briefing" && (
          <label className="iconButton" title="Import CSV">
            <Upload size={18} />
            <input type="file" accept=".csv,text/csv" onChange={onImport} disabled={importing || readOnly} />
          </label>
        )}
        <button className="iconButton" type="button" onClick={onRefresh} disabled={loading} title="Refresh">
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}

function AssistantItemButton({
  item,
  onAppendix,
  className = ""
}: {
  item: AssistantBriefingItem;
  onAppendix: (item: AssistantBriefingItem) => void;
  className?: string;
}) {
  const itemClass = `assistantItem ${className}`;
  if (!item.detail_id) {
    return (
      <article className={`${itemClass} staticItem`}>
        <h3>{item.title}</h3>
        <p>{item.summary}</p>
      </article>
    );
  }

  return (
    <button className={itemClass} type="button" onClick={() => onAppendix(item)}>
      <h3>{item.title}</h3>
      <p>{item.summary}</p>
    </button>
  );
}

function AssistantBriefingView({
  briefing,
  onAppendix
}: {
  briefing: AssistantBriefing;
  onAppendix: (item: AssistantBriefingItem) => void;
}) {
  const hasPrimaryFocus = briefing.mode === "focused" && Boolean(briefing.primary_focus.detail_id);
  const notes = briefing.secondary_notes.filter((item) => item.detail_id || item.summary);
  const needsAttention = briefing.needs_attention ?? [];
  const watchOnly = briefing.watch_only ?? notes;
  const catchUp = briefing.catch_up ?? [];
  const quiet = briefing.quiet ?? [];

  return (
    <section className={`assistantBriefing ${hasPrimaryFocus ? "focusedBriefing" : "quietBriefing"}`}>
      <header className="assistantGreeting">
        <h2>{briefing.greeting}</h2>
      </header>

      {hasPrimaryFocus ? (
        <section className="primaryFocus">
          <p className="sectionKicker">Primary focus</p>
          <AssistantItemButton item={briefing.primary_focus} onAppendix={onAppendix} className="primaryAssistantItem" />
        </section>
      ) : (
        <section className="quietSpotlight">
          <p className="sectionKicker">No spotlight</p>
          <p>Nothing deserves the spotlight today.</p>
        </section>
      )}

      <section className="secondaryNotes">
        <p className="sectionKicker">Needs attention</p>
        {needsAttention.length > 0 ? (
          <div className="noteList">
            {needsAttention.map((item) => (
              <AssistantItemButton item={item} key={`needs-${item.detail_id}-${item.title}`} onAppendix={onAppendix} className="noteItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No decisions, risks, or plan changes need action.</p>
        )}
      </section>

      <section className="secondaryNotes">
        <p className="sectionKicker">Watch only</p>
        {watchOnly.length > 0 ? (
          <div className="noteList">
            {watchOnly.map((item) => (
              <AssistantItemButton item={item} key={`watch-${item.detail_id}-${item.title}`} onAppendix={onAppendix} className="noteItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No useful context needs to stay top-of-mind.</p>
        )}
      </section>

      <section className="secondaryNotes">
        <p className="sectionKicker">Catch up</p>
        {catchUp.length > 0 ? (
          <div className="noteList">
            {catchUp.map((item) => (
              <AssistantItemButton item={item} key={`catch-${item.detail_id}-${item.title}`} onAppendix={onAppendix} className="noteItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No completed events need catch-up time.</p>
        )}
      </section>

      <section className="secondaryNotes">
        <p className="sectionKicker">Quiet</p>
        {quiet.length > 0 ? (
          <div className="noteList quietNoteList">
            {quiet.slice(0, 6).map((item) => (
              <AssistantItemButton item={item} key={`quiet-${item.detail_id}-${item.title}`} onAppendix={onAppendix} className="noteItem quietItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No quiet checks reported.</p>
        )}
      </section>
    </section>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "None";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function toReadableRows(data: unknown): Array<[string, string]> {
  if (!data || typeof data !== "object" || Array.isArray(data)) return [["value", formatValue(data)]];
  return Object.entries(data as Record<string, unknown>)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => [key.split("_").join(" "), formatValue(value)]);
}

function friendlySourceLabel(value: string) {
  const lower = value.toLowerCase();
  if (lower === "openai-web-search" || lower === "codex-cli") return "Web research";
  if (lower === "structured") return "Structured source";
  return value;
}

function sourceRows(data: Record<string, unknown>): Array<[string, string]> {
  return Object.entries(data)
    .filter(([key, value]) => value !== null && value !== undefined && !key.startsWith("parsed_") && key !== "source_type")
    .map(([key, value]) => [key.split("_").join(" "), friendlySourceLabel(formatValue(value))]);
}

function ReadableDataTable({ data }: { data: unknown }) {
  const rows = toReadableRows(data).filter(([, value]) => value.length < 180);
  return (
    <table className="dataTable">
      <tbody>
        {rows.slice(0, 12).map(([key, value]) => (
          <tr key={key}>
            <th>{key}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RawDataTable({ data }: { data: unknown }) {
  return (
    <details className="rawPayload">
      <summary>Raw payloads</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function SourceList({ data }: { data: Record<string, unknown> }) {
  const rows = sourceRows(data);
  if (rows.length === 0) return <p>No source notes available.</p>;
  return (
    <ul className="sourceNotes">
      {rows.map(([key, value]) => (
        <li key={key}>
          <strong>{key}</strong>
          <span>{value}</span>
        </li>
      ))}
    </ul>
  );
}

function AIProcessingPanel({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return null;
  return (
    <DetailSection title="Methodology">
      <ReadableDataTable data={data} />
      <RawDataTable data={data} />
    </DetailSection>
  );
}

function SuppressedItemsPanel({ items }: { items: unknown[] }) {
  return (
    <DetailSection title="Items not shown">
      {items.length > 0 ? <ReadableDataTable data={{ count: items.length }} /> : <p>No meaningful items were hidden for this recommendation.</p>}
      <RawDataTable data={items} />
    </DetailSection>
  );
}

function supportingFacts(detail: RecommendationDetail) {
  const rawBullets = detail.raw_data?.bullets;
  const facts = Array.isArray(rawBullets) ? rawBullets.map((item) => String(item)).filter(Boolean) : [];
  const generated = detail.why_generated.filter(Boolean);
  return facts.length > 0 ? facts : generated;
}

function detailList(data: Record<string, unknown>, key: string) {
  const value = data[key];
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function recordValue(data: unknown, key: string): unknown {
  if (!data || typeof data !== "object" || Array.isArray(data)) return undefined;
  return (data as Record<string, unknown>)[key];
}

function extractProvenance(item: AssistantBriefingItem | null, detail: RecommendationDetail | null): Provenance {
  const rawProvenance = recordValue(detail?.raw_data, "provenance");
  const sourceWatchIds = recordValue(rawProvenance, "source_watch_ids");
  return {
    source_watch_ids: item?.source_watch_ids.length ? item.source_watch_ids : Array.isArray(sourceWatchIds) ? sourceWatchIds.map(String) : [],
    triggered_surface_rule: item?.triggered_surface_rule || String(recordValue(rawProvenance, "triggered_surface_rule") || ""),
    suppressed_by: item?.suppressed_by ?? (recordValue(rawProvenance, "suppressed_by") as string | null | undefined) ?? null,
    why_today: item?.why_today || String(recordValue(rawProvenance, "why_today") || "")
  };
}

function todayIso() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(dateText: string, days: number) {
  const next = new Date(`${dateText}T12:00:00`);
  next.setDate(next.getDate() + days);
  const year = next.getFullYear();
  const month = String(next.getMonth() + 1).padStart(2, "0");
  const correctedDay = String(next.getDate()).padStart(2, "0");
  return `${year}-${month}-${correctedDay}`;
}

function formatBriefingDate(dateText: string) {
  return new Date(`${dateText}T12:00:00`).toLocaleDateString([], {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}

function listText(values: string[]) {
  return values.length ? values.join(", ") : "None configured";
}

function splitList(value: string) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeSymbol(value: string) {
  return value.trim().replace(/^\$/, "").toUpperCase();
}

function parseSymbolNotes(value: string) {
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

function symbolNotesText(watch: WatchItem) {
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

function trackedSymbolsText(watch: WatchItem) {
  return (watch.personal_context.manual_facts?.tracked_symbols ?? []).join(", ");
}

function watchKindLabel(kind: WatchItem["watch_kind"]) {
  if (kind === "external_monitor") return "External Monitor";
  if (kind === "hybrid") return "Hybrid";
  return "Personal Tracker";
}

function watchPriorityLabel(priority: WatchItem["priority"]) {
  if (priority === "primary_allowed") return "Primary allowed";
  if (priority === "quiet_by_default") return "Quiet by default";
  return "Watch only";
}

function thresholdText(values: Record<string, number>) {
  const entries = Object.entries(values);
  if (!entries.length) return "";
  return entries
    .map(([key, value]) => `${key.replace(/_/g, " ")} ${Math.round(value * 100)}%`)
    .join(", ");
}

function formatSourceWatchLabel(value: string) {
  if (value === "system:manual-or-topic-import") return "System/manual import";
  if (value.startsWith("system:")) return value.replace("system:", "System: ").replace(/-/g, " ");
  if (value.startsWith("watch:")) return value.replace("watch:", "").replace(/-/g, " ");
  return value;
}

function WatchConfigRows({ watch }: { watch: WatchItem }) {
  const knownFacts = [
    watch.personal_context.why_i_care,
    ...watch.personal_state.known_facts,
    thresholdText(watch.personal_state.thresholds),
    watch.personal_state.next_relevant_date ? `Next relevant date ${watch.personal_state.next_relevant_date}` : ""
  ].filter(Boolean);
  const rows: Array<[string, string]> = [
    ["Personal Accounts", listText(watch.personal_accounts)],
    ["Interests", listText(watch.personal_interests)],
    ["Symbols", trackedSymbolsText(watch) || "None configured"],
    ["Symbol Notes", symbolNotesText(watch) || "None configured"],
    ["Connected Data Sources", listText(watch.connected_data_sources)],
    ["Missing Sources", listText(watch.missing_sources)],
    ["Manual Inputs", listText(watch.manual_inputs)],
    ["What I know", listText(knownFacts)],
    ["When this should surface", listText(watch.evaluation_rules.surface_when)],
    ["When this should stay quiet", listText(watch.evaluation_rules.suppress_when)],
    ["Can become Primary Focus", watch.evaluation_rules.primary_focus_allowed ? "Yes" : "No"],
    ["Validation", listText(watch.validation_warnings)],
    ["Cadence", watch.cadence],
    ["Expiration", watch.expires_at || "No expiration"]
  ];
  return (
    <>
      <dl className="watchConfigRows">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <details className="promptPreview">
        <summary>Generated prompt</summary>
        <pre>{watch.prompt_config.generated_prompt}</pre>
      </details>
    </>
  );
}

function WatchAdminView({
  watches,
  activeCount,
  draft,
  guidedDraft,
  editingId,
  busy,
  onDraftChange,
  onGuidedDraftChange,
  onSubmit,
  onGuidedSubmit,
  onEdit,
  onCancelEdit,
  onComplete,
  onArchive,
  onDelete,
  onUsePreset
}: {
  watches: WatchItem[];
  activeCount: number;
  draft: string;
  guidedDraft: GuidedWatchDraft;
  editingId: number | null;
  busy: boolean;
  onDraftChange: (value: string) => void;
  onGuidedDraftChange: (value: GuidedWatchDraft) => void;
  onSubmit: () => void;
  onGuidedSubmit: () => void;
  onEdit: (watch: WatchItem) => void;
  onCancelEdit: () => void;
  onComplete: (watchId: number) => void;
  onArchive: (watchId: number) => void;
  onDelete: (watchId: number) => void;
  onUsePreset: (preset: WatchPreset) => void;
}) {
  return (
    <section className="watchAdmin">
      <div className="adminSummary">
        <span>{activeCount} active</span>
        <span>{watches.length} total</span>
      </div>

      <section className="presetPanel">
        <p className="sectionKicker">Presets</p>
        <div className="presetGrid">
          {WATCH_PRESETS.map((preset) => (
            <button type="button" key={preset.label} onClick={() => onUsePreset(preset)} disabled={busy}>
              <Plus size={15} />
              {preset.label}
            </button>
          ))}
        </div>
      </section>

      <section className="watchComposerPanel">
        <div className="watchOwnerHeader">
          <span>{editingId ? "Editing watch" : "New watch"}</span>
          {editingId && (
            <button className="miniIconButton" type="button" onClick={onCancelEdit} disabled={busy} title="Cancel edit">
              <X size={15} />
            </button>
          )}
        </div>
        <div className="watchComposer">
          <textarea
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            placeholder="Outdoor concert Friday&#10;Watch weather, parking, timing, and venue changes."
            rows={4}
            disabled={busy}
          />
          <button className="iconButton" type="button" onClick={onSubmit} disabled={busy || !draft.trim()} title={editingId ? "Save watch" : "Add watch"}>
            {editingId ? <Save size={17} /> : <Plus size={17} />}
          </button>
        </div>
      </section>

      <section className="guidedSetupPanel">
        <div className="watchOwnerHeader">
          <span>Guided setup</span>
        </div>
        <div className="guidedGrid">
          <input value={guidedDraft.title} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, title: event.target.value })} placeholder="Watch name" disabled={busy} />
          <select value={guidedDraft.watch_kind} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, watch_kind: event.target.value as WatchItem["watch_kind"] })} disabled={busy}>
            <option value="personal_tracker">Personal Tracker</option>
            <option value="external_monitor">External Monitor</option>
            <option value="hybrid">Hybrid</option>
          </select>
          <select value={guidedDraft.priority} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, priority: event.target.value as WatchItem["priority"] })} disabled={busy}>
            <option value="primary_allowed">Primary allowed</option>
            <option value="watch_only">Watch only</option>
            <option value="quiet_by_default">Quiet by default</option>
          </select>
          <select value={guidedDraft.cadence} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, cadence: event.target.value as GuidedWatchDraft["cadence"] })} disabled={busy}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="event_driven">Event driven</option>
          </select>
        </div>
        <textarea value={guidedDraft.why_i_care} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, why_i_care: event.target.value })} placeholder="Why I care" rows={2} disabled={busy} />
        <div className="guidedGrid">
          <textarea value={guidedDraft.accounts} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, accounts: event.target.value })} placeholder="Personal accounts / interests" rows={3} disabled={busy} />
          <textarea value={guidedDraft.connected_sources} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, connected_sources: event.target.value })} placeholder="Connected data sources" rows={3} disabled={busy} />
          <textarea value={guidedDraft.manual_inputs} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, manual_inputs: event.target.value })} placeholder="Manual inputs needed" rows={3} disabled={busy} />
          <textarea value={guidedDraft.interests} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, interests: event.target.value })} placeholder="Interests / owned assets" rows={3} disabled={busy} />
        </div>
        <div className="guidedGrid">
          <textarea value={guidedDraft.symbols} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, symbols: event.target.value })} placeholder="Symbols, one per line or comma-separated" rows={3} disabled={busy} />
          <textarea value={guidedDraft.symbol_notes} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, symbol_notes: event.target.value })} placeholder="Symbol notes, one per line. Example: USO: short position; alert when it moves in favor" rows={3} disabled={busy} />
        </div>
        <div className="guidedGrid">
          <textarea value={guidedDraft.surface_when} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, surface_when: event.target.value })} placeholder="When this should surface" rows={3} disabled={busy} />
          <textarea value={guidedDraft.suppress_when} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, suppress_when: event.target.value })} placeholder="When this should stay quiet" rows={3} disabled={busy} />
        </div>
        <textarea value={guidedDraft.daily_prompt_override} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, daily_prompt_override: event.target.value })} placeholder="Advanced daily prompt override" rows={3} disabled={busy} />
        <label className="checkLine">
          <input type="checkbox" checked={guidedDraft.primary_focus_allowed} onChange={(event) => onGuidedDraftChange({ ...guidedDraft, primary_focus_allowed: event.target.checked })} disabled={busy} />
          Can become Primary Focus
        </label>
        <button className="textButton" type="button" onClick={onGuidedSubmit} disabled={busy || !guidedDraft.title.trim()} title={editingId ? "Save guided watch" : "Add guided watch"}>
          {editingId ? <Save size={15} /> : <Plus size={15} />}
          {editingId ? "Save guided watch" : "Add guided watch"}
        </button>
      </section>

      <section className="ownedWatchList">
        {watches.map((watch) => (
          <article className="ownedWatchItem" key={watch.id}>
            <div>
              <div className="watchItemTitleRow">
                <h3>{watch.title}</h3>
                <div className="watchBadges">
                  <span>{watchKindLabel(watch.watch_kind)}</span>
                  <span>{watchPriorityLabel(watch.priority)}</span>
                  <span>{watch.status}</span>
                </div>
              </div>
              <p>{watch.why_today || watch.latest_evaluation?.summary || watch.original_text}</p>
              <WatchConfigRows watch={watch} />
            </div>
            <div className="watchItemActions">
              <button className="miniIconButton" type="button" onClick={() => onEdit(watch)} disabled={busy} title="Edit watch">
                <Pencil size={15} />
              </button>
              {watch.status === "active" && (
                <button className="miniIconButton" type="button" onClick={() => onComplete(watch.id)} disabled={busy} title="Complete watch">
                  <Check size={15} />
                </button>
              )}
              <button className="miniIconButton" type="button" onClick={() => onArchive(watch.id)} disabled={busy} title="Archive watch">
                <Archive size={15} />
              </button>
              <button className="miniIconButton dangerButton" type="button" onClick={() => onDelete(watch.id)} disabled={busy} title="Remove watch">
                <Trash2 size={15} />
              </button>
            </div>
          </article>
        ))}
        {watches.length === 0 && <p className="quietLine">No watches configured.</p>}
      </section>
    </section>
  );
}

function ArchiveView({
  briefing,
  selectedDate,
  currentDate,
  loading,
  onPreviousDay,
  onToday,
  onNextDay,
  onAppendix
}: {
  briefing: Briefing | null;
  selectedDate: string;
  currentDate: string;
  loading: boolean;
  onPreviousDay: () => void;
  onToday: () => void;
  onNextDay: () => void;
  onAppendix: (item: AssistantBriefingItem) => void;
}) {
  const isToday = selectedDate === currentDate;
  return (
    <section className="archiveView">
      <nav className="dateNav" aria-label="Briefing archive">
        <button type="button" onClick={onPreviousDay} disabled={loading}>
          Previous Day
        </button>
        <button type="button" onClick={onToday} disabled={loading || isToday}>
          Today
        </button>
        <button type="button" onClick={onNextDay} disabled={loading || isToday}>
          Next Day
        </button>
      </nav>

      {briefing?.archive_review && (
        <section className="archiveReview">
          <p className="sectionKicker">Simulation</p>
          <h2>{briefing.archive_review.scenario}</h2>
          <p>{briefing.archive_review.notes}</p>
        </section>
      )}

      {briefing ? <AssistantBriefingView briefing={briefing.assistant_briefing} onAppendix={onAppendix} /> : <p className="emptyState">No archived briefing loaded.</p>}
    </section>
  );
}

function AppendixView({
  item,
  detail,
  detailLoading,
  watches
}: {
  item: AssistantBriefingItem | null;
  detail: RecommendationDetail | null;
  detailLoading: boolean;
  watches: WatchItem[];
}) {
  const provenance = extractProvenance(item, detail);
  const watchNameById = new Map(
    watches.flatMap((watch) => [
      [`watch:${watch.id}`, watch.title],
      [watch.source_watch_id, watch.title]
    ])
  );
  const sourceWatches = provenance.source_watch_ids.map((id) => watchNameById.get(id) || formatSourceWatchLabel(id));

  return (
    <section className="appendixView">
      <div className="detailPanel inlineDetailPanel">
        <div className="detailHeader">
          <div>
            <p className="eyebrow">Decision Appendix</p>
            <h2>{detailLoading ? "Loading" : detail?.title || item?.title || "Select a briefing output"}</h2>
          </div>
        </div>

        <div className="detailBody">
          <DetailSection title="Provenance">
            <dl className="provenanceRows">
              <div>
                <dt>Source watch</dt>
                <dd>{sourceWatches.length ? sourceWatches.join(", ") : "No watch lineage supplied"}</dd>
              </div>
              <div>
                <dt>Triggered rule</dt>
                <dd>{provenance.triggered_surface_rule || "No triggered rule supplied"}</dd>
              </div>
              <div>
                <dt>Suppressed rule</dt>
                <dd>{provenance.suppressed_by || "No suppression rule applied"}</dd>
              </div>
              <div>
                <dt>Why today</dt>
                <dd>{provenance.why_today || "No current-day reason supplied"}</dd>
              </div>
            </dl>
          </DetailSection>

          {detail && (
            <>
              <DetailSection title="Why you received this">
                <p>{detail.summary}</p>
              </DetailSection>

              <DetailSection title="What triggered it">
                {supportingFacts(detail).length > 0 ? (
                  <ul>
                    {supportingFacts(detail).slice(0, 6).map((fact) => (
                      <li key={fact}>{fact}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No additional supporting facts available.</p>
                )}
              </DetailSection>

              {detail.action && (
                <DetailSection title="Action implied">
                  <p>{detail.action}</p>
                </DetailSection>
              )}

              <DetailSection title="Sources">
                <SourceList data={detail.source_data} />
              </DetailSection>

              <DetailSection title="Account and source split">
                <dl className="provenanceRows">
                  <div>
                    <dt>Personal accounts</dt>
                    <dd>{listText(detailList(detail.source_data, "personal_accounts"))}</dd>
                  </div>
                  <div>
                    <dt>Connected data sources</dt>
                    <dd>{listText(detailList(detail.source_data, "connected_data_sources"))}</dd>
                  </div>
                  <div>
                    <dt>Manual inputs</dt>
                    <dd>{listText(detailList(detail.source_data, "manual_inputs"))}</dd>
                  </div>
                  <div>
                    <dt>Missing sources</dt>
                    <dd>{listText(detailList(detail.source_data, "missing_sources"))}</dd>
                  </div>
                </dl>
              </DetailSection>

              <DetailSection title="Underlying data">
                <ReadableDataTable data={detail.raw_data} />
                <RawDataTable data={detail.raw_data} />
              </DetailSection>

              <AIProcessingPanel data={detail.ai_processing} />

              <SuppressedItemsPanel items={detail.suppressed_signals} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const currentDate = useMemo(() => todayIso(), []);
  const [activeView, setActiveView] = useState<AppView>("briefing");
  const [selectedDate, setSelectedDate] = useState(currentDate);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appendixItem, setAppendixItem] = useState<AssistantBriefingItem | null>(null);
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [watchItems, setWatchItems] = useState<WatchItem[]>([]);
  const [activeWatchCount, setActiveWatchCount] = useState(0);
  const [watchDraft, setWatchDraft] = useState("");
  const [guidedWatchDraft, setGuidedWatchDraft] = useState<GuidedWatchDraft>(EMPTY_GUIDED_WATCH);
  const [editingWatchId, setEditingWatchId] = useState<number | null>(null);
  const [watchBusy, setWatchBusy] = useState(false);

  async function loadWatchItems() {
    const response = await requestJson<WatchListResponse>("/api/watch-items", undefined, "Watch Admin unavailable");
    setWatchItems(response.watch_items);
    setActiveWatchCount(response.active_count);
  }

  async function loadBriefing(dateText = selectedDate) {
    setLoading(true);
    setError(null);
    setSelectedDate(dateText);
    try {
      const nextBriefing = await requestJson<Briefing>(`/api/briefing?date=${encodeURIComponent(dateText)}`, undefined, "Briefing unavailable");
      setBriefing(nextBriefing);
      await loadWatchItems();
    } catch (err) {
      console.error("briefing_load_failed", err);
      setError(err instanceof Error ? err.message : "Briefing unavailable");
    } finally {
      setLoading(false);
    }
  }

  async function refreshAfterWatchChange() {
    await loadWatchItems();
    if (selectedDate === currentDate) {
      await loadBriefing(currentDate);
    }
  }

  async function submitWatch() {
    if (!watchDraft.trim()) return;
    setWatchBusy(true);
    setError(null);
    try {
      if (editingWatchId) {
        await requestJson<unknown>(
          `/api/watch-items/${editingWatchId}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: watchDraft })
          },
          "Watch update failed"
        );
      } else {
        await requestJson<unknown>(
          "/api/watch-items",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: watchDraft })
          },
          "Watch add failed"
        );
      }
      setWatchDraft("");
      setEditingWatchId(null);
      await refreshAfterWatchChange();
    } catch (err) {
      console.error("watch_save_failed", err);
      setError(err instanceof Error ? err.message : "Watch save failed");
    } finally {
      setWatchBusy(false);
    }
  }

  async function submitGuidedWatch() {
    if (!guidedWatchDraft.title.trim()) return;
    setWatchBusy(true);
    setError(null);
    const surfaceWhen = splitList(guidedWatchDraft.surface_when);
    const suppressWhen = splitList(guidedWatchDraft.suppress_when);
    const trackedSymbols = splitList(guidedWatchDraft.symbols).map(normalizeSymbol);
    const symbolNotes = parseSymbolNotes(guidedWatchDraft.symbol_notes);
    const manualFacts = {
      tracked_symbols: trackedSymbols,
      symbol_notes: symbolNotes
    };
    const method = editingWatchId ? "PATCH" : "POST";
    const path = editingWatchId ? `/api/watch-items/${editingWatchId}` : "/api/watch-items";
    try {
      await requestJson<unknown>(
        path,
        {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: guidedWatchDraft.title,
            original_text: `${guidedWatchDraft.title}\n${guidedWatchDraft.why_i_care}`.trim(),
            watch_kind: guidedWatchDraft.watch_kind,
            priority: guidedWatchDraft.priority,
            check_frequency: guidedWatchDraft.cadence,
            watch_for: splitList(guidedWatchDraft.interests),
            personal_context: {
              why_i_care: guidedWatchDraft.why_i_care,
              accounts: splitList(guidedWatchDraft.accounts),
              interests: splitList(guidedWatchDraft.interests),
              owned_assets: [],
              ignored_accounts: [],
              manual_facts: manualFacts
            },
            source_config: {
              connected_sources: splitList(guidedWatchDraft.connected_sources),
              available_sources: [],
              missing_sources: [],
              manual_inputs: splitList(guidedWatchDraft.manual_inputs)
            },
            evaluation_rules: {
              surface_when: surfaceWhen,
              suppress_when: suppressWhen,
              primary_focus_allowed: guidedWatchDraft.primary_focus_allowed
            },
            prompt_config: {
              daily_prompt_override: guidedWatchDraft.daily_prompt_override || null
            }
          })
        },
        "Guided watch add failed"
      );
      setGuidedWatchDraft(EMPTY_GUIDED_WATCH);
      setEditingWatchId(null);
      setWatchDraft("");
      await refreshAfterWatchChange();
    } catch (err) {
      console.error("guided_watch_save_failed", err);
      setError(err instanceof Error ? err.message : "Guided watch save failed");
    } finally {
      setWatchBusy(false);
    }
  }

  function editWatch(watch: WatchItem) {
    setEditingWatchId(watch.id);
    setWatchDraft(watch.original_text);
    setGuidedWatchDraft({
      title: watch.title,
      watch_kind: watch.watch_kind,
      priority: watch.priority,
      cadence: watch.check_frequency === "weekly" || watch.check_frequency === "event_driven" ? watch.check_frequency : "daily",
      why_i_care: watch.personal_context.why_i_care || "",
      accounts: watch.personal_accounts.join("\n"),
      interests: watch.personal_interests.join("\n"),
      symbols: trackedSymbolsText(watch),
      symbol_notes: symbolNotesText(watch),
      connected_sources: watch.connected_data_sources.join("\n"),
      manual_inputs: watch.manual_inputs.join("\n"),
      surface_when: watch.evaluation_rules.surface_when.join("\n"),
      suppress_when: watch.evaluation_rules.suppress_when.join("\n"),
      primary_focus_allowed: watch.evaluation_rules.primary_focus_allowed,
      daily_prompt_override: watch.prompt_config.daily_prompt_override || ""
    });
  }

  function cancelWatchEdit() {
    setEditingWatchId(null);
    setWatchDraft("");
    setGuidedWatchDraft(EMPTY_GUIDED_WATCH);
  }

  function usePreset(preset: WatchPreset) {
    setEditingWatchId(null);
    setWatchDraft(preset.text);
  }

  async function mutateWatch(path: string, method: "POST" | "DELETE", fallback: string) {
    setWatchBusy(true);
    setError(null);
    try {
      await requestJson<unknown>(path, { method }, fallback);
      if (editingWatchId && path.includes(`/api/watch-items/${editingWatchId}`)) {
        cancelWatchEdit();
      }
      await refreshAfterWatchChange();
    } catch (err) {
      console.error("watch_mutation_failed", err);
      setError(err instanceof Error ? err.message : fallback);
    } finally {
      setWatchBusy(false);
    }
  }

  async function importCsv(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const source = sourceFromFile(file);
      await requestJson<{ imported: number }>(
        `/api/import/holdings?source=${encodeURIComponent(source)}&replace=true`,
        {
          method: "POST",
          body
        },
        "Import failed"
      );
      await loadBriefing(currentDate);
    } catch (err) {
      console.error("holdings_import_failed", err);
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
      event.target.value = "";
    }
  }

  async function openAppendix(item: AssistantBriefingItem) {
    setAppendixItem(item);
    setActiveView("appendix");
    if (!item.detail_id) return;
    setDetailLoading(true);
    setDetail(null);
    setError(null);
    try {
      setDetail(await requestJson<RecommendationDetail>(`/api/recommendations/${encodeURIComponent(item.detail_id)}`, undefined, "Detail unavailable"));
    } catch (err) {
      console.error("recommendation_detail_load_failed", err);
      setError(err instanceof Error ? err.message : "Detail unavailable");
    } finally {
      setDetailLoading(false);
    }
  }

  function switchView(view: AppView) {
    setActiveView(view);
    if (view === "briefing" && selectedDate !== currentDate) {
      void loadBriefing(currentDate);
    }
    if (view === "archive" && selectedDate === currentDate) {
      void loadBriefing(addDays(currentDate, -1));
    }
    if (view === "watch-admin") {
      void loadWatchItems();
    }
  }

  function loadArchiveDate(dateText: string) {
    setActiveView(dateText === currentDate ? "briefing" : "archive");
    void loadBriefing(dateText);
  }

  useEffect(() => {
    void loadBriefing(currentDate);
    // Initial page load only; later refreshes are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const briefingDate = useMemo(() => {
    return formatBriefingDate(briefing?.briefing_date ?? selectedDate);
  }, [briefing, selectedDate]);
  const readOnly = Boolean(briefing?.read_only);
  const hasPrimaryFocus = Boolean(briefing && briefing.assistant_briefing.mode === "focused" && briefing.assistant_briefing.primary_focus.detail_id);
  const outputCount = briefing
    ? (hasPrimaryFocus ? 1 : 0) +
      briefing.assistant_briefing.needs_attention.length +
      briefing.assistant_briefing.watch_only.length +
      (briefing.assistant_briefing.catch_up ?? []).length
    : null;

  return (
    <main className="shell">
      <BriefingHeader
        activeView={activeView}
        briefingDate={briefingDate}
        attentionCount={outputCount}
        onViewChange={switchView}
        onRefresh={() => {
          if (activeView === "watch-admin") {
            void loadWatchItems();
            return;
          }
          void loadBriefing(selectedDate);
        }}
        onImport={importCsv}
        loading={loading}
        importing={importing}
        readOnly={readOnly}
      />

      {error && <div className="error">{error}</div>}

      <section className="briefingStack" aria-busy={loading || importing}>
        {activeView === "briefing" && briefing && <AssistantBriefingView briefing={briefing.assistant_briefing} onAppendix={openAppendix} />}

        {activeView === "archive" && (
          <ArchiveView
            briefing={briefing}
            selectedDate={selectedDate}
            currentDate={currentDate}
            loading={loading}
            onPreviousDay={() => loadArchiveDate(addDays(selectedDate, -1))}
            onToday={() => loadArchiveDate(currentDate)}
            onNextDay={() => {
              const nextDate = addDays(selectedDate, 1);
              if (nextDate <= currentDate) loadArchiveDate(nextDate);
            }}
            onAppendix={openAppendix}
          />
        )}

        {activeView === "watch-admin" && (
          <WatchAdminView
            watches={watchItems}
            activeCount={activeWatchCount}
            draft={watchDraft}
            guidedDraft={guidedWatchDraft}
            editingId={editingWatchId}
            busy={watchBusy}
            onDraftChange={setWatchDraft}
            onGuidedDraftChange={setGuidedWatchDraft}
            onSubmit={() => void submitWatch()}
            onGuidedSubmit={() => void submitGuidedWatch()}
            onEdit={editWatch}
            onCancelEdit={cancelWatchEdit}
            onComplete={(watchId) => void mutateWatch(`/api/watch-items/${watchId}/complete`, "POST", "Watch complete failed")}
            onArchive={(watchId) => void mutateWatch(`/api/watch-items/${watchId}/archive`, "POST", "Watch archive failed")}
            onDelete={(watchId) => void mutateWatch(`/api/watch-items/${watchId}`, "DELETE", "Watch remove failed")}
            onUsePreset={usePreset}
          />
        )}

        {activeView === "appendix" && <AppendixView item={appendixItem} detail={detail} detailLoading={detailLoading} watches={watchItems} />}

        {!loading && !briefing && activeView !== "watch-admin" && <div className="emptyState">Nothing clears the attention bar.</div>}
        {loading && <div className="emptyState">Loading briefing</div>}
      </section>
    </main>
  );
}
