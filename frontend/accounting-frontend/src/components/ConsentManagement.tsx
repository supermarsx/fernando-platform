/**
 * Consent Management Component for GDPR Compliance
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Shield, 
  Settings, 
  Cookie, 
  BarChart3, 
  Zap, 
  Target,
  CheckCircle,
  XCircle,
  Info
} from 'lucide-react';
import telemetryService from '../services/telemetryService';

interface ConsentPreferences {
  essential: boolean; // Always true, cannot be disabled
  analytics: boolean;
  performance: boolean;
  advertising: boolean;
}

interface ConsentBannerProps {
  onConsentUpdate?: (preferences: ConsentPreferences) => void;
  position?: 'bottom' | 'top' | 'center';
}

export function ConsentBanner({ onConsentUpdate, position = 'bottom' }: ConsentBannerProps) {
  const [showBanner, setShowBanner] = useState(false);
  const [preferences, setPreferences] = useState<ConsentPreferences>({
    essential: true,
    analytics: true,
    performance: true,
    advertising: false,
  });

  useEffect(() => {
    // Check if consent has already been given
    const existingConsent = localStorage.getItem('telemetry_consent');
    if (!existingConsent) {
      setShowBanner(true);
    } else {
      try {
        const consent = JSON.parse(existingConsent);
        setPreferences(consent);
      } catch (error) {
        console.warn('Invalid consent data:', error);
        setShowBanner(true);
      }
    }
  }, []);

  const handleAcceptAll = () => {
    const allAccepted = {
      essential: true,
      analytics: true,
      performance: true,
      advertising: true,
    };
    
    setPreferences(allAccepted);
    telemetryService.setConsent(allAccepted);
    setShowBanner(false);
    onConsentUpdate?.(allAccepted);
  };

  const handleRejectAll = () => {
    const minimal = {
      essential: true,
      analytics: false,
      performance: false,
      advertising: false,
    };
    
    setPreferences(minimal);
    telemetryService.setConsent(minimal);
    setShowBanner(false);
    onConsentUpdate?.(minimal);
  };

  const handleSavePreferences = () => {
    telemetryService.setConsent(preferences);
    setShowBanner(false);
    onConsentUpdate?.(preferences);
  };

  const handlePreferenceChange = (key: keyof ConsentPreferences, value: boolean) => {
    if (key === 'essential') return; // Essential cookies cannot be disabled
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  if (!showBanner) {
    return null;
  }

  const positionClasses = {
    bottom: 'fixed bottom-0 left-0 right-0 z-50',
    top: 'fixed top-0 left-0 right-0 z-50',
    center: 'fixed inset-0 z-50 flex items-center justify-center',
  };

  return (
    <div className={positionClasses[position]}>
      <Card className="m-4 shadow-lg border-2 border-blue-200">
        <CardHeader className="bg-blue-50">
          <CardTitle className="flex items-center gap-2 text-blue-900">
            <Cookie className="w-5 h-5" />
            Your Privacy Matters
          </CardTitle>
          <CardDescription className="text-blue-700">
            We use cookies and similar technologies to enhance your experience, analyze usage, 
            and provide personalized content. You can control what we collect.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Consent Categories */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-green-600" />
                  <div>
                    <Label className="font-medium">Essential Cookies</Label>
                    <p className="text-sm text-gray-600">Required for basic functionality</p>
                  </div>
                </div>
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>

              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                  <div>
                    <Label className="font-medium">Analytics</Label>
                    <p className="text-sm text-gray-600">Help us understand how you use our app</p>
                  </div>
                </div>
                <Switch
                  checked={preferences.analytics}
                  onCheckedChange={(checked) => handlePreferenceChange('analytics', checked)}
                />
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-orange-600" />
                  <div>
                    <Label className="font-medium">Performance</Label>
                    <p className="text-sm text-gray-600">Monitor app performance and speed</p>
                  </div>
                </div>
                <Switch
                  checked={preferences.performance}
                  onCheckedChange={(checked) => handlePreferenceChange('performance', checked)}
                />
              </div>

              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Target className="w-5 h-5 text-purple-600" />
                  <div>
                    <Label className="font-medium">Advertising</Label>
                    <p className="text-sm text-gray-600">Personalized ads and marketing</p>
                  </div>
                </div>
                <Switch
                  checked={preferences.advertising}
                  onCheckedChange={(checked) => handlePreferenceChange('advertising', checked)}
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-end">
            <Button 
              variant="outline" 
              onClick={handleRejectAll}
              className="flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Reject All
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => setPreferences(prev => ({ ...prev, analytics: false, performance: false, advertising: false }))}
            >
              Essential Only
            </Button>
            
            <Button 
              onClick={handleSavePreferences}
              className="flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Save Preferences
            </Button>
            
            <Button 
              onClick={handleAcceptAll}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
            >
              Accept All
            </Button>
          </div>

          {/* Privacy Notice */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-sm">
              You can change your preferences anytime in the settings. We respect your privacy 
              and will only use data you've consented to. For more details, see our{' '}
              <a href="/privacy" className="underline text-blue-600">Privacy Policy</a>.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
}

interface ConsentSettingsProps {
  onClose?: () => void;
  className?: string;
}

