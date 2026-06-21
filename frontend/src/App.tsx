import { RefreshCw, Upload } from "lucide-react";
import { ChangeEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { requestJson, sourceFromFile } from "./api";
import type { AttentionItem, Briefing, RecommendationDetail } from "./types";

function BriefingHeader({
  briefingDate,
  attentionCount,
  onRefresh,
  onImport,
  loading,
  importing
}: {
  briefingDate: string;
  attentionCount: number | null;
  onRefresh: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
  loading: boolean;
  importing: boolean;
}) {
  return (
    <header className="masthead">
      <div>
        <p className="brand">FocusOS</p>
        <h1>Morning Briefing</h1>
        <p className="briefingMeta">
          {briefingDate}
          {attentionCount !== null ? ` · ${attentionCount} items` : ""}
        </p>
      </div>
      <div className="actions">
        <label className="iconButton" title="Import CSV">
          <Upload size={18} />
          <input type="file" accept=".csv,text/csv" onChange={onImport} disabled={importing} />
        </label>
        <button className="iconButton" type="button" onClick={onRefresh} disabled={loading} title="Refresh">
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}

function BriefingItem({
  item,
  onDetail,
  featured = false
}: {
  item: AttentionItem;
  onDetail: (detailId: string) => void;
  featured?: boolean;
}) {
  const className = `attentionItem ${featured ? "featuredItem" : "storyItem"}`;
  if (!item.detail_id) {
    return (
      <article className={`${className} staticItem`}>
        <h3>{item.title}</h3>
        <p>{item.why_now}</p>
      </article>
    );
  }

  return (
    <button className={className} type="button" onClick={() => onDetail(item.detail_id)}>
      <h3>{item.title}</h3>
      <p>{item.why_now}</p>
    </button>
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

export default function App() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  async function loadBriefing() {
    setLoading(true);
    setError(null);
    try {
      setBriefing(await requestJson<Briefing>("/api/briefing", undefined, "Briefing unavailable"));
    } catch (err) {
      console.error("briefing_load_failed", err);
      setError(err instanceof Error ? err.message : "Briefing unavailable");
    } finally {
      setLoading(false);
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
      await loadBriefing();
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
    void loadBriefing();
  }, []);

  const briefingDate = useMemo(() => {
    if (!briefing) return new Date().toLocaleDateString([], { weekday: "long", month: "long", day: "numeric", year: "numeric" });
    return new Date(briefing.generated_at).toLocaleDateString([], {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric"
    });
  }, [briefing]);

  const topStoryItems = useMemo(() => {
    return briefing?.attention ?? [];
  }, [briefing]);
  const featuredItem = topStoryItems[0];
  const secondaryItems = topStoryItems.slice(1);

  return (
    <main className="shell">
      <BriefingHeader
        briefingDate={briefingDate}
        attentionCount={briefing ? topStoryItems.length : null}
        onRefresh={loadBriefing}
        onImport={importCsv}
        loading={loading}
        importing={importing}
      />

      {error && <div className="error">{error}</div>}

      <section className="briefingStack" aria-busy={loading || importing}>
        <article className="attentionCard">
          <div className="attentionList">
            {featuredItem && <BriefingItem item={featuredItem} onDetail={openDetail} featured />}
            <div className="storyList">
              {secondaryItems.map((item) => (
                <BriefingItem item={item} key={`${item.title}-${item.action}`} onDetail={openDetail} />
              ))}
            </div>
            {!loading && topStoryItems.length === 0 && (
              <div className="emptyState">Nothing clears the attention bar.</div>
            )}
            {loading && <div className="emptyState">Loading briefing</div>}
          </div>
        </article>
      </section>

      {(detail || detailLoading) && (
        <div className="modalBackdrop" role="presentation" onClick={() => setDetail(null)}>
          <aside className="detailPanel" aria-live="polite" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="detailHeader">
              <div>
                <p className="eyebrow">Research Appendix</p>
                <h2>{detailLoading ? "Loading" : detail?.title}</h2>
              </div>
              <button className="textButton" type="button" onClick={() => setDetail(null)}>
                Close
              </button>
            </div>

            {detail && (
              <div className="detailBody">
                <DetailSection title="Reasoning">
                  <p>{detail.summary}</p>
                </DetailSection>

                <DetailSection title="Sources">
                  <SourceList data={detail.source_data} />
                </DetailSection>

                <DetailSection title="Why it appeared">
                  {supportingFacts(detail).length > 0 ? (
                    <ul>
                      {supportingFacts(detail).map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No additional supporting facts available.</p>
                  )}
                </DetailSection>

                <details className="detailDisclosure">
                  <summary>Details</summary>
                  <div className="detailDisclosureBody">
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
