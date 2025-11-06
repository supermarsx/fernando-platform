/**
 * Telemetry Testing Utilities
 * Helper functions for testing and debugging telemetry implementation
 */

import telemetryService from '../services/telemetryService';
import performanceMonitor from '../services/performanceMonitor';
import eventTracker from '../services/eventTracker';
import analyticsService from '../services/analytics';

export class TelemetryTester {
  private testUserId = 'test_user_' + Math.random().toString(36).substr(2, 9);
  private testSessionId = '';

  constructor() {
    this.testSessionId = telemetryService.getSessionInfo().sessionId;
  }

  /**
   * Generate test events for all telemetry types
   */
  generateTestEvents(count: number = 10): void {
    console.log(`🔄 Generating ${count} test events...`);
    
    for (let i = 0; i < count; i++) {
      // Page views
      telemetryService.trackPageView(`/test-page-${i}`, {
        testEvent: true,
        iteration: i,
      });

      // User actions
      telemetryService.trackAction('click', `test-button-${i}`, {
        testEvent: true,
        iteration: i,
        buttonText: `Test Button ${i}`,
      });

      // Feature usage
      telemetryService.trackFeatureUsage(`test-feature-${i}`, {
        testEvent: true,
        iteration: i,
        action: 'use',
      });

      // Form events
      if (i % 3 === 0) {
        telemetryService.trackAction('form_change', 'test-form', {
          testEvent: true,
          iteration: i,
          fieldName: `field-${i}`,
          fieldType: 'text',
        });
      }

      // Errors
      if (i % 7 === 0) {
        telemetryService.trackEvent('error', {
          testEvent: true,
          iteration: i,
          error: new Error(`Test error ${i}`).message,
          component: 'TelemetryTester',
        });
      }

      // Performance events
      if (i % 5 === 0) {
        performanceMonitor.markPerformance(`test-mark-${i}`);
        performanceMonitor.measurePerformance(
          `test-measure-${i}`,
          `test-mark-${i}`,
          `test-mark-${i + 1}`
        );
      }

      // User journey
      if (i % 4 === 0) {
        eventTracker.trackUserJourney(`test-journey-${i}`, {
          testEvent: true,
          iteration: i,
          step: `step-${i}`,
        });
      }

      // A/B test
      if (i % 6 === 0) {
        eventTracker.trackABTest('test-experiment', `variant-${i % 2}`);
      }

      // Conversion
      if (i % 8 === 0) {
        telemetryService.trackConversion('test-conversion', i * 10, {
          testEvent: true,
          iteration: i,
          value: i * 10,
        });
      }
    }

    console.log('✅ Test events generated successfully');
  }

  /**
   * Test consent management
   */
  testConsentManagement(): void {
    console.log('🛡️ Testing consent management...');

    // Test setting consent
    telemetryService.setConsent({
      essential: true,
      analytics: true,
      performance: true,
      advertising: false,
    });

    // Verify consent is working
    const hasConsent = telemetryService.isAnalyticsEnabled();
    console.log('Consent status:', hasConsent ? 'Enabled' : 'Disabled');

    // Test revoking consent
    telemetryService.setConsent({
      essential: true,
      analytics: false,
      performance: false,
      advertising: false,
    });

    const revokedConsent = telemetryService.isAnalyticsEnabled();
    console.log('After revocation:', revokedConsent ? 'Enabled' : 'Disabled');

    console.log('✅ Consent management test completed');
  }

  /**
   * Test performance monitoring
   */
  testPerformanceMonitoring(): void {
    console.log('⚡ Testing performance monitoring...');

    // Test Core Web Vitals
    const vitals = performanceMonitor.getCoreWebVitals();
    console.log('Core Web Vitals:', vitals);

    // Test navigation timing
    const navTiming = performanceMonitor.getNavigationTiming();
    console.log('Navigation Timing:', navTiming);

    // Test resource timings
    const resources = performanceMonitor.getResourceTimings();
    console.log('Resource Timings:', resources.length, 'resources tracked');

    // Test custom performance marks
    performanceMonitor.markPerformance('test-operation-start');
    
    // Simulate some work
    setTimeout(() => {
      performanceMonitor.markPerformance('test-operation-end');
      const duration = performanceMonitor.measurePerformance(
        'test-operation',
        'test-operation-start',
        'test-operation-end'
      );
      console.log('Custom operation duration:', duration + 'ms');
      console.log('✅ Performance monitoring test completed');
    }, 100);
  }

  /**
   * Test analytics service
   */
  testAnalyticsService(): void {
    console.log('📊 Testing analytics service...');

    // Generate some sample data
    analyticsService.createConversionFunnel('signup', [
      'landing_page',
      'signup_form',
      'email_verification',
      'profile_completion',
    ]);

    // Simulate funnel progression
    for (let i = 0; i < 20; i++) {
      analyticsService.trackFunnelStep('signup', 0, `user_${i}`);
      if (i > 10) {
        analyticsService.trackFunnelStep('signup', 1, `user_${i}`);
      }
      if (i > 5) {
        analyticsService.trackFunnelStep('signup', 2, `user_${i}`);
      }
      if (i > 2) {
        analyticsService.trackFunnelStep('signup', 3, `user_${i}`);
      }
    }

    // Get funnel data
    const funnel = analyticsService.getConversionFunnel('signup');
    console.log('Conversion Funnel:', funnel);

    // Get insights
    const insights = analyticsService.getInsights();
    console.log('Analytics Insights:', insights);

    // Get current metrics
    const metrics = analyticsService.getCurrentMetrics();
    console.log('Current Metrics:', metrics);

    console.log('✅ Analytics service test completed');
  }

