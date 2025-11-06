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
  Shield, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  Users,
  Server,
  Key,
  Globe,
  Zap,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  DollarSign,
  Activity
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface RateLimitRule {
  id: string;
  name: string;
  type: 'global' | 'api-key' | 'ip' | 'user' | 'endpoint';
  enabled: boolean;
  limits: {
    perMinute: number;
    perHour: number;
    perDay: number;
    perMonth: number;
  };
  scope: {
    apiKeys?: string[];
    ips?: string[];
    users?: string[];
    endpoints?: string[];
    paths?: string[];
  };
  burstLimit?: number;
  costPerRequest?: number;
  priority: number;
  strategy: 'fixed' | 'sliding' | 'token-bucket';
  description: string;
}

interface QuotaSettings {
  dailyBudget?: number;
  monthlyBudget?: number;
  alerting: {
    enabled: boolean;
    thresholds: {
      warning: number; // percentage
      critical: number; // percentage
    };
    email?: string[];
  };
  enforcement: {
    mode: 'warn' | 'block' | 'upgrade-required';
    gracePeriod: number; // minutes
  };
}

interface RateLimitStats {
  totalRequests: number;
  blockedRequests: number;
  averageRate: number;
  peakRate: number;
  costToday: number;
  costThisMonth: number;
  mostRestrictedEndpoints: Array<{
    endpoint: string;
    blockCount: number;
    blockRate: number;
  }>;
  topBlockedIPs: Array<{
    ip: string;
    blockCount: number;
    blockRate: number;
  }>;
}

