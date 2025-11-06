import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Server, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Settings,
  TrendingUp,
  Activity,
  Globe,
  Shield,
  Zap,
  Database
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface LoadBalancerConfig {
  algorithm: 'round-robin' | 'least-connections' | 'weighted' | 'ip-hash';
  healthCheck: {
    enabled: boolean;
    interval: number;
    timeout: number;
    path: string;
    expectedStatus: number;
    retries: number;
  };
  sticky: {
    enabled: boolean;
    cookieName: string;
    ttl: number;
  };
  failover: {
    enabled: boolean;
    primaryServers: string[];
    backupServers: string[];
    failoverTimeout: number;
  };
  advanced: {
    maxConnections: number;
    connectionTimeout: number;
    keepAlive: boolean;
    compression: boolean;
    bufferSize: number;
  };
}

interface BackendServer {
  id: string;
  name: string;
  url: string;
  weight: number;
  health: 'healthy' | 'unhealthy' | 'unknown';
  status: 'active' | 'inactive' | 'draining';
  currentConnections: number;
  totalRequests: number;
  errorRate: number;
  responseTime: number;
  lastHealthCheck: string;
}

const LoadBalancerConfigComponent: React.FC = () => {
  const [config, setConfig] = useState<LoadBalancerConfig>({
    algorithm: 'round-robin',
    healthCheck: {
      enabled: true,
      interval: 30,
      timeout: 5,
      path: '/health',
      expectedStatus: 200,
      retries: 3
    },
    sticky: {
      enabled: false,
      cookieName: 'lb_session',
      ttl: 3600
    },
    failover: {
      enabled: true,
      primaryServers: [],
      backupServers: [],
      failoverTimeout: 10
    },
    advanced: {
      maxConnections: 1000,
      connectionTimeout: 30,
      keepAlive: true,
      compression: true,
      bufferSize: 4096
    }
  });

  const [servers, setServers] = useState<BackendServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newServer, setNewServer] = useState({
    name: '',
    url: '',
    weight: 1
  });
  const [showAddServer, setShowAddServer] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadConfiguration();
    loadServers();
  }, []);

  const loadConfiguration = async () => {
    try {
      const response = await fetch('/api/proxy/load-balancer/config');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to load load balancer configuration:', error);
      toast({
        title: 'Error',
        description: 'Failed to load configuration',
        variant: 'destructive'
      });
    }
  };

  const loadServers = async () => {
    try {
      const response = await fetch('/api/proxy/load-balancer/servers');
      if (response.ok) {
        const data = await response.json();
        setServers(data);
      }
    } catch (error) {
      console.error('Failed to load backend servers:', error);
      toast({
        title: 'Error',
        description: 'Failed to load backend servers',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/proxy/load-balancer/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Load balancer configuration saved successfully'
        });
      } else {
        throw new Error('Failed to save configuration');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save configuration',
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  };

  const addServer = async () => {
    try {
      const response = await fetch('/api/proxy/load-balancer/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newServer)
      });
      
      if (response.ok) {
        const server = await response.json();
        setServers(prev => [...prev, server]);
        setNewServer({ name: '', url: '', weight: 1 });
        setShowAddServer(false);
        toast({
          title: 'Success',
          description: 'Server added successfully'
        });
      } else {
        throw new Error('Failed to add server');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add server',
        variant: 'destructive'
      });
    }
  };

  const removeServer = async (serverId: string) => {
    try {
      const response = await fetch(`/api/proxy/load-balancer/servers/${serverId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setServers(prev => prev.filter(s => s.id !== serverId));
        toast({
          title: 'Success',
          description: 'Server removed successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to remove server',
        variant: 'destructive'
      });
    }
  };

  const updateServerWeight = async (serverId: string, weight: number) => {
    try {
      const response = await fetch(`/api/proxy/load-balancer/servers/${serverId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight })
      });
      
      if (response.ok) {
        setServers(prev => prev.map(s => 
          s.id === serverId ? { ...s, weight } : s
        ));
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update server weight',
        variant: 'destructive'
      });
    }
  };

  const getHealthBadge = (health: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary'> = {
      healthy: 'default',
      unhealthy: 'destructive',
      unknown: 'secondary'
    };
    const icons = {
      healthy: CheckCircle,
      unhealthy: XCircle,
      unknown: AlertTriangle
    };
    const Icon = icons[health] || AlertTriangle;
    
    return (
      <Badge variant={variants[health] || 'secondary'} className="flex items-center space-x-1">
        <Icon className="h-3 w-3" />
        <span className="capitalize">{health}</span>
      </Badge>
    );
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary'> = {
      active: 'default',
      inactive: 'secondary',
      draining: 'secondary'
    };
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading load balancer configuration...</span>
      </div>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-5 w-5" />
              <span>Load Balancer Configuration</span>
            </CardTitle>
            <CardDescription>
              Configure load balancing algorithms and backend server management
            </CardDescription>
          </div>
          <Button onClick={saveConfiguration} disabled={saving}>
            {saving ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Settings className="h-4 w-4 mr-2" />
            )}
            Save Configuration
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="algorithm" className="space-y-4">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="algorithm">Algorithm</TabsTrigger>
            <TabsTrigger value="health">Health Check</TabsTrigger>
            <TabsTrigger value="servers">Servers</TabsTrigger>
            <TabsTrigger value="failover">Failover</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="algorithm" className="space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="algorithm">Load Balancing Algorithm</Label>
                <Select
                  value={config.algorithm}
                  onValueChange={(value: any) => setConfig(prev => ({ ...prev, algorithm: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="round-robin">Round Robin</SelectItem>
                    <SelectItem value="least-connections">Least Connections</SelectItem>
                    <SelectItem value="weighted">Weighted Round Robin</SelectItem>
                    <SelectItem value="ip-hash">IP Hash</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose how requests are distributed across backend servers
                </p>
              </div>

              {config.algorithm === 'weighted' && (
                <div>
                  <Label>Server Weights</Label>
                  <p className="text-sm text-muted-foreground">
                    Configure server weights in the Servers tab
                  </p>
                </div>
              )}

              {config.algorithm === 'ip-hash' && (
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4" />
                    <span className="text-sm font-medium">Sticky Sessions</span>
                    <Switch
                      checked={config.sticky.enabled}
                      onCheckedChange={(checked) => setConfig(prev => ({ 
                        ...prev, 
                        sticky: { ...prev.sticky, enabled: checked }
                      }))}
                    />
                  </div>
                  {config.sticky.enabled && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="cookieName">Cookie Name</Label>
                        <Input
                          id="cookieName"
                          value={config.sticky.cookieName}
                          onChange={(e) => setConfig(prev => ({ 
                            ...prev, 
                            sticky: { ...prev.sticky, cookieName: e.target.value }
                          }))}
                        />
                      </div>
                      <div>
                        <Label htmlFor="ttl">TTL (seconds)</Label>
                        <Input
                          id="ttl"
                          type="number"
                          value={config.sticky.ttl}
                          onChange={(e) => setConfig(prev => ({ 
                            ...prev, 
                            sticky: { ...prev.sticky, ttl: parseInt(e.target.value) }
                          }))}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="health" className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Activity className="h-4 w-4" />
                <span className="text-sm font-medium">Health Check Configuration</span>
                <Switch
                  checked={config.healthCheck.enabled}
                  onCheckedChange={(checked) => setConfig(prev => ({ 
                    ...prev, 
                    healthCheck: { ...prev.healthCheck, enabled: checked }
                  }))}
                />
              </div>

              {config.healthCheck.enabled && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="interval">Check Interval (seconds)</Label>
                    <Input
                      id="interval"
                      type="number"
                      value={config.healthCheck.interval}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        healthCheck: { ...prev.healthCheck, interval: parseInt(e.target.value) }
                      }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="timeout">Timeout (seconds)</Label>
                    <Input
                      id="timeout"
                      type="number"
                      value={config.healthCheck.timeout}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        healthCheck: { ...prev.healthCheck, timeout: parseInt(e.target.value) }
                      }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="path">Health Check Path</Label>
                    <Input
                      id="path"
                      value={config.healthCheck.path}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        healthCheck: { ...prev.healthCheck, path: e.target.value }
                      }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="expectedStatus">Expected Status Code</Label>
                    <Input
                      id="expectedStatus"
                      type="number"
                      value={config.healthCheck.expectedStatus}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        healthCheck: { ...prev.healthCheck, expectedStatus: parseInt(e.target.value) }
                      }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="retries">Max Retries</Label>
                    <Input
                      id="retries"
                      type="number"
                      value={config.healthCheck.retries}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        healthCheck: { ...prev.healthCheck, retries: parseInt(e.target.value) }
                      }))}
                    />
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="servers" className="space-y-4">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Backend Servers</h3>
                <Button onClick={() => setShowAddServer(true)}>
                  <Server className="h-4 w-4 mr-2" />
                  Add Server
                </Button>
              </div>

              {showAddServer && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Add Backend Server</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <Label htmlFor="serverName">Name</Label>
                        <Input
                          id="serverName"
                          value={newServer.name}
                          onChange={(e) => setNewServer(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="server-01"
                        />
                      </div>
                      <div>
                        <Label htmlFor="serverUrl">URL</Label>
                        <Input
                          id="serverUrl"
                          value={newServer.url}
                          onChange={(e) => setNewServer(prev => ({ ...prev, url: e.target.value }))}
                          placeholder="http://192.168.1.100:8080"
                        />
                      </div>
                      <div>
                        <Label htmlFor="serverWeight">Weight</Label>
                        <Input
                          id="serverWeight"
                          type="number"
                          value={newServer.weight}
                          onChange={(e) => setNewServer(prev => ({ ...prev, weight: parseInt(e.target.value) }))}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-2 mt-4">
                      <Button variant="outline" onClick={() => setShowAddServer(false)}>Cancel</Button>
                      <Button onClick={addServer}>Add Server</Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="space-y-2">
                {servers.map((server) => (
                  <Card key={server.id}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <div>
                              <h4 className="font-semibold">{server.name}</h4>
                              <p className="text-sm text-muted-foreground">{server.url}</p>
                            </div>
                            {getHealthBadge(server.health)}
                            {getStatusBadge(server.status)}
                          </div>
                          <div className="grid grid-cols-4 gap-4 mt-3 text-sm">
                            <div>
                              <p className="text-muted-foreground">Weight</p>
                              <p className="font-semibold">{server.weight}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">Connections</p>
                              <p className="font-semibold">{server.currentConnections}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">Total Requests</p>
                              <p className="font-semibold">{server.totalRequests.toLocaleString()}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">Error Rate</p>
                              <p className="font-semibold">{server.errorRate}%</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex items-center space-x-1">
                            <Label htmlFor={`weight-${server.id}`} className="text-xs">Weight</Label>
                            <Input
                              id={`weight-${server.id}`}
                              type="number"
                              value={server.weight}
                              onChange={(e) => updateServerWeight(server.id, parseInt(e.target.value))}
                              className="w-16 h-8"
                            />
                          </div>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => removeServer(server.id)}
                          >
                            Remove
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="failover" className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Zap className="h-4 w-4" />
                <span className="text-sm font-medium">Failover Configuration</span>
                <Switch
                  checked={config.failover.enabled}
                  onCheckedChange={(checked) => setConfig(prev => ({ 
                    ...prev, 
                    failover: { ...prev.failover, enabled: checked }
                  }))}
                />
              </div>

              {config.failover.enabled && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="failoverTimeout">Failover Timeout (seconds)</Label>
                    <Input
                      id="failoverTimeout"
                      type="number"
                      value={config.failover.failoverTimeout}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        failover: { ...prev.failover, failoverTimeout: parseInt(e.target.value) }
                      }))}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Primary Servers</Label>
                      <p className="text-sm text-muted-foreground">
                        {config.failover.primaryServers.length} configured
                      </p>
                    </div>
                    <div>
                      <Label>Backup Servers</Label>
                      <p className="text-sm text-muted-foreground">
                        {config.failover.backupServers.length} configured
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-4">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="maxConnections">Max Connections</Label>
                  <Input
                    id="maxConnections"
                    type="number"
                    value={config.advanced.maxConnections}
                    onChange={(e) => setConfig(prev => ({ 
                      ...prev, 
                      advanced: { ...prev.advanced, maxConnections: parseInt(e.target.value) }
                    }))}
                  />
                </div>
                <div>
                  <Label htmlFor="connectionTimeout">Connection Timeout (seconds)</Label>
                  <Input
                    id="connectionTimeout"
                    type="number"
                    value={config.advanced.connectionTimeout}
                    onChange={(e) => setConfig(prev => ({ 
                      ...prev, 
                      advanced: { ...prev.advanced, connectionTimeout: parseInt(e.target.value) }
                    }))}
                  />
                </div>
                <div>
                  <Label htmlFor="bufferSize">Buffer Size (bytes)</Label>
                  <Input
                    id="bufferSize"
                    type="number"
                    value={config.advanced.bufferSize}
                    onChange={(e) => setConfig(prev => ({ 
                      ...prev, 
                      advanced: { ...prev.advanced, bufferSize: parseInt(e.target.value) }
                    }))}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Database className="h-4 w-4" />
                  <span className="text-sm font-medium">Keep Alive Connections</span>
                  <Switch
                    checked={config.advanced.keepAlive}
                    onCheckedChange={(checked) => setConfig(prev => ({ 
                      ...prev, 
                      advanced: { ...prev.advanced, keepAlive: checked }
                    }))}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Globe className="h-4 w-4" />
                  <span className="text-sm font-medium">Response Compression</span>
                  <Switch
                    checked={config.advanced.compression}
                    onCheckedChange={(checked) => setConfig(prev => ({ 
                      ...prev, 
                      advanced: { ...prev.advanced, compression: checked }
                    }))}
                  />
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default LoadBalancerConfigComponent;