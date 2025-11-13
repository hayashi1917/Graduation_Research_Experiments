/**
 * Type definitions for the paper proofreading system
 */

export interface Paper {
  id: string;
  pdf: string;
}

export interface Phase1Session {
  phase1_id: string;
  paper_id: string;
  started_at: string;
  completed_at: string;
  iterations: number;
  excluded_items: string[];
  status: 'in_progress' | 'completed' | 'aborted';
  final_pdf_path: string;
}

export interface ProofreadingIssue {
  issue_number: number;
  before: string;
  reasoning: string;
  after: string;
}

export interface WebSocketMessage {
  type: string;
  message?: string;
  level?: 'info' | 'success' | 'warning' | 'error';
  [key: string]: any;
}

export interface IterationInfo {
  session_id: string;
  paper_id: string;
  phase: string;
  iteration: number;
  timestamp: string;
  detected_errors: string[];
  new_issues_count: number;
}

export interface DetectionRate {
  total_embedded: number;
  total_detected: number;
  detection_rate: number;
}

export type UserAction = 'A' | 'S' | 'Q';
export type UserChoice = 'Y' | 'N';
