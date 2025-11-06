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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Zap, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  RefreshCw,
  Activity,
  Clock,
  TrendingDown,
  Settings,
  Play,
  Pause,
  BarChart3,
  History
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';

interface CircuitBreakerConfig {
  id: string;
  name: string;
  enabled: boolean;
  service: string;
  endpoint?: string;
  thresholds: {
    failureRate: number; // percentage
    responseTime: number; // milliseconds
    consecutiveFailures: number;
    halfOpenMaxCalls: number;
    timeout: number; // seconds
  };
  timeouts: {
    resetTimeout: number; // seconds
    failureTimeout: number; // seconds
  };
  strategy: 'failure-rate' | 'response-time' | 'consecutive-failures';
  description: string;
}

interface CircuitBreakerState {
  id: string;
  name: string;
  currentState: 'closed' | 'open' | 'half-open';
  lastStateChange: string;
  failureCount: number;
  successCount: number;
  totalCalls: number;
  currentFailureRate: number;
  averageResponseTime: number;
  nextAttemptTime?: string;
  statistics: {
    callsThisHour: number;
    failuresThisHour: number;
    averageResponseTime: number;
    lastFailure?: string;
    lastSuccess?: string;
  };
}

const CircuitBreakerMonitor: React.FC = () => {
  const [configs, setConfigs] = useState<CircuitBreakerConfig[]>([]);
  const [states, setStates] = useState<CircuitBreakerState[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [selectedBreaker, setSelectedBreaker] = useState<CircuitBreakerState | null>(null);
  const [newConfig, setNewConfig] = useState<CircuitBreakerConfig>({
    id: '',
    name: '',
    enabled: true,
    service: '',
    endpoint: '',
    thresholds: {
      failureRate: 50,
      responseTime: 5000,
      consecutiveFailures: 5,
      halfOpenMaxCalls: 3,
      timeout: 60
    },
    timeouts: {
      resetTimeout: 30,
      failureTimeout: 60
    },
    strategy: 'failure-rate',
    description: ''
  });
  const { toast } = useToast();
  
  const { connected, data: wsData } = useWebSocket('/ws/proxy/circuit-breaker');

  useEffect(() => {
    loadConfiguration();
    loadStates();
  }, []);

  useEffect(() => {
    if (wsData) {
      // Update circuit breaker states in real-time
      if (wsData.stateUpdate) {
        setStates(prev => 
          prev.map(state => 
            state.id === wsData.stateUpdate.id 
              ? { ...state, ...wsData.stateUpdate }
              : state
          )
        );
      }
    }
  }, [wsData]);

  const loadConfiguration = async () => {
    try {
      const response = await fetch('/api/proxy/circuit-breaker/configs');
      if (response.ok) {
        const data = await response.json();
        setConfigs(data);
      }
    } catch (error) {
      console.error('Failed to load circuit breaker configuration:', error);
      toast({
        title: 'Error',
        description: 'Failed to load configuration',
        variant: 'destructive'
      });
    }
  };

  const loadStates = async () => {
    try {
      const response = await fetch('/api/proxy/circuit-breaker/states');
      if (response.ok) {
        const data = await response.json();
        setStates(data);
      }
    } catch (error) {
      console.error('Failed to load circuit breaker states:', error);
      toast({
        title: 'Error',
        description: 'Failed to load states',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/proxy/circuit-breaker/configs', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configs)
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Circuit breaker configuration saved successfully'
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

  const createConfig = async () => {
    try {
      const response = await fetch('/api/proxy/circuit-breaker/configs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      
      if (response.ok) {
        const config = await response.json();
        setConfigs(prev => [config, ...prev]);
        setShowCreateDialog(false);
        resetNewConfigForm();
        toast({
          title: 'Success',
          description: 'Circuit breaker configuration created successfully'
        });
      } else {
        throw new Error('Failed to create configuration');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create configuration',
        variant: 'destructive'
      });
    }
  };

  const updateConfig = async (configId: string, updates: Partial<CircuitBreakerConfig>) => {
    try {
      const response = await fetch(`/api/proxy/circuit-breaker/configs/${configId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (response.ok) {
        setConfigs(prev => prev.map(config => 
          config.id === configId ? { ...config, ...updates } : config
        ));
        toast({
          title: 'Success',
          description: 'Configuration updated successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update configuration',
        variant: 'destructive'
      });
    }
  };

  const resetCircuitBreaker = async (circuitId: string) => {
    try {
      const response = await fetch(`/api/proxy/circuit-breaker/reset/${circuitId}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        loadStates();
        toast({
          title: 'Success',
          description: 'Circuit breaker reset successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to reset circuit breaker',
        variant: 'destructive'
      });
    }
  };

  const openCircuitBreaker = async (circuitId: string) => {
    try {
      const response = await fetch(`/api/proxy/circuit-breaker/open/${circuitId}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        loadStates();
        toast({
          title: 'Success',
          description: 'Circuit breaker opened manually'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to open circuit breaker',
        variant: 'destructive'
      });
    }
  };

  const resetNewConfigForm = () => {
    setNewConfig({
      id: '',
      name: '',
      enabled: true,
      service: '',
      endpoint: '',
      thresholds: {
        failureRate: 50,
        responseTime: 5000,
        consecutiveFailures: 5,
        halfOpenMaxCalls: 3,
        timeout: 60
      },
      timeouts: {
        resetTimeout: 30,
        failureTimeout: 60
      },
      strategy: 'failure-rate',
      description: ''
    });
  };

  const getStateBadge = (state: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary'> = {
      closed: 'default',
      open: 'destructive',
      'half-open': 'secondary'
    };
    const colors = {
      closed: 'text-green-600',
      open: 'text-red-600',
      'half-open': 'text-yellow-600'
    };
    const icons = {
      closed: CheckCircle,
      open: XCircle,
      'half-open': AlertTriangle
    };
    const Icon = icons[state] || AlertTriangle;
    
    return (
      <Badge variant={variants[state] || 'secondary'} className="flex items-center space-x-1">
        <Icon className="h-3 w-3" />
        <span className="capitalize">{state}</span>
      </Badge>
    );
  };

  const getStateColor = (state: string) => {
    const colors = {
      closed: 'text-green-600',
      open: 'text-red-600',
      'half-open': 'text-yellow-600'
    };
    return colors[state] || 'text-gray-600';
  };

  const getFailureRateColor = (rate: number) => {
    if (rate >= 50) return 'text-red-500';
    if (rate >= 25) return 'text-yellow-500';
    return 'text-green-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading circuit breaker states...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Circuit Breaker Monitor</h1>
          <p className="text-muted-foreground">Monitor and configure circuit breaker states</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={connected ? 'default' : 'destructive'}>
            {connected ? 'Live' : 'Offline'}
          </Badge>
          <Button variant="outline" onClick={loadStates}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={saveConfiguration} disabled={saving}>
            {saving ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Settings className="h-4 w-4 mr-2" />
            )}
            Save Config
          </Button>
        </div>
      </div>

      {/* Overall Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Circuits</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{states.filter(s => s.currentState === 'closed').length}</div>
            <p className="text-xs text-muted-foreground">
              {states.length} total circuits
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Circuits</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{states.filter(s => s.currentState === 'open').length}</div>
            <p className="text-xs text-muted-foreground">
              Tripped circuits
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Half-Open Circuits</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{states.filter(s => s.currentState === 'half-open').length}</div>
            <p className="text-xs text-muted-foreground">
              Recovery testing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Failure Rate</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {states.length > 0 
                ? (states.reduce((sum, s) => sum + s.currentFailureRate, 0) / states.length).toFixed(1)
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              Across all circuits
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="states" className="space-y-4">
        <TabsList>
          <TabsTrigger value="states">Circuit States</TabsTrigger>
          <TabsTrigger value="configurations">Configurations</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="states" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Active Circuit Breakers</h3>
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Zap className="h-4 w-4 mr-2" />
                  Create Circuit
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Circuit Breaker Configuration</DialogTitle>
                  <DialogDescription>
                    Configure a new circuit breaker for service protection
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="configName">Name</Label>
                      <Input
                        id="configName"
                        value={newConfig.name}
                        onChange={(e) => setNewConfig(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="User Service Circuit"
                      />
                    </div>
                    <div>
                      <Label htmlFor="serviceName">Service</Label>
                      <Input
                        id="serviceName"
                        value={newConfig.service}
                        onChange={(e) => setNewConfig(prev => ({ ...prev, service: e.target.value }))}
                        placeholder="user-service"
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="endpoint">Endpoint (optional)</Label>
                    <Input
                      id="endpoint"
                      value={newConfig.endpoint}
                      onChange={(e) => setNewConfig(prev => ({ ...prev, endpoint: e.target.value }))}
                      placeholder="/api/users/*"
                    />
                  </div>

                  <div>
                    <Label htmlFor="strategy">Trigger Strategy</Label>
                    <Select
                      value={newConfig.strategy}
                      onValueChange={(value: any) => setNewConfig(prev => ({ ...prev, strategy: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="failure-rate">Failure Rate</SelectItem>
                        <SelectItem value="response-time">Response Time</SelectItem>
                        <SelectItem value="consecutive-failures">Consecutive Failures</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="failureRate">Failure Rate (%)</Label>
                      <Input
                        id="failureRate"
                        type="number"
                        value={newConfig.thresholds.failureRate}
                        onChange={(e) => setNewConfig(prev => ({ 
                          ...prev, 
                          thresholds: { ...prev.thresholds, failureRate: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="responseTime">Response Time (ms)</Label>
                      <Input
                        id="responseTime"
                        type="number"
                        value={newConfig.thresholds.responseTime}
                        onChange={(e) => setNewConfig(prev => ({ 
                          ...prev, 
                          thresholds: { ...prev.thresholds, responseTime: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="consecutiveFailures">Consecutive Failures</Label>
                      <Input
                        id="consecutiveFailures"
                        type="number"
                        value={newConfig.thresholds.consecutiveFailures}
                        onChange={(e) => setNewConfig(prev => ({ 
                          ...prev, 
                          thresholds: { ...prev.thresholds, consecutiveFailures: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="timeout">Timeout (seconds)</Label>
                      <Input
                        id="timeout"
                        type="number"
                        value={newConfig.thresholds.timeout}
                        onChange={(e) => setNewConfig(prev => ({ 
                          ...prev, 
                          thresholds: { ...prev.thresholds, timeout: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="resetTimeout">Reset Timeout (seconds)</Label>
                      <Input
                        id="resetTimeout"
                        type="number"
                        value={newConfig.timeouts.resetTimeout}
                        onChange={(e) => setNewConfig(prev => ({ 
                          ...prev, 
                          timeouts: { ...prev.timeouts, resetTimeout: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={newConfig.description}
                      onChange={(e) => setNewConfig(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Protection for user authentication service"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                  <Button onClick={createConfig}>Create Circuit</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-3">
            {states.map((state) => (
              <Card key={state.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-semibold">{state.name}</h4>
                        {getStateBadge(state.currentState)}
                        {state.currentState === 'half-open' && state.nextAttemptTime && (
                          <span className="text-sm text-muted-foreground">
                            Next attempt: {new Date(state.nextAttemptTime).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        Service: {state.service} • Last state change: {new Date(state.lastStateChange).toLocaleString()}
                      </p>
                      
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Total Calls</p>
                          <p className="font-semibold">{state.totalCalls.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Failure Rate</p>
                          <p className={`font-semibold ${getFailureRateColor(state.currentFailureRate)}`}>
                            {state.currentFailureRate.toFixed(1)}%
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Avg Response Time</p>
                          <p className="font-semibold">{state.averageResponseTime}ms</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Calls This Hour</p>
                          <p className="font-semibold">{state.statistics.callsThisHour}</p>
                        </div>
                      </div>

                      <div className="mt-3">
                        <p className="text-sm text-muted-foreground mb-1">Failure Progress</p>
                        <div className="flex items-center space-x-2">
                          <Progress value={(state.failureCount / state.totalCalls) * 100} className="flex-1" />
                          <span className="text-sm font-semibold">
                            {state.failureCount}/{state.totalCalls}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2 ml-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedBreaker(state);
                          setShowHistoryDialog(true);
                        }}
                      >
                        <History className="h-4 w-4 mr-1" />
                        History
                      </Button>
                      
                      {state.currentState === 'open' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => resetCircuitBreaker(state.id)}
                        >
                          <RefreshCw className="h-4 w-4 mr-1" />
                          Reset
                        </Button>
                      )}
                      
                      {state.currentState === 'closed' && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => openCircuitBreaker(state.id)}
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Open
                        </Button>
                      )}
                      
                      {state.currentState === 'half-open' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openCircuitBreaker(state.id)}
                        >
                          <Pause className="h-4 w-4 mr-1" />
                          Close
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="configurations" className="space-y-4">
          <div className="space-y-3">
            {configs.map((config) => (
              <Card key={config.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-semibold">{config.name}</h4>
                        <Badge variant={config.enabled ? 'default' : 'secondary'}>
                          {config.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        <Badge variant="outline" className="capitalize">
                          {config.strategy.replace('-', ' ')}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{config.description}</p>
                      
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Failure Rate</p>
                          <p className="font-semibold">{config.thresholds.failureRate}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Response Time</p>
                          <p className="font-semibold">{config.thresholds.responseTime}ms</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Timeout</p>
                          <p className="font-semibold">{config.thresholds.timeout}s</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={config.enabled}
                        onCheckedChange={(checked) => updateConfig(config.id, { enabled: checked })}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {/* Edit configuration */}}
                      >
                        Edit
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Circuit State Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Closed Circuits</span>
                    <div className="flex items-center space-x-2">
                      <Progress value={60} className="w-20" />
                      <span className="text-sm font-semibold text-green-600">60%</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Open Circuits</span>
                    <div className="flex items-center space-x-2">
                      <Progress value={25} className="w-20" />
                      <span className="text-sm font-semibold text-red-600">25%</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Half-Open Circuits</span>
                    <div className="flex items-center space-x-2">
                      <Progress value={15} className="w-20" />
                      <span className="text-sm font-semibold text-yellow-600">15%</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Performance Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 flex items-center justify-center text-muted-foreground">
                  Performance chart would be displayed here
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>State Transition History</CardTitle>
              <CardDescription>
                View the state transition history for circuit breakers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {selectedBreaker ? (
                  <div>
                    <h4 className="font-semibold mb-3">{selectedBreaker.name} - Recent History</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center space-x-2">
                          <XCircle className="h-4 w-4 text-red-500" />
                          <span className="text-sm">Circuit opened</span>
                        </div>
                        <span className="text-xs text-muted-foreground">2 minutes ago</span>
                      </div>
                      <div className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center space-x-2">
                          <AlertTriangle className="h-4 w-4 text-yellow-500" />
                          <span className="text-sm">Failure threshold exceeded</span>
                        </div>
                        <span className="text-xs text-muted-foreground">5 minutes ago</span>
                      </div>
                      <div className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm">Circuit closed</span>
                        </div>
                        <span className="text-xs text-muted-foreground">1 hour ago</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Select a circuit breaker from the States tab to view its history.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* History Dialog */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>State Transition History</DialogTitle>
            <DialogDescription>
              Historical state transitions for {selectedBreaker?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2 border rounded">
              <div className="flex items-center space-x-2">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm">Circuit opened - Failure rate exceeded</span>
              </div>
              <span className="text-xs text-muted-foreground">2 minutes ago</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CircuitBreakerMonitor;