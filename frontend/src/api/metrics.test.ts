import { fetchDoraMetrics } from './metrics';

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('fetchDoraMetrics', () => {
  it('returns parsed DORA metrics on success', async () => {
    const mockData = {
      deployment_frequency: 1.2,
      lead_time: 18.4,
      change_failure_rate: 0.12,
      mttr: 3.6,
      trend: [],
    };

    jest.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchDoraMetrics();
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith('/api/metrics/dora');
  });

  it('throws on non-ok response', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response);

    await expect(fetchDoraMetrics()).rejects.toThrow('Failed to fetch DORA metrics');
  });

  it('throws on network error', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'));

    await expect(fetchDoraMetrics()).rejects.toThrow('Network error');
  });
});