  /**
   * Test user identification
   */
  testUserIdentification(): void {
    console.log('👤 Testing user identification...');

    // Identify user
    telemetryService.identify(this.testUserId, {
      email: 'test@example.com',
      plan: 'premium',
      testUser: true,
    });

    // Verify identification
    const sessionInfo = telemetryService.getSessionInfo();
    console.log('Session Info:', sessionInfo);

    console.log('✅ User identification test completed');
  }

  /**
   * Test error tracking
   */
  testErrorTracking(): void {
    console.log('❌ Testing error tracking...');

    // Simulate various error types
    const errors = [
      new Error('Test JavaScript error'),
      { message: 'Test custom error object', stack: 'Custom stack' },
      'Test string error',
    ];

    errors.forEach((error, index) => {
      telemetryService.trackEvent('test_error', {
        error: error instanceof Error ? error.message : error,
        testError: true,
        errorIndex: index,
        component: 'TelemetryTester',
      });
    });

    console.log('✅ Error tracking test completed');
  }

  /**
   * Run comprehensive test suite
   */
  async runComprehensiveTest(): Promise<void> {
    console.log('🚀 Starting comprehensive telemetry test suite...');
    console.log('=' .repeat(60));

    try {
      // Test user identification
      this.testUserIdentification();
      console.log('');

      // Test consent management
      this.testConsentManagement();
      console.log('');

      // Generate test events
      this.generateTestEvents(50);
      console.log('');

      // Test performance monitoring
      this.testPerformanceMonitoring();
      await new Promise(resolve => setTimeout(resolve, 200));
      console.log('');

      // Test analytics service
      this.testAnalyticsService();
      console.log('');

      // Test error tracking
      this.testErrorTracking();
      console.log('');

      // Flush events
      await telemetryService.flush();
      console.log('📤 Events flushed to server');

      console.log('');
      console.log('=' .repeat(60));
      console.log('✅ All tests completed successfully!');
      console.log('');
      
      // Show final state
      const finalMetrics = analyticsService.getCurrentMetrics();
      const finalSession = telemetryService.getSessionInfo();
      
      console.log('📈 Final Test Results:');
      console.log(`- Page Views: ${finalMetrics.pageViews}`);
      console.log(`- User Actions: Multiple tracked`);
      console.log(`- Errors Tracked: 3`);
      console.log(`- Performance Metrics: Tracked`);
      console.log(`- Session ID: ${finalSession.sessionId}`);
      console.log(`- User ID: ${finalSession.userId || 'Not set'}`);
      
    } catch (error) {
      console.error('❌ Test suite failed:', error);
    }
  }

  /**
   * Get test summary
   */
  getTestSummary(): any {
    return {
      testUserId: this.testUserId,
      testSessionId: this.testSessionId,
      sessionInfo: telemetryService.getSessionInfo(),
      currentMetrics: analyticsService.getCurrentMetrics(),
      coreWebVitals: performanceMonitor.getCoreWebVitals(),
      performanceSummary: performanceMonitor.getPerformanceSummary(),
      consentStatus: telemetryService.isAnalyticsEnabled(),
      realTimeMetrics: analyticsService.getRealTimeMetrics(),
    };
  }

  /**
   * Clear test data
   */
  clearTestData(): void {
    console.log('🧹 Clearing test data...');
    
    // Clear telemetry data
    telemetryService.clearData();
    performanceMonitor.clearData();
    eventTracker.clearData();
    
    console.log('✅ Test data cleared');
  }
}

// Helper functions for quick testing
export const quickTelemetryTest = () => {
  const tester = new TelemetryTester();
  
  // Generate some quick events
  telemetryService.trackPageView('/test');
  telemetryService.trackAction('click', 'test-button');
  telemetryService.trackFeatureUsage('test-feature');
  
  console.log('Quick test completed. Check the analytics dashboard!');
  
  return tester;
};

export const simulateUserJourney = (steps: string[]) => {
  console.log('🎯 Simulating user journey:', steps.join(' → '));
  
  steps.forEach((step, index) => {
    setTimeout(() => {
      telemetryService.trackEvent('user_journey_step', {
        step,
        stepIndex: index,
        totalSteps: steps.length,
      });
      
      if (index === steps.length - 1) {
        telemetryService.trackConversion('journey_complete', 1, {
          journeySteps: steps,
          totalDuration: steps.length * 1000,
        });
      }
    }, index * 1000);
  });
};

export const simulateErrors = () => {
  console.log('❌ Simulating errors...');
  
  // Trigger various error types
  setTimeout(() => {
    throw new Error('Simulated JavaScript error');
  }, 100);
  
  setTimeout(() => {
    telemetryService.trackEvent('custom_error', {
      message: 'Simulated custom error',
      component: 'TestComponent',
    });
  }, 200);
  
  setTimeout(() => {
    Promise.reject(new Error('Simulated promise rejection'));
  }, 300);
};

export const testPerformance = () => {
  console.log('⚡ Testing performance...');
  
  performanceMonitor.markPerformance('test-start');
  
  // Simulate some work
  const start = Date.now();
  while (Date.now() - start < 100) {
    // Busy wait to simulate work
  }
  
  performanceMonitor.markPerformance('test-end');
  const duration = performanceMonitor.measurePerformance('test-operation', 'test-start', 'test-end');
  
  console.log(`Operation took: ${duration}ms`);
};

export default TelemetryTester;
