import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { 
  Server, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  ArrowRight, 
  Globe, 
  Mail, 
  Building,
  Settings,
  Shield,
  Wifi
} from 'lucide-react';

interface OnboardingData {
  serverName: string;
  serverDescription: string;
  contactEmail: string;
  companyName: string;
  serverUrl: string;
  expectedCustomers: string;
  features: string[];
  agreeToTerms: boolean;
}

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  completed: boolean;
}

export const ClientServerOnboarding: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registrationData, setRegistrationData] = useState<OnboardingData>({
    serverName: '',
    serverDescription: '',
    contactEmail: '',
    companyName: '',
    serverUrl: '',
    expectedCustomers: '',
    features: [],
    agreeToTerms: false
  });

  const steps: OnboardingStep[] = [
    {
      id: 'basic',
      title: 'Basic Information',
      description: 'Server and contact details',
      icon: <Server className="h-4 w-4" />,
      completed: false
    },
    {
      id: 'configuration',
      title: 'Configuration',
      description: 'Features and capabilities',
      icon: <Settings className="h-4 w-4" />,
      completed: false
    },
    {
      id: 'review',
      title: 'Review & Submit',
      description: 'Final review and registration',
      icon: <CheckCircle className="h-4 w-4" />,
      completed: false
    },
    {
      id: 'completion',
      title: 'Registration Complete',
      description: 'Server registered successfully',
      icon: <Shield className="h-4 w-4" />,
      completed: false
    }
  ];

  const availableFeatures = [
    'document_processing',
    'customer_management',
    'billing_integration',
    'usage_tracking',
    'analytics_dashboard',
    'api_access',
    'webhook_support',
    'custom_branding',
    'multi_tenant_support',
    'compliance_tools'
  ];

  const handleInputChange = (field: keyof OnboardingData, value: string | boolean | string[]) => {
    setRegistrationData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFeatureToggle = (feature: string) => {
    setRegistrationData(prev => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter(f => f !== feature)
        : [...prev.features, feature]
    }));
  };

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 0: // Basic information
        return !!(registrationData.serverName && 
                 registrationData.contactEmail && 
                 registrationData.companyName);
      case 1: // Configuration
        return registrationData.features.length > 0;
      case 2: // Review
        return registrationData.agreeToTerms;
      default:
        return true;
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
      setError(null);
    } else {
      setError('Please complete all required fields before proceeding.');
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
    setError(null);
  };

  const submitRegistration = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/server/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          server_name: registrationData.serverName,
          server_description: registrationData.serverDescription,
          contact_email: registrationData.contactEmail,
          company_name: registrationData.companyName,
          server_url: registrationData.serverUrl,
          expected_customers: parseInt(registrationData.expectedCustomers) || 0,
          features: registrationData.features,
          metadata: {
            onboarding_version: '1.0.0',
            registration_timestamp: new Date().toISOString()
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Registration failed');
      }

      const result = await response.json();
      setSuccess(true);
      setCurrentStep(3);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const getStepProgress = () => {
    return ((currentStep + 1) / steps.length) * 100;
  };

  const renderBasicInfoStep = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="serverName">Server Name *</Label>
          <Input
            id="serverName"
            value={registrationData.serverName}
            onChange={(e) => handleInputChange('serverName', e.target.value)}
            placeholder="My Client Server"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="companyName">Company Name *</Label>
          <Input
            id="companyName"
            value={registrationData.companyName}
            onChange={(e) => handleInputChange('companyName', e.target.value)}
            placeholder="ACME Corporation"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="contactEmail">Contact Email *</Label>
        <Input
          id="contactEmail"
          type="email"
          value={registrationData.contactEmail}
          onChange={(e) => handleInputChange('contactEmail', e.target.value)}
          placeholder="admin@acme.com"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="serverUrl">Server URL</Label>
        <Input
          id="serverUrl"
          value={registrationData.serverUrl}
          onChange={(e) => handleInputChange('serverUrl', e.target.value)}
          placeholder="https://server.acme.com"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="serverDescription">Server Description</Label>
        <Textarea
          id="serverDescription"
          value={registrationData.serverDescription}
          onChange={(e) => handleInputChange('serverDescription', e.target.value)}
          placeholder="Describe your server's purpose and expected usage..."
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="expectedCustomers">Expected Number of Customers</Label>
        <Select onValueChange={(value) => handleInputChange('expectedCustomers', value)}>
          <SelectTrigger>
            <SelectValue placeholder="Select expected customer count" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1-10">1-10 customers</SelectItem>
            <SelectItem value="11-50">11-50 customers</SelectItem>
            <SelectItem value="51-100">51-100 customers</SelectItem>
            <SelectItem value="101-500">101-500 customers</SelectItem>
            <SelectItem value="500+">500+ customers</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderConfigurationStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-4">Select Server Features</h3>
        <p className="text-sm text-gray-600 mb-4">
          Choose the features your server will provide to customers. This helps us optimize the server configuration.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {availableFeatures.map(feature => (
            <div key={feature} className="flex items-center space-x-2">
              <Checkbox
                id={feature}
                checked={registrationData.features.includes(feature)}
                onCheckedChange={() => handleFeatureToggle(feature)}
              />
              <Label htmlFor={feature} className="text-sm capitalize">
                {feature.replace(/_/g, ' ')}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {registrationData.features.length > 0 && (
        <div>
          <h4 className="font-medium mb-2">Selected Features:</h4>
          <div className="flex flex-wrap gap-2">
            {registrationData.features.map(feature => (
              <Badge key={feature} variant="secondary" className="capitalize">
                {feature.replace(/_/g, ' ')}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderReviewStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-4">Review Registration Details</h3>
        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-medium mb-2">Server Information</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Server Name:</span>
                <p>{registrationData.serverName}</p>
              </div>
              <div>
                <span className="font-medium">Company:</span>
                <p>{registrationData.companyName}</p>
              </div>
              <div>
                <span className="font-medium">Contact Email:</span>
                <p>{registrationData.contactEmail}</p>
              </div>
              <div>
                <span className="font-medium">Server URL:</span>
                <p>{registrationData.serverUrl || 'Not specified'}</p>
              </div>
              {registrationData.serverDescription && (
                <div className="col-span-2">
                  <span className="font-medium">Description:</span>
                  <p>{registrationData.serverDescription}</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-medium mb-2">Selected Features</h4>
            <div className="flex flex-wrap gap-2">
              {registrationData.features.map(feature => (
                <Badge key={feature} variant="outline" className="capitalize">
                  {feature.replace(/_/g, ' ')}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="terms"
          checked={registrationData.agreeToTerms}
          onCheckedChange={(checked) => handleInputChange('agreeToTerms', checked as boolean)}
        />
        <Label htmlFor="terms" className="text-sm">
          I agree to the terms of service and understand that this server will be registered with the supplier network.
        </Label>
      </div>
    </div>
  );

  const renderCompletionStep = () => (
    <div className="text-center space-y-6">
      <div className="flex justify-center">
        <div className="rounded-full bg-green-100 p-3">
          <CheckCircle className="h-12 w-12 text-green-600" />
        </div>
      </div>
      <div>
        <h3 className="text-2xl font-bold text-gray-900">Registration Complete!</h3>
        <p className="text-gray-600 mt-2">
          Your server has been successfully registered with the supplier network.
        </p>
      </div>
      <div className="bg-green-50 p-4 rounded-lg">
        <h4 className="font-medium text-green-800 mb-2">Next Steps:</h4>
        <ul className="text-sm text-green-700 space-y-1">
          <li>• Wait for supplier approval (usually within 24 hours)</li>
          <li>• Configure your server's API endpoints</li>
          <li>• Set up monitoring and health checks</li>
          <li>• Begin onboarding your first customers</li>
        </ul>
      </div>
      <Button onClick={() => window.location.href = '/dashboard'}>
        Go to Dashboard
      </Button>
    </div>
  );

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Client Server Onboarding</h1>
        <p className="text-gray-600 mt-1">
          Register your server with the supplier network to begin serving customers.
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Step {currentStep + 1} of {steps.length}</span>
          <span className="text-sm text-gray-600">
            {steps[currentStep].title}
          </span>
        </div>
        <Progress value={getStepProgress()} className="w-full" />
      </div>

      {/* Step Navigation */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div 
            key={step.id}
            className={`flex items-center space-x-2 ${
              index <= currentStep ? 'text-blue-600' : 'text-gray-400'
            }`}
          >
            <div className={`rounded-full p-2 ${
              index < currentStep ? 'bg-blue-600 text-white' :
              index === currentStep ? 'bg-blue-100 text-blue-600' :
              'bg-gray-100 text-gray-400'
            }`}>
              {step.icon}
            </div>
            <span className="text-sm font-medium hidden md:block">{step.title}</span>
            {index < steps.length - 1 && (
              <ArrowRight className="h-4 w-4 text-gray-400 hidden md:block" />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            {steps[currentStep].icon}
            <span>{steps[currentStep].title}</span>
          </CardTitle>
          <CardDescription>{steps[currentStep].description}</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!success && (
            <>
              {currentStep === 0 && renderBasicInfoStep()}
              {currentStep === 1 && renderConfigurationStep()}
              {currentStep === 2 && renderReviewStep()}
              {currentStep === 3 && renderCompletionStep()}

              {/* Navigation Buttons */}
              {currentStep < 3 && (
                <div className="flex justify-between mt-8">
                  <Button
                    variant="outline"
                    onClick={prevStep}
                    disabled={currentStep === 0}
                  >
                    Previous
                  </Button>
                  
                  {currentStep === 2 ? (
                    <Button 
                      onClick={submitRegistration}
                      disabled={!validateStep(2) || loading}
                    >
                      {loading ? (
                        <>
                          <Clock className="h-4 w-4 mr-2 animate-spin" />
                          Registering...
                        </>
                      ) : (
                        'Register Server'
                      )}
                    </Button>
                  ) : (
                    <Button onClick={nextStep} disabled={!validateStep(currentStep)}>
                      Next
                    </Button>
                  )}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ClientServerOnboarding;