const RateLimitingConfig: React.FC = () => {
  const [rules, setRules] = useState<RateLimitRule[]>([]);
  const [quotaSettings, setQuotaSettings] = useState<QuotaSettings>({
    alerting: {
      enabled: true,
      thresholds: { warning: 80, critical: 95 }
    },
    enforcement: {
      mode: 'block',
      gracePeriod: 15
    }
  });
  const [stats, setStats] = useState<RateLimitStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedRule, setSelectedRule] = useState<RateLimitRule | null>(null);
  const [newRule, setNewRule] = useState({
    name: '',
    type: 'api-key' as RateLimitRule['type'],
    limits: { perMinute: 100, perHour: 5000, perDay: 100000, perMonth: 3000000 },
    scope: {} as RateLimitRule['scope'],
    burstLimit: 200,
    costPerRequest: 0.001,
    priority: 1,
    strategy: 'fixed' as RateLimitRule['strategy'],
    description: ''
  });
  const { toast } = useToast();

  useEffect(() => {
    loadConfiguration();
    loadStats();
  }, []);

  const loadConfiguration = async () => {
    try {
      const [rulesResponse, quotaResponse] = await Promise.all([
        fetch('/api/proxy/rate-limits/rules'),
        fetch('/api/proxy/rate-limits/quota')
      ]);
      
      if (rulesResponse.ok) {
        const rulesData = await rulesResponse.json();
        setRules(rulesData);
      }
      
      if (quotaResponse.ok) {
        const quotaData = await quotaResponse.json();
        setQuotaSettings(quotaData);
      }
    } catch (error) {
      console.error('Failed to load rate limiting configuration:', error);
      toast({
        title: 'Error',
        description: 'Failed to load configuration',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/proxy/rate-limits/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to load rate limit stats:', error);
    }
  };

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/proxy/rate-limits/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules, quotaSettings })
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Rate limiting configuration saved successfully'
        });
        loadStats(); // Refresh stats after saving
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

  const createRule = async () => {
    try {
      const response = await fetch('/api/proxy/rate-limits/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newRule)
      });
      
      if (response.ok) {
        const rule = await response.json();
        setRules(prev => [rule, ...prev]);
        setShowCreateDialog(false);
        resetNewRuleForm();
        toast({
          title: 'Success',
          description: 'Rate limit rule created successfully'
        });
      } else {
        throw new Error('Failed to create rule');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create rule',
        variant: 'destructive'
      });
    }
  };

  const updateRule = async (ruleId: string, updates: Partial<RateLimitRule>) => {
    try {
      const response = await fetch(`/api/proxy/rate-limits/rules/${ruleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (response.ok) {
        setRules(prev => prev.map(rule => 
          rule.id === ruleId ? { ...rule, ...updates } : rule
        ));
        toast({
          title: 'Success',
          description: 'Rule updated successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update rule',
        variant: 'destructive'
      });
    }
  };

  const deleteRule = async (ruleId: string) => {
    try {
      const response = await fetch(`/api/proxy/rate-limits/rules/${ruleId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setRules(prev => prev.filter(rule => rule.id !== ruleId));
        toast({
          title: 'Success',
          description: 'Rule deleted successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete rule',
        variant: 'destructive'
      });
    }
  };

  const resetNewRuleForm = () => {
    setNewRule({
      name: '',
      type: 'api-key',
      limits: { perMinute: 100, perHour: 5000, perDay: 100000, perMonth: 3000000 },
      scope: {},
      burstLimit: 200,
      costPerRequest: 0.001,
      priority: 1,
      strategy: 'fixed',
      description: ''
    });
  };

  const getTypeIcon = (type: string) => {
    const icons = {
      global: Globe,
      'api-key': Key,
      ip: Server,
      user: Users,
      endpoint: Activity
    };
    const Icon = icons[type] || Globe;
    return <Icon className="h-4 w-4" />;
  };

  const getStrategyBadge = (strategy: string) => {
    const variants: Record<string, 'default' | 'secondary'> = {
      'fixed': 'default',
      'sliding': 'secondary',
      'token-bucket': 'secondary'
    };
    return <Badge variant={variants[strategy] || 'secondary'} className="capitalize">{strategy}</Badge>;
  };

  const getBlockRateColor = (rate: number) => {
    if (rate >= 50) return 'text-red-500';
    if (rate >= 20) return 'text-yellow-500';
    return 'text-green-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading rate limiting configuration...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Rate Limiting & Quotas</h1>
          <p className="text-muted-foreground">Configure rate limits, quotas, and cost controls</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={loadStats}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Stats
          </Button>
          <Button onClick={saveConfiguration} disabled={saving}>
            {saving ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Shield className="h-4 w-4 mr-2" />
            )}
            Save Configuration
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalRequests.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                {stats.blockedRequests.toLocaleString()} blocked
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Block Rate</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {((stats.blockedRequests / stats.totalRequests) * 100).toFixed(2)}%
              </div>
              <Progress value={(stats.blockedRequests / stats.totalRequests) * 100} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Peak Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.peakRate.toLocaleString()}/min</div>
              <p className="text-xs text-muted-foreground">
                Avg: {stats.averageRate.toLocaleString()}/min
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cost Today</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${stats.costToday.toFixed(2)}</div>
              <p className="text-xs text-muted-foreground">
                Month: ${stats.costThisMonth.toFixed(2)}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Configuration Tabs */}
      <Tabs defaultValue="rules" className="space-y-4">
        <TabsList>
          <TabsTrigger value="rules">Rate Limit Rules</TabsTrigger>
          <TabsTrigger value="quota">Quota Settings</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="enforcement">Enforcement</TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Rate Limit Rules</h3>
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Zap className="h-4 w-4 mr-2" />
                  Create Rule
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Rate Limit Rule</DialogTitle>
                  <DialogDescription>
                    Define rate limiting rules and quota restrictions
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="ruleName">Rule Name</Label>
                      <Input
                        id="ruleName"
                        value={newRule.name}
                        onChange={(e) => setNewRule(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="API Key Rate Limit"
                      />
                    </div>
                    <div>
                      <Label htmlFor="ruleType">Rule Type</Label>
                      <Select 
                        value={newRule.type}
                        onValueChange={(value: any) => setNewRule(prev => ({ ...prev, type: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="global">Global</SelectItem>
                          <SelectItem value="api-key">API Key</SelectItem>
                          <SelectItem value="ip">IP Address</SelectItem>
                          <SelectItem value="user">User</SelectItem>
                          <SelectItem value="endpoint">Endpoint</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-4 gap-2">
                    <div>
                      <Label htmlFor="perMinute">Per Minute</Label>
                      <Input
                        id="perMinute"
                        type="number"
                        value={newRule.limits.perMinute}
                        onChange={(e) => setNewRule(prev => ({ 
                          ...prev, 
                          limits: { ...prev.limits, perMinute: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="perHour">Per Hour</Label>
                      <Input
                        id="perHour"
                        type="number"
                        value={newRule.limits.perHour}
                        onChange={(e) => setNewRule(prev => ({ 
                          ...prev, 
                          limits: { ...prev.limits, perHour: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="perDay">Per Day</Label>
                      <Input
                        id="perDay"
                        type="number"
                        value={newRule.limits.perDay}
                        onChange={(e) => setNewRule(prev => ({ 
                          ...prev, 
                          limits: { ...prev.limits, perDay: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="perMonth">Per Month</Label>
                      <Input
                        id="perMonth"
                        type="number"
                        value={newRule.limits.perMonth}
                        onChange={(e) => setNewRule(prev => ({ 
                          ...prev, 
                          limits: { ...prev.limits, perMonth: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="burstLimit">Burst Limit</Label>
                      <Input
                        id="burstLimit"
                        type="number"
                        value={newRule.burstLimit}
                        onChange={(e) => setNewRule(prev => ({ ...prev, burstLimit: parseInt(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="costPerRequest">Cost Per Request ($)</Label>
                      <Input
                        id="costPerRequest"
                        type="number"
                        step="0.001"
                        value={newRule.costPerRequest}
                        onChange={(e) => setNewRule(prev => ({ ...prev, costPerRequest: parseFloat(e.target.value) }))}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="strategy">Rate Limiting Strategy</Label>
                    <Select 
                      value={newRule.strategy}
                      onValueChange={(value: any) => setNewRule(prev => ({ ...prev, strategy: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fixed">Fixed Window</SelectItem>
                        <SelectItem value="sliding">Sliding Window</SelectItem>
                        <SelectItem value="token-bucket">Token Bucket</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={newRule.description}
                      onChange={(e) => setNewRule(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Rule description"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                  <Button onClick={createRule}>Create Rule</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-2">
            {rules.map((rule) => (
              <Card key={rule.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        {getTypeIcon(rule.type)}
                        <h4 className="font-semibold">{rule.name}</h4>
                        <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        {getStrategyBadge(rule.strategy)}
                        <span className="text-sm text-muted-foreground">Priority: {rule.priority}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
                      
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Per Minute</p>
                          <p className="font-semibold">{rule.limits.perMinute.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Per Hour</p>
                          <p className="font-semibold">{rule.limits.perHour.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Per Day</p>
                          <p className="font-semibold">{rule.limits.perDay.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Cost/Request</p>
                          <p className="font-semibold">${rule.costPerRequest?.toFixed(3)}</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={rule.enabled}
                        onCheckedChange={(checked) => updateRule(rule.id, { enabled: checked })}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedRule(rule)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteRule(rule.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="quota" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Quota & Budget Settings</CardTitle>
              <CardDescription>
                Configure usage quotas, budgets, and alerting thresholds
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="dailyBudget">Daily Budget ($)</Label>
                  <Input
                    id="dailyBudget"
                    type="number"
                    value={quotaSettings.dailyBudget || ''}
                    onChange={(e) => setQuotaSettings(prev => ({ 
                      ...prev, 
                      dailyBudget: e.target.value ? parseFloat(e.target.value) : undefined
                    }))}
                    placeholder="1000.00"
                  />
                </div>
                <div>
                  <Label htmlFor="monthlyBudget">Monthly Budget ($)</Label>
                  <Input
                    id="monthlyBudget"
                    type="number"
                    value={quotaSettings.monthlyBudget || ''}
                    onChange={(e) => setQuotaSettings(prev => ({ 
                      ...prev, 
                      monthlyBudget: e.target.value ? parseFloat(e.target.value) : undefined
                    }))}
                    placeholder="25000.00"
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-semibold mb-3">Alerting Configuration</h4>
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4" />
                    <span className="text-sm font-medium">Enable Budget Alerts</span>
                    <Switch
                      checked={quotaSettings.alerting.enabled}
                      onCheckedChange={(checked) => setQuotaSettings(prev => ({ 
                        ...prev, 
                        alerting: { ...prev.alerting, enabled: checked }
                      }))}
                    />
                  </div>
                  
                  {quotaSettings.alerting.enabled && (
                    <div className="grid grid-cols-2 gap-4 ml-6">
                      <div>
                        <Label htmlFor="warningThreshold">Warning Threshold (%)</Label>
                        <Input
                          id="warningThreshold"
                          type="number"
                          value={quotaSettings.alerting.thresholds.warning}
                          onChange={(e) => setQuotaSettings(prev => ({ 
                            ...prev, 
                            alerting: { 
                              ...prev.alerting, 
                              thresholds: { 
                                ...prev.alerting.thresholds, 
                                warning: parseInt(e.target.value) 
                              }
                            }
                          }))}
                        />
                      </div>
                      <div>
                        <Label htmlFor="criticalThreshold">Critical Threshold (%)</Label>
                        <Input
                          id="criticalThreshold"
                          type="number"
                          value={quotaSettings.alerting.thresholds.critical}
                          onChange={(e) => setQuotaSettings(prev => ({ 
                            ...prev, 
                            alerting: { 
                              ...prev.alerting, 
                              thresholds: { 
                                ...prev.alerting.thresholds, 
                                critical: parseInt(e.target.value) 
                              }
                            }
                          }))}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-semibold mb-3">Enforcement Policy</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="enforcementMode">Enforcement Mode</Label>
                    <Select
                      value={quotaSettings.enforcement.mode}
                      onValueChange={(value: any) => setQuotaSettings(prev => ({ 
                        ...prev, 
                        enforcement: { ...prev.enforcement, mode: value }
                      }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="warn">Warn Only</SelectItem>
                        <SelectItem value="block">Block Requests</SelectItem>
                        <SelectItem value="upgrade-required">Require Upgrade</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="gracePeriod">Grace Period (minutes)</Label>
                    <Input
                      id="gracePeriod"
                      type="number"
                      value={quotaSettings.enforcement.gracePeriod}
                      onChange={(e) => setQuotaSettings(prev => ({ 
                        ...prev, 
                        enforcement: { ...prev.enforcement, gracePeriod: parseInt(e.target.value) }
                      }))}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          {stats && (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Most Restricted Endpoints</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {stats.mostRestrictedEndpoints.map((endpoint, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded">
                        <span className="text-sm font-mono">{endpoint.endpoint}</span>
                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-semibold ${getBlockRateColor(endpoint.blockRate)}`}>
                            {endpoint.blockRate.toFixed(1)}%
                          </span>
                          <Badge variant="outline">{endpoint.blockCount}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Top Blocked IPs</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {stats.topBlockedIPs.map((ip, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded">
                        <span className="text-sm font-mono">{ip.ip}</span>
                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-semibold ${getBlockRateColor(ip.blockRate)}`}>
                            {ip.blockRate.toFixed(1)}%
                          </span>
                          <Badge variant="outline">{ip.blockCount}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="enforcement" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active Enforcements</CardTitle>
              <CardDescription>
                Monitor current rate limit violations and enforcement actions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border rounded">
                  <div className="flex items-center space-x-3">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    <div>
                      <p className="font-semibold">API Key: sk-test-123456789</p>
                      <p className="text-sm text-muted-foreground">Daily limit exceeded (1,050 / 1,000)</p>
                    </div>
                  </div>
                  <Badge variant="destructive">Blocked</Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 border rounded">
                  <div className="flex items-center space-x-3">
                    <Clock className="h-4 w-4 text-yellow-500" />
                    <div>
                      <p className="font-semibold">IP: 192.168.1.100</p>
                      <p className="text-sm text-muted-foreground">Burst limit approaching (185 / 200)</p>
                    </div>
                  </div>
                  <Badge variant="secondary">Warning</Badge>
                </div>

                <div className="flex items-center justify-between p-3 border rounded">
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <div>
                      <p className="font-semibold">Budget Alert</p>
                      <p className="text-sm text-muted-foreground">Monthly budget at 78% ($19,500 / $25,000)</p>
                    </div>
                  </div>
                  <Badge variant="outline">Monitor</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RateLimitingConfig;