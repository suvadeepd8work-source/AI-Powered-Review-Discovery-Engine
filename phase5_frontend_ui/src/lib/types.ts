export interface SentimentDistribution {
  positive: number;
  neutral: number;
  negative: number;
}

export interface CategoryDistribution {
  name: string;
  value: number;
}

export interface LatestAnalysis {
  total_reviews: number;
  sentiment_distribution: SentimentDistribution;
  category_distribution?: CategoryDistribution[];
  data_available: boolean;
  report_available: boolean;
  top_theme?: string;
  top_segment?: string;
  last_analysis_timestamp?: string;
}

export interface ThemeCluster {
  id: string;
  name: string;
  description: string;
  review_count: number;
  sentiment_distribution: SentimentDistribution;
  representative_reviews: string[];
}

export interface PainPoint {
  id: string;
  description: string;
  frequency: number;
  severity: 'low' | 'medium' | 'high';
  target_segments: string[];
  representative_reviews: string[];
}

export interface FeatureRequest {
  id: string;
  description: string;
  impact_score: number;
  request_count: number;
  target_segments: string[];
  status: 'pending' | 'in_progress' | 'implemented';
}

export interface UserSegment {
  id: string;
  name: string;
  description: string;
  size: number;
  traits: string[];
  challenges: string[];
  listening_behavior: string;
}

export interface Insight {
  id: string;
  type: 'pain_point' | 'feature_request' | 'theme';
  content: string;
  confidence: number;
}

export interface Report {
  summary: string;
  content: string;
  generated_at: string;
  insights: Insight[];
}

export interface Review {
  id: string;
  review_text: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  rating?: number;
  category?: string;
  platform?: string;
  barriers?: string[];
  timestamp?: string;
}

export interface PipelineStatus {
  run_id: string;
  status: 'running' | 'completed' | 'failed';
  current_phase: string;
  phases: Array<{
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
  }>;
  started_at: string;
  completed_at?: string;
  error?: string;
}
