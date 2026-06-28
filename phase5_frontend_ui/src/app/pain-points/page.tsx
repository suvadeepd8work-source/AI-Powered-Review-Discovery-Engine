import { AlertTriangle, Frown } from 'lucide-react';
import { getInsights } from '@/lib/api';
import type { Insight } from '@/lib/types';
import ErrorAlert from '@/components/ErrorAlert';

export default async function PainPointsPage() {
  let insights: Insight[] = [];
  let error = null;

  try {
    insights = await getInsights();
  } catch (err) {
    error = 'Failed to fetch pain points';
    console.error(err);
  }

  // Filter insights for pain points
  const painPoints = insights.filter((insight) => 
    insight.type === 'pain_point'
  );

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Error Alert */}
      {error && (
        <ErrorAlert 
          message={error}
        />
      )}

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
          <AlertTriangle className="text-amber-500" />
          Pain Points
        </h1>
        <p className="text-slate-400 dark:text-slate-400">
          Key user frustrations and barriers identified from reviews
        </p>
      </div>

      {/* Pain Points List */}
      {painPoints.length > 0 ? (
        <div className="space-y-4">
          {painPoints.map((insight) => (
            <div key={insight.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-amber-400">
                  Pain Point
                </h3>
                <Frown size={16} className="text-slate-400" />
              </div>
              
              <p className="text-slate-300 dark:text-slate-300 text-sm mb-4">{insight.content}</p>

              <div className="flex items-center gap-2 text-sm text-slate-400 dark:text-slate-400">
                <span>Confidence:</span>
                <span className="text-indigo-400">{(insight.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <AlertTriangle size={48} className="text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 dark:text-slate-400">
            No pain points available. Run the pipeline to analyze reviews.
          </p>
        </div>
      )}
    </div>
  );
}
