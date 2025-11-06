# Client-Side Telemetry Integration

This comprehensive client-side telemetry system provides detailed analytics, performance monitoring, and user behavior tracking for the Fernando frontend React application.

## Features

### 🏃‍♂️ Performance Monitoring
- **Core Web Vitals**: LCP, FID, CLS, FCP, TTFB tracking
- **Custom Performance Marks**: Measure specific operations
- **Resource Timing**: Monitor resource loading times
- **Long Task Detection**: Identify blocking operations
- **System Health Metrics**: CPU, memory, response time

### 📊 User Analytics
- **Page View Tracking**: Automatic page view recording
- **User Interaction Events**: Clicks, form submissions, navigation
- **Feature Usage Analytics**: Track feature adoption and usage
- **User Journey Mapping**: Complete user flow visualization
- **Conversion Tracking**: Monitor goal completions

### 🎯 A/B Testing
- **Variant Assignment**: Automatic user assignment to test variants
- **Conversion Tracking**: Monitor A/B test performance
- **Statistical Analysis**: Built-in test result analysis

### 🛡️ Privacy & Compliance
- **GDPR Compliance**: User consent management
- **Data Anonymization**: Automatic PII protection
- **Consent Preferences**: Granular consent controls
- **Data Export/Deletion**: User data rights

### 🔄 Real-time Dashboard
- **Live Metrics**: Real-time user activity monitoring
- **Interactive Charts**: Visual analytics with Recharts
- **System Monitoring**: Performance and health metrics
- **AI-Powered Insights**: Automated recommendations

## Quick Start

### 1. Initialize Telemetry Services

```tsx
// main.tsx - Already configured
import { TelemetryProvider } from './contexts/TelemetryContext';
import { ConsentBanner } from './components/ConsentManagement';

<TelemetryProvider>
  <App />
  <ConsentBanner position="bottom" />
</TelemetryProvider>
```

### 2. Use Telemetry Hooks in Components

```tsx
import {
  useComponentTelemetry,
  useInteractionTracking,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useFormTelemetry,
  useJourneyTracking,
  useABTest,
  useConsentManagement,
} from '../hooks/useTelemetry';

function MyComponent() {
  // Track component lifecycle
  useComponentTelemetry('MyComponent', { version: '1.0' });
  
  // Track user interactions
  const { trackClick } = useInteractionTracking('my-button', 'buttons');
  
  // Track feature usage
  const { trackFeatureOpen, trackFeatureClose } = useFeatureTelemetry('my-feature');
  
  // Measure performance
  const { startOperation, endOperation } = usePerformanceTelemetry('my-operation');
  
  // Track user journey
  const { startJourney, nextStep, completeJourney } = useJourneyTracking('user-flow');
  
  // A/B testing
  const { assignedVariant, trackConversion } = useABTest('test-name', ['A', 'B']);
  
  // Form tracking
  const { trackFieldChange, trackFormSubmit } = useFormTelemetry('my-form');
  
  const handleButtonClick = () => {
    trackClick();
    // Your button logic
  };
  
  return (
    <button onClick={handleButtonClick}>
      Click Me
    </button>
  );
}
```

### 3. Access Analytics Dashboard

Navigate to `/analytics` to view:
- Real-time metrics
- User behavior analytics
- Performance insights
- Conversion funnels
- Consent management

## API Reference

### Core Services

#### TelemetryService
```typescript
import telemetryService from '../services/telemetryService';

// Track events
telemetryService.trackEvent('custom_event', {
  property: 'value',
});

// Identify users
telemetryService.identify('user_id', { 
  email: 'user@example.com',
  plan: 'premium'
});

// Track page views
telemetryService.trackPageView('/my-page');

// Track actions
telemetryService.trackAction('click', 'button_id', {
  buttonText: 'Submit',
});

// Track feature usage
telemetryService.trackFeatureUsage('feature_name', {
  action: 'use',
  context: 'dashboard',
});

// Track conversions
telemetryService.trackConversion('signup', 1, {
  plan: 'premium',
});

// Set consent
telemetryService.setConsent({
  essential: true,
  analytics: true,
  performance: true,
  advertising: false,
});
```

