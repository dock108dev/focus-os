import { ChangeEvent, useEffect, useMemo, useState } from "react";

import { requestJson, sourceFromFile } from "./api";
import { AppendixView } from "./AppendixView";
import { ArchiveView } from "./ArchiveView";
import { AssistantBriefingView } from "./AssistantBriefingView";
import { BriefingHeader } from "./BriefingHeader";
import { EMPTY_GUIDED_WATCH } from "./appConfig";
import type { AppView, GuidedWatchDraft, WatchPreset } from "./appConfig";
import type { AssistantBriefingItem, Briefing, RecommendationDetail, WatchItem, WatchListResponse } from "./types";
import { addDays, formatBriefingDate, todayIso } from "./dateUtils";
import { parseSymbolNotes, normalizeSymbol, splitList, symbolNotesText, trackedSymbolsText } from "./watchFormat";
import { WatchAdminView } from "./WatchAdminView";

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
