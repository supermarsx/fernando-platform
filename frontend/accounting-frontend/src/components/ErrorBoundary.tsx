import React from 'react';
import telemetryService from '../services/telemetryService';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

const serializeError = (error: any) => {
  if (error instanceof Error) {
    return {
      message: error.message,
      stack: error.stack,
      name: error.name,
    };
  }
  return { message: 'Unknown error', stack: JSON.stringify(error, null, 2) };
};

export interface ErrorBoundaryState {
  hasError: boolean;
  error: any;
  errorInfo: any;
  errorId: string;
  timestamp: number;
}

export class ErrorBoundary extends React.Component<
  { 
    children: React.ReactNode;
    fallback?: React.ComponentType<{error: any; retry: () => void}>;
    onError?: (error: any, errorInfo: any) => void;
    componentName?: string;
  },
  ErrorBoundaryState
> {
  private retryCount = 0;
  private maxRetries = 3;
  private componentName: string;

  constructor(props: { 
    children: React.ReactNode;
    fallback?: React.ComponentType<{error: any; retry: () => void}>;
    onError?: (error: any, errorInfo: any) => void;
    componentName?: string;
  }) {
    super(props);
    this.componentName = props.componentName || 'ErrorBoundary';
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
      timestamp: 0,
    };
  }

  static getDerivedStateFromError(error: any): Partial<ErrorBoundaryState> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return {
      hasError: true,
      error,
      errorId,
      timestamp: Date.now(),
    };
  }

  componentDidCatch(error: any, errorInfo: any) {
    const errorData = serializeError(error);
    
    // Enhanced error tracking with telemetry
    telemetryService.trackEvent('component_error', {
      errorId: this.state.errorId,
      errorMessage: errorData.message,
      errorStack: errorData.stack,
      errorName: errorData.name,
      componentName: this.componentName,
      retryCount: this.retryCount,
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: this.state.timestamp,
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
      ...this.getErrorContext(),
    });

    // Track error severity
    this.trackErrorSeverity(errorData.message, errorInfo.componentStack);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    this.setState({ errorInfo });
  }

  private getErrorContext() {
    return {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      devicePixelRatio: window.devicePixelRatio,
      onlineStatus: navigator.onLine,
      memoryUsage: (performance as any).memory ? {
        usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
        totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
      } : null,
    };
  }

  private trackErrorSeverity(message: string, componentStack: string) {
    let severity: 'low' | 'medium' | 'high' | 'critical' = 'medium';
    
    // Critical errors
    if (message.includes('ChunkLoadError') || message.includes('Loading chunk')) {
      severity = 'critical';
    }
    // High severity errors
    else if (message.includes('TypeError') || message.includes('ReferenceError')) {
      severity = 'high';
    }
    // Low severity errors
    else if (message.includes('Warning') || message.includes('deprecated')) {
      severity = 'low';
    }

    telemetryService.trackEvent('error_severity', {
      errorId: this.state.errorId,
      severity,
      message,
      componentStack,
    });
  }

  private handleRetry = () => {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      
      telemetryService.trackEvent('error_retry', {
        errorId: this.state.errorId,
        retryCount: this.retryCount,
        componentName: this.componentName,
      });

      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        errorId: '',
        timestamp: 0,
      });
    } else {
      telemetryService.trackEvent('error_retry_exhausted', {
        errorId: this.state.errorId,
        maxRetries: this.maxRetries,
        componentName: this.componentName,
      });
    }
  };

  private handleGoHome = () => {
    telemetryService.trackEvent('error_recovery_action', {
      errorId: this.state.errorId,
      action: 'go_home',
      componentName: this.componentName,
    });

    window.location.href = '/dashboard';
  };

  private handleReportError = () => {
    const errorData = {
      errorId: this.state.errorId,
      timestamp: this.state.timestamp,
      url: window.location.href,
      userAgent: navigator.userAgent,
      error: serializeError(this.state.error),
      componentStack: this.state.errorInfo?.componentStack,
      context: this.getErrorContext(),
    };

    telemetryService.trackEvent('error_report_submitted', {
      errorId: this.state.errorId,
      componentName: this.componentName,
    });

    // In a real implementation, this would send the error to a reporting service
    console.log('Error report:', errorData);
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent 
            error={this.state.error} 
            retry={this.handleRetry}
          />
        );
      }

      const errorData = serializeError(this.state.error);
      const isDev = process.env.NODE_ENV === 'development';

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
          <Card className="w-full max-w-2xl">
            <CardHeader className="text-center">
              <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <CardTitle className="text-red-600">
                {this.retryCount >= this.maxRetries 
                  ? 'Something went seriously wrong' 
                  : 'Something went wrong'
                }
              </CardTitle>
              <CardDescription>
                {this.retryCount >= this.maxRetries
                  ? 'We\'ve encountered a persistent error. Please contact support.'
                  : 'An unexpected error occurred. You can try again or go back to the dashboard.'
                }
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {/* Error Details (only in development or with special permission) */}
              {(isDev || localStorage.getItem('show_error_details') === 'true') && (
                <div className="bg-gray-100 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">Error Details:</h4>
                  <div className="text-sm space-y-2">
                    <p><strong>Error ID:</strong> {this.state.errorId}</p>
                    <p><strong>Component:</strong> {this.componentName}</p>
                    <p><strong>Message:</strong> {errorData.message}</p>
                    {errorData.stack && (
                      <details className="mt-2">
                        <summary className="cursor-pointer font-medium">Stack Trace</summary>
                        <pre className="mt-2 text-xs overflow-auto max-h-40 bg-white p-2 rounded border">
                          {errorData.stack}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                {this.retryCount < this.maxRetries && (
                  <Button 
                    onClick={this.handleRetry} 
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Try Again ({this.maxRetries - this.retryCount} left)
                  </Button>
                )}
                
                <Button 
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2"
                >
                  <Home className="w-4 h-4" />
                  Go to Dashboard
                </Button>

                <Button 
                  onClick={this.handleReportError}
                  variant="secondary"
                  size="sm"
                >
                  Report Error
                </Button>
              </div>

              {/* Recovery Suggestions */}
              <div className="text-center text-sm text-gray-600">
                {this.retryCount < this.maxRetries ? (
                  <p>
                    If the problem persists, try refreshing the page or contact support with the error ID: 
                    <code className="ml-1 px-2 py-1 bg-gray-200 rounded text-xs">
                      {this.state.errorId}
                    </code>
                  </p>
                ) : (
                  <p>
                    Please contact support with error ID: 
                    <code className="ml-1 px-2 py-1 bg-gray-200 rounded text-xs">
                      {this.state.errorId}
                    </code>
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook for easy error boundary usage
export function useErrorHandler() {
  return React.useCallback((error: Error, context?: Record<string, any>) => {
    telemetryService.trackEvent('manual_error', {
      error: serializeError(error),
      context,
      timestamp: Date.now(),
      url: window.location.href,
    });
  }, []);
}