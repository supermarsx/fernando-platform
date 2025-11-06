/**
 * Telemetry Context Provider
 * Provides telemetry services throughout the React application
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import telemetryService from '../services/telemetryService';
import analyticsService from '../services/analytics';
import performanceMonitor from '../services/performanceMonitor';
import eventTracker from '../services/eventTracker';
import telemetryAPI from '../services/telemetryAPI';

interface TelemetryContextType {
  telemetry: typeof telemetryService;
  analytics: typeof analyticsService;
  performance: typeof performanceMonitor;
  events: typeof eventTracker;
  api: typeof telemetryAPI;
  isInitialized: boolean;
  consent: {
    hasConsent: boolean;
    updateConsent: (preferences: any) => Promise<void>;
  };
}

const TelemetryContext = createContext<TelemetryContextType | undefined>(undefined);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [hasConsent, setHasConsent] = useState(false);

  useEffect(() => {
    // Initialize telemetry services
    initializeTelemetry();
    
    return () => {
      // Cleanup on unmount
      telemetryService.destroy();
      analyticsService.destroy();
      performanceMonitor.destroy();
      eventTracker.destroy();
      telemetryAPI.destroy();
    };
  }, []);

  const initializeTelemetry = async () => {
    try {
      // Check for existing consent
      const consent = localStorage.getItem('telemetry_consent');
      if (consent) {
        try {
          const preferences = JSON.parse(consent);
          setHasConsent(preferences.analytics || false);
        } catch (error) {
          console.warn('Invalid consent data:', error);
          setHasConsent(false);
        }
      }

      // Initialize user identification if user is logged in
      const userId = localStorage.getItem('user_id');
      if (userId) {
        telemetryService.identify(userId);
      }

      // Track page view
      telemetryService.trackPageView();

      // Set up real-time updates
      const ws = telemetryAPI.setupRealTimeStream(
        (event) => {
          // Handle real-time telemetry events
          console.log('Real-time telemetry event:', event);
        },
        (error) => {
          console.warn('Telemetry WebSocket error:', error);
        }
      );

      setIsInitialized(true);
    } catch (error) {
      console.error('Failed to initialize telemetry:', error);
      setIsInitialized(false);
    }
  };

  const updateConsent = async (preferences: any) => {
    try {
      telemetryService.setConsent({
        essential: true,
        ...preferences,
      });
      
      setHasConsent(preferences.analytics);
      
      // Track consent update
      telemetryService.trackEvent('consent_updated', {
        preferences,
        timestamp: Date.now(),
      });
    } catch (error) {
      console.error('Failed to update consent:', error);
      throw error;
    }
  };

  const value: TelemetryContextType = {
    telemetry: telemetryService,
    analytics: analyticsService,
    performance: performanceMonitor,
    events: eventTracker,
    api: telemetryAPI,
    isInitialized,
    consent: {
      hasConsent,
      updateConsent,
    },
  };

  return (
    <TelemetryContext.Provider value={value}>
      {children}
    </TelemetryContext.Provider>
  );
}

export function useTelemetry() {
  const context = useContext(TelemetryContext);
  if (context === undefined) {
    throw new Error('useTelemetry must be used within a TelemetryProvider');
  }
  return context;
}

export default TelemetryProvider;
