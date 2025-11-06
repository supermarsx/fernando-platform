import React, { useEffect, useState, useRef } from 'react';
import { 
  Activity, Server, Database, HardDrive, Cpu, MemoryStick, 
  Wifi, CheckCircle, AlertCircle, XCircle, TrendingUp, 
  TrendingDown, RefreshCw, Zap, Globe, Shield, Clock,
  BarChart3, LineChart, Gauge, AlertTriangle, Info
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';
import { useNavigate } from 'react-router-dom';

interface SystemMetrics {
  cpu: {
    usage: number;
    cores: number;
    temperature: number;
    frequency: number;
  };
  memory: {
    total: number;
    used: number;
    available: number;
    percentage: number;
  };
  storage: {
    total: number;
    used: number;
    available: number;
    percentage: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
    connections: number;
    latency: number;
  };
  database: {
    connections: number;
    queries: number;
    avgResponseTime: number;
    status: 'healthy' | 'warning' | 'error';
  };
  services: {
    [key: string]: {
      name: string;
      status: 'healthy' | 'warning' | 'error';
      uptime: number;
      responseTime: number;
      lastCheck: string;
    };
  };
  performance: {
    requestsPerSecond: number;
    averageResponseTime: number;
    errorRate: number;
    availability: number;
  };
  alerts: Array<{
    id: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    message: string;
    timestamp: string;
    acknowledged: boolean;
  }>;
}

export default function SystemHealthPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState<string>('1h');
  const [refreshInterval, setRefreshInterval] = useState(30); // seconds
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    fetchSystemHealth();
    setupRealTimeUpdates();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [user, navigate, refreshInterval]);

  const setupRealTimeUpdates = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    intervalRef.current = setInterval(fetchSystemHealth, refreshInterval * 1000);
  };

  const fetchSystemHealth = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setRefreshing(true);
      const response = await api.get(`/api/v1/admin/health?range=${timeRange}`);
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch system health:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load system health metrics"
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-success-600" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-warning-600" />;
      case 'error': return <XCircle className="h-5 w-5 text-error-600" />;
      default: return <Info className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      healthy: 'success' as const,
      warning: 'warning' as const,
      error: 'error' as const
    };
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    );
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / (24 * 60 * 60));
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((seconds % (60 * 60)) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getSeverityBadge = (severity: string) => {
    const variants = {
      low: 'outline' as const,
      medium: 'secondary' as const,
      high: 'warning' as const,
      critical: 'error' as const
    };
    
    return (
      <Badge variant={variants[severity as keyof typeof variants] || 'outline'}>
        {severity}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading system health...</p>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-error-600 mx-auto" />
          <p className="mt-4 text-error-600">Failed to load system health data</p>
          <Button variant="pastel-primary" className="mt-4" onClick={() => fetchSystemHealth()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                System Health
              </h1>
              <p className="text-sm text-muted-foreground">
                Real-time system monitoring and performance metrics
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Time Range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5m">Last 5 minutes</SelectItem>
                  <SelectItem value="15m">Last 15 minutes</SelectItem>
                  <SelectItem value="1h">Last hour</SelectItem>
                  <SelectItem value="24h">Last 24 hours</SelectItem>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                </SelectContent>
              </Select>
              <Button 
                variant="pastel-secondary" 
                onClick={() => fetchSystemHealth()}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button variant="pastel-secondary" onClick={() => navigate('/admin')}>
                Back to Admin
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Overall Status */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
              <Activity className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold flex items-center gap-2">
                <CheckCircle className="h-6 w-6 text-success-600" />
                Healthy
              </div>
              <p className="text-xs text-muted-foreground">All systems operational</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
              <Cpu className="h-4 w-4 text-secondary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.cpu.usage}%</div>
              <Progress value={metrics.cpu.usage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {metrics.cpu.cores} cores @ {metrics.cpu.frequency}MHz
              </p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
              <MemoryStick className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.memory.percentage}%</div>
              <Progress value={metrics.memory.percentage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {formatBytes(metrics.memory.used)} / {formatBytes(metrics.memory.total)}
              </p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Storage Usage</CardTitle>
              <HardDrive className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.storage.percentage}%</div>
              <Progress value={metrics.storage.percentage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {formatBytes(metrics.storage.used)} / {formatBytes(metrics.storage.total)}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary-600" />
                Performance Metrics
              </CardTitle>
              <CardDescription>System performance indicators</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Requests per Second</span>
                  <span className="text-sm font-bold">{metrics.performance.requestsPerSecond}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Avg Response Time</span>
                  <span className="text-sm font-bold">{metrics.performance.averageResponseTime}ms</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Error Rate</span>
                  <Badge variant={metrics.performance.errorRate < 1 ? 'success' : metrics.performance.errorRate < 5 ? 'warning' : 'error'}>
                    {metrics.performance.errorRate}%
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Availability</span>
                  <Badge variant={metrics.performance.availability > 99 ? 'success' : 'warning'}>
                    {metrics.performance.availability}%
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-secondary-600" />
                Database Status
              </CardTitle>
              <CardDescription>Database connection and performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Status</span>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(metrics.database.status)}
                    {getStatusBadge(metrics.database.status)}
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Active Connections</span>
                  <span className="text-sm font-bold">{metrics.database.connections}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Queries per Second</span>
                  <span className="text-sm font-bold">{metrics.database.queries}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Avg Response Time</span>
                  <span className="text-sm font-bold">{metrics.database.avgResponseTime}ms</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Services Status */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-success-600" />
              Services Status
            </CardTitle>
            <CardDescription>Individual service health monitoring</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(metrics.services).map(([key, service]) => (
                <div key={key} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{service.name}</span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(service.status)}
                      {getStatusBadge(service.status)}
                    </div>
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <div>Uptime: {formatUptime(service.uptime)}</div>
                    <div>Response: {service.responseTime}ms</div>
                    <div>Last check: {new Date(service.lastCheck).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Network & System Info */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wifi className="h-5 w-5 text-primary-600" />
                Network Statistics
              </CardTitle>
              <CardDescription>Network traffic and connectivity</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Data In</span>
                  <span className="text-sm font-bold">{formatBytes(metrics.network.bytesIn)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Data Out</span>
                  <span className="text-sm font-bold">{formatBytes(metrics.network.bytesOut)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Active Connections</span>
                  <span className="text-sm font-bold">{metrics.network.connections}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Network Latency</span>
                  <span className="text-sm font-bold">{metrics.network.latency}ms</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-warning-600" />
                Active Alerts
              </CardTitle>
              <CardDescription>System alerts and notifications</CardDescription>
            </CardHeader>
            <CardContent>
              {metrics.alerts.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  <CheckCircle className="h-8 w-8 text-success-600 mx-auto mb-2" />
                  No active alerts
                </div>
              ) : (
                <div className="space-y-3">
                  {metrics.alerts.slice(0, 5).map((alert) => (
                    <div key={alert.id} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{alert.title}</span>
                        {getSeverityBadge(alert.severity)}
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{alert.message}</p>
                      <div className="flex justify-between items-center text-xs text-muted-foreground">
                        <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
                        {!alert.acknowledged && (
                          <Button size="sm" variant="outline" className="h-6 px-2">
                            Acknowledge
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}