import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { 
  Shield, 
  AlertTriangle, 
  Lock, 
  Unlock,
  MapPin,
  Clock,
  Activity,
  Ban,
  CheckCircle,
  XCircle,
  Eye,
  Globe,
  Zap,
  RefreshCw,
  Plus,
  Trash2,
  Filter,
  Search,
  TrendingUp
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';

interface SecurityPolicy {
  id: string;
  name: string;
  enabled: boolean;
  type: 'ip-whitelist' | 'ip-blacklist' | 'rate-limit' | 'rate-limit-advanced' | 'custom';
  rules: Array<{
    id: string;
    pattern: string;
    description: string;
    action: 'allow' | 'deny' | 'monitor' | 'rate-limit';
    weight: number;
  }>;
  priority: number;
  description: string;
}

interface SecurityEvent {
  id: string;
  timestamp: string;
  type: 'authentication-failure' | 'rate-limit-exceeded' | 'suspicious-activity' | 'ip-blocked' | 'security-policy-violation' | 'ddos-attempt';
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: {
    ip: string;
    userAgent?: string;
    userId?: string;
    apiKey?: string;
  };
  details: {
    message: string;
    endpoint?: string;
    method?: string;
    payload?: any;
    riskScore: number;
  };
  resolved: boolean;
  resolvedAt?: string;
  resolvedBy?: string;
}

interface ThreatDetection {
  id: string;
  type: 'ddos' | 'brute-force' | 'sql-injection' | 'xss' | 'suspicious-pattern' | 'anomalous-behavior';
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  description: string;
  detectedAt: string;
  blocked: boolean;
  confidence: number;
  indicators: string[];
  mitigation: string;
}

const SecurityManagement: React.FC = () => {
  const [policies, setPolicies] = useState<SecurityPolicy[]>([]);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [threats, setThreats] = useState<ThreatDetection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showThreatDialog, setShowThreatDialog] = useState(false);
  const [selectedThreat, setSelectedThreat] = useState<ThreatDetection | null>(null);
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    type: 'ip-whitelist' as SecurityPolicy['type'],
    enabled: true,
    rules: [] as SecurityPolicy['rules'],
    priority: 1,
    description: ''
  });
  const [eventFilters, setEventFilters] = useState({
    severity: 'all',
    type: 'all',
    resolved: 'all',
    timeRange: '24h'
  });
  const { toast } = useToast();
  
  const { connected, data: wsData } = useWebSocket('/ws/proxy/security');

  useEffect(() => {
    loadSecurityData();
  }, []);

  useEffect(() => {
    if (wsData) {
      // Update security events and threats in real-time
      if (wsData.newEvent) {
        setEvents(prev => [wsData.newEvent, ...prev.slice(0, 99)]); // Keep last 100 events
      }
      if (wsData.newThreat) {
        setThreats(prev => [wsData.newThreat, ...prev.slice(0, 49)]); // Keep last 50 threats
      }
    }
  }, [wsData]);

  const loadSecurityData = async () => {
    try {
      const [policiesResponse, eventsResponse, threatsResponse] = await Promise.all([
        fetch('/api/proxy/security/policies'),
        fetch(`/api/proxy/security/events?filters=${JSON.stringify(eventFilters)}`),
        fetch('/api/proxy/security/threats')
      ]);
      
      if (policiesResponse.ok) {
        const policiesData = await policiesResponse.json();
        setPolicies(policiesData);
      }
      
      if (eventsResponse.ok) {
        const eventsData = await eventsResponse.json();
        setEvents(eventsData);
      }
      
      if (threatsResponse.ok) {
        const threatsData = await threatsResponse.json();
        setThreats(threatsData);
      }
    } catch (error) {
      console.error('Failed to load security data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load security data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const createPolicy = async () => {
    try {
      const response = await fetch('/api/proxy/security/policies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPolicy)
      });
      
      if (response.ok) {
        const policy = await response.json();
        setPolicies(prev => [policy, ...prev]);
        setShowCreateDialog(false);
        resetNewPolicyForm();
        toast({
          title: 'Success',
          description: 'Security policy created successfully'
        });
      } else {
        throw new Error('Failed to create policy');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create policy',
        variant: 'destructive'
      });
    }
  };

  const updatePolicy = async (policyId: string, updates: Partial<SecurityPolicy>) => {
    try {
      const response = await fetch(`/api/proxy/security/policies/${policyId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (response.ok) {
        setPolicies(prev => prev.map(policy => 
          policy.id === policyId ? { ...policy, ...updates } : policy
        ));
        toast({
          title: 'Success',
          description: 'Policy updated successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update policy',
        variant: 'destructive'
      });
    }
  };

  const deletePolicy = async (policyId: string) => {
    try {
      const response = await fetch(`/api/proxy/security/policies/${policyId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setPolicies(prev => prev.filter(policy => policy.id !== policyId));
        toast({
          title: 'Success',
          description: 'Policy deleted successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete policy',
        variant: 'destructive'
      });
    }
  };

  const resolveEvent = async (eventId: string) => {
    try {
      const response = await fetch(`/api/proxy/security/events/${eventId}/resolve`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setEvents(prev => prev.map(event => 
          event.id === eventId 
            ? { ...event, resolved: true, resolvedAt: new Date().toISOString() }
            : event
        ));
        toast({
          title: 'Success',
          description: 'Event resolved successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to resolve event',
        variant: 'destructive'
      });
    }
  };

  const blockIP = async (ip: string, reason: string) => {
    try {
      const response = await fetch('/api/proxy/security/block-ip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip, reason })
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: `IP address ${ip} has been blocked`
        });
        loadSecurityData(); // Refresh data
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to block IP address',
        variant: 'destructive'
      });
    }
  };

  const unblockIP = async (ip: string) => {
    try {
      const response = await fetch(`/api/proxy/security/unblock-ip/${ip}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: `IP address ${ip} has been unblocked`
        });
        loadSecurityData(); // Refresh data
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to unblock IP address',
        variant: 'destructive'
      });
    }
  };

  const addIPRule = (policyId: string, pattern: string, action: string) => {
    const newRule = {
      id: `rule-${Date.now()}`,
      pattern,
      description: `IP rule for ${pattern}`,
      action: action as 'allow' | 'deny' | 'monitor' | 'rate-limit',
      weight: 1
    };
    
    setPolicies(prev => prev.map(policy => 
      policy.id === policyId 
        ? { ...policy, rules: [...policy.rules, newRule] }
        : policy
    ));
  };

  const resetNewPolicyForm = () => {
    setNewPolicy({
      name: '',
      type: 'ip-whitelist',
      enabled: true,
      rules: [],
      priority: 1,
      description: ''
    });
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
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      low: 'default',
      medium: 'secondary',
      high: 'destructive',
      critical: 'destructive'
    };
    return <Badge variant={variants[severity] || 'secondary'} className="capitalize">{severity}</Badge>;
  };

  const getEventIcon = (type: string) => {
    const icons = {
      'authentication-failure': Lock,
      'rate-limit-exceeded': Zap,
      'suspicious-activity': Eye,
      'ip-blocked': Ban,
      'security-policy-violation': Shield,
      'ddos-attack': Activity
    };
    const Icon = icons[type] || AlertTriangle;
    return <Icon className="h-4 w-4" />;
  };

  const getTypeBadge = (type: string) => {
    const displayNames: Record<string, string> = {
      'ip-whitelist': 'IP Whitelist',
      'ip-blacklist': 'IP Blacklist',
      'rate-limit': 'Rate Limit',
      'rate-limit-advanced': 'Advanced Rate Limit',
      'custom': 'Custom'
    };
    return <Badge variant="outline">{displayNames[type] || type}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading security data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Security Management</h1>
          <p className="text-muted-foreground">Monitor and manage proxy security policies and threats</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={connected ? 'default' : 'destructive'}>
            {connected ? 'Live' : 'Offline'}
          </Badge>
          <Button variant="outline" onClick={loadSecurityData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Policy
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create Security Policy</DialogTitle>
                <DialogDescription>
                  Define security rules and access controls
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="policyName">Policy Name</Label>
                    <Input
                      id="policyName"
                      value={newPolicy.name}
                      onChange={(e) => setNewPolicy(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Block Suspicious IPs"
                    />
                  </div>
                  <div>
                    <Label htmlFor="policyType">Policy Type</Label>
                    <Select 
                      value={newPolicy.type}
                      onValueChange={(value: any) => setNewPolicy(prev => ({ ...prev, type: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ip-whitelist">IP Whitelist</SelectItem>
                        <SelectItem value="ip-blacklist">IP Blacklist</SelectItem>
                        <SelectItem value="rate-limit">Rate Limit</SelectItem>
                        <SelectItem value="rate-limit-advanced">Advanced Rate Limit</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="policyDescription">Description</Label>
                  <Textarea
                    id="policyDescription"
                    value={newPolicy.description}
                    onChange={(e) => setNewPolicy(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Block requests from known suspicious IP ranges"
                  />
                </div>

                <div>
                  <Label>Enabled</Label>
                  <div className="flex items-center space-x-2 mt-1">
                    <Switch
                      checked={newPolicy.enabled}
                      onCheckedChange={(checked) => setNewPolicy(prev => ({ ...prev, enabled: checked }))}
                    />
                    <span className="text-sm">{newPolicy.enabled ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={createPolicy}>Create Policy</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Security Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Policies</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{policies.filter(p => p.enabled).length}</div>
            <p className="text-xs text-muted-foreground">
              {policies.length} total policies
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Security Events</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{events.filter(e => !e.resolved).length}</div>
            <p className="text-xs text-muted-foreground">
              {events.filter(e => e.severity === 'critical').length} critical
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Threats Detected</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{threats.length}</div>
            <p className="text-xs text-muted-foreground">
              {threats.filter(t => t.severity === 'critical').length} critical threats
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Blocked IPs</CardTitle>
            <Ban className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">
              +3 this week
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="policies" className="space-y-4">
        <TabsList>
          <TabsTrigger value="policies">Security Policies</TabsTrigger>
          <TabsTrigger value="events">Security Events</TabsTrigger>
          <TabsTrigger value="threats">Threat Detection</TabsTrigger>
          <TabsTrigger value="ip-management">IP Management</TabsTrigger>
        </TabsList>

        <TabsContent value="policies" className="space-y-4">
          <div className="space-y-3">
            {policies.map((policy) => (
              <Card key={policy.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-semibold">{policy.name}</h4>
                        {getTypeBadge(policy.type)}
                        <Badge variant={policy.enabled ? 'default' : 'secondary'}>
                          {policy.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        <span className="text-sm text-muted-foreground">Priority: {policy.priority}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{policy.description}</p>
                      
                      <div className="flex items-center space-x-4 text-sm">
                        <span className="text-muted-foreground">Rules: {policy.rules.length}</span>
                        <span className="text-muted-foreground">Type: {policy.type.replace('-', ' ')}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={policy.enabled}
                        onCheckedChange={(checked) => updatePolicy(policy.id, { enabled: checked })}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {/* Edit policy */}}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deletePolicy(policy.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {policy.rules.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="space-y-2">
                        {policy.rules.slice(0, 3).map((rule) => (
                          <div key={rule.id} className="flex items-center justify-between text-sm">
                            <div className="flex items-center space-x-2">
                              <code className="bg-gray-100 px-2 py-1 rounded">{rule.pattern}</code>
                              <Badge variant="outline" className="capitalize">{rule.action}</Badge>
                            </div>
                            <span className="text-muted-foreground">{rule.description}</span>
                          </div>
                        ))}
                        {policy.rules.length > 3 && (
                          <p className="text-sm text-muted-foreground">
                            +{policy.rules.length - 3} more rules
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="events" className="space-y-4">
          <div className="flex items-center space-x-4 mb-4">
            <Select value={eventFilters.severity} onValueChange={(value) => setEventFilters(prev => ({ ...prev, severity: value }))}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>

            <Select value={eventFilters.resolved} onValueChange={(value) => setEventFilters(prev => ({ ...prev, resolved: value }))}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Events</SelectItem>
                <SelectItem value="unresolved">Unresolved</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>

            <Button variant="outline" onClick={loadSecurityData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Apply Filters
            </Button>
          </div>

          <div className="space-y-3">
            {events
              .filter(event => 
                (eventFilters.severity === 'all' || event.severity === eventFilters.severity) &&
                (eventFilters.resolved === 'all' || 
                 (eventFilters.resolved === 'resolved' && event.resolved) ||
                 (eventFilters.resolved === 'unresolved' && !event.resolved))
              )
              .map((event) => (
              <Card key={event.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getEventIcon(event.type)}
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="font-semibold">{event.details.message}</p>
                          {getSeverityBadge(event.severity)}
                          {event.resolved && <Badge variant="outline">Resolved</Badge>}
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                          <span className="flex items-center space-x-1">
                            <MapPin className="h-3 w-3" />
                            <span>{event.source.ip}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{new Date(event.timestamp).toLocaleString()}</span>
                          </span>
                          <span className="capitalize">{event.type.replace('-', ' ')}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {!event.resolved && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => blockIP(event.source.ip, `Security event: ${event.details.message}`)}
                          >
                            <Ban className="h-4 w-4 mr-1" />
                            Block IP
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => resolveEvent(event.id)}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Resolve
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                  
                  {event.details.endpoint && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="flex items-center space-x-2 text-sm">
                        <Badge variant="outline">{event.details.method}</Badge>
                        <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                          {event.details.endpoint}
                        </code>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="threats" className="space-y-4">
          <div className="space-y-3">
            {threats.map((threat) => (
              <Card key={threat.id} className={threat.severity === 'critical' ? 'border-red-200' : ''}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <AlertTriangle className={`h-5 w-5 ${getSeverityColor(threat.severity)}`} />
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="font-semibold">{threat.type.replace('-', ' ')}</p>
                          {getSeverityBadge(threat.severity)}
                          {threat.blocked && <Badge variant="destructive">Blocked</Badge>}
                          <span className="text-sm text-muted-foreground">
                            Confidence: {(threat.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{threat.description}</p>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                          <span>Source: {threat.source}</span>
                          <span>Detected: {new Date(threat.detectedAt).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedThreat(threat);
                          setShowThreatDialog(true);
                        }}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        Details
                      </Button>
                      {!threat.blocked && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => blockIP(threat.source, `Threat detected: ${threat.type}`)}
                        >
                          <Ban className="h-4 w-4 mr-1" />
                          Block
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="ip-management" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>IP Address Management</CardTitle>
              <CardDescription>
                Manage blocked and whitelisted IP addresses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold mb-2">Recently Blocked IPs</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 border rounded">
                        <span className="font-mono text-sm">192.168.1.100</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant="destructive">Suspicious Activity</Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => unblockIP('192.168.1.100')}
                          >
                            <Unlock className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <div className="flex items-center justify-between p-2 border rounded">
                        <span className="font-mono text-sm">10.0.0.50</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant="destructive">Rate Limit Exceeded</Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => unblockIP('10.0.0.50')}
                          >
                            <Unlock className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="font-semibold mb-2">Whitelisted IPs</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 border rounded">
                        <span className="font-mono text-sm">203.0.113.0</span>
                        <Badge variant="outline">Trusted Partner</Badge>
                      </div>
                      <div className="flex items-center justify-between p-2 border rounded">
                        <span className="font-mono text-sm">198.51.100.0</span>
                        <Badge variant="outline">Internal Service</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Threat Details Dialog */}
      <Dialog open={showThreatDialog} onOpenChange={setShowThreatDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Threat Details</DialogTitle>
            <DialogDescription>
              Detailed information about the detected threat
            </DialogDescription>
          </DialogHeader>
          {selectedThreat && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Type</Label>
                  <p className="font-semibold capitalize">{selectedThreat.type.replace('-', ' ')}</p>
                </div>
                <div>
                  <Label>Severity</Label>
                  <div className="flex items-center space-x-2">
                    {getSeverityBadge(selectedThreat.severity)}
                  </div>
                </div>
                <div>
                  <Label>Confidence</Label>
                  <p className="font-semibold">{(selectedThreat.confidence * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <Label>Source</Label>
                  <p className="font-semibold">{selectedThreat.source}</p>
                </div>
              </div>
              
              <div>
                <Label>Description</Label>
                <p className="text-sm">{selectedThreat.description}</p>
              </div>
              
              <div>
                <Label>Indicators</Label>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {selectedThreat.indicators.map((indicator, index) => (
                    <li key={index}>{indicator}</li>
                  ))}
                </ul>
              </div>
              
              <div>
                <Label>Mitigation</Label>
                <p className="text-sm">{selectedThreat.mitigation}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SecurityManagement;