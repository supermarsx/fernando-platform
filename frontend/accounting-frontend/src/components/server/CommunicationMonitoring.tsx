import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { 
  Wifi, 
  MessageSquare, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  Activity,
  Send,
  Server,
  Database,
  BarChart3,
  Filter,
  Search
} from 'lucide-react';

interface CommunicationLog {
  id: string;
  message_id: string;
  source_server_id: string;
  target_server_id: string;
  message_type: string;
  status: 'pending' | 'success' | 'failed' | 'timeout' | 'retry';
  timestamp: string;
  error_message?: string;
  retry_count: number;
}

interface SyncJob {
  id: string;
  source_server_id: string;
  target_server_id: string;
  sync_type: string;
  status: 'scheduled' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

interface ServerEndpoint {
  server_id: string;
  server_name: string;
  server_type: 'client' | 'supplier';
  status: 'online' | 'offline' | 'error';
  last_heartbeat: string;
  api_url: string;
  latency: number;
}

interface CommunicationMetrics {
  total_messages: number;
  successful_messages: number;
  failed_messages: number;
  queued_messages: number;
  active_sync_jobs: number;
  average_latency: number;
  uptime_percentage: number;
}

export const CommunicationMonitoring: React.FC = () => {
  const [communicationLogs, setCommunicationLogs] = useState<CommunicationLog[]>([]);
  const [syncJobs, setSyncJobs] = useState<SyncJob[]>([]);
  const [serverEndpoints, setServerEndpoints] = useState<ServerEndpoint[]>([]);
  const [metrics, setMetrics] = useState<CommunicationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchCommunicationData();
    const interval = setInterval(fetchCommunicationData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [selectedTimeRange, filterStatus]);

  const fetchCommunicationData = async () => {
    try {
      setLoading(true);
      
      // Fetch communication logs
      const logsResponse = await fetch(`/api/communication/logs?time_range=${selectedTimeRange}&status=${filterStatus}`);
      if (logsResponse.ok) {
        const logs = await logsResponse.json();
        setCommunicationLogs(logs);
      }

      // Fetch sync jobs
      const syncResponse = await fetch('/api/communication/sync-jobs');
      if (syncResponse.ok) {
        const sync = await syncResponse.json();
        setSyncJobs(sync);
      }

      // Fetch server endpoints
      const endpointsResponse = await fetch('/api/communication/servers');
      if (endpointsResponse.ok) {
        const endpoints = await endpointsResponse.json();
        setServerEndpoints(endpoints);
      }

      // Fetch metrics
      const metricsResponse = await fetch('/api/communication/metrics');
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

    } catch (error) {
      console.error('Error fetching communication data:', error);
    } finally {
      setLoading(false);
    }
  };

  const retryMessage = async (messageId: string) => {
    try {
      const response = await fetch(`/api/communication/messages/${messageId}/retry`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchCommunicationData();
      }
    } catch (error) {
      console.error('Error retrying message:', error);
    }
  };

  const cancelSyncJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/communication/sync-jobs/${jobId}/cancel`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchCommunicationData();
      }
    } catch (error) {
      console.error('Error canceling sync job:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
      case 'completed':
      case 'online':
        return 'bg-green-500';
      case 'pending':
      case 'scheduled':
      case 'in_progress':
        return 'bg-blue-500';
      case 'failed':
      case 'error':
      case 'offline':
        return 'bg-red-500';
      case 'timeout':
        return 'bg-yellow-500';
      case 'cancelled':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
      case 'completed':
      case 'online':
        return <CheckCircle className="h-4 w-4" />;
      case 'pending':
      case 'scheduled':
      case 'in_progress':
        return <Clock className="h-4 w-4" />;
      case 'failed':
      case 'error':
      case 'offline':
        return <XCircle className="h-4 w-4" />;
      case 'timeout':
        return <AlertTriangle className="h-4 w-4" />;
      case 'cancelled':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatLatency = (latency: number) => {
    return `${latency}ms`;
  };

  const getMessageTypeColor = (messageType: string) => {
    switch (messageType) {
      case 'heartbeat':
        return 'bg-blue-100 text-blue-800';
      case 'registration':
        return 'bg-green-100 text-green-800';
      case 'sync_request':
      case 'sync_response':
        return 'bg-purple-100 text-purple-800';
      case 'license_check':
        return 'bg-yellow-100 text-yellow-800';
      case 'error_notification':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredLogs = communicationLogs.filter(log => {
    if (searchTerm) {
      return log.message_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
             log.source_server_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
             log.target_server_id.toLowerCase().includes(searchTerm.toLowerCase());
    }
    return true;
  });

  if (loading && communicationLogs.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Communication Monitoring</h1>
        <p className="text-gray-600 mt-1">
          Monitor inter-server communication, sync operations, and network health.
        </p>
      </div>

      {/* Metrics Dashboard */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.total_messages > 0 
                  ? Math.round((metrics.successful_messages / metrics.total_messages) * 100)
                  : 0}%
              </div>
              <p className="text-xs text-muted-foreground">
                {metrics.successful_messages} of {metrics.total_messages} messages
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Queued Messages</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.queued_messages}</div>
              <p className="text-xs text-muted-foreground">
                Waiting for delivery
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatLatency(metrics.average_latency)}</div>
              <p className="text-xs text-muted-foreground">
                Response time
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Uptime</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.uptime_percentage}%</div>
              <p className="text-xs text-muted-foreground">
                Network availability
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="logs">Communication Logs</TabsTrigger>
          <TabsTrigger value="sync">Sync Jobs</TabsTrigger>
          <TabsTrigger value="servers">Server Health</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Communication Activity</CardTitle>
                <CardDescription>Latest messages and their status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {communicationLogs.slice(0, 5).map((log) => (
                    <div key={log.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(log.status)}
                        <div>
                          <p className="text-sm font-medium">{log.message_type}</p>
                          <p className="text-xs text-gray-600">
                            {log.source_server_id} → {log.target_server_id}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge className={`${getStatusColor(log.status)} text-white`}>
                          {log.status}
                        </Badge>
                        <p className="text-xs text-gray-600 mt-1">
                          {formatTimestamp(log.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Active Sync Jobs</CardTitle>
                <CardDescription>Currently running synchronizations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {syncJobs
                    .filter(job => job.status === 'in_progress' || job.status === 'scheduled')
                    .slice(0, 5)
                    .map((job) => (
                    <div key={job.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4 text-blue-500" />
                        <div>
                          <p className="text-sm font-medium">{job.sync_type}</p>
                          <p className="text-xs text-gray-600">
                            {job.source_server_id} → {job.target_server_id}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge className={`${getStatusColor(job.status)} text-white`}>
                          {job.status.replace('_', ' ')}
                        </Badge>
                        <p className="text-xs text-gray-600 mt-1">
                          Started {formatTimestamp(job.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  {syncJobs.filter(job => job.status === 'in_progress' || job.status === 'scheduled').length === 0 && (
                    <p className="text-sm text-gray-600">No active sync jobs.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Network Health Status</CardTitle>
              <CardDescription>Overall communication infrastructure status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {serverEndpoints.filter(s => s.status === 'online').length}
                  </div>
                  <p className="text-sm text-gray-600">Servers Online</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {serverEndpoints.filter(s => s.status === 'offline').length}
                  </div>
                  <p className="text-sm text-gray-600">Servers Offline</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {metrics ? metrics.average_latency : 0}ms
                  </div>
                  <p className="text-sm text-gray-600">Average Latency</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Communication Logs</h2>
              <p className="text-gray-600">Detailed message exchange history</p>
            </div>
            <div className="flex space-x-2">
              <Button onClick={fetchCommunicationData} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>

          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center space-x-2">
                  <Search className="h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search logs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                </div>
                <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15m">15 minutes</SelectItem>
                    <SelectItem value="1h">1 hour</SelectItem>
                    <SelectItem value="6h">6 hours</SelectItem>
                    <SelectItem value="24h">24 hours</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left">
                      <th className="p-4">Message ID</th>
                      <th className="p-4">Type</th>
                      <th className="p-4">Source → Target</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Timestamp</th>
                      <th className="p-4">Retries</th>
                      <th className="p-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map((log) => (
                      <tr key={log.id} className="border-b hover:bg-gray-50">
                        <td className="p-4">
                          <span className="font-mono text-sm">{log.message_id.substring(0, 8)}...</span>
                        </td>
                        <td className="p-4">
                          <Badge className={getMessageTypeColor(log.message_type)}>
                            {log.message_type.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="p-4">
                          <div className="text-sm">
                            <div>{log.source_server_id}</div>
                            <div className="text-gray-600">↓</div>
                            <div>{log.target_server_id}</div>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge className={`${getStatusColor(log.status)} text-white`}>
                            {getStatusIcon(log.status)}
                            <span className="ml-1 capitalize">{log.status}</span>
                          </Badge>
                        </td>
                        <td className="p-4 text-gray-600 text-sm">
                          {formatTimestamp(log.timestamp)}
                        </td>
                        <td className="p-4">
                          {log.retry_count > 0 && (
                            <Badge variant="outline">{log.retry_count}</Badge>
                          )}
                        </td>
                        <td className="p-4">
                          {log.status === 'failed' && (
                            <Button 
                              size="sm" 
                              variant="outline"
                              onClick={() => retryMessage(log.message_id)}
                            >
                              <Send className="h-4 w-4 mr-1" />
                              Retry
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sync" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Synchronization Jobs</h2>
              <p className="text-gray-600">Data synchronization between servers</p>
            </div>
            <Button onClick={fetchCommunicationData} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>

          <div className="grid gap-6">
            {syncJobs.map((job) => (
              <Card key={job.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`rounded-full p-2 ${getStatusColor(job.status)} text-white`}>
                        {getStatusIcon(job.status)}
                      </div>
                      <div>
                        <h3 className="font-medium">{job.sync_type.replace('_', ' ')}</h3>
                        <p className="text-sm text-gray-600">
                          {job.source_server_id} → {job.target_server_id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <Badge className={`${getStatusColor(job.status)} text-white`}>
                        {job.status.replace('_', ' ')}
                      </Badge>
                      {job.status === 'in_progress' && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => cancelSyncJob(job.id)}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Created:</span>
                      <p className="text-gray-600">{formatTimestamp(job.created_at)}</p>
                    </div>
                    {job.started_at && (
                      <div>
                        <span className="font-medium">Started:</span>
                        <p className="text-gray-600">{formatTimestamp(job.started_at)}</p>
                      </div>
                    )}
                    {job.completed_at && (
                      <div>
                        <span className="font-medium">Completed:</span>
                        <p className="text-gray-600">{formatTimestamp(job.completed_at)}</p>
                      </div>
                    )}
                    {job.error_message && (
                      <div className="col-span-full">
                        <span className="font-medium text-red-600">Error:</span>
                        <p className="text-red-600">{job.error_message}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="servers" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Server Health</h2>
              <p className="text-gray-600">Network endpoint status and latency</p>
            </div>
            <Button onClick={fetchCommunicationData} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {serverEndpoints.map((server) => (
              <Card key={server.server_id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{server.server_name}</CardTitle>
                    <Badge className={`${getStatusColor(server.status)} text-white`}>
                      {getStatusIcon(server.status)}
                      <span className="ml-1">{server.status}</span>
                    </Badge>
                  </div>
                  <CardDescription>
                    {server.server_type === 'client' ? 'Client Server' : 'Supplier Server'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm font-medium">Server ID:</span>
                      <span className="text-sm text-gray-600">{server.server_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm font-medium">API URL:</span>
                      <span className="text-sm text-gray-600 font-mono">{server.api_url}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm font-medium">Latency:</span>
                      <span className={`text-sm ${
                        server.latency < 100 ? 'text-green-600' : 
                        server.latency < 500 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {formatLatency(server.latency)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm font-medium">Last Heartbeat:</span>
                      <span className="text-sm text-gray-600">
                        {formatTimestamp(server.last_heartbeat)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CommunicationMonitoring;