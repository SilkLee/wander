import React from 'react';
import { render, screen } from '@testing-library/react';
import DoraDashboard from './DoraDashboard';
import DoraMetricCard from './DoraMetricCard';
import DoraTrendChart from './DoraTrendChart';

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
});

describe('DoraDashboard', () => {
  it('renders dashboard heading', () => {
    render(<DoraDashboard />);
    expect(screen.getByRole('heading', { name: /dora metrics/i })).toBeInTheDocument();
  });

  it('renders all four DORA metric cards', () => {
    render(<DoraDashboard />);
    expect(screen.getByText('Deployment Frequency')).toBeInTheDocument();
    expect(screen.getByText('Lead Time for Changes')).toBeInTheDocument();
    expect(screen.getByText('Change Failure Rate')).toBeInTheDocument();
    expect(screen.getByText('Mean Time to Recovery')).toBeInTheDocument();
  });

  it('renders a trend chart', () => {
    render(<DoraDashboard />);
    expect(screen.getByText(/trend/i)).toBeInTheDocument();
  });
});
