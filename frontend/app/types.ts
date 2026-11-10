export type Segment = {
  parent_segment_id?: string | null;
  id: string;
  speaker_id: string;
  role: "customer" | "sales" | "unknown";
  text: string;
  original_text: string;
  start_ms: number | null;
  end_ms: number | null;
  language: string | null;
};
export type Evidence = {
  segment_id: string;
  quote: string;
  speaker_role: string;
  start_ms: number | null;
  end_ms: number | null;
};
export type Requirement = {
  capability_id?: string | null;
  extraction_origin?: string;
  superseded_by?: string[];
  supersedes?: string[];
  id: string;
  title: string;
  description: string;
  original_description: string;
  category: string;
  priority: string;
  information_status: string;
  confidence: number;
  constraints: string[];
  dependencies: string[];
  acceptance_criteria: string[];
  user_story: string;
  evidence: Evidence[];
  open_questions: string[];
  pm_status: string;
  notes: string;
};
export type Assessment = {
  support_bound?: string | null;
  grounding_note?: string;
  requirement_id: string;
  status: string;
  explanation: string;
  documentation_sources: string[];
  dependencies: string[];
  risks: string[];
  clarification_questions: string[];
  reviewer_status: string;
  notes: string;
};
export type Finding = {
  target_id?: string | null;
  origin?: string;
  id: string;
  finding_type: string;
  severity: string;
  description: string;
  original_evidence: Evidence[];
  downstream_text: string;
  suggested_correction: string;
  reviewer_status: string;
  reviewer_notes: string;
};
export type Sales = {
  pitch_reviewed?: boolean;
  product_name: string;
  fit_reasons: { need_id: string; reason: string; sources: string[] }[];
  limitations: string[];
  sources: string[];
  pitch: string;
  next_question: string;
  objection_handling: string;
  escalation_required: boolean;
  escalation_reason: string;
};
export type Conversation = {
  domain_id: Domain;
  processing_step?: string | null;
  audio_path?: string | null;
  original_segments?: Segment[];
  copilot_history?: CopilotSuggestion[];
  semantic_audit?: {
    provider: string;
    rejected_candidates: number;
    at: string;
  } | null;
  observations: {
    id: string;
    kind: string;
    description: string;
    evidence: Evidence[];
    information_status: string;
    dismissed: boolean;
  }[];
  id: string;
  title: string;
  source: string;
  version: number;
  status: string;
  error: string | null;
  transcription_model: string;
  segments: Segment[];
  requirements: Requirement[];
  assessments: Assessment[];
  findings: Finding[];
  sales: Sales;
  signals: {
    id: string;
    label: string;
    kind: string;
    evidence: Evidence[];
    caveat: string;
  }[];
  response: {
    generation_provider?: string;
    text: string;
    language: string;
    approved: boolean;
    sources: string[];
    audio_path: string | null;
  } | null;
  audit_log: {
    action: string;
    role: string;
    reason: string;
    at: string;
    version: number;
  }[];
  node_runs: {
    node: string;
    status: string;
    duration_ms: number;
    provider: string;
  }[];
};
export type Knowledge = {
  domain_id?: Domain;
  status_value?: string;
  capability_id?: string;
  id: string;
  title: string;
  category: string;
  version: string;
  status: string;
  owner: string;
  excerpt: string;
};
export type Listed = {
  domain_id?: Domain;
  id: string;
  title: string;
  status: string;
  source: string;
  requirements: number;
  open_findings: number;
};
export type Scenario = {
  domain_id?: Domain;
  id: string;
  name: string;
  persona: string;
  objective: string;
  questions: string[];
};
export type Training = {
  domain_id?: Domain;
  ai_coaching?: {
    summary: string;
    strengths: string[];
    next_practice: string[];
    examples: {
      turn: number;
      quote: string;
      feedback: string;
      alternative: string;
      source_ids: string[];
    }[];
    provider: string;
    caveat: string;
  };
  id: string;
  scenario: Scenario;
  turns: { customer: string; trainee: string }[];
  question: string;
  complete: boolean;
  evaluation: {
    rubric: {
      category: string;
      score: number;
      out_of: number;
      rationale: string;
    }[];
    flagged_claims: string[];
    examples: { quote: string; feedback: string; alternative: string }[];
    sources: string[];
    caveat: string;
  } | null;
  provider: string;
};
export type Providers = {
  stt: {
    model: string;
    configured: boolean;
    status: string;
    verified?: boolean;
  };
  tts: {
    model: string;
    voice: string;
    configured: boolean;
    status: string;
    verified?: boolean;
  };
  reasoning: {
    provider: string;
    status: string;
    configured: boolean;
    model?: string;
    reachable?: boolean;
    verified?: boolean;
  };
  evon: { status: string };
};

export type Domain = "synthetic-device-lifecycle" | "marketplace";
export type Stage =
  "conversation" | "sales" | "requirements" | "engineering" | "response";
export type Journey = {
  version: number;
  steps: { id: Stage; label: string; state: string }[];
  blockers: { stage: Stage; code: string; item_id?: string; label: string }[];
  next_stage: Stage;
  can_draft: boolean;
  can_approve: boolean;
  can_generate_audio: boolean;
  audit_current: boolean;
  model_audit_required: boolean;
};
export type CopilotSuggestion = {
  question: string;
  status: string;
  answer: string;
  next_question: string;
  objection_response: string;
  escalation_required: boolean;
  escalation_reason: string;
  sources: string[];
  citations?: { source_id: string; quote: string }[];
  conditions?: string[];
  provider: string;
  model_used: boolean;
  at?: string;
};
export type Insights = {
  sample_size: number;
  synthetic: boolean;
  signals: {
    conversation_id: string;
    conversation_title: string;
    id: string;
    label: string;
    evidence: Evidence[];
    caveat: string;
  }[];
  language_counts: Record<string, number>;
  caveat: string;
  data_insufficient: boolean;
};
