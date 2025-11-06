/**
 * Custom React hooks for telemetry integration
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import telemetryService from '../services/telemetryService';
import performanceMonitor from '../services/performanceMonitor';
import eventTracker from '../services/eventTracker';
import analyticsService from '../services/analytics';

/**
 * Hook for tracking component lifecycle events
 */
export function useComponentTelemetry(componentName: string, props?: Record<string, any>) {
  const mountTime = useRef<number>(Date.now());
  const renderCount = useRef<number>(0);
  const previousProps = useRef<Record<string, any>>(props);

  useEffect(() => {
    renderCount.current++;
    
    // Track component mount
    telemetryService.trackEvent('component_mount', {
      component: componentName,
      renderCount: renderCount.current,
      mountTime: Date.now() - mountTime.current,
      props: sanitizeProps(props),
    });

    // Track prop changes
    if (previousProps.current) {
      const changedProps = Object.keys(props || {}).filter(
        key => previousProps.current[key] !== props[key]
      );

      if (changedProps.length > 0) {
        telemetryService.trackEvent('component_props_changed', {
          component: componentName,
          changedProps: changedProps.reduce((acc, key) => {
            acc[key] = {
              from: previousProps.current[key],
              to: props[key],
            };
            return acc;
          }, {} as Record<string, any>),
        });
      }
    }

    previousProps.current = props;

    // Track component unmount
    return () => {
      const totalLifetime = Date.now() - mountTime.current;
      telemetryService.trackEvent('component_unmount', {
        component: componentName,
        totalLifetime,
        totalRenders: renderCount.current,
      });
    };
  }, [componentName]);

  // Track component errors
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      telemetryService.trackEvent('component_error', {
        component: componentName,
        error: event.error?.message,
        stack: event.error?.stack,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, [componentName]);
}

/**
 * Hook for tracking user interactions
 */
export function useInteractionTracking(elementId: string, context?: string) {
  const interactionCount = useRef<number>(0);

  const trackInteraction = useCallback((action: string, metadata?: Record<string, any>) => {
    interactionCount.current++;
    telemetryService.trackAction(action, elementId, {
      context,
      interactionCount: interactionCount.current,
      timestamp: Date.now(),
      ...metadata,
    });
  }, [elementId, context]);

  const trackClick = useCallback((event?: React.MouseEvent) => {
    trackInteraction('click', {
      coordinates: event ? { x: event.clientX, y: event.clientY } : undefined,
    });
  }, [trackInteraction]);

  const trackFocus = useCallback(() => {
    trackInteraction('focus');
  }, [trackInteraction]);

  const trackBlur = useCallback(() => {
    trackInteraction('blur');
  }, [trackInteraction]);

  return {
    trackInteraction,
    trackClick,
    trackFocus,
    trackBlur,
  };
}

/**
 * Hook for tracking form interactions
 */
export function useFormTelemetry(formId: string, formType?: string) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const startTime = useRef<number>(Date.now());

  const trackFieldChange = useCallback((fieldName: string, fieldType: string, value: string) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }));
    
    telemetryService.trackAction('form_change', formId, {
      fieldName,
      fieldType,
      valueLength: value.length,
      hasValue: value.length > 0,
      timestamp: Date.now(),
    });
  }, [formId]);

  const trackFieldFocus = useCallback((fieldName: string) => {
    telemetryService.trackAction('form_focus', formId, {
      fieldName,
      timestamp: Date.now(),
    });
  }, [formId]);

  const trackValidationError = useCallback((fieldName: string, errorMessage: string) => {
    setValidationErrors(prev => ({ ...prev, [fieldName]: errorMessage }));
    
    telemetryService.trackAction('validation_error', formId, {
      fieldName,
      errorMessage,
      timestamp: Date.now(),
    });
  }, [formId]);

  const trackFormSubmit = useCallback((success: boolean, errorMessage?: string) => {
    const duration = Date.now() - startTime.current;
    
    telemetryService.trackAction('form_submit', formId, {
      formType,
      duration,
      success,
      errorMessage,
      fieldCount: Object.keys(formData).length,
      filledFields: Object.keys(formData).length,
      validationErrors: Object.keys(validationErrors).length,
      timestamp: Date.now(),
    });

    if (success && formType) {
      telemetryService.trackConversion('form_submission', 1, {
        formId,
        formType,
        duration,
      });
    }
  }, [formId, formType, formData, validationErrors]);

  return {
    trackFieldChange,
    trackFieldFocus,
    trackValidationError,
    trackFormSubmit,
    formData,
    validationErrors,
  };
}

