/**
 * Custom Analytics and Reporting Service
 * Provides advanced analytics, real-time metrics, and insights
 */

import telemetryService from './telemetryService';
import performanceMonitor from './performanceMonitor';
import eventTracker from './eventTracker';

export interface AnalyticsMetrics {
  pageViews: number;
  uniqueUsers: number;
  sessions: number;
  averageSessionDuration: number;
  bounceRate: number;
  conversions: number;
  topPages: Array<{ page: string; views: number }>;
  topReferrers: Array<{ referrer: string; visits: number }>;
  deviceTypes: Record<string, number>;
  browserTypes: Record<string, number>;
  countries: Record<string, number>;
}

export interface UserJourney {
  steps: Array<{
    step: string;
    timestamp: number;
    page: string;
    duration?: number;
  }>;
  totalDuration: number;
  conversionRate?: number;
}

export interface CohortAnalysis {
  cohort: string;
  period: string;
  users: number;
  retention: number;
  revenue?: number;
}

export interface RealTimeMetrics {
  activeUsers: number;
  currentPage: string;
  recentEvents: Array<{
    type: string;
    timestamp: number;
    userId?: string;
  }>;
  systemLoad: {
    cpu: number;
    memory: number;
    responseTime: number;
  };
}

export interface ConversionFunnel {
  name: string;
  steps: Array<{
    name: string;
    users: number;
    conversionRate: number;
    dropoffRate: number;
  }>;
  overallConversion: number;
}

class AnalyticsService {
  private metrics: AnalyticsMetrics;
  private userJourneys: Map<string, UserJourney> = new Map();
  private realTimeData: RealTimeMetrics;
  private cohortData: Map<string, CohortAnalysis> = new Map();
  private conversionFunnels: Map<string, ConversionFunnel> = new Map();
  private eventBuffer: Array<any> = [];
  private dashboardCallbacks: Array<(metrics: any) => void> = [];

  constructor() {
    this.metrics = this.initializeMetrics();
    this.realTimeData = this.initializeRealTimeData();
    this.setupDataCollection();
    this.startRealTimeUpdates();
  }

  private initializeMetrics(): AnalyticsMetrics {
    const stored = localStorage.getItem('analytics_metrics');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (error) {
        console.warn('Failed to parse stored metrics:', error);
      }
    }

