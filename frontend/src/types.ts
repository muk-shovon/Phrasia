export interface Option {
  id: string;
  label: string;
}

export interface ModelOption {
  id: string;
  label: string;
  paid: boolean;
  enabled: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  tier: string;
  notes: string;
  models: ModelOption[];
}

export interface Limits {
  max_input_chars: number;
  chunk_chars: number;
  max_upload_bytes: number;
  max_words_per_request: number;
}

export interface MetaResponse {
  version: string;
  modes: Option[];
  intensities: Option[];
  paid_models_enabled: boolean;
  limits: Limits;
  providers: ProviderInfo[];
  disclaimers: { detector: string; plagiarism: string };
}

export interface ProviderSetting {
  id: string;
  name: string;
  anonymous: boolean;
  requires_key: boolean;
  configured: boolean;
  source: "saved" | "none";
  masked_key: string;
  model: string;
  base_url: string;
  enabled: number;
  rate_limit_requests_per_minute: number;
}

export interface SettingsResponse {
  providers: ProviderSetting[];
  preferred_provider: string | null;
  paid_models_enabled: boolean;
  database_path: string;
  limits: Limits;
}

export interface JobChunk {
  id: number;
  seq: number;
  status: string;
  attempt_count: number;
  error: string | null;
  source_length: number;
  output_length: number | null;
}

export interface JobDetail {
  id: number;
  document_id: number;
  title: string;
  status: string;
  mode: string;
  intensity: string;
  provider_id: string | null;
  model_id: string | null;
  error: string | null;
  total_chunks: number;
  completed_chunks: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
  input_text: string;
  output_text: string | null;
  options: { preserve_formatting?: boolean; keep_quotes?: boolean };
  chunks: JobChunk[];
}

export interface JobSummary {
  id: number;
  status: string;
  mode: string;
  intensity: string;
  total_chunks: number;
  completed_chunks: number;
  provider_id: string | null;
  model_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  document_id: number;
  title: string;
  input_excerpt: string;
  output_excerpt: string | null;
}

export interface DocumentSummary {
  id: number;
  title: string;
  source_type: string;
  created_at: string;
  updated_at: string;
  version_count: number;
  latest_job_id: number | null;
  latest_job_status: string | null;
  latest_excerpt: string | null;
}

export interface DocumentDetail {
  id: number;
  title: string;
  source_type: string;
  created_at: string;
  updated_at: string;
  content: string;
  versions: {
    id: number;
    version_type: string;
    word_count: number;
    char_count: number;
    provider_id: string | null;
    model_id: string | null;
    created_at: string;
  }[];
  jobs: {
    id: number;
    status: string;
    mode: string;
    intensity: string;
    total_chunks: number;
    completed_chunks: number;
    provider_id: string | null;
    model_id: string | null;
    error: string | null;
    created_at: string;
    updated_at: string;
  }[];
}

export interface PlagiarismMatch {
  reference_id: number | null;
  title: string;
  similarity_percent: number;
  overlap_words: number;
  excerpt: string;
  matched_sentences: { sentence: string; overlap_percent: number }[];
  matched_passages: { passage: string; length_chars: number }[];
}

export interface WebCheckResult {
  available: boolean;
  results: { title: string; url: string; snippet: string }[];
  provider: string | null;
  disclaimer?: string;
  error: string | null;
}

export interface PlagiarismReport {
  local_only: boolean;
  disclaimer: string;
  web: WebCheckResult;
  word_count: number;
  sentence_count: number;
  checked_references: number;
  coverage_percent: number;
  matches: PlagiarismMatch[];
  repeated_phrases: { phrase: string; count: number }[];
  notes: string[];
}

export interface DetectorPatternMatch {
  start: number;
  end: number;
  text: string;
}

export interface DetectorPatternGroup {
  id: string;
  name: string;
  hint: string;
  weight: "strong" | "weak";
  count: number;
  matches: DetectorPatternMatch[];
}

export interface DetectorReport {
  disclaimer: string;
  word_count: number;
  total_matches: number;
  patterns: DetectorPatternGroup[];
}

export interface Reference {
  id: number;
  title: string;
  word_count: number;
  created_at: string;
}

export interface HumanizePayload {
  text: string;
  title?: string | null;
  mode: string;
  intensity: string;
  preserve_formatting: boolean;
  keep_quotes: boolean;
  clean_invisible: boolean;
  provider_id?: string | null;
}


export interface DiffSegment {
  type: "equal" | "changed";
  text?: string;
  original: string;
  rewritten: string;
  risk: "none" | "meaning" | "number";
}

export interface DiffStylePattern { id: string; name: string; count: number; }
export interface DiffStyleSide { total: number; strong: number; weak: number; by_pattern: DiffStylePattern[]; }
export interface DiffStyle {
  before: DiffStyleSide;
  after: DiffStyleSide;
  removed: number;
  remaining: DiffStylePattern[];
  changed_words_pct: number;
}

export interface DiffReport {
  segments: DiffSegment[];
  changed: number;
  review: number;
  style: DiffStyle;
}
