import type { ReactNode } from "react";

import type { Provenance } from "./appConfig";
import type { AssistantBriefingItem, RecommendationDetail, WatchItem } from "./types";
import { formatSourceWatchLabel, listText } from "./watchFormat";

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

export function AppendixView({
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
