export interface DORATrendPoint {
  timestamp: string;
  deployment_frequency: number;
  lead_time: number;
  change_failure_rate: number;
  mttr: number;
}

export interface DORAMetrics {
  deployment_frequency: number;
  lead_time: number;
  change_failure_rate: number;
  mttr: number;
  level?: string;
  trend: DORATrendPoint[];
}

export async function fetchDoraMetrics(signal?: AbortSignal): Promise<DORAMetrics> {
  const response = await fetch('/api/metrics/dora', { signal });
  if (!response.ok) {
    throw new Error('Failed to fetch DORA metrics');
  }
  return response.json();
}

export interface DeploymentEventRequest {
  repo: string;
  sha: string;
  deployed_at: string;
  success?: boolean;
}

export interface EventResponse {
  id: string;
  status: string;
}

export async function recordDeployment(
  event: DeploymentEventRequest,
  signal?: AbortSignal,
): Promise<EventResponse> {
  const response = await fetch('/api/metrics/events/deployment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event),
    signal,
  });
  if (!response.ok) {
    throw new Error('Failed to record deployment');
  }
  return response.json();
}
