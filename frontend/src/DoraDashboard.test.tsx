import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import DoraDashboard from './DoraDashboard';
import DoraMetricCard from './DoraMetricCard';
import DoraTrendChart from './DoraTrendChart';

const mockDoraResponse = {
  deployment_frequency: 3.2,
  lead_time: 2.5,
  change_failure_rate: 0.042,
  mttr: 0.8,
  trend: [{ timestamp: '2026-03-01', deployment_frequency: 3.2, lead_time: 2.5, change_failure_rate: 0.042, mttr: 0.8 }],
};

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('DoraMetricCard', () => {
  it('renders metric name and value', () => {
    render(<DoraMetricCard name="Deployment Frequency" value="3.2/day" />);
    expect(screen.getByText('Deployment Frequency')).toBeInTheDocument();
    expect(screen.getByText('3.2/day')).toBeInTheDocument();
  });

  it('renders rating when provided', () => {
    render(<DoraMetricCard name="Lead Time" value="2.5 hrs" rating="Elite" />);
    expect(screen.getByText('Elite')).toBeInTheDocument();
  });
});

describe('DoraTrendChart', () => {
  it('renders chart title', () => {
    render(<DoraTrendChart title="Deployment Frequency Trend" data={[1, 2, 3]} />);
    expect(screen.getByText('Deployment Frequency Trend')).toBeInTheDocument();
  });

  it('renders data points as bars', () => {
    render(<DoraTrendChart title="Trend" data={[10, 20, 30]} />);
    const bars = screen.getAllByTestId('trend-bar');
    expect(bars).toHaveLength(3);
  });

  it('renders zero bars for empty data', () => {
    render(<DoraTrendChart title="Empty" data={[]} />);
    expect(screen.getByText('Empty')).toBeInTheDocument();
    expect(screen.queryAllByTestId('trend-bar')).toHaveLength(0);
  });
});

describe('DoraDashboard', () => {
  it('renders dashboard heading', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDoraResponse,
    });

    render(<DoraDashboard />);
    expect(screen.getByRole('heading', { name: /dora metrics/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Deployment Frequency')).toBeInTheDocument();
    });
  });

  it('renders fetched DORA metric cards', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDoraResponse,
    });

    render(<DoraDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Deployment Frequency')).toBeInTheDocument();
    });
    expect(screen.getByText('Lead Time for Changes')).toBeInTheDocument();
    expect(screen.getByText('Change Failure Rate')).toBeInTheDocument();
    expect(screen.getByText('Mean Time to Recovery')).toBeInTheDocument();
  });

  it('renders a trend chart with fetched data', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDoraResponse,
    });

    render(<DoraDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/trend/i)).toBeInTheDocument();
    });
  });

  it('shows empty state on fetch failure', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<DoraDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No data available')).toBeInTheDocument();
    });
  });

  it('shows empty state on non-ok response', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<DoraDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No data available')).toBeInTheDocument();
    });
  });
});