/**
 * Hook for feature usage tracking
 */
export function useFeatureTelemetry(featureName: string) {
  const usageCount = useRef<number>(0);
  const startTime = useRef<number>(Date.now());

  const trackFeatureOpen = useCallback(() => {
    startTime.current = Date.now();
    eventTracker.trackFeatureEvent(featureName, 'open');
  }, [featureName]);

  const trackFeatureUse = useCallback((action?: string, metadata?: Record<string, any>) => {
    usageCount.current++;
    telemetryService.trackFeatureUsage(featureName, {
      action: action || 'use',
      usageCount: usageCount.current,
      timestamp: Date.now(),
      ...metadata,
    });
  }, [featureName]);

  const trackFeatureClose = useCallback((completed: boolean = true) => {
    const duration = Date.now() - startTime.current;
    
    eventTracker.trackFeatureEvent(featureName, completed ? 'complete' : 'abandon', {
      duration,
      usageCount: usageCount.current,
    });
  }, [featureName]);

  const trackFeatureError = useCallback((error: string, context?: string) => {
    telemetryService.trackEvent('feature_error', {
      feature: featureName,
      error,
      context,
      timestamp: Date.now(),
    });
  }, [featureName]);

  return {
    trackFeatureOpen,
    trackFeatureUse,
    trackFeatureClose,
    trackFeatureError,
  };
}

/**
 * Hook for performance monitoring
 */
export function usePerformanceTelemetry(operationName: string) {
  const operationCount = useRef<number>(0);
  const startTime = useRef<number>(0);

  const startOperation = useCallback(() => {
    operationCount.current++;
    startTime.current = performance.now();
    performanceMonitor.markPerformance(`${operationName}_start_${operationCount.current}`);
  }, [operationName]);

  const endOperation = useCallback((metadata?: Record<string, any>) => {
    if (startTime.current > 0) {
      const duration = performance.now() - startTime.current;
      const measurement = performanceMonitor.measurePerformance(
        `${operationName}_${operationCount.current}`,
        `${operationName}_start_${operationCount.current}`
      );

      telemetryService.trackEvent('performance_operation', {
        operation: operationName,
        duration,
        measurement,
        count: operationCount.current,
        timestamp: Date.now(),
        ...metadata,
      });

      return duration;
    }
    return 0;
  }, [operationName]);

  const trackApiCall = useCallback(async <T>(
    apiCall: () => Promise<T>,
    endpoint?: string,
    metadata?: Record<string, any>
  ): Promise<T> => {
    startOperation();
    
    try {
      const result = await apiCall();
      const duration = endOperation({
        success: true,
        endpoint,
        ...metadata,
      });

      telemetryService.trackEvent('api_call', {
        endpoint,
        duration,
        success: true,
        timestamp: Date.now(),
      });

      return result;
    } catch (error) {
      const duration = endOperation({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        ...metadata,
      });

      telemetryService.trackEvent('api_call', {
        endpoint,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now(),
      });

      throw error;
    }
  }, [startOperation, endOperation]);

  return {
    startOperation,
    endOperation,
    trackApiCall,
  };
}

/**
 * Hook for user journey tracking
 */
export function useJourneyTracking(journeyName: string) {
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const stepStartTime = useRef<number>(0);
  const steps = useRef<string[]>([]);

  const startJourney = useCallback((initialStep: string) => {
    setCurrentStep(initialStep);
    stepStartTime.current = Date.now();
    steps.current = [initialStep];
    
    eventTracker.trackUserJourney(`${journeyName}_start`, {
      initialStep,
    });
  }, [journeyName]);

  const nextStep = useCallback((stepName: string, metadata?: Record<string, any>) => {
    if (currentStep) {
      const stepDuration = Date.now() - stepStartTime.current;
      
      telemetryService.trackEvent('journey_step', {
        journey: journeyName,
        from: currentStep,
        to: stepName,
        duration: stepDuration,
        stepIndex: steps.current.length,
        timestamp: Date.now(),
        ...metadata,
      });

      setCurrentStep(stepName);
      stepStartTime.current = Date.now();
      steps.current.push(stepName);
    }
  }, [journeyName, currentStep]);

  const completeJourney = useCallback((success: boolean = true, metadata?: Record<string, any>) => {
    if (currentStep) {
      const totalDuration = Date.now() - stepStartTime.current;
      
      telemetryService.trackEvent('journey_complete', {
        journey: journeyName,
        finalStep: currentStep,
        totalDuration,
        stepCount: steps.current.length,
        success,
        steps: steps.current,
        timestamp: Date.now(),
        ...metadata,
      });

      if (success) {
        telemetryService.trackConversion('journey_completion', 1, {
          journey: journeyName,
          stepCount: steps.current.length,
          totalDuration,
        });
      }

      setCurrentStep(null);
    }
  }, [journeyName, currentStep]);

  return {
    currentStep,
    steps: [...steps.current],
    startJourney,
    nextStep,
    completeJourney,
  };
}

