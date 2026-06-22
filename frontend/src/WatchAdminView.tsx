import { Archive, Check, Pencil, Plus, Save, Trash2, X } from "lucide-react";

import type { GuidedWatchDraft, WatchPreset } from "./appConfig";
import { WATCH_PRESETS } from "./appConfig";
import type { WatchItem } from "./types";
import { WatchConfigRows } from "./WatchConfigRows";
import { watchKindLabel, watchPriorityLabel } from "./watchFormat";

export function WatchAdminView({
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
