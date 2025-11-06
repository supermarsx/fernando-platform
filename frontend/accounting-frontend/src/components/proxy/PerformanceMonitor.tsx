import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Activity,
  Clock,
  Zap,
  Server,
  Database,
  Globe,
  RefreshCw,
  Download,
  Filter,
  Calendar,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Cpu,
  HardDrive,
  Network
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useRealtimeData } from '@/hooks/useRealtimeData';

interface PerformanceMetrics {
  timestamp: string;
  cpu: {
    usage: number;
    load: number;
  };
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
    packetsIn: number;
    packetsOut: number;
    errors: number;
  };
  requests: {
    total: number;
    successful: number;
    failed: number;
    averageResponseTime: number;
    throughput: number;
    concurrency: number;
  };
  cache: {
    hitRate: number;
    misses: number;
    evictions: number;
    size: number;
  };
  database: {
    connections: number;
    queryTime: number;
    queriesPerSecond: number;
    slowQueries: number;
  }
}

interface EndpointMetrics {
  path: string;
  method: string;
  averageResponseTime: number;
  requestCount: number;
  errorRate: number;
  throughput: number;
}

interface Alert {
  id: string;
  type: 'performance' | 'availability' | 'error' | 'resource';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [endpointMetrics, setEndpointMetrics] = useState<EndpointMetrics[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [timeRange, setTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  
  const { connected, data: wsData } = useWebSocket('/ws/proxy/performance');
  const { data: realtimeData, refresh } = useRealtimeData('/api/proxy/performance');

  useEffect(() => {
    loadPerformanceData();
    
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadPerformanceData, 30000); // Refresh every 30 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, timeRange, selectedEndpoint]);

  useEffect(() => {
    if (wsData) {
      // Update metrics in real-time
      setMetrics(prev => prev ? { ...prev, ...wsData } : wsData);
    }
  }, [wsData]);

  useEffect(() => {
    if (realtimeData) {
      setMetrics(realtimeData.metrics || null);
      setEndpointMetrics(realtimeData.endpoints || []);
      setAlerts(realtimeData.alerts || []);
      setLoading(false);
    }
  }, [realtimeData]);

  const loadPerformanceData = async () => {
    try {
      const params = new URLSearchParams({
        timeRange,
        endpoint: selectedEndpoint
      });
      
      const response = await fetch(`/api/proxy/performance?${params}`);
      if (response.ok) {
        const data = await response.json();
        setMetrics(data.metrics || null);
        setEndpointMetrics(data.endpoints || []);
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to load performance data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load performance data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const exportMetrics = async () => {
    try {
      const params = new URLSearchParams({
        timeRange,
        endpoint: selectedEndpoint,
        format: 'csv'
      });
      
      const response = await fetch(`/api/proxy/performance/export?${params}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proxy-performance-${timeRange}.csv`;
      a.click();
      
      toast({
        title: 'Success',
        description: 'Performance metrics exported successfully'
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to export metrics',
        variant: 'destructive'
      });
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/proxy/performance/alerts/${alertId}/acknowledge`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setAlerts(prev => prev.map(alert => 
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        ));
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to acknowledge alert',
        variant: 'destructive'
      });
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      low: 'text-blue-600',
      medium: 'text-yellow-600',
      high: 'text-orange-600',
      critical: 'text-red-600'
    };
    return colors[severity] || 'text-gray-600';
  };

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      low: 'default',
      medium: 'secondary',
      high: 'destructive',
      critical: 'destructive'
    };
    return <Badge variant={variants[severity] || 'secondary'} className="capitalize">{severity}</Badge>;
  };

  const getAlertIcon = (type: string) => {
    const icons = {
      performance: BarChart3,
      availability: CheckCircle,
      error: XCircle,
      resource: Cpu
    };
    const Icon = icons[type] || AlertTriangle;
    return <Icon className="h-4 w-4" />;
  };

  const getResponseTimeColor = (time: number) => {
    if (time > 5000) return 'text-red-500';
    if (time > 1000) return 'text-yellow-500';
    return 'text-green-500';
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading performance metrics...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Performance Monitor</h1>
          <p className="text-muted-foreground">Real-time performance metrics and monitoring</p>
        </div>
        <div className="flex items-center space-x-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="15m">15 minutes</SelectItem>
              <SelectItem value="1h">1 hour</SelectItem>
              <SelectItem value="6h">6 hours</SelectItem>
              <SelectItem value="24h">24 hours</SelectItem>
              <SelectItem value="7d">7 days</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          
          <Button variant="outline" onClick={exportMetrics}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          
          <div className="flex items-center space-x-1">
            <Label htmlFor="auto-refresh" className="text-sm">Auto-refresh</Label>
            <input
              id="auto-refresh"
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
          </div>
          
          <Badge variant={connected ? 'default' : 'destructive'}>
            {connected ? 'Live' : 'Offline'}
          </Badge>
        </div>
      </div>

      {/* Current Status Overview */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
              <Cpu className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.cpu.usage}%</div>
              <Progress value={metrics.cpu.usage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                Load: {metrics.cpu.load.toFixed(2)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
              <HardDrive className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.memory.percentage}%</div>
              <Progress value={metrics.memory.percentage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {formatBytes(metrics.memory.used)} / {formatBytes(metrics.memory.total)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Network I/O</CardTitle>
              <Network className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatBytes(metrics.network.bytesIn + metrics.network.bytesOut)}/s
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                In: {formatBytes(metrics.network.bytesIn)}/s • Out: {formatBytes(metrics.network.bytesOut)}/s
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Response Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.requests.averageResponseTime}ms</div>
              <p className="text-xs text-muted-foreground mt-1">
                {metrics.requests.throughput} req/s
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {metrics && (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center space-x-2">
                    <BarChart3 className="h-5 w-5" />
                    <span>Request Metrics</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Requests</p>
                      <p className="text-2xl font-bold">{metrics.requests.total.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Success Rate</p>
                      <p className="text-2xl font-bold text-green-600">
                        {((metrics.requests.successful / metrics.requests.total) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Throughput</p>
                      <p className="text-2xl font-bold">{metrics.requests.throughput}/s</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Concurrency</p>
                      <p className="text-2xl font-bold">{metrics.requests.concurrency}</p>
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Error Rate</p>
                    <div className="flex items-center space-x-2">
                      <Progress value={(metrics.requests.failed / metrics.requests.total) * 100} className="flex-1" />
                      <span className="text-sm font-semibold">
                        {((metrics.requests.failed / metrics.requests.total) * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center space-x-2">
                    <Database className="h-5 w-5" />
                    <span>Cache Performance</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Hit Rate</p>
                      <p className="text-2xl font-bold text-green-600">{metrics.cache.hitRate}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Cache Size</p>
                      <p className="text-2xl font-bold">{formatBytes(metrics.cache.size)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Misses</p>
                      <p className="text-2xl font-bold">{metrics.cache.misses.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Evictions</p>
                      <p className="text-2xl font-bold">{metrics.cache.evictions.toLocaleString()}</p>
                    </div>
                  </div>
                  
                  <Progress value={metrics.cache.hitRate} className="w-full" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center space-x-2">
                    <Globe className="h-5 w-5" />
                    <span>Database Performance</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Active Connections</p>
                      <p className="text-2xl font-bold">{metrics.database.connections}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Query Time</p>
                      <p className="text-2xl font-bold">{metrics.database.queryTime}ms</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Queries/Second</p>
                      <p className="text-2xl font-bold">{metrics.database.queriesPerSecond}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Slow Queries</p>
                      <p className="text-2xl font-bold text-red-600">{metrics.database.slowQueries}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Real-time Chart</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    Performance chart would be displayed here
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="endpoints" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Endpoint Performance</h3>
            <Select value={selectedEndpoint} onValueChange={setSelectedEndpoint}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select endpoint" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Endpoints</SelectItem>
                {endpointMetrics.map(endpoint => (
                  <SelectItem key={`${endpoint.method}-${endpoint.path}`} value={`${endpoint.method}-${endpoint.path}`}>
                    {endpoint.method} {endpoint.path}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            {endpointMetrics.map((endpoint, index) => (
              <Card key={index}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <Badge variant="outline">{endpoint.method}</Badge>
                        <code className="text-sm font-mono">{endpoint.path}</code>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Avg Response Time</p>
                          <p className={`text-lg font-semibold ${getResponseTimeColor(endpoint.averageResponseTime)}`}>
                            {endpoint.averageResponseTime}ms
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Request Count</p>
                          <p className="text-lg font-semibold">{endpoint.requestCount.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Error Rate</p>
                          <p className="text-lg font-semibold">{endpoint.errorRate.toFixed(2)}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Throughput</p>
                          <p className="text-lg font-semibold">{endpoint.throughput}/s</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="resources" className="space-y-4">
          {metrics && (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">System Resources</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm">CPU Usage</span>
                      <span className="text-sm font-semibold">{metrics.cpu.usage}%</span>
                    </div>
                    <Progress value={metrics.cpu.usage} className="h-2" />
                  </div>
                  
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm">Memory Usage</span>
                      <span className="text-sm font-semibold">{metrics.memory.percentage}%</span>
                    </div>
                    <Progress value={metrics.memory.percentage} className="h-2" />
                  </div>
                  
                  <div className="pt-2 border-t">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Load Average</p>
                        <p className="font-semibold">{metrics.cpu.load.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Used Memory</p>
                        <p className="font-semibold">{formatBytes(metrics.memory.used)}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Network Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Bytes In</p>
                      <p className="text-lg font-semibold">{formatBytes(metrics.network.bytesIn)}/s</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Bytes Out</p>
                      <p className="text-lg font-semibold">{formatBytes(metrics.network.bytesOut)}/s</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Packets In</p>
                      <p className="text-lg font-semibold">{metrics.network.packetsIn.toLocaleString()}/s</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Network Errors</p>
                      <p className="text-lg font-semibold text-red-600">{metrics.network.errors}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Active Alerts</h3>
            <Button variant="outline" onClick={loadPerformanceData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Alerts
            </Button>
          </div>

          <div className="space-y-3">
            {alerts.filter(alert => !alert.acknowledged).map((alert) => (
              <Card key={alert.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getAlertIcon(alert.type)}
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="font-semibold">{alert.message}</p>
                          {getSeverityBadge(alert.severity)}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {alert.type} • {new Date(alert.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => acknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {alerts.filter(alert => !alert.acknowledged).length === 0 && (
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-center space-x-2 text-green-600">
                    <CheckCircle className="h-5 w-5" />
                    <span>No active alerts</span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Trends</CardTitle>
              <CardDescription>
                Historical performance data over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-96 flex items-center justify-center text-muted-foreground">
                Performance trends chart would be displayed here
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PerformanceMonitor;