export interface DocumentSummary {
  id: number;
  title: string;
  source_type: string;
  created_at: string;
  updated_at: string;
  version_count: number;
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
    content: string;
    word_count: number;
    char_count: number;
    created_at: string;
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

export interface PlagiarismReport {
  local_only: boolean;
  disclaimer: string;
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
  weight: "strong" | "normal" | "weak";
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

export interface DiffSegment {
  type: "equal" | "changed";
  text?: string;
  original: string;
  rewritten: string;
  risk: "none" | "meaning" | "number";
  low_change?: boolean;
  sentence_start?: boolean;
  sentence_end?: boolean;
  sentence_space?: boolean;
}

export interface SentenceRecord {
  source_ids: number[];
  source: string;
  text: string;
  rules: string[];
  similarity: number;
  status: "restructured" | "lexical" | "unchanged";
  restructured: boolean;
  flags: string[];
  allowed_drop?: boolean;
}

export interface StyleCheck {
  sentences_restructured: number;
  sentences_total: number;
  words_changed_pct: number;
}

export interface HumanizePayload {
  text: string;
  tone: string;
  strength: string;
  variation: number;
  clean_invisible: boolean;
  replace_dashes: boolean;
  straight_quotes: boolean;
}

export interface SkillSectionReport {
  section: number;
  name: string;
  found: number;
  fixed: number;
  survived: number;
  review: number;
}

export interface SkillReviewItem {
  section: number;
  name: string;
  snippet: string;
  hint: string;
  span: [number, number];
  tier: "A" | "B" | "C";
}

export interface SkillReport {
  found: number;
  fixed: number;
  survived: number;
  sections: SkillSectionReport[];
  review: SkillReviewItem[];
  dropped_by_rule: { section: number; id: string; snippet: string }[];
  reason: string;
}

export interface HumanizeResult {
  rewritten: string;
  sentences: SentenceRecord[];
  diff: { segments: DiffSegment[]; changed: number; review: number };
  style_check: StyleCheck;
  report: SkillReport;
  document_id: number;
}
