import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { 
  Server, 
  Activity, 
  Users, 
  Database, 
  Settings, 
  Shield, 
  Wifi, 
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  BarChart3
} from 'lucide-react';

interface ServerInfo {
  server_id: string;
  server_type: 'client' | 'supplier';
  name: string;
  version: string;
  status: 'active' | 'inactive' | 'maintenance' | 'error';
  host: string;
  port: number;
  available_features: string[];
  capabilities: string[];
  created_at: string;
  uptime: number;
}

interface ServerMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_requests: number;
  active_connections: number;
  response_time: number;
}

interface CommunicationStatus {
  recent_messages: number;
  failed_messages: number;
  active_sync_jobs: number;
  queued_messages: number;
  last_heartbeat: string;
}

export const ServerManagementDashboard: React.FC = () => {
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null);
  const [metrics, setMetrics] = useState<ServerMetrics | null>(null);
  const [commStatus, setCommStatus] = useState<CommunicationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchServerData();
    const interval = setInterval(fetchServerData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchServerData = async () => {
    try {
      setLoading(true);
      
      // Fetch server information
      const serverResponse = await fetch('/api/server/info');
      if (!serverResponse.ok) throw new Error('Failed to fetch server info');
      const serverData = await serverResponse.json();
      setServerInfo(serverData);

      // Fetch metrics
      const metricsResponse = await fetch('/api/server/metrics');
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

      // Fetch communication status
      const commResponse = await fetch('/api/server/communication/status');
      if (commResponse.ok) {
        const commData = await commResponse.json();
        setCommStatus(commData);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'maintenance': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4" />;
      case 'maintenance': return <Clock className="h-4 w-4" />;
      case 'error': return <AlertTriangle className="h-4 w-4" />;
      default: return <Activity className="h-4 w-4" />;
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  if (loading && !serverInfo) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={fetchServerData} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  if (!serverInfo) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert>
          <AlertDescription>No server information available.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {serverInfo.name}
            </h1>
            <p className="text-gray-600 mt-1">
              {serverInfo.server_type === 'client' ? 'Client Server' : 'Supplier Server'} Dashboard
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge 
              variant={serverInfo.status === 'active' ? 'default' : 'secondary'}
              className={`${getStatusColor(serverInfo.status)} text-white`}
            >
              {getStatusIcon(serverInfo.status)}
              <span className="ml-1 capitalize">{serverInfo.status}</span>
            </Badge>
            <Button onClick={fetchServerData} variant="outline" size="sm">
              <Activity className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="features">Features</TabsTrigger>
          <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
          <TabsTrigger value="communication">Communication</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Server Status</CardTitle>
                <Server className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{serverInfo.status}</div>
                <p className="text-xs text-muted-foreground">
                  {serverInfo.host}:{serverInfo.port}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Uptime</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatUptime(serverInfo.uptime)}</div>
                <p className="text-xs text-muted-foreground">
                  Since {new Date(serverInfo.created_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Features</CardTitle>
                <Settings className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{serverInfo.available_features.length}</div>
                <p className="text-xs text-muted-foreground">
                  Available features
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Version</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{serverInfo.version}</div>
                <p className="text-xs text-muted-foreground">
                  {serverInfo.server_type === 'client' ? 'Client' : 'Supplier'} Server
                </p>
              </CardContent>
            </Card>
          </div>

          {metrics && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>CPU Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Usage</span>
                      <span className="text-sm font-medium">{metrics.cpu_usage}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${metrics.cpu_usage}%` }}
                      ></div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Memory Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Usage</span>
                      <span className="text-sm font-medium">{metrics.memory_usage}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full" 
                        style={{ width: `${metrics.memory_usage}%` }}
                      ></div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Active Connections</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.active_connections}</div>
                  <p className="text-xs text-muted-foreground">
                    Response time: {metrics.response_time}ms
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="features" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Available Features</CardTitle>
                <CardDescription>Features currently enabled on this server</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {serverInfo.available_features.map((feature, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">{feature}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Server Capabilities</CardTitle>
                <CardDescription>Core capabilities of this server type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {serverInfo.capabilities.map((capability, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Shield className="h-4 w-4 text-blue-500" />
                      <span className="text-sm">{capability}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Server Configuration</CardTitle>
              <CardDescription>Current server configuration details</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Server ID:</span>
                  <p className="text-gray-600">{serverInfo.server_id}</p>
                </div>
                <div>
                  <span className="font-medium">Server Type:</span>
                  <p className="text-gray-600 capitalize">{serverInfo.server_type}</p>
                </div>
                <div>
                  <span className="font-medium">Host:</span>
                  <p className="text-gray-600">{serverInfo.host}</p>
                </div>
                <div>
                  <span className="font-medium">Port:</span>
                  <p className="text-gray-600">{serverInfo.port}</p>
                </div>
                <div>
                  <span className="font-medium">Created:</span>
                  <p className="text-gray-600">{new Date(serverInfo.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <span className="font-medium">Uptime:</span>
                  <p className="text-gray-600">{formatUptime(serverInfo.uptime)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="monitoring" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">CPU</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.cpu_usage || 0}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Processor utilization
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Memory</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.memory_usage || 0}%
                </div>
                <p className="text-xs text-muted-foreground">
                  RAM utilization
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Disk</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.disk_usage || 0}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Storage utilization
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Network</CardTitle>
                <Wifi className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.network_requests || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Requests/minute
                </p>
              </CardContent>
            </Card>
          </div>

          {metrics && (
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
                <CardDescription>Real-time server performance data</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Response Time</span>
                    <span className="text-sm">{metrics.response_time}ms</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Active Connections</span>
                    <span className="text-sm">{metrics.active_connections}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Network Requests</span>
                    <span className="text-sm">{metrics.network_requests}/min</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="communication" className="space-y-6">
          {commStatus && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Messages</CardTitle>
                    <Wifi className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{commStatus.recent_messages}</div>
                    <p className="text-xs text-muted-foreground">Recent successful</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Failed</CardTitle>
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-600">{commStatus.failed_messages}</div>
                    <p className="text-xs text-muted-foreground">Failed messages</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Sync Jobs</CardTitle>
                    <Activity className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{commStatus.active_sync_jobs}</div>
                    <p className="text-xs text-muted-foreground">Active synchronizations</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Queued</CardTitle>
                    <Clock className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{commStatus.queued_messages}</div>
                    <p className="text-xs text-muted-foreground">Messages in queue</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Communication Status</CardTitle>
                  <CardDescription>Inter-server communication health</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Last Heartbeat</span>
                      <span className="text-sm">
                        {new Date(commStatus.last_heartbeat).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Communication Health</span>
                      <Badge variant={commStatus.failed_messages === 0 ? 'default' : 'destructive'}>
                        {commStatus.failed_messages === 0 ? 'Healthy' : 'Issues Detected'}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {!commStatus && (
            <Alert>
              <Wifi className="h-4 w-4" />
              <AlertDescription>
                Communication monitoring is not available.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ServerManagementDashboard;