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
  trend: DORATrendPoint[];
}

export async function fetchDoraMetrics(signal?: AbortSignal): Promise<DORAMetrics> {
  const response = await fetch('/api/metrics/dora', { signal });
  if (!response.ok) {
    throw new Error('Failed to fetch DORA metrics');
  }
  return response.json();
}
