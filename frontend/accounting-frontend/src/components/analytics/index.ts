/**
 * Analytics Components Index
 * Exports all analytics dashboard components for easy importing
 */

export { default as LogTrendAnalysis } from './LogTrendAnalysis';
export { default as SecurityThreatDetection } from './SecurityThreatDetection';
export { default as PerformanceAnalytics } from './PerformanceAnalytics';
export { default as ComplianceStatusDashboard } from './ComplianceStatusDashboard';

// Types
export type { 
  LogTrendData, 
  TrendMetrics,
  LogTrendAnalysisProps 
} from './LogTrendAnalysis';

export type { 
  SecurityEvent, 
  ThreatMetrics,
  SecurityThreatDetectionProps 
} from './SecurityThreatDetection';

export type { 
  PerformanceMetrics, 
  PerformanceSummary,
  PerformanceAnalyticsProps 
} from './PerformanceAnalytics';

export type { 
  ComplianceControl, 
  ComplianceMetrics,
  ComplianceDashboardProps 
} from './ComplianceStatusDashboard';