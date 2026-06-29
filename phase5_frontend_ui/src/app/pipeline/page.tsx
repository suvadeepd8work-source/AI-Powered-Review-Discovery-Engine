'use client';

import { useState, useEffect } from 'react';
import { Activity, Play, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { runPipeline, getPipelineStatus } from '@/lib/api';
import type { PipelineStatus } from '@/lib/types';
import ErrorAlert from '@/components/ErrorAlert';

export default function PipelinePage() {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [error, setError] = useState('');
  const [isPolling, setIsPolling] = useState(false);

  const startPipeline = async () => {
    console.log('[Pipeline] Start button clicked');
    setError('');
    try {
      console.log('[Pipeline] Calling runPipeline API...');
      const result = await runPipeline();
      console.log('[Pipeline] Pipeline started:', result);
      setPipelineStatus({
        run_id: result.run_id,
        status: 'running',
        current_phase: 'Pipeline started',
        phases: [],
        started_at: new Date().toISOString(),
      });
      setIsPolling(true);
    } catch (err) {
      console.error('[Pipeline] Error starting pipeline:', err);
      setError('Failed to start pipeline');
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isPolling && pipelineStatus?.run_id && pipelineStatus.status === 'running') {
      interval = setInterval(async () => {
        try {
          const result = await getPipelineStatus(pipelineStatus.run_id);
          setPipelineStatus(result);
          
          if (result.status === 'completed' || result.status === 'failed') {
            setIsPolling(false);
            clearInterval(interval);
          }
        } catch (err) {
          setError('Failed to check pipeline status');
          setIsPolling(false);
          clearInterval(interval);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPolling, pipelineStatus?.run_id, pipelineStatus?.status]);

  const getPhaseStatusIcon = (phaseStatus: string) => {
    switch (phaseStatus) {
      case 'completed':
        return <CheckCircle className="text-emerald-500" size={16} />;
      case 'running':
        return <Activity className="text-indigo-500 animate-spin" size={16} />;
      case 'failed':
        return <AlertCircle className="text-red-500" size={16} />;
      default:
        return <Clock className="text-slate-400" size={16} />;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
            <Activity className="text-indigo-500" />
            Pipeline Status
          </h1>
          <p className="text-slate-400 dark:text-slate-400">
            Monitor and control the multi-agent analysis pipeline
          </p>
        </div>
        <button
          onClick={startPipeline}
          disabled={isPolling}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          <Play size={16} fill="white" />
          {isPolling ? 'Running...' : 'Run Pipeline'}
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <ErrorAlert 
          message={error}
          onRetry={startPipeline}
        />
      )}

      {/* Pipeline Status Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Current Status</h2>
          <div className="flex items-center gap-2">
            {!pipelineStatus && <Clock className="text-slate-400" size={20} />}
            {pipelineStatus?.status === 'running' && <Activity className="text-indigo-500 animate-spin" size={20} />}
            {pipelineStatus?.status === 'completed' && <CheckCircle className="text-emerald-500" size={20} />}
            {pipelineStatus?.status === 'failed' && <AlertCircle className="text-red-500" size={20} />}
            <span className={`font-medium ${
              pipelineStatus?.status === 'completed' ? 'text-emerald-400' :
              pipelineStatus?.status === 'failed' ? 'text-red-400' :
              pipelineStatus?.status === 'running' ? 'text-indigo-400' :
              'text-slate-400'
            }`}>
              {pipelineStatus?.status?.toUpperCase() || 'IDLE'}
            </span>
          </div>
        </div>

        {pipelineStatus?.run_id && (
          <div className="mb-4 text-sm text-slate-400 dark:text-slate-400">
            Run ID: <span className="text-indigo-400 font-mono">{pipelineStatus.run_id}</span>
          </div>
        )}

        {pipelineStatus?.current_phase && (
          <div className="mb-4 p-4 bg-gray-100 dark:bg-slate-800 rounded-lg">
            <p className="text-gray-700 dark:text-slate-300">{pipelineStatus.current_phase}</p>
          </div>
        )}

        {pipelineStatus?.error && (
          <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
            {pipelineStatus.error}
          </div>
        )}

        {pipelineStatus?.started_at && (
          <div className="mt-4 text-sm text-slate-400 dark:text-slate-400">
            Started: {new Date(pipelineStatus.started_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Pipeline Phases */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-6">Pipeline Phases</h2>
        <div className="space-y-4">
          {pipelineStatus?.phases && pipelineStatus.phases.length > 0 ? (
            pipelineStatus.phases.map((phase, index) => (
              <div key={index} className="flex items-start gap-4 p-4 bg-gray-100 dark:bg-slate-800 rounded-lg">
                <div className="flex-shrink-0">
                  {getPhaseStatusIcon(phase.status)}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-slate-200">{phase.name}</h3>
                  <p className="text-sm text-slate-400 dark:text-slate-400 capitalize">{phase.status}</p>
                </div>
              </div>
            ))
          ) : (
            // Default phases when no pipeline is running
            [
              { name: 'Data Ingestion', description: 'Collect and store raw reviews from sources' },
              { name: 'Data Cleaning', description: 'Agent 2: Clean and standardize review text' },
              { name: 'Review Analysis', description: 'Agent 3: Analyze sentiment and categorize reviews' },
              { name: 'Theme Clustering', description: 'Agent 4: Identify and cluster themes' },
              { name: 'User Segmentation', description: 'Agent 5: Segment users by behavior' },
              { name: 'Product Insights', description: 'Agent 6: Generate product insights' },
              { name: 'Executive Report', description: 'Agent 7: Create comprehensive report' },
            ].map((phase, index) => (
              <div key={index} className="flex items-start gap-4 p-4 bg-gray-100 dark:bg-slate-800 rounded-lg">
                <div className="flex-shrink-0">
                  <Clock className="text-slate-400" size={16} />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-slate-200">{phase.name}</h3>
                  <p className="text-sm text-slate-400 dark:text-slate-400">{phase.description}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Agent Status */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-6">Agent Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { name: 'Agent 1: Review Collector', status: 'Ready' },
            { name: 'Agent 2: Data Cleaner', status: 'Ready' },
            { name: 'Agent 3: Review Analyzer', status: 'Ready' },
            { name: 'Agent 4: Theme Clustering', status: 'Ready' },
            { name: 'Agent 5: User Segmentation', status: 'Ready' },
            { name: 'Agent 6: Product Insights', status: 'Ready' },
            { name: 'Agent 7: Executive Report', status: 'Ready' },
          ].map((agent) => (
            <div key={agent.name} className="p-4 bg-gray-100 dark:bg-slate-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-900 dark:text-slate-200">{agent.name}</span>
                <span className="px-2 py-0.5 bg-emerald-900/30 text-emerald-400 rounded text-xs">
                  {agent.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