/**
 * Hook for A/B testing
 */
export function useABTest(testName: string, variants: string[]) {
  const [assignedVariant, setAssignedVariant] = useState<string | null>(null);

  useEffect(() => {
    // Get or assign variant
    const storageKey = `ab_test_${testName}`;
    let variant = localStorage.getItem(storageKey);

    if (!variant) {
      // Random assignment (could be weighted)
      const randomIndex = Math.floor(Math.random() * variants.length);
      variant = variants[randomIndex];
      localStorage.setItem(storageKey, variant);
    }

    setAssignedVariant(variant);
    eventTracker.trackABTest(testName, variant);
  }, [testName, variants]);

  const trackConversion = useCallback((value?: number) => {
    if (assignedVariant) {
      telemetryService.trackConversion('ab_test_conversion', value || 1, {
        testName,
        variant: assignedVariant,
      });
    }
  }, [testName, assignedVariant]);

  const trackEvent = useCallback((eventName: string, metadata?: Record<string, any>) => {
    if (assignedVariant) {
      telemetryService.trackEvent(`ab_test_${eventName}`, {
        testName,
        variant: assignedVariant,
        timestamp: Date.now(),
        ...metadata,
      });
    }
  }, [testName, assignedVariant]);

  return {
    assignedVariant,
    trackConversion,
    trackEvent,
  };
}

/**
 * Hook for consent management
 */
export function useConsentManagement() {
  const [consent, setConsent] = useState(telemetryService.isAnalyticsEnabled());
  const [isLoading, setIsLoading] = useState(false);

  const updateConsent = useCallback(async (preferences: {
    analytics: boolean;
    performance: boolean;
    advertising: boolean;
  }) => {
    setIsLoading(true);
    
    try {
      telemetryService.setConsent({
        ...preferences,
        essential: true, // Essential cookies are always enabled
      });
      setConsent(preferences.analytics);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const revokeConsent = useCallback(() => {
    telemetryService.setConsent({
      analytics: false,
      performance: false,
      advertising: false,
      essential: true,
    });
    setConsent(false);
  }, []);

  return {
    hasConsent: consent,
    isLoading,
    updateConsent,
    revokeConsent,
  };
}

/**
 * Hook for real-time analytics
 */
export function useRealTimeAnalytics() {
  const [metrics, setMetrics] = useState(analyticsService.getRealTimeMetrics());
  const [insights, setInsights] = useState<any[]>([]);

  useEffect(() => {
    const unsubscribe = analyticsService.subscribeToDashboard((data) => {
      setMetrics(analyticsService.getRealTimeMetrics());
      setInsights(analyticsService.getInsights());
    });

    return unsubscribe;
  }, []);

  return {
    metrics,
    insights,
  };
}

/**
 * Helper function to sanitize props before logging
 */
function sanitizeProps(props?: Record<string, any>): Record<string, any> {
  if (!props) return {};
  
  const sanitized: Record<string, any> = {};
  const sensitiveKeys = ['password', 'token', 'key', 'secret', 'auth'];
  
  for (const [key, value] of Object.entries(props)) {
    if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      try {
        sanitized[key] = JSON.stringify(value).length > 100 ? 
          JSON.stringify(value).substring(0, 97) + '...' : 
          value;
      } catch {
        sanitized[key] = '[OBJECT]';
      }
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
}

export default {
  useComponentTelemetry,
  useInteractionTracking,
  useFormTelemetry,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useJourneyTracking,
  useABTest,
  useConsentManagement,
  useRealTimeAnalytics,
};
