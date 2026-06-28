import { Sparkles, Play, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import MetricCard from '@/components/MetricCard';
import { Database, ShieldAlert, BarChart3 } from 'lucide-react';
import { getLatestAnalysis } from '@/lib/api';
import type { LatestAnalysis } from '@/lib/types';
import SentimentChart from '@/components/SentimentChart';
import CustomBarChart from '@/components/BarChart';
import LoadingSpinner from '@/components/LoadingSpinner';
import SkeletonCard from '@/components/SkeletonCard';
import ErrorAlert from '@/components/ErrorAlert';

export default async function OverviewPage() {
  let latestData: LatestAnalysis | null = null;
  let error = null;

  try {
    latestData = await getLatestAnalysis();
  } catch (err) {
    error = 'Failed to fetch latest analysis data';
    console.error(err);
  }

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Error Alert */}
      {error && (
        <ErrorAlert 
          message={error}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Dashboard Overview</h1>
          <p className="text-slate-400 dark:text-slate-400">
            AI-Powered Music App Review Analysis Dashboard
          </p>
          {latestData?.last_analysis_timestamp && (
            <div className="flex items-center gap-2 text-sm text-slate-500 mt-2">
              <Clock size={14} />
              <span>Last analysis: {formatTimestamp(latestData.last_analysis_timestamp)}</span>
            </div>
          )}
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg font-medium transition-colors">
          <Play size={16} fill="white" />
          Run Pipeline
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Total Reviews"
          value={latestData?.total_reviews || 0}
          change={latestData?.sentiment_distribution?.positive ? `${latestData.sentiment_distribution.positive} positive` : undefined}
          icon={Database}
        />
        <MetricCard
          title="Discovery Issues Flagged"
          value={latestData?.sentiment_distribution?.negative || 0}
          change={latestData?.total_reviews && latestData?.sentiment_distribution?.negative 
            ? `${((latestData.sentiment_distribution.negative / latestData.total_reviews) * 100).toFixed(1)}% of total`
            : undefined
          }
          icon={ShieldAlert}
          iconColor="text-amber-500"
        />
        <MetricCard
          title="Active Insights Agents"
          value="7 / 7"
          change={latestData?.data_available ? 'All agents online' : 'Waiting for data'}
          icon={BarChart3}
          iconColor="text-pink-500"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
          {latestData?.sentiment_distribution ? (
            <SentimentChart data={latestData.sentiment_distribution} />
          ) : (
            <div className="flex items-center justify-center h-[300px]">
              <LoadingSpinner size={32} />
            </div>
          )}
        </div>

        {/* Themes Overview */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Review Categories</h3>
          {latestData?.category_distribution ? (
            <CustomBarChart
              data={latestData.category_distribution}
              color="#6366f1"
            />
          ) : (
            <CustomBarChart
              data={[
                { name: 'Recommendation', value: 45 },
                { name: 'UI', value: 32 },
                { name: 'Search', value: 28 },
                { name: 'Performance', value: 15 },
                { name: 'Audio', value: 12 },
              ]}
              color="#6366f1"
            />
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Analysis Status</h3>
          {latestData?.data_available ? (
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle size={20} />
              <span>Data available from latest pipeline run</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-amber-400">
              <AlertCircle size={20} />
              <span>Run the pipeline to generate insights</span>
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Report Availability</h3>
          {latestData?.report_available ? (
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle size={20} />
              <span>Executive report available</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-400">
              <Sparkles size={20} />
              <span>Report will be generated after pipeline completion</span>
            </div>
          )}
        </div>
      </div>

      {/* Top Insights */}
      {latestData?.data_available ? (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Top Insights</h3>
          <div className="space-y-4">
            {latestData.top_theme && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-1">Top Theme</h4>
                <p className="text-indigo-400">{latestData.top_theme}</p>
              </div>
            )}
            {latestData.top_segment && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-1">Top User Segment</h4>
                <p className="text-indigo-400">{latestData.top_segment}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <SkeletonCard />
      )}
    </div>
  );
}
