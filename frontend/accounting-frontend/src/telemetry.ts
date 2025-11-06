/**
 * Telemetry Services Index
 * Main exports for the telemetry system
 */

// Services
export { default as telemetryService } from './services/telemetryService';
export { default as performanceMonitor } from './services/performanceMonitor';
export { default as eventTracker } from './services/eventTracker';
export { default as analyticsService } from './services/analytics';
export { default as telemetryAPI } from './services/telemetryAPI';

// React Context
export { TelemetryProvider, useTelemetry } from './contexts/TelemetryContext';

// React Hooks
export {
  useComponentTelemetry,
  useInteractionTracking,
  useFormTelemetry,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useJourneyTracking,
  useABTest,
  useConsentManagement,
  useRealTimeAnalytics,
} from './hooks/useTelemetry';

// Components
export { ConsentBanner, ConsentSettings, useConsent } from './components/ConsentManagement';
export { TelemetryDashboard } from './components/TelemetryDashboard';
export { ErrorBoundary, useErrorHandler } from './components/ErrorBoundary';

// Types
export type {
  TelemetryEvent,
  TelemetryConfig,
  ConsentPreferences,
} from './services/telemetryService';

export type {
  PerformanceMetric,
  CoreWebVitals,
  NavigationTiming,
  ResourceTiming,
} from './services/performanceMonitor';

export type {
  InteractionEvent,
  FormEvent,
  NavigationEvent,
  FeatureUsageEvent,
} from './services/eventTracker';

export type {
  AnalyticsMetrics,
  UserJourney,
  CohortAnalysis,
  RealTimeMetrics,
  ConversionFunnel,
} from './services/analytics';

export type {
  TelemetryEventData,
  TelemetryBatchResponse,
} from './services/telemetryAPI';

export type {
  ErrorBoundaryState,
} from './components/ErrorBoundary';

// Default configuration
export const defaultTelemetryConfig = {
  apiEndpoint: '/api/telemetry',
  batchSize: 10,
  flushInterval: 30000,
  enableConsoleLogging: process.env.NODE_ENV === 'development',
  enableErrorTracking: true,
  enablePerformanceTracking: true,
  sampleRate: 1.0,
  anonymize: false,
  enableConsentMode: true,
};

// Helper functions
export const initializeTelemetry = (config = {}) => {
  const finalConfig = { ...defaultTelemetryConfig, ...config };
  
  return {
    config: finalConfig,
    services: {
      telemetry: telemetryService,
      performance: performanceMonitor,
      events: eventTracker,
      analytics: analyticsService,
      api: telemetryAPI,
    },
  };
};

export const cleanupTelemetry = () => {
  telemetryService.destroy();
  performanceMonitor.destroy();
  eventTracker.destroy();
  analyticsService.destroy();
  telemetryAPI.destroy();
};

export default {
  // Services
  telemetryService,
  performanceMonitor,
  eventTracker,
  analyticsService,
  telemetryAPI,
  
  // React
  TelemetryProvider,
  useTelemetry,
  
  // Hooks
  useComponentTelemetry,
  useInteractionTracking,
  useFormTelemetry,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useJourneyTracking,
  useABTest,
  useConsentManagement,
  useRealTimeAnalytics,
  
  // Components
  ConsentBanner,
  ConsentSettings,
  useConsent,
  TelemetryDashboard,
  ErrorBoundary,
  useErrorHandler,
  
  // Utilities
  initializeTelemetry,
  cleanupTelemetry,
  defaultTelemetryConfig,
};
