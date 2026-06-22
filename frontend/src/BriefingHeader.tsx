import { Archive, ClipboardList, FileText, ListChecks, RefreshCw, Upload } from "lucide-react";
import type { ChangeEvent } from "react";

import type { AppView } from "./appConfig";

export function BriefingHeader({
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
