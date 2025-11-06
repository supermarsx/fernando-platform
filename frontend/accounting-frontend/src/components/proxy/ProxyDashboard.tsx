import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Activity, 
  Server, 
  Shield, 
  Zap, 
  Database,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  BarChart3,
  Globe,
  Key,
  Settings
} from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useRealtimeData } from '@/hooks/useRealtimeData';

interface ProxyServer {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'maintenance' | 'error';
  health: number;
  uptime: string;
  lastHeartbeat: string;
  region: string;
  load: number;
  responseTime: number;
  errorRate: number;
  activeConnections: number;
}

interface ProxyMetrics {
  totalRequests: number;
  successRate: number;
  averageResponseTime: number;
  cacheHitRatio: number;
  activeConnections: number;
  errorRate: number;
  throughput: number;
}

const ProxyDashboard: React.FC = () => {
  const [proxyServers, setProxyServers] = useState<ProxyServer[]>([]);
  const [metrics, setMetrics] = useState<ProxyMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');

  const { connected, data: wsData } = useWebSocket('/ws/proxy/metrics');
  const { data: realtimeData, refresh } = useRealtimeData('/api/proxy/status');

  useEffect(() => {
    if (realtimeData) {
      setProxyServers(realtimeData.servers || []);
      setMetrics(realtimeData.metrics || null);
      setLoading(false);
    }
  }, [realtimeData]);

  useEffect(() => {
    if (wsData) {
      // Update metrics in real-time
      setMetrics(prev => prev ? { ...prev, ...wsData } : wsData);
      // Update individual server status
      if (wsData.serverUpdate) {
        setProxyServers(prev => 
          prev.map(server => 
            server.id === wsData.serverUpdate.id 
              ? { ...server, ...wsData.serverUpdate }
              : server
          )
        );
      }
    }
  }, [wsData]);

  const handleServerAction = async (serverId: string, action: string) => {
    try {
      await fetch(`/api/proxy/servers/${serverId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      refresh();
    } catch (error) {
      console.error(`Failed to ${action} server:`, error);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
      active: 'default',
      inactive: 'secondary',
      maintenance: 'outline',
      error: 'destructive'
    };
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>;
  };

  const getHealthColor = (health: number) => {
    if (health >= 95) return 'text-green-500';
    if (health >= 80) return 'text-yellow-500';
    return 'text-red-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading proxy servers...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Proxy Management</h1>
          <p className="text-muted-foreground">Monitor and manage your proxy server infrastructure</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Badge variant={connected ? 'default' : 'destructive'}>
            {connected ? 'Live' : 'Offline'}
          </Badge>
        </div>
      </div>

      {/* Overall Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.totalRequests?.toLocaleString() || 0}</div>
            <p className="text-xs text-muted-foreground">
              +12% from last hour
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{metrics?.successRate || 0}%</div>
            <Progress value={metrics?.successRate || 0} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.averageResponseTime || 0}ms</div>
            <p className="text-xs text-muted-foreground">
              -5% from last hour
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cache Hit Ratio</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{metrics?.cacheHitRatio || 0}%</div>
            <Progress value={metrics?.cacheHitRatio || 0} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="servers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="servers">Server Status</TabsTrigger>
          <TabsTrigger value="metrics">Performance Metrics</TabsTrigger>
          <TabsTrigger value="logs">System Logs</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="servers" className="space-y-4">
          <div className="grid gap-4">
            {proxyServers.map((server) => (
              <Card key={server.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center space-x-2">
                        <Server className="h-5 w-5" />
                        <span>{server.name}</span>
                        {getStatusBadge(server.status)}
                      </CardTitle>
                      <CardDescription>
                        Region: {server.region} • Uptime: {server.uptime}
                      </CardDescription>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleServerAction(server.id, 'restart')}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Restart
                      </Button>
                      <Button
                        variant={server.status === 'maintenance' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => handleServerAction(server.id, 'maintenance')}
                      >
                        <Settings className="h-4 w-4 mr-1" />
                        {server.status === 'maintenance' ? 'Exit Maintenance' : 'Maintenance'}
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Health</p>
                      <p className={`text-lg font-semibold ${getHealthColor(server.health)}`}>
                        {server.health}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Load</p>
                      <p className="text-lg font-semibold">{server.load}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Response Time</p>
                      <p className="text-lg font-semibold">{server.responseTime}ms</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Active Connections</p>
                      <p className="text-lg font-semibold">{server.activeConnections}</p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-sm text-muted-foreground">Error Rate</p>
                    <div className="flex items-center space-x-2">
                      <Progress value={server.errorRate} className="flex-1" />
                      <span className="text-sm">{server.errorRate}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <PerformanceMonitor />
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Proxy Server Logs</CardTitle>
              <CardDescription>Real-time proxy server activity logs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm h-96 overflow-y-auto">
                {/* Real-time logs would be displayed here */}
                <div className="space-y-1">
                  <div>[2024-01-15 10:30:15] INFO: Proxy server started successfully</div>
                  <div>[2024-01-15 10:30:20] DEBUG: Load balancer initialized</div>
                  <div>[2024-01-15 10:30:25] INFO: New connection established from 192.168.1.100</div>
                  <div>[2024-01-15 10:30:30] WARN: High latency detected on server-01</div>
                  <div>[2024-01-15 10:30:35] INFO: Request routed to server-02</div>
                  <div>[2024-01-15 10:30:40] DEBUG: Cache hit for /api/data</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <LoadBalancerConfig />
            <RateLimitingConfig />
            <CircuitBreakerMonitor />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ProxyDashboard;