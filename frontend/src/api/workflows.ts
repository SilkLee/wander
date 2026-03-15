import { apiGet, apiPost } from './client';

export interface LogAnalysisRequest {
  log_content: string;
  log_type?: string;
}

export interface LogAnalysisResponse {
  analysis_id: string;
  root_cause: string;
  severity: string;
  suggested_fixes: string[];
  references: string[];
  confidence: number;
  intermediate_summary: Record<string, unknown>;
}

export interface WorkflowExecutionRequest {
  workflow_type: string;
  inputs: Record<string, unknown>;
}

export interface WorkflowExecutionResponse {
  execution_id: string;
  status: string;
  outputs: Record<string, unknown>;
  execution_time: number;
  error: string | null;
}

export function analyzeLog(
  request: LogAnalysisRequest,
  signal?: AbortSignal,
): Promise<LogAnalysisResponse> {
  return apiPost<LogAnalysisResponse>('/workflows/analyze-log', request, signal);
}

export function executeWorkflow(
  request: WorkflowExecutionRequest,
  signal?: AbortSignal,
): Promise<WorkflowExecutionResponse> {
  return apiPost<WorkflowExecutionResponse>('/workflows/execute', request, signal);
}

export function getWorkflowTypes(
  signal?: AbortSignal,
): Promise<{
  workflows: Array<{ type: string; name: string; description: string; status: string }>;
}> {
  return apiGet('/workflows/types', signal);
}
