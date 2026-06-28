'use client';

import { useState } from 'react';
import { Search, Filter, SlidersHorizontal, X } from 'lucide-react';
import { getReviews } from '@/lib/api';
import type { Review } from '@/lib/types';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorAlert from '@/components/ErrorAlert';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [sentiment, setSentiment] = useState('');
  const [category, setCategory] = useState('');
  const [platform, setPlatform] = useState('');
  const [minRating, setMinRating] = useState('');
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getReviews({ 
        q: query, 
        sentiment, 
        category, 
        platform,
        limit: 50 
      });
      setReviews(data.reviews || []);
    } catch (err) {
      setError('Failed to fetch reviews. Please try again.');
      setReviews([]);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setSentiment('');
    setCategory('');
    setPlatform('');
    setMinRating('');
  };

  const hasActiveFilters = sentiment || category || platform || minRating;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
          <Search className="text-indigo-500" />
          Search Reviews
        </h1>
        <p className="text-slate-400 dark:text-slate-400">
          Search and filter through analyzed user reviews
        </p>
      </div>

      {/* Search Form */}
      <div className="card space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-400" />
            <input
              type="text"
              placeholder="Search reviews..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg pl-10 pr-4 py-2 text-gray-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <LoadingSpinner size={16} /> : <Search size={16} />}
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
          >
            <SlidersHorizontal size={16} />
            Filters
          </button>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="pt-4 border-t border-gray-200 dark:border-slate-700 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-700 dark:text-gray-300">Advanced Filters</h3>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <X size={14} />
                  Clear all
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Sentiment Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Sentiment
                </label>
                <select
                  value={sentiment}
                  onChange={(e) => setSentiment(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-gray-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Sentiments</option>
                  <option value="positive">Positive</option>
                  <option value="neutral">Neutral</option>
                  <option value="negative">Negative</option>
                </select>
              </div>

              {/* Category Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-gray-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Categories</option>
                  <option value="recommendation">Recommendation</option>
                  <option value="ui">UI</option>
                  <option value="search">Search</option>
                  <option value="performance">Performance</option>
                  <option value="audio">Audio</option>
                </select>
              </div>

              {/* Platform Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Platform
                </label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-gray-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Platforms</option>
                  <option value="ios">iOS</option>
                  <option value="android">Android</option>
                  <option value="web">Web</option>
                </select>
              </div>

              {/* Rating Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Minimum Rating
                </label>
                <select
                  value={minRating}
                  onChange={(e) => setMinRating(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-gray-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Any Rating</option>
                  <option value="5">5 Stars</option>
                  <option value="4">4+ Stars</option>
                  <option value="3">3+ Stars</option>
                  <option value="2">2+ Stars</option>
                  <option value="1">1+ Stars</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <ErrorAlert 
          message={error} 
          onRetry={handleSearch}
        />
      )}

      {/* Results */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size={48} />
        </div>
      ) : reviews.length > 0 ? (
        <div className="space-y-4">
          <p className="text-slate-400 dark:text-slate-400 text-sm">
            {reviews.length} reviews found
            {hasActiveFilters && ' (filtered)'}
          </p>
          {reviews.map((review) => (
            <div key={review.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <p className="text-gray-900 dark:text-slate-200 flex-1">"{review.review_text}"</p>
                <div className="flex gap-2 ml-4 flex-shrink-0">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    review.sentiment === 'positive' ? 'bg-emerald-900/30 text-emerald-400' :
                    review.sentiment === 'negative' ? 'bg-red-900/30 text-red-400' :
                    'bg-blue-900/30 text-blue-400'
                  }`}>
                    {review.sentiment || 'neutral'}
                  </span>
                  {review.rating && (
                    <span className="px-2 py-1 bg-amber-900/30 text-amber-400 rounded text-xs">
                      {'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-4 text-sm text-slate-400 dark:text-slate-400">
                {review.category && (
                  <span>Category: <span className="text-indigo-400">{review.category}</span></span>
                )}
                {review.platform && (
                  <span>Platform: <span className="text-indigo-400">{review.platform}</span></span>
                )}
              </div>
              {review.barriers && review.barriers.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-400 mb-2">Discovery Barriers:</p>
                  <div className="flex flex-wrap gap-2">
                    {review.barriers.map((barrier, idx) => (
                      <span key={idx} className="px-2 py-1 bg-gray-100 dark:bg-slate-800 rounded text-xs text-gray-700 dark:text-slate-300">
                        {barrier}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Search size={48} className="text-slate-400 dark:text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 dark:text-slate-400">
            {query || hasActiveFilters ? 'No reviews found matching your search.' : 'Enter a search query or apply filters to find reviews.'}
          </p>
        </div>
      )}
    </div>
  );
}
