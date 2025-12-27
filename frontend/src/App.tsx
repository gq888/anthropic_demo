import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import type { CitationEntry, EvaluationResult, EventMessage, RunSummary } from './types';

const API_BASE = (import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_API_BASE ??
  'http://localhost:8000/api';
const WS_BASE = (import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_WS_BASE ??
  'ws://localhost:8000/api/ws';

export default function App() {
  const [query, setQuery] = useState('2025年排名最高的AI代理平台有哪些？');
  const [goal, setGoal] = useState('总结生态和差异。');
  const [activeRunId, setActiveRunId] = useState<string>('');
  const [events, setEvents] = useState<EventMessage[]>([]);

  useEffect(() => {
    if (!activeRunId) {
      return undefined;
    }
    const socket = new WebSocket(`${WS_BASE}/runs/${activeRunId}`);
    socket.onmessage = (message: MessageEvent<string>) => {
      try {
        const data = JSON.parse(message.data) as EventMessage;
        setEvents((prev: EventMessage[]) => [...prev, data]);
      } catch (error) {
        console.error('Failed to parse event message', error);
      }
    };
    return () => {
      socket.close();
    };
  }, [activeRunId]);

  const runQuery = useQuery<RunSummary>({
    queryKey: ['run', activeRunId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/runs/${activeRunId}`);
      if (!response.ok) {
        throw new Error('Run not found');
      }
      return (await response.json()) as RunSummary;
    },
    enabled: Boolean(activeRunId),
    refetchInterval: 5000,
  });

  const createRun = useMutation<{ run_id: string }, Error, void>({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, goal }),
      });
      if (!response.ok) {
        throw new Error('Failed to create run');
      }
      return (await response.json()) as { run_id: string };
    },
    onSuccess: (data: { run_id: string }) => {
      setActiveRunId(data.run_id);
      setEvents([]);
    },
  });

  const plan = useMemo(() => runQuery.data?.plan ?? 'Plan will appear once the lead agent responds.', [runQuery.data]);
  const finalReport = useMemo(
    () => runQuery.data?.final_report ?? 'Research loop has not finished yet.',
    [runQuery.data]
  );

  return (
    <div className="app-shell">
      <header>
        <div>
          <p className="eyebrow">Inspired by Anthropic's Research architecture</p>
          <h1>Multi-Agent Research Demo</h1>
        </div>
        {activeRunId && <span className="run-id">Run ID: {activeRunId}</span>}
      </header>

      <main>
        <section className="panel">
          <div className="panel-header">
            <h2>New Research Run</h2>
            <p>Lead agent plans, subagents explore, citation agent wraps up.</p>
          </div>
          <label>
            Query
            <textarea
              value={query}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setQuery(event.target.value)}
              rows={3}
            />
          </label>
          <label>
            Goal
            <textarea
              value={goal}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setGoal(event.target.value)}
              rows={3}
            />
          </label>
          <button onClick={() => createRun.mutate()} disabled={createRun.isPending}>
            {createRun.isPending ? 'Launching…' : 'Launch Run'}
          </button>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Live Event Stream</h2>
            <p>WebSocket feed of planning, delegation, tool calls and synthesis.</p>
          </div>
          <div className="events" data-empty={!events.length}>
            {events.length === 0 && <p className="muted">Run events will appear here once started.</p>}
            {events.map((event: EventMessage, idx: number) => (
              <article key={`${event.type}-${idx}`} className="event-item">
                <div className="event-meta">
                  <span className="event-type">{event.type}</span>
                  <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
                {event.type === 'citations_generated' ? (
                  <div className="citation-event">
                    <div className="citation-summary">
                      Generated {(event.payload as any).citation_count} citations
                    </div>
                    {(event.payload as any).report_preview && (
                      <div className="report-preview">
                        <strong>Report Preview:</strong> {(event.payload as any).report_preview}
                      </div>
                    )}
                  </div>
                ) : event.type === 'evaluation_completed' ? (
                  <div className="evaluation-event">
                    <div className="evaluation-overview">
                      <span
                        className={`score-pill ${((event.payload as any)?.passed ?? false) ? 'score-pass' : 'score-fail'}`}
                      >
                        {Math.round((((event.payload as any)?.overall_score ?? 0) as number) * 100)}%
                      </span>
                      <span className="score-status">
                        {((event.payload as any)?.passed ?? false) ? 'Pass' : 'Needs review'}
                      </span>
                    </div>
                    <div className="rubric-grid">
                      {Object.entries(((event.payload as any)?.rubric_scores ?? {}) as Record<string, number>).map(
                        ([criterion, score]) => (
                          <div key={criterion} className="rubric-row">
                            <span className="rubric-label">{criterion.replace(/_/g, ' ')}</span>
                            <span className="rubric-score">{Math.round(score * 100)}%</span>
                          </div>
                        ),
                      )}
                    </div>
                    {Boolean((event.payload as any)?.feedback) && (
                      <p className="evaluation-feedback">{String((event.payload as any)?.feedback)}</p>
                    )}
                  </div>
                ) : (
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                )}
              </article>
            ))}
          </div>
        </section>

        {runQuery.data && (
          <section className="panel">
            <div className="panel-header">
              <h2>Run Summary</h2>
              <p>Track the lead researcher plan, aggregated findings and citations.</p>
            </div>
            <div className="summary-grid">
              <div>
                <h3>Status</h3>
                <p className="status-chip">{runQuery.data.status}</p>
              </div>
              <div>
                <h3>Plan</h3>
                <pre>{plan}</pre>
              </div>
              <div>
                <h3>Final Report</h3>
                <pre className="final">{finalReport}</pre>
              </div>
              <div>
                <h3>Citations</h3>
                {runQuery.data.citations && runQuery.data.citations.length > 0 ? (
                  <div className="citations-list">
                    {runQuery.data.citations.map((citation: CitationEntry, index: number) => (
                      <div key={`${citation.citation}-${index}`} className="citation-item">
                        <span className="citation-number">[{index + 1}]</span>
                        <span className="citation-text">{citation.citation}</span>
                        {citation.url && (
                          <a 
                            href={citation.url} 
                            target="_blank" 
                            rel="noreferrer"
                            className="citation-link"
                          >
                            🌐 Visit Source
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted">Citations will be listed once the citation agent completes.</p>
                )}
              </div>
              <div>
                <h3>Evaluation</h3>
                {runQuery.data.evaluation ? (
                  <EvaluationSummary evaluation={runQuery.data.evaluation} />
                ) : (
                  <p className="muted">Evaluation will appear once the judge agent completes.</p>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

type EvaluationSummaryProps = {
  evaluation: EvaluationResult;
};

function EvaluationSummary({ evaluation }: EvaluationSummaryProps) {
  const entries = Object.entries(evaluation.rubric_scores ?? {});

  return (
    <div className="evaluation-card">
      <div className="evaluation-overview">
        <span className={`score-pill ${evaluation.passed ? 'score-pass' : 'score-fail'}`}>
          {Math.round(evaluation.overall_score * 100)}%
        </span>
        <span className="score-status">{evaluation.passed ? 'Pass' : 'Needs review'}</span>
      </div>
      {entries.length > 0 && (
        <div className="rubric-grid">
          {entries.map(([criterion, score]) => (
            <div key={criterion} className="rubric-row">
              <span className="rubric-label">{criterion.replace(/_/g, ' ')}</span>
              <span className="rubric-score">{Math.round(score * 100)}%</span>
            </div>
          ))}
        </div>
      )}
      {evaluation.feedback && <p className="evaluation-feedback">{evaluation.feedback}</p>}
    </div>
  );
}