#### PerformanceMonitor
```typescript
import performanceMonitor from '../services/performanceMonitor';

// Mark performance points
performanceMonitor.markPerformance('operation_start');

// Measure between marks
const duration = performanceMonitor.measurePerformance(
  'operation_name',
  'operation_start',
  'operation_end'
);

// Get Core Web Vitals
const vitals = performanceMonitor.getCoreWebVitals();
// { LCP: 1234, FID: 56, CLS: 0.05, FCP: 987, TTFB: 234 }

// Get performance summary
const summary = performanceMonitor.getPerformanceSummary();
```

#### EventTracker
```typescript
import eventTracker from '../services/eventTracker';

// Track feature events
eventTracker.trackFeatureEvent('feature_name', 'open');
eventTracker.trackFeatureEvent('feature_name', 'use');
eventTracker.trackFeatureEvent('feature_name', 'close');

// Track navigation
eventTracker.trackNavigation({
  from: '/page1',
  to: '/page2',
  type: 'link',
  trigger: 'navigation link',
  timestamp: Date.now(),
});

// Track user journeys
eventTracker.trackUserJourney('signup_flow', {
  step: 'email_entered',
});
```

#### AnalyticsService
```typescript
import analyticsService from '../services/analytics';

// Get current metrics
const metrics = analyticsService.getCurrentMetrics();

// Get real-time data
const realTime = analyticsService.getRealTimeMetrics();

// Create conversion funnels
analyticsService.createConversionFunnel('signup', [
  'landing_page',
  'signup_form',
  'email_verification',
  'profile_completion'
});

// Track funnel steps
analyticsService.trackFunnelStep('signup', 1, 'user_id');

// Subscribe to updates
const unsubscribe = analyticsService.subscribeToDashboard((metrics) => {
  console.log('Updated metrics:', metrics);
});

// Export data
const data = analyticsService.exportData('json');
```

### React Hooks

#### useComponentTelemetry
```typescript
useComponentTelemetry(componentName: string, props?: Record<string, any>);
```

Automatically tracks:
- Component mount/unmount
- Render count
- Prop changes
- Component errors

#### useInteractionTracking
```typescript
const { trackInteraction, trackClick, trackFocus, trackBlur } = 
  useInteractionTracking(elementId: string, context?: string);
```

Tracks user interactions with elements.

#### useFeatureTelemetry
```typescript
const { 
  trackFeatureOpen, 
  trackFeatureUse, 
  trackFeatureClose, 
  trackFeatureError 
} = useFeatureTelemetry(featureName: string);
```

Comprehensive feature usage tracking.

#### usePerformanceTelemetry
```typescript
const { startOperation, endOperation, trackApiCall } = 
  usePerformanceTelemetry(operationName: string);
```

Performance monitoring with automatic timing.

#### useFormTelemetry
```typescript
const { 
  trackFieldChange, 
  trackFieldFocus, 
  trackValidationError, 
  trackFormSubmit 
} = useFormTelemetry(formId: string, formType?: string);
```

Complete form interaction tracking.

#### useJourneyTracking
```typescript
const { currentStep, steps, startJourney, nextStep, completeJourney } = 
  useJourneyTracking(journeyName: string);
```

User journey and flow tracking.

#### useABTest
```typescript
const { assignedVariant, trackConversion, trackEvent } = 
  useABTest(testName: string, variants: string[]);
```

A/B testing with conversion tracking.

#### useConsentManagement
```typescript
const { hasConsent, isLoading, updateConsent, revokeConsent } = 
  useConsentManagement();
```

Consent management integration.

#### useRealTimeAnalytics
```typescript
const { metrics, insights } = useRealTimeAnalytics();
```

Real-time dashboard data.

### Components

#### ConsentBanner
```tsx
<ConsentBanner 
  position="bottom" // 'bottom' | 'top' | 'center'
  onConsentUpdate={(preferences) => {
    console.log('Consent updated:', preferences);
  }}
/>
```

