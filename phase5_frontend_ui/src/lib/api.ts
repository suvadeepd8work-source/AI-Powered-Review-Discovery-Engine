/**
 * API client for backend communication
 * The frontend never directly accesses JSON files - only backend APIs
 */

import type {
  LatestAnalysis,
  ThemeCluster,
  PainPoint,
  FeatureRequest,
  UserSegment,
  Insight,
  Report,
  Review,
  PipelineStatus,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://ai-powered-review-discovery-engine.onrender.com';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function fetchWithRetry<T>(
  url: string,
  options: RequestInit = {},
  retries = 3
): Promise<T> {
  const fullUrl = `${API_BASE_URL}${url}`;
  
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (i === retries - 1) throw error;
      // Exponential backoff: 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
  throw new Error('Max retries exceeded');
}

// Reviews API
export async function getReviews(params?: {
  q?: string;
  sentiment?: string;
  category?: string;
  platform?: string;
  limit?: number;
  offset?: number;
}): Promise<{ reviews: Review[]; total: number }> {
  const queryString = new URLSearchParams(params as any).toString();
  const url = queryString ? `/api/reviews?${queryString}` : '/api/reviews';
  return fetchWithRetry(url);
}

// Insights API
export async function getThemes(): Promise<ThemeCluster[]> {
  return fetchWithRetry('/api/insights/themes');
}

export async function getSegments(): Promise<UserSegment[]> {
  return fetchWithRetry('/api/insights/segments');
}

export async function getInsights(): Promise<Insight[]> {
  return fetchWithRetry('/api/insights/insights');
}

export async function getReport(): Promise<Report> {
  return fetchWithRetry('/api/insights/report');
}

export async function getLatestAnalysis(): Promise<LatestAnalysis> {
  return fetchWithRetry('/api/insights/latest');
}

// Pipeline API
export async function runPipeline(): Promise<{ run_id: string }> {
  return fetchWithRetry('/api/pipeline/run', { method: 'POST' });
}

export async function getPipelineStatus(runId: string): Promise<PipelineStatus> {
  return fetchWithRetry(`/api/pipeline/status/${runId}`);
}

// Health API
export async function getHealth(): Promise<{ status: string; timestamp: string }> {
  return fetchWithRetry('/api/health');
}