    return {
      pageViews: 0,
      uniqueUsers: 0,
      sessions: 0,
      averageSessionDuration: 0,
      bounceRate: 0,
      conversions: 0,
      topPages: [],
      topReferrers: [],
      deviceTypes: {},
      browserTypes: {},
      countries: {},
    };
  }

  private initializeRealTimeData(): RealTimeMetrics {
    return {
      activeUsers: 0,
      currentPage: window.location.pathname,
      recentEvents: [],
      systemLoad: {
        cpu: 0,
        memory: 0,
        responseTime: 0,
      },
    };
  }

  private setupDataCollection(): void {
    // Subscribe to telemetry events
    this.setupTelemetrySubscription();
    
    // Set up periodic data processing
    setInterval(() => {
      this.processEventBuffer();
      this.updateMetrics();
      this.notifyDashboard();
    }, 30000); // Process every 30 seconds

    // Track page lifecycle events
    this.trackPageLifecycle();
  }

  private setupTelemetrySubscription(): void {
    // Listen to telemetry service events
    const originalTrackEvent = telemetryService.trackEvent.bind(telemetryService);
    telemetryService.trackEvent = (eventType: string, data: any, options?: any) => {
      originalTrackEvent(eventType, data, options);
      
      // Add to our event buffer for analysis
      this.eventBuffer.push({
        type: eventType,
        data,
        timestamp: Date.now(),
        ...options,
      });

      // Update real-time metrics
      this.updateRealTimeMetrics(eventType, data);
    };
  }

  private trackPageLifecycle(): void {
    // Track page views
    telemetryService.trackPageView();

    // Track session start
    this.startSession();

    // Track page unload
    window.addEventListener('beforeunload', () => {
      this.endSession();
      this.saveMetrics();
    });

    // Track visibility changes for engagement
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pauseSession();
      } else {
        this.resumeSession();
      }
    });
  }

  private startSession(): void {
    const sessionId = telemetryService.getSessionInfo().sessionId;
    
    if (!this.userJourneys.has(sessionId)) {
      this.userJourneys.set(sessionId, {
        steps: [],
        totalDuration: 0,
      });
      
      this.metrics.sessions++;
    }
  }

  private endSession(): void {
    const sessionId = telemetryService.getSessionInfo().sessionId;
    const journey = this.userJourneys.get(sessionId);
    
    if (journey) {
      journey.totalDuration = Date.now() - (journey.steps[0]?.timestamp || Date.now());
      this.calculateAverageSessionDuration();
    }
  }

  private pauseSession(): void {
    // Implementation for session pause
  }

  private resumeSession(): void {
    // Implementation for session resume
  }

  private updateRealTimeMetrics(eventType: string, data: any): void {
    this.realTimeData.recentEvents.unshift({
      type: eventType,
      timestamp: Date.now(),
      userId: data.userId,
    });

    // Keep only recent events (last 100)
    if (this.realTimeData.recentEvents.length > 100) {
      this.realTimeData.recentEvents = this.realTimeData.recentEvents.slice(0, 100);
    }

    // Update active users count based on recent activity
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    this.realTimeData.activeUsers = new Set(
      this.realTimeData.recentEvents
        .filter(event => event.timestamp > fiveMinutesAgo)
        .map(event => event.userId || 'anonymous')
    ).size;
  }

  private processEventBuffer(): void {
    const events = [...this.eventBuffer];
    this.eventBuffer = [];

    events.forEach(event => {
      this.processEvent(event);
    });
  }

  private processEvent(event: any): void {
    switch (event.type) {
      case 'page_view':
        this.processPageView(event);
        break;
      case 'user_action':
        this.processUserAction(event);
        break;
      case 'feature_usage':
        this.processFeatureUsage(event);
        break;
      case 'conversion':
        this.processConversion(event);
        break;
      case 'performance_measure':
        this.processPerformanceMetric(event);
        break;
    }
  }

  private processPageView(event: any): void {
    this.metrics.pageViews++;
    
    // Update top pages
    const page = event.data.page || window.location.pathname;
    const existingPage = this.metrics.topPages.find(p => p.page === page);
    if (existingPage) {
      existingPage.views++;
    } else {
      this.metrics.topPages.push({ page, views: 1 });
    }

    // Update top referrers
    const referrer = event.metadata?.referrer || 'direct';
    const existingReferrer = this.metrics.topReferrers.find(r => r.referrer === referrer);
    if (existingReferrer) {
      existingReferrer.visits++;
    } else {
      this.metrics.topReferrers.push({ referrer, visits: 1 });
    }

    // Update device types
    const userAgent = event.metadata?.userAgent || navigator.userAgent;
    const deviceType = this.detectDeviceType(userAgent);
    this.metrics.deviceTypes[deviceType] = (this.metrics.deviceTypes[deviceType] || 0) + 1;

    // Update browser types
    const browserType = this.detectBrowserType(userAgent);
    this.metrics.browserTypes[browserType] = (this.metrics.browserTypes[browserType] || 0) + 1;
  }

  private processUserAction(event: any): void {
    // Track user journey steps
    const sessionId = telemetryService.getSessionInfo().sessionId;
    const journey = this.userJourneys.get(sessionId);
    
    if (journey) {
      journey.steps.push({
        step: `${event.type}_${event.data.action || 'unknown'}`,
        timestamp: event.timestamp,
        page: event.data.page || window.location.pathname,
      });
    }
  }

  private processFeatureUsage(event: any): void {
    // Update feature usage analytics
    // This could be expanded to track feature adoption rates, etc.
  }

  private processConversion(event: any): void {
    this.metrics.conversions++;
    
    // Track conversion source
    const sessionId = telemetryService.getSessionInfo().sessionId;
    const journey = this.userJourneys.get(sessionId);
    if (journey) {
      journey.conversionRate = 1; // Simplified - would need to calculate properly
    }
  }

  private processPerformanceMetric(event: any): void {
    // Store performance metrics for analysis
    // Could be used for performance insights and optimization recommendations
  }

  private updateMetrics(): void {
    this.saveMetrics();
    this.calculateDerivedMetrics();
  }

  private calculateDerivedMetrics(): void {
    // Calculate bounce rate (sessions with only one page view)
    const singlePageSessions = Array.from(this.userJourneys.values())
      .filter(journey => journey.steps.length === 1).length;
    
    this.metrics.bounceRate = this.metrics.sessions > 0 
      ? (singlePageSessions / this.metrics.sessions) * 100 
      : 0;
  }

  private calculateAverageSessionDuration(): void {
    const durations = Array.from(this.userJourneys.values())
      .filter(journey => journey.totalDuration > 0)
      .map(journey => journey.totalDuration);
    
    if (durations.length > 0) {
      this.metrics.averageSessionDuration = durations.reduce((sum, duration) => sum + duration, 0) / durations.length;
    }
  }

  private detectDeviceType(userAgent: string): string {
    if (/mobile/i.test(userAgent)) return 'mobile';
    if (/tablet/i.test(userAgent)) return 'tablet';
    return 'desktop';
  }

  private detectBrowserType(userAgent: string): string {
    if (/chrome/i.test(userAgent) && !/edg/i.test(userAgent)) return 'chrome';
    if (/firefox/i.test(userAgent)) return 'firefox';
    if (/safari/i.test(userAgent) && !/chrome/i.test(userAgent)) return 'safari';
    if (/edg/i.test(userAgent)) return 'edge';
    if (/opera/i.test(userAgent)) return 'opera';
    return 'other';
  }

  private saveMetrics(): void {
    localStorage.setItem('analytics_metrics', JSON.stringify(this.metrics));
  }

  private startRealTimeUpdates(): void {
    // Update system load metrics
    setInterval(() => {
      this.updateSystemLoadMetrics();
    }, 5000);

    // Clean up old real-time data
    setInterval(() => {
      this.cleanupOldData();
    }, 60000);
  }

  private updateSystemLoadMetrics(): void {
    // Simulate system load metrics (in real implementation, these would come from actual monitoring)
    this.realTimeData.systemLoad = {
      cpu: Math.random() * 100, // Simulated
      memory: (performance as any).memory ? 
        ((performance as any).memory.usedJSHeapSize / (performance as any).memory.totalJSHeapSize) * 100 : 
        Math.random() * 100,
      responseTime: Math.random() * 1000, // Simulated
    };
  }

  private cleanupOldData(): void {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    this.realTimeData.recentEvents = this.realTimeData.recentEvents.filter(
      event => event.timestamp > oneHourAgo
    );
  }

  private notifyDashboard(): void {
    const currentMetrics = this.getCurrentMetrics();
    this.dashboardCallbacks.forEach(callback => {
      try {
        callback(currentMetrics);
      } catch (error) {
        console.warn('Dashboard callback failed:', error);
      }
    });
  }

  /**
   * Get current analytics metrics
   */
  public getCurrentMetrics(): AnalyticsMetrics {
    return { ...this.metrics };
  }

  /**
   * Get real-time metrics
   */
  public getRealTimeMetrics(): RealTimeMetrics {
    return { ...this.realTimeData };
  }

  /**
   * Get user journey for a session
   */
  public getUserJourney(sessionId: string): UserJourney | null {
    return this.userJourneys.get(sessionId) || null;
  }

  /**
   * Get all user journeys
   */
  public getAllUserJourneys(): Map<string, UserJourney> {
    return new Map(this.userJourneys);
  }

  /**
   * Create a conversion funnel
   */
  public createConversionFunnel(name: string, steps: string[]): void {
    const funnel: ConversionFunnel = {
      name,
      steps: steps.map((stepName, index) => ({
        name: stepName,
        users: 0,
        conversionRate: 0,
        dropoffRate: 0,
      })),
      overallConversion: 0,
    };

    this.conversionFunnels.set(name, funnel);
  }

  /**
   * Track funnel step completion
   */
  public trackFunnelStep(funnelName: string, stepIndex: number, userId: string): void {
    const funnel = this.conversionFunnels.get(funnelName);
    if (funnel && funnel.steps[stepIndex]) {
      funnel.steps[stepIndex].users++;
      this.calculateFunnelMetrics(funnel);
    }
  }

  /**
   * Calculate funnel metrics
   */
  private calculateFunnelMetrics(funnel: ConversionFunnel): void {
    const totalUsers = funnel.steps[0]?.users || 0;
    
    funnel.steps.forEach((step, index) => {
      if (totalUsers > 0) {
        step.conversionRate = (step.users / totalUsers) * 100;
      }
      
      if (index > 0 && funnel.steps[index - 1].users > 0) {
        const dropoffs = funnel.steps[index - 1].users - step.users;
        step.dropoffRate = (dropoffs / funnel.steps[index - 1].users) * 100;
      }
    });

    if (totalUsers > 0) {
      funnel.overallConversion = (funnel.steps[funnel.steps.length - 1]?.users / totalUsers) * 100;
    }
  }

  /**
   * Get conversion funnel data
   */
  public getConversionFunnel(funnelName: string): ConversionFunnel | null {
    return this.conversionFunnels.get(funnelName) || null;
  }

  /**
   * Perform cohort analysis
   */
  public performCohortAnalysis(cohortDate: string, period: 'daily' | 'weekly' | 'monthly'): void {
    const cohort = Array.from(this.userJourneys.entries())
      .filter(([_, journey]) => {
        const firstStep = journey.steps[0];
        return firstStep && this.getDateString(firstStep.timestamp) === cohortDate;
      });

    const cohortAnalysis: CohortAnalysis = {
      cohort: cohortDate,
      period,
      users: cohort.length,
      retention: this.calculateRetentionRate(cohort),
    };

    this.cohortData.set(cohortDate, cohortAnalysis);
  }

  /**
   * Calculate retention rate for a cohort
   */
  private calculateRetentionRate(cohort: Array<[string, UserJourney]>): number {
    if (cohort.length === 0) return 0;

    const activeUsers = cohort.filter(([_, journey]) => 
      journey.steps.length > 1 // More than just the first page view
    ).length;

    return (activeUsers / cohort.length) * 100;
  }

  private getDateString(timestamp: number): string {
    return new Date(timestamp).toISOString().split('T')[0];
  }

  /**
   * Get analytics insights and recommendations
   */
  public getInsights(): Array<{
    type: 'info' | 'warning' | 'success';
    title: string;
    description: string;
    impact: 'low' | 'medium' | 'high';
  }> {
    const insights = [];

    // Performance insights
    const coreWebVitals = performanceMonitor.getCoreWebVitals();
    if (coreWebVitals.LCP && coreWebVitals.LCP > 2500) {
      insights.push({
        type: 'warning',
        title: 'Slow Loading Times',
        description: `Largest Contentful Paint is ${Math.round(coreWebVitals.LCP)}ms. Consider optimizing images and reducing server response times.`,
        impact: 'high',
      });
    }

    // Conversion insights
    if (this.metrics.conversions === 0 && this.metrics.pageViews > 100) {
      insights.push({
        type: 'warning',
        title: 'No Conversions Detected',
        description: 'Consider reviewing your conversion funnel and calls-to-action.',
        impact: 'high',
      });
    }

    // Engagement insights
    if (this.metrics.bounceRate > 70) {
      insights.push({
        type: 'warning',
        title: 'High Bounce Rate',
        description: `${Math.round(this.metrics.bounceRate)}% of visitors leave after viewing only one page. Consider improving page content and navigation.`,
        impact: 'medium',
      });
    }

    // User journey insights
    const avgSteps = Array.from(this.userJourneys.values())
      .reduce((sum, journey) => sum + journey.steps.length, 0) / this.userJourneys.size;

    if (avgSteps < 3) {
      insights.push({
        type: 'info',
        title: 'Short User Journeys',
        description: 'Users typically take only a few steps. Consider guiding them to explore more features.',
        impact: 'low',
      });
    }

    return insights;
  }

  /**
   * Subscribe to dashboard updates
   */
  public subscribeToDashboard(callback: (metrics: any) => void): () => void {
    this.dashboardCallbacks.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.dashboardCallbacks.indexOf(callback);
      if (index > -1) {
        this.dashboardCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Export analytics data
   */
  public exportData(format: 'json' | 'csv'): string {
    const data = {
      metrics: this.metrics,
      realTime: this.realTimeData,
      userJourneys: Object.fromEntries(this.userJourneys),
      cohorts: Object.fromEntries(this.cohortData),
      funnels: Object.fromEntries(this.conversionFunnels),
      exportDate: new Date().toISOString(),
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    } else {
      // Convert to CSV format (simplified)
      return this.convertToCSV(data);
    }
  }

  private convertToCSV(data: any): string {
    // Simplified CSV conversion - would need more sophisticated handling for real data
    const headers = ['metric', 'value'];
    const rows = [
      headers.join(','),
      `pageViews,${data.metrics.pageViews}`,
      `uniqueUsers,${data.metrics.uniqueUsers}`,
      `sessions,${data.metrics.sessions}`,
      `conversions,${data.metrics.conversions}`,
      `bounceRate,${data.metrics.bounceRate}`,
    ];
    
    return rows.join('\n');
  }

  /**
   * Clear all analytics data
   */
  public clearData(): void {
    this.metrics = this.initializeMetrics();
    this.userJourneys.clear();
    this.cohortData.clear();
    this.conversionFunnels.clear();
    this.realTimeData = this.initializeRealTimeData();
    this.eventBuffer = [];
    
    localStorage.removeItem('analytics_metrics');
  }

  /**
   * Clean up resources
   */
  public destroy(): void {
    this.saveMetrics();
    this.dashboardCallbacks = [];
    this.eventBuffer = [];
  }
}

// Create singleton instance
const analyticsService = new AnalyticsService();

export default analyticsService;