export function ConsentSettings({ onClose, className }: ConsentSettingsProps) {
  const [preferences, setPreferences] = useState<ConsentPreferences>({
    essential: true,
    analytics: telemetryService.isAnalyticsEnabled(),
    performance: true,
    advertising: false,
  });

  const [hasChanges, setHasChanges] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('telemetry_consent');
    if (consent) {
      try {
        const parsed = JSON.parse(consent);
        setPreferences(parsed);
      } catch (error) {
        console.warn('Invalid consent data:', error);
      }
    }
  }, []);

  const handlePreferenceChange = (key: keyof ConsentPreferences, value: boolean) => {
    if (key === 'essential') return;
    setPreferences(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setSaved(false);
  };

  const handleSave = () => {
    telemetryService.setConsent(preferences);
    setHasChanges(false);
    setSaved(true);
    
    setTimeout(() => setSaved(false), 3000);
  };

  const handleReset = () => {
    const consent = localStorage.getItem('telemetry_consent');
    if (consent) {
      try {
        const parsed = JSON.parse(consent);
        setPreferences(parsed);
        setHasChanges(false);
      } catch (error) {
        console.warn('Invalid consent data:', error);
      }
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Privacy Settings
        </CardTitle>
        <CardDescription>
          Manage how we collect and use your data. These settings affect your privacy and experience.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Current Status */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Current Status</span>
          </div>
          <div className="mt-2 text-sm text-green-700">
            Analytics: {preferences.analytics ? 'Enabled' : 'Disabled'} • 
            Performance: {preferences.performance ? 'Enabled' : 'Disabled'} • 
            Advertising: {preferences.advertising ? 'Enabled' : 'Disabled'}
          </div>
        </div>

        {/* Consent Categories */}
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-green-600" />
              <div>
                <Label className="font-medium">Essential Cookies</Label>
                <p className="text-sm text-gray-600">
                  These cookies are necessary for the website to function and cannot be switched off.
                </p>
              </div>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              <div>
                <Label className="font-medium">Analytics Cookies</Label>
                <p className="text-sm text-gray-600">
                  Help us understand how visitors interact with our website by collecting anonymous information.
                </p>
              </div>
            </div>
            <Switch
              checked={preferences.analytics}
              onCheckedChange={(checked) => handlePreferenceChange('analytics', checked)}
            />
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-orange-600" />
              <div>
                <Label className="font-medium">Performance Cookies</Label>
                <p className="text-sm text-gray-600">
                  Allow us to recognize and count the number of visitors and see how visitors move around our website.
                </p>
              </div>
            </div>
            <Switch
              checked={preferences.performance}
              onCheckedChange={(checked) => handlePreferenceChange('performance', checked)}
            />
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-purple-600" />
              <div>
                <Label className="font-medium">Advertising Cookies</Label>
                <p className="text-sm text-gray-600">
                  These cookies may be used to build a profile of your interests and show you relevant advertisements.
                </p>
              </div>
            </div>
            <Switch
              checked={preferences.advertising}
              onCheckedChange={(checked) => handlePreferenceChange('advertising', checked)}
            />
          </div>
        </div>

        {/* Data Usage Information */}
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>What we collect:</strong> Page views, clicks, performance metrics, and error information. 
            <strong>How we use it:</strong> To improve our service, fix bugs, and understand user behavior. 
            <strong>Your control:</strong> You can disable analytics and performance tracking at any time.
          </AlertDescription>
        </Alert>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-end">
          <Button variant="outline" onClick={handleReset} disabled={!hasChanges}>
            Reset Changes
          </Button>
          
          {saved && (
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <CheckCircle className="w-4 h-4" />
              Settings saved successfully!
            </div>
          )}
          
          <Button onClick={handleSave} disabled={!hasChanges}>
            Save Settings
          </Button>
          
          {onClose && (
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </div>

        {/* Data Export/Deletion */}
        <div className="pt-4 border-t">
          <h4 className="font-medium mb-2">Your Data Rights</h4>
          <div className="flex flex-col sm:flex-row gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                const data = telemetryService.getSessionInfo();
                // In a real implementation, this would generate a data export
                console.log('Data export:', data);
                alert('Data export feature would be implemented here');
              }}
            >
              Export My Data
            </Button>
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                if (confirm('Are you sure you want to delete all your data? This action cannot be undone.')) {
                  telemetryService.clearData();
                  alert('All data has been deleted.');
                }
              }}
            >
              Delete My Data
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Hook for accessing consent status
export function useConsent() {
  const [consent, setConsent] = useState(telemetryService.isAnalyticsEnabled());
  const [isLoading, setIsLoading] = useState(false);

  const updateConsent = async (preferences: Omit<ConsentPreferences, 'essential'>) => {
    setIsLoading(true);
    
    try {
      telemetryService.setConsent({
        essential: true,
        ...preferences,
      });
      setConsent(preferences.analytics);
    } finally {
      setIsLoading(false);
    }
  };

  const revokeConsent = () => {
    telemetryService.setConsent({
      essential: true,
      analytics: false,
      performance: false,
      advertising: false,
    });
    setConsent(false);
  };

  return {
    hasConsent: consent,
    isLoading,
    updateConsent,
    revokeConsent,
  };
}

export default {
  ConsentBanner,
  ConsentSettings,
  useConsent,
};