#### ConsentSettings
```tsx
<ConsentSettings 
  onClose={() => setShowSettings(false)}
  className="my-custom-class"
/>
```

#### TelemetryDashboard
```tsx
// Accessible at /analytics route
<TelemetryDashboard />
```

#### ErrorBoundary (Enhanced)
```tsx
// Already enhanced with telemetry in the app
<ErrorBoundary 
  componentName="MyComponent"
  onError={(error, errorInfo) => {
    // Custom error handling
  }}
/>
```

## Configuration

### Telemetry Configuration
```typescript
const telemetryConfig = {
  apiEndpoint: '/api/telemetry',
  batchSize: 10,
  flushInterval: 30000,
  enableConsoleLogging: process.env.NODE_ENV === 'development',
  enableErrorTracking: true,
  enablePerformanceTracking: true,
  sampleRate: 1.0, // 100% of users
  anonymize: false,
  enableConsentMode: true,
};
```

### Environment Variables
```env
REACT_APP_TELEMETRY_API_URL=/api/telemetry
REACT_APP_TELEMETRY_ENABLED=true
REACT_APP_TELEMETRY_SAMPLE_RATE=1.0
REACT_APP_CONSENT_REQUIRED=true
```

## Privacy & GDPR Compliance

### Consent Management
- Users can opt-in/out of different data collection types
- Granular controls for analytics, performance, and advertising tracking
- Consent can be updated anytime
- All tracking respects user preferences

### Data Anonymization
```typescript
// Automatic PII detection and redaction
telemetryService.trackEvent('user_action', {
  email: 'user@example.com', // Will be redacted
  password: 'secret', // Will be redacted
  safeData: 'normal data', // Will be tracked
});
```

### Data Export/Deletion
Users can export their data or request deletion through the consent settings panel.

## Best Practices

### 1. Performance
- Use `usePerformanceTelemetry` for API calls and heavy operations
- Mark performance critical sections with `performanceMonitor.markPerformance()`
- Monitor Core Web Vitals regularly

### 2. User Experience
- Track user journeys to understand flow bottlenecks
- Use A/B testing for feature decisions
- Monitor feature adoption rates

### 3. Error Handling
- Enhanced ErrorBoundary automatically tracks errors
- Use `useErrorHandler()` for manual error tracking
- Include context in error reports

### 4. Privacy
- Always respect user consent preferences
- Use data anonymization for sensitive information
- Provide clear privacy controls

### 5. Development
- Enable console logging in development
- Use sample rates for large-scale deployments
- Monitor telemetry performance impact

## Analytics Dashboard

Access comprehensive analytics at `/analytics`:

### Overview Tab
- Key metrics (users, page views, sessions, conversions)
- Performance insights and recommendations
- Real-time activity summary

### Real-time Tab
- Live user activity monitoring
- System health metrics
- Core Web Vitals tracking
- Live event timeline

### Users Tab
- User behavior analytics
- Device and browser distribution
- User journey visualization
- Conversion funnel analysis

### Settings Tab
- Consent management
- Privacy controls
- Data export/deletion

## Troubleshooting

### Common Issues

1. **Events not sending**
   - Check API endpoint configuration
   - Verify network connectivity
   - Check user consent settings

2. **High memory usage**
   - Events are batched and sent automatically
   - Check for memory leaks in event handlers
   - Monitor event queue size

3. **Performance impact**
   - Use appropriate sample rates
   - Disable telemetry in performance-critical paths
   - Monitor performance metrics

4. **Consent issues**
   - Ensure consent banner is displayed
   - Check localStorage for consent data
   - Verify consent update handlers

### Debug Mode
```typescript
// Enable debug logging
localStorage.setItem('telemetry_debug', 'true');

// View current session info
console.log(telemetryService.getSessionInfo());
```

## Support

For questions or issues:
1. Check the analytics dashboard for insights
2. Review browser console for errors
3. Use debug mode for detailed logging
4. Check network tab for event transmission

This telemetry system provides comprehensive insights into user behavior and application performance while maintaining privacy and compliance standards.
