import type { WatchItem } from "./types";
import { listText, symbolNotesText, thresholdText, trackedSymbolsText } from "./watchFormat";

export function WatchConfigRows({ watch }: { watch: WatchItem }) {
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
