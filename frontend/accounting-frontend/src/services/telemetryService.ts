/**
 * Core Telemetry Service
 * Handles client-side telemetry collection, storage, and transmission
 */

export interface TelemetryEvent {
  id: string;
  timestamp: number;
  eventType: string;
  userId?: string;
  sessionId: string;
  page?: string;
  data: Record<string, any>;
  metadata?: {
    userAgent: string;
    url: string;
    referrer: string;
    viewport: { width: number; height: number };
    timezone?: string;
    locale?: string;
  };
}

export interface TelemetryConfig {
  apiEndpoint?: string;
  batchSize?: number;
  flushInterval?: number;
  enableConsoleLogging?: boolean;
  enableErrorTracking?: boolean;
  enablePerformanceTracking?: boolean;
  sampleRate?: number; // 0-1, percentage of users to track
  anonymize?: boolean;
  enableConsentMode?: boolean;
}

export interface ConsentPreferences {
  analytics: boolean;
  performance: boolean;
  advertising: boolean;
  essential: boolean; // Always true
  timestamp: number;
  version: string;
}

class TelemetryService {
  private config: TelemetryConfig;
  private eventQueue: TelemetryEvent[] = [];
  private batchSize: number;
  private flushInterval: number;
  private flushTimer: NodeJS.Timeout | null = null;
  private sessionId: string;
  private userId?: string;
  private consentPreferences?: ConsentPreferences;
  private isEnabled: boolean = true;

