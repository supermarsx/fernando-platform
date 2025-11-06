/**
 * Frontend Performance Monitoring Service
 * Tracks Core Web Vitals, custom performance metrics, and resource timing
 */

import telemetryService from './telemetryService';

export interface PerformanceMetric {
  name: string;
  value: number;
  rating?: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
  page?: string;
  metadata?: Record<string, any>;
}

export interface CoreWebVitals {
  LCP?: number; // Largest Contentful Paint
  FID?: number; // First Input Delay  
  CLS?: number; // Cumulative Layout Shift
  FCP?: number; // First Contentful Paint
  TTFB?: number; // Time to First Byte
  TTI?: number; // Time to Interactive
}

export interface NavigationTiming {
  domContentLoaded: number;
  loadComplete: number;
  firstByte: number;
  domInteractive: number;
  pageLoad: number;
}

export interface ResourceTiming {
  name: string;
  duration: number;
  size: number;
  type: string;
  url: string;
  startTime: number;
}

class PerformanceMonitor {
  private coreWebVitals: CoreWebVitals = {};
  private navigationTiming: NavigationTiming | null = null;
  private resourceTimings: ResourceTiming[] = [];
  private observer?: PerformanceObserver;
  private isTrackingEnabled: boolean = true;

  constructor() {
    this.initializePerformanceMonitoring();
  }

  private initializePerformanceMonitoring(): void {
    if (!('performance' in window)) {
      console.warn('Performance API not supported');
      return;
    }

    // Set up Core Web Vitals tracking
    this.trackCoreWebVitals();

    // Set up performance observer for long tasks
    this.observeLongTasks();

    // Set up resource timing
    this.trackResourceTiming();

    // Track navigation timing when page loads
    if (document.readyState === 'complete') {
      this.captureNavigationTiming();
    } else {
      window.addEventListener('load', () => this.captureNavigationTiming());
    }
  }

  /**
   * Track Core Web Vitals
   */
  private trackCoreWebVitals(): void {
    // Track Largest Contentful Paint (LCP)
    this.observePerformanceEntry('largest-contentful-paint', (entry) => {
      const lcp = entry.startTime;
      this.coreWebVitals.LCP = lcp;
      
      telemetryService.trackEvent('web_vitals', {
        metric: 'LCP',
        value: lcp,
        rating: this.getLCPRating(lcp),
        element: entry.element?.tagName,
      });

      this.reportPerformanceMetric('largest_contentful_paint', lcp, this.getLCPRating(lcp));
    });

    // Track First Input Delay (FID)
    this.observePerformanceEntry('first-input', (entry) => {
      const fid = entry.processingStart - entry.startTime;
      this.coreWebVitals.FID = fid;
      
      telemetryService.trackEvent('web_vitals', {
        metric: 'FID',
        value: fid,
        rating: this.getFIDRating(fid),
        eventType: entry.name,
      });

      this.reportPerformanceMetric('first_input_delay', fid, this.getFIDRating(fid));
    });

    // Track Cumulative Layout Shift (CLS)
    this.observeLayoutShift();

    // Track First Contentful Paint (FCP)
    this.observePerformanceEntry('paint', (entry) => {
      if (entry.name === 'first-contentful-paint') {
        const fcp = entry.startTime;
        this.coreWebVitals.FCP = fcp;
        
        telemetryService.trackEvent('web_vitals', {
          metric: 'FCP',
          value: fcp,
          rating: this.getFCPRating(fcp),
        });

        this.reportPerformanceMetric('first_contentful_paint', fcp, this.getFCPRating(fcp));
      }
    });
  }

