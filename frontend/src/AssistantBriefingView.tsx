import type { AssistantBriefing, AssistantBriefingItem } from "./types";

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

export function AssistantBriefingView({
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
