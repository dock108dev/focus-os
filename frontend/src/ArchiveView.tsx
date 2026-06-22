import { AssistantBriefingView } from "./AssistantBriefingView";
import type { AssistantBriefingItem, Briefing } from "./types";

export function ArchiveView({
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
