/**
 * Telemetry API Service
 * Handles communication with the telemetry backend
 */

import apiClient from '../lib/api';

export interface TelemetryEventData {
  events: Array<{
    id: string;
    timestamp: number;
    eventType: string;
    userId?: string;
    sessionId: string;
    page?: string;
    data: Record<string, any>;
    metadata?: Record<string, any>;
  }>;
  sessionId: string;
  userId?: string;
  timestamp: number;
}

export interface TelemetryBatchResponse {
  success: boolean;
  batchId: string;
  processed: number;
  errors?: string[];
}

class TelemetryAPI {
  private batchQueue: TelemetryEventData[] = [];
  private isProcessing = false;
  private flushInterval: NodeJS.Timeout;
  private readonly maxBatchSize = 50;
  private readonly flushTimeout = 10000; // 10 seconds

  constructor() {
    // Set up periodic batch processing
    this.flushInterval = setInterval(() => {
      this.flushBatch();
    }, this.flushTimeout);
  }

  /**
   * Send telemetry events to the server
   */
  async sendEvents(eventData: TelemetryEventData): Promise<TelemetryBatchResponse> {
    try {
      const response = await apiClient.post('/api/telemetry/events', eventData);
      return response.data;
    } catch (error) {
      console.error('Failed to send telemetry events:', error);
      
      // Add to batch queue for retry
      this.batchQueue.push(eventData);
      
      return {
        success: false,
        batchId: '',
        processed: 0,
        errors: [error instanceof Error ? error.message : 'Unknown error'],
      };
    }
  }

  /**
   * Send a single event immediately
   */
  async sendEvent(event: TelemetryEventData['events'][0]): Promise<TelemetryBatchResponse> {
    return this.sendEvents({
      events: [event],
      sessionId: event.sessionId,
      userId: event.userId,
      timestamp: Date.now(),
    });
  }

  /**
   * Flush the current batch queue
   */
  private async flushBatch(): Promise<void> {
    if (this.isProcessing || this.batchQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    try {
      const batch = this.batchQueue.splice(0, this.maxBatchSize);
      const batchData: TelemetryEventData = {
        events: batch.flatMap(b => b.events),
        sessionId: batch[0]?.sessionId || 'unknown',
        userId: batch[0]?.userId,
        timestamp: Date.now(),
      };

      await this.sendEvents(batchData);
    } catch (error) {
      console.error('Failed to flush telemetry batch:', error);
      // Re-add failed events to queue for next retry
      this.batchQueue.unshift(...this.batchQueue.splice(0, this.maxBatchSize));
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Get analytics data from the server
   */
  async getAnalyticsData(params?: {
    startDate?: string;
    endDate?: string;
    page?: string;
    eventType?: string;
  }): Promise<any> {
    try {
      const response = await apiClient.get('/api/telemetry/analytics', { params });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
      throw error;
    }
  }

  /**
   * Get real-time metrics
   */
  async getRealTimeMetrics(): Promise<any> {
    try {
      const response = await apiClient.get('/api/telemetry/realtime');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch real-time metrics:', error);
      throw error;
    }
  }

  /**
   * Get user journey data
   */
  async getUserJourney(sessionId: string): Promise<any> {
    try {
      const response = await apiClient.get(`/api/telemetry/journey/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user journey:', error);
      throw error;
    }
  }

  /**
   * Get conversion funnel data
   */
  async getConversionFunnel(funnelName: string): Promise<any> {
    try {
      const response = await apiClient.get(`/api/telemetry/funnel/${funnelName}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch conversion funnel:', error);
      throw error;
    }
  }

  /**
   * Report an error to the server
   */
  async reportError(errorData: {
    errorId: string;
    error: {
      message: string;
      stack?: string;
      name?: string;
    };
    context: Record<string, any>;
    userId?: string;
  }): Promise<void> {
    try {
      await apiClient.post('/api/telemetry/errors', errorData);
    } catch (error) {
      console.error('Failed to report error:', error);
      // Don't throw - error reporting shouldn't break the app
    }
  }

  /**
   * Track user consent preferences
   */
  async trackConsent(consentData: {
    userId?: string;
    preferences: {
      essential: boolean;
      analytics: boolean;
      performance: boolean;
      advertising: boolean;
    };
    timestamp: number;
    version: string;
  }): Promise<void> {
    try {
      await apiClient.post('/api/telemetry/consent', consentData);
    } catch (error) {
      console.error('Failed to track consent:', error);
    }
  }

  /**
   * Get A/B test results
   */
  async getABTestResults(testName: string): Promise<any> {
    try {
      const response = await apiClient.get(`/api/telemetry/abtest/${testName}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch A/B test results:', error);
      throw error;
    }
  }

  /**
   * Export telemetry data
   */
  async exportData(params: {
    startDate: string;
    endDate: string;
    format: 'json' | 'csv';
    includeEvents?: boolean;
    includePerformance?: boolean;
    includeErrors?: boolean;
  }): Promise<Blob> {
    try {
      const response = await apiClient.get('/api/telemetry/export', {
        params,
        responseType: 'blob',
      });
      
      return response.data;
    } catch (error) {
      console.error('Failed to export data:', error);
      throw error;
    }
  }

  /**
   * Get performance insights
   */
  async getPerformanceInsights(): Promise<any> {
    try {
      const response = await apiClient.get('/api/telemetry/performance/insights');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch performance insights:', error);
      throw error;
    }
  }

  /**
   * Clear telemetry data for a user (GDPR compliance)
   */
  async clearUserData(userId: string): Promise<void> {
    try {
      await apiClient.delete(`/api/telemetry/user/${userId}/data`);
    } catch (error) {
      console.error('Failed to clear user data:', error);
      throw error;
    }
  }

  /**
   * Get user data (for export)
   */
  async getUserData(userId: string): Promise<any> {
    try {
      const response = await apiClient.get(`/api/telemetry/user/${userId}/data`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      throw error;
    }
  }

  /**
   * Set up real-time telemetry stream
   */
  setupRealTimeStream(
    onEvent: (event: any) => void,
    onError: (error: Event) => void
  ): WebSocket | null {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('Telemetry WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onEvent(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      ws.onerror = onError;
      
      ws.onclose = () => {
        console.log('Telemetry WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          this.setupRealTimeStream(onEvent, onError);
        }, 5000);
      };
      
      return ws;
    } catch (error) {
      console.error('Failed to setup telemetry WebSocket:', error);
      return null;
    }
  }

  /**
   * Get telemetry service status
   */
  async getServiceStatus(): Promise<any> {
    try {
      const response = await apiClient.get('/api/telemetry/status');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch service status:', error);
      return {
        status: 'error',
        message: 'Service unavailable',
      };
    }
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }
    
    // Flush any remaining events
    this.flushBatch();
  }
}

// Create singleton instance
const telemetryAPI = new TelemetryAPI();

export default telemetryAPI;
