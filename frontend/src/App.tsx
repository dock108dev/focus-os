import { Archive, Check, Pencil, Plus, RefreshCw, Save, Trash2, Upload, X } from "lucide-react";
import { ChangeEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { requestJson, sourceFromFile } from "./api";
import type { AssistantBriefing, AssistantBriefingItem, Briefing, RecommendationDetail, WatchItem, WatchListResponse, WatchStatus } from "./types";

function BriefingHeader({
  briefingDate,
  attentionCount,
  onRefresh,
  onImport,
  onPreviousDay,
  onToday,
  onNextDay,
  loading,
  importing,
  isToday,
  readOnly
}: {
  briefingDate: string;
  attentionCount: number | null;
  onRefresh: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
  onPreviousDay: () => void;
  onToday: () => void;
  onNextDay: () => void;
  loading: boolean;
  importing: boolean;
  isToday: boolean;
  readOnly: boolean;
}) {
  return (
    <header className="masthead">
      <div>
        <p className="brand">FocusOS</p>
        <h1>Morning Briefing</h1>
        <p className="briefingMeta">
          {briefingDate}
          {attentionCount !== null ? ` · ${attentionCount} items` : ""}
          {readOnly ? " · archived snapshot" : ""}
        </p>
        <nav className="dateNav" aria-label="Briefing timeline">
          <button type="button" onClick={onPreviousDay} disabled={loading}>
            ← Previous Day
          </button>
          <button type="button" onClick={onToday} disabled={loading || isToday}>
            Today
          </button>
          <button type="button" onClick={onNextDay} disabled={loading || isToday}>
            Next Day →
          </button>
        </nav>
      </div>
      <div className="actions">
        <label className="iconButton" title="Import CSV">
          <Upload size={18} />
          <input type="file" accept=".csv,text/csv" onChange={onImport} disabled={importing || readOnly} />
        </label>
        <button className="iconButton" type="button" onClick={onRefresh} disabled={loading} title="Refresh">
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}

function AssistantItemButton({
  item,
  onDetail,
  className = ""
}: {
  item: AssistantBriefingItem;
  onDetail: (detailId: string) => void;
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
    <button className={itemClass} type="button" onClick={() => onDetail(item.detail_id)}>
      <h3>{item.title}</h3>
      <p>{item.summary}</p>
    </button>
  );
}

function WatchStatusList({ items, onDetail }: { items: WatchStatus[]; onDetail: (detailId: string) => void }) {
  if (items.length === 0) {
    return <p className="quietLine">Nothing user-created is close enough to need attention.</p>;
  }
  return (
    <div className="watchStatusList">
      {items.map((item) => {
        const content = (
          <>
            <h3>{item.title}</h3>
            <p>{item.summary}</p>
          </>
        );
        return item.detail_id ? (
          <button className="watchStatusItem" type="button" key={item.id} onClick={() => onDetail(item.detail_id)}>
            {content}
          </button>
        ) : (
          <article className="watchStatusItem staticItem" key={item.id}>
            {content}
          </article>
        );
      })}
    </div>
  );
}

function WatchManager({
  watches,
  activeCount,
  draft,
  editingId,
  busy,
  readOnly,
  onDraftChange,
  onSubmit,
  onEdit,
  onCancelEdit,
  onComplete,
  onArchive,
  onDelete
}: {
  watches: WatchItem[];
  activeCount: number;
  draft: string;
  editingId: number | null;
  busy: boolean;
  readOnly: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onEdit: (watch: WatchItem) => void;
  onCancelEdit: () => void;
  onComplete: (watchId: number) => void;
  onArchive: (watchId: number) => void;
  onDelete: (watchId: number) => void;
}) {
  const visible = watches.filter((watch) => watch.status !== "archived").slice(0, 6);
  return (
    <div className="watchOwnerPanel">
      <div className="watchOwnerHeader">
        <span>{activeCount} active</span>
        {editingId && (
          <button className="miniIconButton" type="button" onClick={onCancelEdit} disabled={busy} title="Cancel edit">
            <X size={15} />
          </button>
        )}
      </div>
      {!readOnly && (
        <div className="watchComposer">
          <textarea
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            placeholder="Outdoor concert Friday&#10;Watch weather, parking, timing, and venue changes."
            rows={3}
            disabled={busy}
          />
          <button className="iconButton" type="button" onClick={onSubmit} disabled={busy || !draft.trim()} title={editingId ? "Save watch" : "Add watch"}>
            {editingId ? <Save size={17} /> : <Plus size={17} />}
          </button>
        </div>
      )}
      {visible.length > 0 && (
        <div className="ownedWatchList">
          {visible.map((watch) => (
            <article className="ownedWatchItem" key={watch.id}>
              <div>
                <h3>{watch.title}</h3>
                <p>{watch.why_today || watch.latest_evaluation?.summary || watch.original_text}</p>
                <span>{watch.status}</span>
              </div>
              {!readOnly && (
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
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function AssistantBriefingView({
  briefing,
  onDetail,
  watchManager
}: {
  briefing: AssistantBriefing;
  onDetail: (detailId: string) => void;
  watchManager: ReactNode;
}) {
  return (
    <section className={`assistantBriefing ${briefing.mode === "quiet" ? "quietBriefing" : "focusedBriefing"}`}>
      <header className="assistantGreeting">
        <h2>{briefing.greeting}</h2>
      </header>

      <section className="primaryFocus">
        <p className="sectionKicker">{briefing.mode === "quiet" ? "Nothing needs the spotlight" : "One thing worth paying attention to"}</p>
        <AssistantItemButton item={briefing.primary_focus} onDetail={onDetail} className="primaryAssistantItem" />
      </section>

      <section className="secondaryNotes">
        <p className="sectionKicker">A few other things</p>
        {briefing.secondary_notes.length > 0 ? (
          <div className="noteList">
            {briefing.secondary_notes.map((item) => (
              <AssistantItemButton item={item} key={`${item.title}-${item.domain}`} onDetail={onDetail} className="noteItem" />
            ))}
          </div>
        ) : (
          <p className="quietLine">No other notes need attention.</p>
        )}
      </section>

      <section className="watchStatus">
        <p className="sectionKicker">Watching</p>
        <WatchStatusList items={briefing.watch_status} onDetail={onDetail} />
        {watchManager}
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
  const day = String(next.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatBriefingDate(dateText: string) {
  return new Date(`${dateText}T12:00:00`).toLocaleDateString([], {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}

export default function App() {
  const currentDate = useMemo(() => todayIso(), []);
  const [selectedDate, setSelectedDate] = useState(currentDate);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [watchItems, setWatchItems] = useState<WatchItem[]>([]);
  const [activeWatchCount, setActiveWatchCount] = useState(0);
  const [watchDraft, setWatchDraft] = useState("");
  const [editingWatchId, setEditingWatchId] = useState<number | null>(null);
  const [watchBusy, setWatchBusy] = useState(false);

  async function loadWatchItems() {
    const response = await requestJson<WatchListResponse>("/api/watch-items", undefined, "Watchlist unavailable");
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
      if (!nextBriefing.read_only) {
        await loadWatchItems();
      }
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

  async function openDetail(detailId: string) {
    if (!detailId) return;
    setDetailLoading(true);
    setError(null);
    try {
      setDetail(await requestJson<RecommendationDetail>(`/api/recommendations/${encodeURIComponent(detailId)}`, undefined, "Detail unavailable"));
    } catch (err) {
      console.error("recommendation_detail_load_failed", err);
      setError(err instanceof Error ? err.message : "Detail unavailable");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadBriefing(currentDate);
  }, []);

  const briefingDate = useMemo(() => {
    return formatBriefingDate(briefing?.briefing_date ?? selectedDate);
  }, [briefing, selectedDate]);
  const isToday = selectedDate === currentDate;
  const readOnly = Boolean(briefing?.read_only);

  const itemCount = briefing
    ? 1 + briefing.assistant_briefing.secondary_notes.length + briefing.assistant_briefing.watch_status.length
    : null;

  return (
    <main className="shell">
      <BriefingHeader
        briefingDate={briefingDate}
        attentionCount={itemCount}
        onRefresh={() => void loadBriefing(selectedDate)}
        onImport={importCsv}
        onPreviousDay={() => void loadBriefing(addDays(selectedDate, -1))}
        onToday={() => void loadBriefing(currentDate)}
        onNextDay={() => void loadBriefing(addDays(selectedDate, 1))}
        loading={loading}
        importing={importing}
        isToday={isToday}
        readOnly={readOnly}
      />

      {error && <div className="error">{error}</div>}

      <section className="briefingStack" aria-busy={loading || importing}>
        {briefing && (
          <AssistantBriefingView
            briefing={briefing.assistant_briefing}
            onDetail={openDetail}
            watchManager={
              <WatchManager
                watches={watchItems}
                activeCount={activeWatchCount}
                draft={watchDraft}
                editingId={editingWatchId}
                busy={watchBusy}
                readOnly={readOnly}
                onDraftChange={setWatchDraft}
                onSubmit={() => void submitWatch()}
                onEdit={editWatch}
                onCancelEdit={cancelWatchEdit}
                onComplete={(watchId) => void mutateWatch(`/api/watch-items/${watchId}/complete`, "POST", "Watch complete failed")}
                onArchive={(watchId) => void mutateWatch(`/api/watch-items/${watchId}/archive`, "POST", "Watch archive failed")}
                onDelete={(watchId) => void mutateWatch(`/api/watch-items/${watchId}`, "DELETE", "Watch remove failed")}
              />
            }
          />
        )}
        {!loading && !briefing && <div className="emptyState">Nothing clears the attention bar.</div>}
        {loading && <div className="emptyState">Loading briefing</div>}
      </section>

      {(detail || detailLoading) && (
        <div className="modalBackdrop" role="presentation" onClick={() => setDetail(null)}>
          <aside className="detailPanel" aria-live="polite" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="detailHeader">
              <div>
                <p className="eyebrow">Decision Appendix</p>
                <h2>{detailLoading ? "Loading" : detail?.title}</h2>
              </div>
              <button className="textButton" type="button" onClick={() => setDetail(null)}>
                Close
              </button>
            </div>

            {detail && (
              <div className="detailBody">
                <DetailSection title="Why you received this">
                  <p>{detail.summary}</p>
                </DetailSection>

                <DetailSection title="What triggered it">
                  {supportingFacts(detail).length > 0 ? (
                    <ul>
                      {supportingFacts(detail).slice(0, 6).map((item) => (
                        <li key={item}>{item}</li>
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

                <details className="detailDisclosure">
                  <summary>Details</summary>
                  <div className="detailDisclosureBody">
                    <DetailSection title="Sources">
                      <SourceList data={detail.source_data} />
                    </DetailSection>

                    <DetailSection title="Underlying data">
                      <ReadableDataTable data={detail.raw_data} />
                      <RawDataTable data={detail.raw_data} />
                    </DetailSection>

                    <AIProcessingPanel data={detail.ai_processing} />

                    <SuppressedItemsPanel items={detail.suppressed_signals} />
                  </div>
                </details>
              </div>
            )}
          </aside>
        </div>
      )}
    </main>
  );
}