  constructor(config: TelemetryConfig = {}) {
    this.config = {
      apiEndpoint: config.apiEndpoint || '/api/telemetry',
      batchSize: config.batchSize || 10,
      flushInterval: config.flushInterval || 30000, // 30 seconds
      enableConsoleLogging: config.enableConsoleLogging || false,
      enableErrorTracking: config.enableErrorTracking ?? true,
      enablePerformanceTracking: config.enablePerformanceTracking ?? true,
      sampleRate: config.sampleRate || 1.0,
      anonymize: config.anonymize || false,
      enableConsentMode: config.enableConsentMode || false,
      ...config,
    };

    this.batchSize = this.config.batchSize!;
    this.flushInterval = this.config.flushInterval!;
    this.sessionId = this.generateSessionId();
    this.loadStoredData();
    this.startFlushTimer();
    this.setupEventListeners();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private loadStoredData(): void {
    try {
      const storedSession = localStorage.getItem('telemetry_session_id');
      if (storedSession) {
        this.sessionId = storedSession;
      } else {
        localStorage.setItem('telemetry_session_id', this.sessionId);
      }

      const storedUserId = localStorage.getItem('telemetry_user_id');
      if (storedUserId) {
        this.userId = storedUserId;
      }

      // Load consent preferences if consent mode is enabled
      if (this.config.enableConsentMode) {
        const consent = localStorage.getItem('telemetry_consent');
        if (consent) {
          this.consentPreferences = JSON.parse(consent);
        }
      }
    } catch (error) {
      console.warn('Failed to load stored telemetry data:', error);
    }
  }

  private startFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.flushInterval);
  }

  private setupEventListeners(): void {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.flush();
      }
    });

    // Handle page unload
    window.addEventListener('beforeunload', () => {
      this.flush();
    });

    // Handle errors
    if (this.config.enableErrorTracking) {
      window.addEventListener('error', (event) => {
        this.trackEvent('error', {
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          stack: event.error?.stack,
        });
      });

      window.addEventListener('unhandledrejection', (event) => {
        this.trackEvent('unhandled_promise_rejection', {
          reason: event.reason,
        });
      });
    }
  }

  /**
   * Set user identification for telemetry
   */
  public identify(userId: string, traits?: Record<string, any>): void {
    this.userId = userId;
    localStorage.setItem('telemetry_user_id', userId);
    
    this.trackEvent('user_identified', {
      userId: this.config.anonymize ? this.anonymizeId(userId) : userId,
      traits: traits || {},
    });
  }

  /**
   * Set consent preferences for GDPR compliance
   */
  public setConsent(preferences: Omit<ConsentPreferences, 'timestamp' | 'version'>): void {
    this.consentPreferences = {
      ...preferences,
      timestamp: Date.now(),
      version: '1.0',
    };
    localStorage.setItem('telemetry_consent', JSON.stringify(this.consentPreferences));
    
    this.trackEvent('consent_updated', {
      preferences: preferences,
    });

    // Update enabled state based on consent
    this.updateEnabledState();
  }

  /**
   * Check if analytics is enabled based on consent
   */
  public isAnalyticsEnabled(): boolean {
    if (!this.config.enableConsentMode) {
      return true;
    }
    return this.consentPreferences?.analytics ?? false;
  }

  /**
   * Update the enabled state based on consent preferences
   */
  private updateEnabledState(): void {
    this.isEnabled = this.config.enableConsentMode 
      ? this.consentPreferences?.analytics ?? false 
      : true;
  }

  /**
   * Track an event
   */
  public trackEvent(
    eventType: string,
    data: Record<string, any>,
    options?: {
      page?: string;
      userId?: string;
      anonymize?: boolean;
    }
  ): void {
    if (!this.isEnabled) {
      return;
    }

    // Check sampling
    if (Math.random() > this.config.sampleRate!) {
      return;
    }

    // Check if this type of event is allowed by consent
    if (this.config.enableConsentMode && !this.canTrackEventType(eventType)) {
      return;
    }

    const event: TelemetryEvent = {
      id: this.generateEventId(),
      timestamp: Date.now(),
      eventType,
      userId: options?.userId || this.userId,
      sessionId: this.sessionId,
      page: options?.page || this.getCurrentPage(),
      data: options?.anonymize || this.config.anonymize 
        ? this.anonymizeData(data)
        : data,
      metadata: this.getMetadata(),
    };

    this.eventQueue.push(event);

    if (this.config.enableConsoleLogging) {
      console.log('Telemetry Event:', event);
    }

    // Auto-flush if batch size is reached
    if (this.eventQueue.length >= this.batchSize) {
      this.flush();
    }
  }

  /**
   * Check if a specific event type can be tracked based on consent
   */
  private canTrackEventType(eventType: string): boolean {
    if (!this.consentPreferences) {
      return true; // Default to allowing if no consent given
    }

    switch (eventType) {
      case 'page_view':
      case 'user_identified':
      case 'consent_updated':
        return true; // Essential events always allowed
      case 'performance_measure':
      case 'web_vitals':
        return this.consentPreferences.performance;
      case 'error':
      case 'unhandled_promise_rejection':
        return true; // Error tracking is generally essential
      default:
        return this.consentPreferences.analytics;
    }
  }

  /**
   * Generate a unique event ID
   */
  private generateEventId(): string {
    return `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current page URL/path
   */
  private getCurrentPage(): string {
    return window.location.pathname + window.location.search;
  }

  /**
   * Get metadata for the current session
   */
  private getMetadata() {
    return {
      userAgent: navigator.userAgent,
      url: window.location.href,
      referrer: document.referrer,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      locale: navigator.language,
    };
  }

  /**
   * Anonymize user ID
   */
  private anonymizeId(userId: string): string {
    // Simple hash function for anonymization
    let hash = 0;
    for (let i = 0; i < userId.length; i++) {
      const char = userId.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return `anon_${Math.abs(hash).toString(16)}`;
  }

  /**
   * Anonymize sensitive data
   */
  private anonymizeData(data: Record<string, any>): Record<string, any> {
    const sensitiveKeys = ['email', 'password', 'phone', 'ssn', 'creditCard'];
    const anonymized = { ...data };

    for (const [key, value] of Object.entries(anonymized)) {
      if (sensitiveKeys.includes(key.toLowerCase())) {
        anonymized[key] = '[REDACTED]';
      } else if (typeof value === 'string' && value.includes('@')) {
        // Email addresses
        const parts = value.split('@');
        anonymized[key] = `${parts[0].charAt(0)}***@${parts[1]}`;
      }
    }

    return anonymized;
  }

  /**
   * Flush events to the server
   */
  public async flush(): Promise<void> {
    if (this.eventQueue.length === 0 || !this.isEnabled) {
      return;
    }

    const events = [...this.eventQueue];
    this.eventQueue = [];

    try {
      const response = await fetch(this.config.apiEndpoint!, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          events,
          sessionId: this.sessionId,
          userId: this.userId,
          timestamp: Date.now(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (this.config.enableConsoleLogging) {
        console.log(`Sent ${events.length} telemetry events`);
      }
    } catch (error) {
      console.error('Failed to send telemetry events:', error);
      // Re-queue events on failure (with a limit to prevent memory issues)
      if (this.eventQueue.length < 1000) {
        this.eventQueue.unshift(...events);
      }
    }
  }

  /**
   * Track page view
   */
  public trackPageView(page?: string, properties?: Record<string, any>): void {
    this.trackEvent('page_view', {
      page: page || this.getCurrentPage(),
      ...properties,
    });
  }

  /**
   * Track user action (click, form submission, etc.)
   */
  public trackAction(action: string, target?: string, properties?: Record<string, any>): void {
    this.trackEvent('user_action', {
      action,
      target,
      ...properties,
    });
  }

  /**
   * Track feature usage
   */
  public trackFeatureUsage(feature: string, properties?: Record<string, any>): void {
    this.trackEvent('feature_usage', {
      feature,
      ...properties,
    });
  }

  /**
   * Track conversion events
   */
  public trackConversion(conversion: string, value?: number, properties?: Record<string, any>): void {
    this.trackEvent('conversion', {
      conversion,
      value,
      ...properties,
    });
  }

  /**
   * Get current session info
   */
  public getSessionInfo() {
    return {
      sessionId: this.sessionId,
      userId: this.userId,
      consentPreferences: this.consentPreferences,
      queueLength: this.eventQueue.length,
    };
  }

  /**
   * Reset session
   */
  public resetSession(): void {
    this.sessionId = this.generateSessionId();
    localStorage.setItem('telemetry_session_id', this.sessionId);
    this.flush(); // Send any remaining events first
  }

  /**
   * Clear all data (for privacy compliance)
   */
  public clearData(): void {
    this.eventQueue = [];
    localStorage.removeItem('telemetry_session_id');
    localStorage.removeItem('telemetry_user_id');
    localStorage.removeItem('telemetry_consent');
    this.userId = undefined;
    this.consentPreferences = undefined;
  }

  /**
   * Destroy the telemetry service
   */
  public destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.flush();
  }
}

// Create singleton instance
const telemetryService = new TelemetryService();

export default telemetryService;
