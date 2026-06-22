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
  attention_bucket: AttentionBucket;
  importance_score: number;
  actionability_score: number;
  expiration_hours: number;
  why_user_cares: string;
  situation: string;
  why_it_matters: string;
  what_changed: string;
  suggested_posture: "Ignore" | "Consider" | "Review" | "Watch" | "Act";
  story_type?: "focusos" | "external";
  attention_section: AttentionSection;
  domain?: string;
  vertical?: string;
  novelty_status?: "new" | "changed" | "repeated" | "seen_today";
  novelty_reason?: string;
  classification?: BriefingClass;
  source?: string;
  topic?: string;
  source_watch_ids?: string[];
  triggered_surface_rule?: string;
  suppressed_by?: string | null;
  why_today?: string;
  generation_metadata?: GenerationMetadata;
};

export type BriefingClass = "action_required" | "opportunity" | "awareness";
export type AttentionCategory = "action" | "opportunity" | "awareness";
export type AttentionBucket = AttentionSection;
export type AttentionSection = "Today" | "Around You" | "Background";

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
  briefing_date: string;
  is_archived: boolean;
  read_only: boolean;
  archive_source: "live" | "mock" | string;
  archive_review?: {
    scenario: string;
    notes: string;
    recommended_layout: string;
    layout_reason: string;
    scan_violations: string[];
  };
  holdings_count: number;
  sources: string[];
  topic_briefings: TopicBriefing[];
  recommended_actions: RecommendedAction[];
  assistant_briefing: AssistantBriefing;
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

export type AssistantBriefingItem = {
  title: string;
  summary: string;
  detail_id: string;
  domain: string;
  category: AttentionCategory;
  importance_score: number;
  story_type: "focusos" | "external";
  source_watch_ids: string[];
  triggered_surface_rule: string;
  suppressed_by: string | null;
  why_today: string;
};

export type WatchStatus = {
  id: number;
  title: string;
  summary: string;
  status: string;
  event_date: string | null;
  detail_id: string;
};

export type AssistantBriefing = {
  greeting: string;
  mode: "focused" | "quiet";
  primary_focus: AssistantBriefingItem;
  secondary_notes: AssistantBriefingItem[];
  watch_status: WatchStatus[];
};

export type WatchEvaluation = {
  id: number;
  watch_item_id: number;
  as_of: string;
  title: string;
  summary: string;
  category: AttentionCategory;
  importance_score: number;
  actionability_score: number;
  should_surface: boolean;
  trigger_reason: string;
  evidence: Record<string, unknown>;
  generation_metadata: GenerationMetadata;
};

export type GenerationMetadata = {
  why_generated: string;
  what_changed: string;
  why_user_should_care: string;
  expiration_date: string;
};

export type WatchItem = {
  id: number;
  source_watch_id: string;
  title: string;
  original_text: string;
  event_date: string | null;
  expires_at: string | null;
  check_frequency: string;
  watch_for: string[];
  conditions: string[];
  source_inputs: string[];
  cadence: string;
  surface_when: string[];
  surface_rules: string[];
  suppression_rules: string[];
  briefing_posture: string;
  preferred_output: string;
  status: "active" | "completed" | "archived";
  last_evaluated_on: string | null;
  latest_evaluation: WatchEvaluation | null;
  why_today: string | null;
};

export type WatchListResponse = {
  active_count: number;
  counts: {
    active: number;
    completed: number;
    archived: number;
    total: number;
  };
  watch_items: WatchItem[];
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
