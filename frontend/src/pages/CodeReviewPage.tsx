import React, { useState } from 'react';
import { executeWorkflow } from '../api/workflows';
import type { WorkflowExecutionResponse } from '../api/workflows';

function CodeReviewPage() {
  const [diff, setDiff] = useState('');
  const [standards, setStandards] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkflowExecutionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReview = async () => {
    if (!diff.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await executeWorkflow({
        workflow_type: 'code_review',
        inputs: { diff, coding_standards: standards || undefined },
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28 }}>Code Review</h1>
      <p style={{ margin: '0 0 24px', color: '#666', fontSize: 14 }}>
        AI-powered code review with actionable feedback
      </p>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          PR Diff *
        </label>
        <textarea
          value={diff}
          onChange={(e) => setDiff(e.target.value)}
          placeholder="Paste PR diff here..."
          style={{
            width: '100%',
            minHeight: 180,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #ccc',
            fontFamily: 'monospace',
            fontSize: 13,
            resize: 'vertical',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          Coding Standards (optional)
        </label>
        <textarea
          value={standards}
          onChange={(e) => setStandards(e.target.value)}
          placeholder="Team coding standards or style guide..."
          style={{
            width: '100%',
            minHeight: 80,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 13,
            resize: 'vertical',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <button
        onClick={handleReview}
        disabled={loading || !diff.trim()}
        style={{
          padding: '8px 24px',
          borderRadius: 6,
          border: 'none',
          backgroundColor: '#9c27b0',
          color: '#fff',
          fontSize: 14,
          cursor: loading ? 'wait' : 'pointer',
          opacity: loading || !diff.trim() ? 0.6 : 1,
        }}
      >
        {loading ? 'Reviewing...' : 'Review Code'}
      </button>

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: 6,
            backgroundColor: '#fce4ec',
            color: '#c62828',
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: 24,
            background: '#fff',
            borderRadius: 8,
            padding: 24,
            border: '1px solid #e0e0e0',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>Review Result</h2>
            <span
              style={{
                padding: '4px 12px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: result.status === 'completed' ? '#4caf50' : '#f44336',
              }}
            >
              {result.status}
            </span>
          </div>
          {result.error && (
            <p style={{ color: '#c62828' }}>Error: {result.error}</p>
          )}
          <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>
            Execution time: {result.execution_time.toFixed(2)}s
          </div>
          <pre
            style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 6,
              overflow: 'auto',
              fontSize: 13,
              maxHeight: 400,
            }}
          >
            {JSON.stringify(result.outputs, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default CodeReviewPage;
