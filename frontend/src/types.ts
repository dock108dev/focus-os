export type Allocation = {
  label: string;
  value: number;
  percent: number;
};

export type AttentionItem = {
  title: string;
  why_now: string;
  action: string;
  priority: number;
  detail_id: string;
  category: AttentionCategory;
  importance_score: number;
  actionability_score: number;
  expiration_hours: number;
  why_user_cares: string;
  classification?: BriefingClass;
  source?: string;
  topic?: string;
};

export type BriefingClass = "action_required" | "opportunity" | "awareness";
export type AttentionCategory = "action" | "opportunity" | "awareness";

export type Opportunity = {
  title: string;
  action: string;
  priority: number;
  detail_id: string;
};

export type RecommendedAction = {
  title: string;
  reason: string;
  priority: number;
  detail_id: string;
};

export type Briefing = {
  generated_at: string;
  holdings_count: number;
  sources: string[];
  topic_briefings: TopicBriefing[];
  recommended_actions: RecommendedAction[];
  summary: {
    current_value: number;
    daily_change: number;
    daily_change_pct: number;
    monthly_change: number;
    monthly_change_pct: number;
    cash_available: number;
    cash_percent: number;
    latest_as_of: string;
    allocation: Allocation[];
  };
  attention: AttentionItem[];
  opportunities: Opportunity[];
};

export type TopicBriefing = {
  id: number;
  topic: string;
  category: string;
  source_type: string;
  priority: number;
  as_of: string;
  title: string;
  summary: string;
  bullets: string[];
  action: string;
  generated_by: string;
};

export type RecommendationDetail = {
  id: string;
  title: string;
  summary: string;
  action: string;
  why_generated: string[];
  raw_data: Record<string, unknown>;
  source_data: Record<string, unknown>;
  ai_processing: Record<string, unknown> | null;
  suppressed_signals: unknown[];
};
