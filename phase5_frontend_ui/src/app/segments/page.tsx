'use client';

import { useState, useEffect } from 'react';
import { Users, Target } from 'lucide-react';
import { getSegments } from '@/lib/api';
import type { UserSegment } from '@/lib/types';
import ErrorAlert from '@/components/ErrorAlert';

export default function SegmentsPage() {
  const [segments, setSegments] = useState<UserSegment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getSegments();
        setSegments(data);
      } catch (err) {
        setError('Failed to fetch user segments');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

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
          <Users className="text-indigo-500" />
          User Segments
        </h1>
        <p className="text-slate-400 dark:text-slate-400">
          Distinct user groups identified based on behavior and preferences
        </p>
      </div>

      {/* Segments Grid */}
      {segments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {segments.map((segment) => (
            <div key={segment.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-indigo-400">
                  {segment.name}
                </h3>
                <Target size={16} className="text-slate-400" />
              </div>
              
              <p className="text-slate-300 dark:text-slate-300 text-sm mb-4">{segment.description}</p>
              
              {segment.traits && segment.traits.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-slate-400 mb-2">Traits:</h4>
                  <div className="flex flex-wrap gap-2">
                    {segment.traits.map((trait, idx) => (
                      <span key={idx} className="px-2 py-1 bg-gray-100 dark:bg-slate-800 rounded text-xs text-gray-700 dark:text-slate-300">
                        {trait}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {segment.challenges && segment.challenges.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-slate-400 mb-2">Challenges:</h4>
                  <ul className="space-y-1">
                    {segment.challenges.map((challenge, idx) => (
                      <li key={idx} className="text-slate-300 dark:text-slate-300 text-sm flex items-start gap-2">
                        <span className="text-amber-500 mt-1">•</span>
                        {challenge}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-4 border-t border-gray-200 dark:border-slate-800 text-sm text-slate-400 dark:text-slate-400">
                {segment.size} reviews in this segment
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Users size={48} className="text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 dark:text-slate-400">
            No user segments available. Run the pipeline to analyze reviews.
          </p>
        </div>
      )}
    </div>
  );
}
