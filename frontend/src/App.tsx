import { Archive, Check, ClipboardList, FileText, ListChecks, Pencil, Plus, RefreshCw, Save, Trash2, Upload, X } from "lucide-react";
import { ChangeEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { requestJson, sourceFromFile } from "./api";
import type { AssistantBriefing, AssistantBriefingItem, Briefing, RecommendationDetail, WatchItem, WatchListResponse } from "./types";

type AppView = "briefing" | "archive" | "watch-admin" | "appendix";

type WatchPreset = {
  label: string;
  text: string;
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
  return (
    <header className="masthead">
      <div>
        <p className="brand">FocusOS</p>
        <h1>{activeView === "watch-admin" ? "Watch Admin" : activeView === "archive" ? "Archive" : activeView === "appendix" ? "Appendix" : "Morning Briefing"}</h1>
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
        <p className="sectionKicker">Briefing outputs</p>
        {notes.length > 0 ? (
          <div className="noteList">
            {notes.map((item) => (
              <AssistantItemButton item={item} key={`${item.detail_id}-${item.title}`} onAppendix={onAppendix} className="noteItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No other outputs need attention.</p>
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

function formatSourceWatchLabel(value: string) {
  if (value === "system:manual-or-topic-import") return "System/manual import";
  if (value.startsWith("system:")) return value.replace("system:", "System: ").replace(/-/g, " ");
  if (value.startsWith("watch:")) return value.replace("watch:", "").replace(/-/g, " ");
  return value;
}

function WatchConfigRows({ watch }: { watch: WatchItem }) {
  const rows: Array<[string, string]> = [
    ["Conditions", listText(watch.conditions)],
    ["Sources", listText(watch.source_inputs)],
    ["Cadence", watch.cadence],
    ["Surface rules", listText(watch.surface_rules)],
    ["Suppression rules", listText(watch.suppression_rules)],
    ["Expiration", watch.expires_at || "No expiration"],
    ["Preferred output", watch.preferred_output]
  ];
  return (
    <dl className="watchConfigRows">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function WatchAdminView({
  watches,
  activeCount,
  draft,
  editingId,
  busy,
  onDraftChange,
  onSubmit,
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
  editingId: number | null;
  busy: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
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

      <section className="ownedWatchList">
        {watches.map((watch) => (
          <article className="ownedWatchItem" key={watch.id}>
            <div>
              <div className="watchItemTitleRow">
                <h3>{watch.title}</h3>
                <span>{watch.status}</span>
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

  function editWatch(watch: WatchItem) {
    setEditingWatchId(watch.id);
    setWatchDraft(watch.original_text);
  }

  function cancelWatchEdit() {
    setEditingWatchId(null);
    setWatchDraft("");
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
  }, []);

  const briefingDate = useMemo(() => {
    return formatBriefingDate(briefing?.briefing_date ?? selectedDate);
  }, [briefing, selectedDate]);
  const readOnly = Boolean(briefing?.read_only);
  const hasPrimaryFocus = Boolean(briefing && briefing.assistant_briefing.mode === "focused" && briefing.assistant_briefing.primary_focus.detail_id);
  const outputCount = briefing ? (hasPrimaryFocus ? 1 : 0) + briefing.assistant_briefing.secondary_notes.length : null;

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
            editingId={editingWatchId}
            busy={watchBusy}
            onDraftChange={setWatchDraft}
            onSubmit={() => void submitWatch()}
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
