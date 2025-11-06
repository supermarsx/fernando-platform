import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  Activity, 
  TrendingUp, 
  Zap, 
  AlertTriangle, 
  BarChart3, 
  Settings,
  Download,
  Filter,
  Maximize2,
  Grid,
  Server,
  Globe,
  Users,
  Clock
} from 'lucide-react';

import SystemDashboard from '../components/dashboards/SystemDashboard';
import BusinessMetricsDashboard from '../components/dashboards/BusinessMetricsDashboard';
import PerformanceDashboard from '../components/dashboards/PerformanceDashboard';
import AlertDashboard from '../components/dashboards/AlertDashboard';
import { telemetryAPI } from '../lib/api';

interface DashboardWidget {
  id: string;
  title: string;
  component: string;
  position: { x: number; y: number; w: number; h: number };
  settings: any;
}

const TelemetryDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('system');
  const [layout, setLayout] = useState<'grid' | 'tabs'>('tabs');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dashboardConfig, setDashboardConfig] = useState<any>(null);
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [loading, setLoading] = useState(true);

  // Load dashboard configuration
  const loadDashboardConfig = async () => {
    try {
      setLoading(true);
      const config = await telemetryAPI.getDashboardConfig('main');
      setDashboardConfig(config.data);
      
      // Default widgets configuration
      const defaultWidgets: DashboardWidget[] = [
        {
          id: 'system-overview',
          title: 'System Overview',
          component: 'system-metrics',
          position: { x: 0, y: 0, w: 6, h: 4 },
          settings: { refreshInterval: 30 }
        },
        {
          id: 'business-kpis',
          title: 'Business KPIs',
          component: 'business-metrics',
          position: { x: 6, y: 0, w: 6, h: 4 },
          settings: { refreshInterval: 60 }
        },
        {
          id: 'performance-metrics',
          title: 'Performance Metrics',
          component: 'performance',
          position: { x: 0, y: 4, w: 12, h: 6 },
          settings: { refreshInterval: 15 }
        },
        {
          id: 'active-alerts',
          title: 'Active Alerts',
          component: 'alerts',
          position: { x: 0, y: 10, w: 12, h: 4 },
          settings: { refreshInterval: 10 }
        }
      ];
      
      setWidgets(defaultWidgets);
    } catch (error) {
      console.error('Failed to load dashboard configuration:', error);
      // Use default configuration
      setWidgets([
        {
          id: 'system-overview',
          title: 'System Overview',
          component: 'system-metrics',
          position: { x: 0, y: 0, w: 6, h: 4 },
          settings: { refreshInterval: 30 }
        },
        {
          id: 'business-kpis',
          title: 'Business KPIs',
          component: 'business-metrics',
          position: { x: 6, y: 0, w: 6, h: 4 },
          settings: { refreshInterval: 60 }
        },
        {
          id: 'performance-metrics',
          title: 'Performance Metrics',
          component: 'performance',
          position: { x: 0, y: 4, w: 12, h: 6 },
          settings: { refreshInterval: 15 }
        },
        {
          id: 'active-alerts',
          title: 'Active Alerts',
          component: 'alerts',
          position: { x: 0, y: 10, w: 12, h: 4 },
          settings: { refreshInterval: 10 }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardConfig();
  }, []);

  // Export dashboard data
  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    try {
      const response = await telemetryAPI.exportMetrics({
        format,
        time_range: '24h',
        metrics: ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'total_revenue', 'active_users'],
        filters: { dashboard: 'main' }
      });
      
      // Create download link
      const blob = new Blob([JSON.stringify(response.data)], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `telemetry-dashboard-${format}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  // Handle fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // Quick stats for overview
  const quickStats = [
    {
      title: 'System Health',
      value: '98.5%',
      status: 'healthy',
      icon: Server,
      color: 'text-green-600',
      description: 'All systems operational'
    },
    {
      title: 'Active Users',
      value: '2,847',
      status: 'up',
      icon: Users,
      color: 'text-blue-600',
      description: '+12.3% from yesterday'
    },
    {
      title: 'Response Time',
      value: '145ms',
      status: 'good',
      icon: Zap,
      color: 'text-purple-600',
      description: 'Average response time'
    },
    {
      title: 'Active Alerts',
      value: '3',
      status: 'warning',
      icon: AlertTriangle,
      color: 'text-orange-600',
      description: '2 critical, 1 high priority'
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading telemetry dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-50 ${isFullscreen ? 'p-0' : 'p-6'}`}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Telemetry Dashboard</h1>
            <p className="text-muted-foreground">
              Real-time monitoring and analytics for Fernando platform
            </p>
          </div>
          <div className="flex gap-2">
            <Select value={layout} onValueChange={(value: any) => setLayout(value)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tabs">Tabs View</SelectItem>
                <SelectItem value="grid">Grid View</SelectItem>
              </SelectContent>
            </Select>
            <Select onValueChange={(value) => handleExport(value as any)}>
              <SelectTrigger className="w-32">
                <Download className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Export" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">Export CSV</SelectItem>
                <SelectItem value="json">Export JSON</SelectItem>
                <SelectItem value="pdf">Export PDF</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={toggleFullscreen}>
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {quickStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                    <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                    <p className="text-xs text-muted-foreground mt-1">{stat.description}</p>
                  </div>
                  <Icon className={`h-8 w-8 ${stat.color}`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Dashboard Content */}
      {layout === 'tabs' ? (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="system" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              System Health
            </TabsTrigger>
            <TabsTrigger value="business" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Business Metrics
            </TabsTrigger>
            <TabsTrigger value="performance" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Performance
            </TabsTrigger>
            <TabsTrigger value="alerts" className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Alerts
            </TabsTrigger>
          </TabsList>

          <TabsContent value="system" className="mt-6">
            <SystemDashboard />
          </TabsContent>

          <TabsContent value="business" className="mt-6">
            <BusinessMetricsDashboard />
          </TabsContent>

          <TabsContent value="performance" className="mt-6">
            <PerformanceDashboard />
          </TabsContent>

          <TabsContent value="alerts" className="mt-6">
            <AlertDashboard />
          </TabsContent>
        </Tabs>
      ) : (
        /* Grid Layout */
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Grid className="h-5 w-5" />
                System Health Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96">
                <SystemDashboard />
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Business Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <BusinessMetricsDashboard />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <PerformanceDashboard />
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Active Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <AlertDashboard />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Dashboard Settings Panel */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Dashboard Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-4">
              <h4 className="font-medium">Display Settings</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Auto-refresh</span>
                  <Badge variant="outline">Enabled</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Refresh interval</span>
                  <span>30 seconds</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Time range default</span>
                  <span>24 hours</span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium">Data Sources</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>System Metrics</span>
                  <Badge variant="outline">Connected</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Business Metrics</span>
                  <Badge variant="outline">Connected</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Performance Metrics</span>
                  <Badge variant="outline">Connected</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Alert System</span>
                  <Badge variant="outline">Connected</Badge>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium">Notifications</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Email alerts</span>
                  <Badge variant="outline">Enabled</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Slack integration</span>
                  <Badge variant="outline">Enabled</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Browser notifications</span>
                  <Badge variant="outline">Enabled</Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Mobile push</span>
                  <Badge variant="outline">Disabled</Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TelemetryDashboardPage;