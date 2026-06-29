'use client';

import { useState, useEffect } from 'react';
import { Layers, Tag } from 'lucide-react';
import { getThemes } from '@/lib/api';
import type { ThemeCluster } from '@/lib/types';
import ErrorAlert from '@/components/ErrorAlert';

export default function ThemesPage() {
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getThemes();
        setThemes(data);
      } catch (err) {
        setError('Failed to fetch theme clusters');
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
          <Layers className="text-indigo-500" />
          Theme Clusters
        </h1>
        <p className="text-slate-400 dark:text-slate-400">
          Discover the main themes and topics emerging from user reviews
        </p>
      </div>

      {/* Themes Grid */}
      {themes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {themes.map((theme) => (
            <div key={theme.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-indigo-400">
                  {theme.name}
                </h3>
                <Tag size={16} className="text-slate-400" />
              </div>
              
              <p className="text-slate-300 dark:text-slate-300 text-sm mb-4">{theme.description}</p>
              
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400 dark:text-slate-400">
                  {theme.review_count} reviews
                </span>
                <div className="flex gap-2">
                  <span className="text-emerald-400">
                    {theme.sentiment_distribution?.positive || 0}+
                  </span>
                  <span className="text-rose-400">
                    {theme.sentiment_distribution?.negative || 0}-
                  </span>
                </div>
              </div>

              {theme.representative_reviews && theme.representative_reviews.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-800">
                  <p className="text-xs text-slate-500 mb-2">Sample Review:</p>
                  <p className="text-sm text-slate-300 dark:text-slate-300 italic">
                    "{theme.representative_reviews[0]}"
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Layers size={48} className="text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 dark:text-slate-400">
            No themes available. Run the pipeline to analyze reviews.
          </p>
        </div>
      )}
    </div>
  );
}