  /**
   * Observe performance entries of a specific type
   */
  private observePerformanceEntry(type: string, callback: (entry: any) => void): void {
    try {
      if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            callback(entry);
          }
        });
        observer.observe({ type, buffered: true });
      }
    } catch (error) {
      console.warn(`Failed to observe ${type} performance entries:`, error);
    }
  }

  /**
   * Observe layout shifts for CLS calculation
   */
  private observeLayoutShift(): void {
    let clsScore = 0;
    let lastEntryTime = 0;

    this.observePerformanceEntry('layout-shift', (entry) => {
      if (!entry.hadRecentInput) {
        clsScore += entry.value;
        this.coreWebVitals.CLS = clsScore;
        
        telemetryService.trackEvent('web_vitals', {
          metric: 'CLS',
          value: clsScore,
          rating: this.getCLSRating(clsScore),
          sources: entry.sources?.length || 0,
        });

        // Only report if it's a significant change or after some time
        if (entry.startTime - lastEntryTime > 1000 || clsScore > 0.1) {
          this.reportPerformanceMetric('cumulative_layout_shift', clsScore, this.getCLSRating(clsScore));
          lastEntryTime = entry.startTime;
        }
      }
    });
  }

  /**
   * Observe long tasks
   */
  private observeLongTasks(): void {
    this.observePerformanceEntry('longtask', (entry) => {
      const duration = entry.duration;
      
      telemetryService.trackEvent('performance', {
        type: 'long_task',
        duration,
        startTime: entry.startTime,
        attribution: entry.attribution?.map(attr => attr.name) || [],
      });

      // Report if long task is significant (> 100ms)
      if (duration > 100) {
        this.reportPerformanceMetric('long_task', duration, 'needs-improvement');
      }
    });
  }

  /**
   * Track resource timing
   */
  private trackResourceTiming(): void {
    const captureResourceTiming = () => {
      if (!('getEntriesByType' in performance)) return;

      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      resources.forEach((resource, index) => {
        // Avoid duplicates by checking if we already captured this resource
        if (this.resourceTimings.some(rt => rt.name === resource.name)) {
          return;
        }

        const timing: ResourceTiming = {
          name: resource.name,
          duration: resource.duration,
          size: resource.transferSize || 0,
          type: this.getResourceType(resource.name),
          url: resource.name,
          startTime: resource.startTime,
        };

        this.resourceTimings.push(timing);

        // Track slow resources (> 1 second)
        if (resource.duration > 1000) {
          telemetryService.trackEvent('performance', {
            type: 'slow_resource',
            name: resource.name,
            duration: resource.duration,
            size: resource.transferSize,
            type: timing.type,
          });
        }
      });
    };

    // Capture immediately if page is loaded, otherwise wait for load
    if (document.readyState === 'complete') {
      captureResourceTiming();
    } else {
      window.addEventListener('load', captureResourceTiming);
    }

    // Set up observer for new resources
    if ('PerformanceObserver' in window) {
      this.observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'resource') {
            const resource = entry as PerformanceResourceTiming;
            const timing: ResourceTiming = {
              name: resource.name,
              duration: resource.duration,
              size: resource.transferSize || 0,
              type: this.getResourceType(resource.name),
              url: resource.name,
              startTime: resource.startTime,
            };

            // Avoid duplicates
            if (!this.resourceTimings.some(rt => rt.name === resource.name)) {
              this.resourceTimings.push(timing);
            }
          }
        }
      });
      this.observer.observe({ entryTypes: ['resource'] });
    }
  }

  /**
   * Capture navigation timing
   */
  private captureNavigationTiming(): void {
    if (!('getEntriesByType' in performance)) return;

    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    
    if (navigation) {
      this.navigationTiming = {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstByte: navigation.responseStart - navigation.requestStart,
        domInteractive: navigation.domInteractive - navigation.navigationStart,
        pageLoad: navigation.loadEventEnd - navigation.navigationStart,
      };

      telemetryService.trackEvent('performance', {
        type: 'navigation_timing',
        ...this.navigationTiming,
      });

      // Track Time to First Byte (TTFB)
      this.coreWebVitals.TTFB = this.navigationTiming.firstByte;
      this.reportPerformanceMetric('time_to_first_byte', this.navigationTiming.firstByte, this.getTTFBRating(this.navigationTiming.firstByte));

      // Track Time to Interactive (TTI) - approximate
      const tti = navigation.domInteractive - navigation.navigationStart;
      this.coreWebVitals.TTI = tti;
      this.reportPerformanceMetric('time_to_interactive', tti, this.getTTIRating(tti));
    }
  }

  /**
   * Get rating for LCP metric
   */
  private getLCPRating(lcp: number): 'good' | 'needs-improvement' | 'poor' {
    if (lcp <= 2500) return 'good';
    if (lcp <= 4000) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get rating for FID metric
   */
  private getFIDRating(fid: number): 'good' | 'needs-improvement' | 'poor' {
    if (fid <= 100) return 'good';
    if (fid <= 300) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get rating for CLS metric
   */
  private getCLSRating(cls: number): 'good' | 'needs-improvement' | 'poor' {
    if (cls <= 0.1) return 'good';
    if (cls <= 0.25) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get rating for FCP metric
   */
  private getFCPRating(fcp: number): 'good' | 'needs-improvement' | 'poor' {
    if (fcp <= 1800) return 'good';
    if (fcp <= 3000) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get rating for TTFB metric
   */
  private getTTFBRating(ttfb: number): 'good' | 'needs-improvement' | 'poor' {
    if (ttfb <= 800) return 'good';
    if (ttfb <= 1800) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get rating for TTI metric
   */
  private getTTIRating(ti: number): 'good' | 'needs-improvement' | 'poor' {
    if (tti <= 3800) return 'good';
    if (tti <= 7300) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Get resource type from URL
   */
  private getResourceType(url: string): string {
    if (url.includes('.js')) return 'script';
    if (url.includes('.css')) return 'stylesheet';
    if (url.match(/\.(jpg|jpeg|png|gif|webp|svg)$/)) return 'image';
    if (url.includes('.woff') || url.includes('.ttf')) return 'font';
    if (url.includes('.mp4') || url.includes('.webm')) return 'video';
    if (url.includes('.mp3') || url.includes('.wav')) return 'audio';
    if (url.includes('fetch') || url.includes('xhr')) return 'fetch';
    return 'other';
  }

  /**
   * Report a performance metric
   */
  private reportPerformanceMetric(name: string, value: number, rating?: string): void {
    const metric: PerformanceMetric = {
      name,
      value,
      rating: rating as any,
      timestamp: Date.now(),
      page: window.location.pathname,
    };

    telemetryService.trackEvent('performance_measure', {
      metric: metric.name,
      value: metric.value,
      rating: metric.rating,
      page: metric.page,
    });
  }

  /**
   * Track custom performance marks
   */
  public markPerformance(markName: string, metadata?: Record<string, any>): void {
    try {
      performance.mark(markName);
      telemetryService.trackEvent('performance', {
        type: 'custom_mark',
        markName,
        timestamp: performance.now(),
        metadata,
      });
    } catch (error) {
      console.warn('Failed to create performance mark:', error);
    }
  }

  /**
   * Measure performance between two marks
   */
  public measurePerformance(measureName: string, startMark: string, endMark?: string, metadata?: Record<string, any>): number | null {
    try {
      performance.measure(measureName, startMark, endMark);
      const measure = performance.getEntriesByName(measureName).pop() as PerformanceMeasure;
      
      if (measure) {
        telemetryService.trackEvent('performance', {
          type: 'custom_measure',
          measureName,
          duration: measure.duration,
          startTime: measure.startTime,
          metadata,
        });
        
        return measure.duration;
      }
    } catch (error) {
      console.warn('Failed to create performance measure:', error);
    }
    
    return null;
  }

  /**
   * Get current Core Web Vitals
   */
  public getCoreWebVitals(): CoreWebVitals {
    return { ...this.coreWebVitals };
  }

  /**
   * Get navigation timing
   */
  public getNavigationTiming(): NavigationTiming | null {
    return this.navigationTiming ? { ...this.navigationTiming } : null;
  }

  /**
   * Get resource timings
   */
  public getResourceTimings(): ResourceTiming[] {
    return [...this.resourceTimings];
  }

  /**
   * Get performance summary
   */
  public getPerformanceSummary() {
    return {
      coreWebVitals: this.coreWebVitals,
      navigationTiming: this.navigationTiming,
      resourceCount: this.resourceTimings.length,
      totalResourceSize: this.resourceTimings.reduce((sum, rt) => sum + rt.size, 0),
      slowResourceCount: this.resourceTimings.filter(rt => rt.duration > 1000).length,
    };
  }

  /**
   * Enable/disable performance tracking
   */
  public setTrackingEnabled(enabled: boolean): void {
    this.isTrackingEnabled = enabled;
  }

  /**
   * Clear performance data
   */
  public clearData(): void {
    this.coreWebVitals = {};
    this.navigationTiming = null;
    this.resourceTimings = [];
    
    try {
      performance.clearMarks();
      performance.clearMeasures();
    } catch (error) {
      console.warn('Failed to clear performance data:', error);
    }
  }

  /**
   * Clean up
   */
  public destroy(): void {
    if (this.observer) {
      this.observer.disconnect();
    }
    this.clearData();
  }
}

// Create singleton instance
const performanceMonitor = new PerformanceMonitor();

export default performanceMonitor;
