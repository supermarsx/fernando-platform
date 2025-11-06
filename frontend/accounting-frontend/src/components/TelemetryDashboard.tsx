/**
 * Real-time Telemetry Dashboard Component
 * Displays live analytics, performance metrics, and insights
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import {
  Activity,
  Users,
  Clock,
  TrendingUp,
  TrendingDown,
  Zap,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Download,
  Filter,
  Eye,
  MousePointer,
  Globe,
  Smartphone,
  Monitor
} from 'lucide-react';
import analyticsService from '../services/analytics';
import telemetryService from '../services/telemetryService';
import performanceMonitor from '../services/performanceMonitor';
import { useRealTimeAnalytics } from '../hooks/useTelemetry';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color?: 'blue' | 'green' | 'orange' | 'red' | 'purple';
}

function MetricCard({ title, value, change, icon, color = 'blue' }: MetricCardProps) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-100',
    green: 'text-green-600 bg-green-100',
    orange: 'text-orange-600 bg-orange-100',
    red: 'text-red-600 bg-red-100',
    purple: 'text-purple-600 bg-purple-100',
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            {change !== undefined && (
              <div className={`flex items-center mt-2 text-sm ${
                change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {change >= 0 ? (
                  <TrendingUp className="w-4 h-4 mr-1" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-1" />
                )}
                {Math.abs(change)}%
              </div>
            )}
          </div>
          <div className={`p-3 rounded-full ${colorClasses[color]}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface WebVitalsGaugeProps {
  metric: 'LCP' | 'FID' | 'CLS' | 'FCP' | 'TTFB';
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
}

function WebVitalsGauge({ metric, value, rating }: WebVitalsGaugeProps) {
  const getGaugeColor = (rating: string) => {
    switch (rating) {
      case 'good': return 'text-green-600';
      case 'needs-improvement': return 'text-orange-600';
      case 'poor': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getProgressValue = (metric: string, value: number) => {
    // Calculate progress based on metric thresholds
    switch (metric) {
      case 'LCP': return Math.min((value / 4000) * 100, 100);
      case 'FID': return Math.min((value / 300) * 100, 100);
      case 'CLS': return Math.min((value / 0.25) * 100, 100);
      case 'FCP': return Math.min((value / 3000) * 100, 100);
      case 'TTFB': return Math.min((value / 1800) * 100, 100);
      default: return 0;
    }
  };

  const formatValue = (metric: string, value: number) => {
    switch (metric) {
      case 'CLS': return value.toFixed(3);
      default: return Math.round(value) + 'ms';
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{metric}</span>
        <span className={`text-sm font-medium ${getGaugeColor(rating)}`}>
          {formatValue(metric, value)}
        </span>
      </div>
      <Progress 
        value={getProgressValue(metric, value)} 
        className="h-2"
      />
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Poor</span>
        <span className={`font-medium ${getGaugeColor(rating)}`}>
          {rating.replace('-', ' ').toUpperCase()}
        </span>
        <span>Good</span>
      </div>
    </div>
  );
}

interface EventTimelineProps {
  events: Array<{
    type: string;
    timestamp: number;
    userId?: string;
  }>;
}

function EventTimeline({ events }: EventTimelineProps) {
  const getEventIcon = (type: string) => {
    switch (type) {
      case 'page_view': return <Eye className="w-4 h-4" />;
      case 'user_action': return <MousePointer className="w-4 h-4" />;
      case 'feature_usage': return <Zap className="w-4 h-4" />;
      case 'error': return <AlertTriangle className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'page_view': return 'bg-blue-100 text-blue-600';
      case 'user_action': return 'bg-green-100 text-green-600';
      case 'feature_usage': return 'bg-purple-100 text-purple-600';
      case 'error': return 'bg-red-100 text-red-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {events.slice(0, 10).map((event, index) => (
        <div key={index} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
          <div className={`p-1 rounded-full ${getEventColor(event.type)}`}>
            {getEventIcon(event.type)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {event.type.replace('_', ' ').toUpperCase()}
            </p>
            <p className="text-xs text-gray-500">
              {formatTime(event.timestamp)}
              {event.userId && ` • ${event.userId.substring(0, 8)}...`}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

interface SystemHealthProps {
  systemLoad: {
    cpu: number;
    memory: number;
    responseTime: number;
  };
}

function SystemHealth({ systemLoad }: SystemHealthProps) {
  const getHealthColor = (value: number, thresholds: { good: number; warning: number }) => {
    if (value <= thresholds.good) return 'text-green-600';
    if (value <= thresholds.warning) return 'text-orange-600';
    return 'text-red-600';
  };

  const getHealthStatus = (value: number, thresholds: { good: number; warning: number }) => {
    if (value <= thresholds.good) return 'Good';
    if (value <= thresholds.warning) return 'Warning';
    return 'Critical';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">CPU Usage</span>
        <span className={`text-sm font-medium ${getHealthColor(systemLoad.cpu, { good: 50, warning: 80 })}`}>
          {getHealthStatus(systemLoad.cpu, { good: 50, warning: 80 })}
        </span>
      </div>
      <Progress value={systemLoad.cpu} className="h-2" />
      <div className="text-xs text-gray-500">{systemLoad.cpu.toFixed(1)}%</div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Memory Usage</span>
        <span className={`text-sm font-medium ${getHealthColor(systemLoad.memory, { good: 70, warning: 85 })}`}>
          {getHealthStatus(systemLoad.memory, { good: 70, warning: 85 })}
        </span>
      </div>
      <Progress value={systemLoad.memory} className="h-2" />
      <div className="text-xs text-gray-500">{systemLoad.memory.toFixed(1)}%</div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Response Time</span>
        <span className={`text-sm font-medium ${getHealthColor(systemLoad.responseTime, { good: 200, warning: 500 })}`}>
          {getHealthStatus(systemLoad.responseTime, { good: 200, warning: 500 })}
        </span>
      </div>
      <Progress value={(systemLoad.responseTime / 1000) * 100} className="h-2" />
      <div className="text-xs text-gray-500">{systemLoad.responseTime.toFixed(0)}ms</div>
    </div>
  );
}

export function TelemetryDashboard() {
  const { metrics, insights } = useRealTimeAnalytics();
  const [currentMetrics, setCurrentMetrics] = useState(analyticsService.getCurrentMetrics());
  const [coreWebVitals, setCoreWebVitals] = useState(performanceMonitor.getCoreWebVitals());
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    // Subscribe to real-time updates
    const unsubscribe = analyticsService.subscribeToDashboard(() => {
      setCurrentMetrics(analyticsService.getCurrentMetrics());
      setCoreWebVitals(performanceMonitor.getCoreWebVitals());
    });

    return unsubscribe;
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate refresh delay
    setTimeout(() => {
      setCurrentMetrics(analyticsService.getCurrentMetrics());
      setCoreWebVitals(performanceMonitor.getCoreWebVitals());
      setIsRefreshing(false);
    }, 1000);
  };

  const handleExportData = () => {
    const data = analyticsService.exportData('json');
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `telemetry-data-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Prepare chart data
  const deviceData = Object.entries(currentMetrics.deviceTypes).map(([device, count]) => ({
    name: device.charAt(0).toUpperCase() + device.slice(1),
    value: count,
  }));

  const browserData = Object.entries(currentMetrics.browserTypes).map(([browser, count]) => ({
    name: browser.charAt(0).toUpperCase() + browser.slice(1),
    value: count,
  }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

  return (
    <div className="min-h-screen bg-gray-50 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Telemetry Dashboard</h1>
          <p className="text-gray-600">Real-time analytics and performance monitoring</p>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            Live
          </Badge>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportData}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Users"
          value={metrics.activeUsers}
          icon={<Users className="w-6 h-6" />}
          color="blue"
        />
        
        <MetricCard
          title="Page Views"
          value={currentMetrics.pageViews}
          icon={<Eye className="w-6 h-6" />}
          color="green"
        />
        
        <MetricCard
          title="Sessions"
          value={currentMetrics.sessions}
          icon={<Activity className="w-6 h-6" />}
          color="purple"
        />
        
        <MetricCard
          title="Conversions"
          value={currentMetrics.conversions}
          icon={<TrendingUp className="w-6 h-6" />}
          color="orange"
        />
      </div>

      {/* Core Web Vitals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Core Web Vitals
            </CardTitle>
            <CardDescription>
              Key performance metrics that affect user experience
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {coreWebVitals.LCP && (
              <WebVitalsGauge
                metric="LCP"
                value={coreWebVitals.LCP}
                rating={coreWebVitals.LCP <= 2500 ? 'good' : coreWebVitals.LCP <= 4000 ? 'needs-improvement' : 'poor'}
              />
            )}
            
            {coreWebVitals.FID && (
              <WebVitalsGauge
                metric="FID"
                value={coreWebVitals.FID}
                rating={coreWebVitals.FID <= 100 ? 'good' : coreWebVitals.FID <= 300 ? 'needs-improvement' : 'poor'}
              />
            )}
            
            {coreWebVitals.CLS && (
              <WebVitalsGauge
                metric="CLS"
                value={coreWebVitals.CLS}
                rating={coreWebVitals.CLS <= 0.1 ? 'good' : coreWebVitals.CLS <= 0.25 ? 'needs-improvement' : 'poor'}
              />
            )}
            
            {coreWebVitals.FCP && (
              <WebVitalsGauge
                metric="FCP"
                value={coreWebVitals.FCP}
                rating={coreWebVitals.FCP <= 1800 ? 'good' : coreWebVitals.FCP <= 3000 ? 'needs-improvement' : 'poor'}
              />
            )}
          </CardContent>
        </Card>

        {/* Real-time Events */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Live Events
            </CardTitle>
            <CardDescription>
              Recent user interactions and system events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EventTimeline events={metrics.recentEvents} />
          </CardContent>
        </Card>
      </div>

      {/* Device & Browser Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Smartphone className="w-5 h-5" />
              Device Types
            </CardTitle>
            <CardDescription>
              Distribution of devices accessing your application
            </CardDescription>
          </CardHeader>
          <CardContent>
            {deviceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={deviceData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {deviceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No device data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Browser Distribution
            </CardTitle>
            <CardDescription>
              Browser usage statistics
            </CardDescription>
          </CardHeader>
          <CardContent>
            {browserData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={browserData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No browser data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* System Health & Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Monitor className="w-5 h-5" />
              System Health
            </CardTitle>
            <CardDescription>
              Real-time system performance metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SystemHealth systemLoad={metrics.systemLoad} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              Insights & Recommendations
            </CardTitle>
            <CardDescription>
              AI-powered insights to improve your application
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.length > 0 ? (
                insights.map((insight, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border-l-4 ${
                      insight.type === 'success'
                        ? 'bg-green-50 border-green-400'
                        : insight.type === 'warning'
                        ? 'bg-orange-50 border-orange-400'
                        : 'bg-blue-50 border-blue-400'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {insight.type === 'success' && <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />}
                      {insight.type === 'warning' && <AlertTriangle className="w-4 h-4 text-orange-600 mt-0.5" />}
                      {insight.type === 'info' && <Activity className="w-4 h-4 text-blue-600 mt-0.5" />}
                      
                      <div className="flex-1">
                        <p className="font-medium text-sm">{insight.title}</p>
                        <p className="text-xs text-gray-600 mt-1">{insight.description}</p>
                        <Badge 
                          variant="outline" 
                          className="mt-2 text-xs"
                        >
                          {insight.impact} impact
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No insights available yet</p>
                  <p className="text-sm">Start using the application to generate insights</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default TelemetryDashboard;
