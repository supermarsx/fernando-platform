import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { 
  Key, 
  Plus, 
  Trash2, 
  Edit, 
  Eye, 
  EyeOff, 
  Copy, 
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  BarChart3,
  Shield,
  RefreshCw,
  Download
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ApiKey {
  id: string;
  name: string;
  key: string;
  masked: string;
  status: 'active' | 'inactive' | 'expired' | 'revoked';
  createdAt: string;
  lastUsed: string;
  expiresAt: string;
  permissions: string[];
  usage: {
    totalRequests: number;
    dailyLimit: number;
    monthlyLimit: number;
    currentDaily: number;
    currentMonthly: number;
    costThisMonth: number;
  };
  rateLimit: {
    requestsPerMinute: number;
    requestsPerHour: number;
    requestsPerDay: number;
  };
  ipWhitelist: string[];
  ipBlacklist: string[];
}

const ApiKeyManager: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState<ApiKey | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [newKey, setNewKey] = useState({
    name: '',
    permissions: [] as string[],
    dailyLimit: 1000,
    monthlyLimit: 30000,
    expiresInDays: 90,
    rateLimit: { perMinute: 100, perHour: 5000, perDay: 100000 },
    ipWhitelist: [] as string[],
    ipBlacklist: [] as string[]
  });
  const { toast } = useToast();

  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    try {
      const response = await fetch('/api/proxy/api-keys');
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error('Failed to load API keys:', error);
      toast({
        title: 'Error',
        description: 'Failed to load API keys',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const createApiKey = async () => {
    try {
      const response = await fetch('/api/proxy/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newKey)
      });
      
      if (response.ok) {
        const createdKey = await response.json();
        setApiKeys(prev => [createdKey, ...prev]);
        setShowCreateDialog(false);
        resetNewKeyForm();
        toast({
          title: 'Success',
          description: 'API key created successfully'
        });
      } else {
        throw new Error('Failed to create API key');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create API key',
        variant: 'destructive'
      });
    }
  };

  const revokeApiKey = async (keyId: string) => {
    try {
      const response = await fetch(`/api/proxy/api-keys/${keyId}/revoke`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setApiKeys(prev => prev.map(key => 
          key.id === keyId ? { ...key, status: 'revoked' as const } : key
        ));
        toast({
          title: 'Success',
          description: 'API key revoked successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to revoke API key',
        variant: 'destructive'
      });
    }
  };

  const rotateApiKey = async (keyId: string) => {
    try {
      const response = await fetch(`/api/proxy/api-keys/${keyId}/rotate`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const rotatedKey = await response.json();
        setApiKeys(prev => prev.map(key => 
          key.id === keyId ? { ...key, key: rotatedKey.key, masked: rotatedKey.masked } : key
        ));
        toast({
          title: 'Success',
          description: 'API key rotated successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to rotate API key',
        variant: 'destructive'
      });
    }
  };

  const toggleKeyVisibility = (keyId: string) => {
    const newVisible = new Set(visibleKeys);
    if (newVisible.has(keyId)) {
      newVisible.delete(keyId);
    } else {
      newVisible.add(keyId);
    }
    setVisibleKeys(newVisible);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: 'Copied',
        description: 'API key copied to clipboard'
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to copy to clipboard',
        variant: 'destructive'
      });
    }
  };

  const resetNewKeyForm = () => {
    setNewKey({
      name: '',
      permissions: [],
      dailyLimit: 1000,
      monthlyLimit: 30000,
      expiresInDays: 90,
      rateLimit: { perMinute: 100, perHour: 5000, perDay: 100000 },
      ipWhitelist: [],
      ipBlacklist: []
    });
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
      active: 'default',
      inactive: 'secondary',
      expired: 'destructive',
      revoked: 'destructive'
    };
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>;
  };

  const getUsagePercentage = (current: number, limit: number) => {
    return Math.min((current / limit) * 100, 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-500';
    if (percentage >= 75) return 'text-yellow-500';
    return 'text-green-500';
  };

  const exportUsageReport = async (keyId: string) => {
    try {
      const response = await fetch(`/api/proxy/api-keys/${keyId}/usage-report`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `api-key-${keyId}-usage-report.csv`;
      a.click();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to export usage report',
        variant: 'destructive'
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading API keys...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">API Key Management</h1>
          <p className="text-muted-foreground">Securely manage and monitor your API keys</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New API Key</DialogTitle>
              <DialogDescription>
                Configure and generate a new API key for your application
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Key Name</Label>
                  <Input
                    id="name"
                    value={newKey.name}
                    onChange={(e) => setNewKey(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="My Application API Key"
                  />
                </div>
                <div>
                  <Label htmlFor="expires">Expires In (Days)</Label>
                  <Select 
                    value={newKey.expiresInDays.toString()}
                    onValueChange={(value) => setNewKey(prev => ({ ...prev, expiresInDays: parseInt(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30">30 days</SelectItem>
                      <SelectItem value="90">90 days</SelectItem>
                      <SelectItem value="180">6 months</SelectItem>
                      <SelectItem value="365">1 year</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="dailyLimit">Daily Request Limit</Label>
                  <Input
                    id="dailyLimit"
                    type="number"
                    value={newKey.dailyLimit}
                    onChange={(e) => setNewKey(prev => ({ ...prev, dailyLimit: parseInt(e.target.value) }))}
                  />
                </div>
                <div>
                  <Label htmlFor="monthlyLimit">Monthly Request Limit</Label>
                  <Input
                    id="monthlyLimit"
                    type="number"
                    value={newKey.monthlyLimit}
                    onChange={(e) => setNewKey(prev => ({ ...prev, monthlyLimit: parseInt(e.target.value) }))}
                  />
                </div>
                <div>
                  <Label htmlFor="rpm">Requests/Minute</Label>
                  <Input
                    id="rpm"
                    type="number"
                    value={newKey.rateLimit.perMinute}
                    onChange={(e) => setNewKey(prev => ({ 
                      ...prev, 
                      rateLimit: { ...prev.rateLimit, perMinute: parseInt(e.target.value) }
                    }))}
                  />
                </div>
              </div>

              <div>
                <Label>Permissions</Label>
                <div className="grid grid-cols-3 gap-2 mt-2">
                  {['read', 'write', 'admin'].map(permission => (
                    <label key={permission} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={newKey.permissions.includes(permission)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNewKey(prev => ({ ...prev, permissions: [...prev.permissions, permission] }));
                          } else {
                            setNewKey(prev => ({ ...prev, permissions: prev.permissions.filter(p => p !== permission) }));
                          }
                        }}
                      />
                      <span className="capitalize">{permission}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={createApiKey}>Create Key</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* API Keys List */}
      <div className="grid gap-4">
        {apiKeys.map((apiKey) => (
          <Card key={apiKey.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center space-x-2">
                    <Key className="h-5 w-5" />
                    <span>{apiKey.name}</span>
                    {getStatusBadge(apiKey.status)}
                  </CardTitle>
                  <CardDescription>
                    Created: {new Date(apiKey.createdAt).toLocaleDateString()} • 
                    Expires: {new Date(apiKey.expiresAt).toLocaleDateString()}
                  </CardDescription>
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedKey(apiKey);
                      setShowKeyDialog(true);
                    }}
                  >
                    <BarChart3 className="h-4 w-4 mr-1" />
                    Analytics
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportUsageReport(apiKey.id)}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Export
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => rotateApiKey(apiKey.id)}
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Rotate
                  </Button>
                  {apiKey.status === 'active' && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => revokeApiKey(apiKey.id)}
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* API Key Display */}
                <div className="flex items-center space-x-2">
                  <code className="flex-1 bg-gray-100 p-2 rounded text-sm">
                    {visibleKeys.has(apiKey.id) ? apiKey.key : apiKey.masked}
                  </code>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleKeyVisibility(apiKey.id)}
                  >
                    {visibleKeys.has(apiKey.id) ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(apiKey.key)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>

                {/* Usage Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Daily Usage</p>
                    <div className="flex items-center space-x-2">
                      <Progress value={getUsagePercentage(apiKey.usage.currentDaily, apiKey.usage.dailyLimit)} className="flex-1" />
                      <span className={`text-sm font-semibold ${getUsageColor(getUsagePercentage(apiKey.usage.currentDaily, apiKey.usage.dailyLimit))}`}>
                        {apiKey.usage.currentDaily}/{apiKey.usage.dailyLimit}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Monthly Usage</p>
                    <div className="flex items-center space-x-2">
                      <Progress value={getUsagePercentage(apiKey.usage.currentMonthly, apiKey.usage.monthlyLimit)} className="flex-1" />
                      <span className={`text-sm font-semibold ${getUsageColor(getUsagePercentage(apiKey.usage.currentMonthly, apiKey.usage.monthlyLimit))}`}>
                        {apiKey.usage.currentMonthly}/{apiKey.usage.monthlyLimit}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Cost This Month</p>
                    <p className="text-lg font-semibold">${apiKey.usage.costThisMonth.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Last Used</p>
                    <p className="text-lg font-semibold">
                      {apiKey.lastUsed ? new Date(apiKey.lastUsed).toLocaleDateString() : 'Never'}
                    </p>
                  </div>
                </div>

                {/* Rate Limits */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-2">Rate Limits</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Per Minute</p>
                      <p className="font-semibold">{apiKey.rateLimit.requestsPerMinute}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Per Hour</p>
                      <p className="font-semibold">{apiKey.rateLimit.requestsPerHour.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Per Day</p>
                      <p className="font-semibold">{apiKey.rateLimit.requestsPerDay.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* API Key Analytics Dialog */}
      <Dialog open={showKeyDialog} onOpenChange={setShowKeyDialog}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>API Key Analytics: {selectedKey?.name}</DialogTitle>
            <DialogDescription>
              Detailed usage analytics and performance metrics
            </DialogDescription>
          </DialogHeader>
          {selectedKey && (
            <Tabs defaultValue="usage" className="mt-4">
              <TabsList>
                <TabsTrigger value="usage">Usage Patterns</TabsTrigger>
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="security">Security Events</TabsTrigger>
              </TabsList>
              
              <TabsContent value="usage" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Request Volume</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64 flex items-center justify-center text-muted-foreground">
                        Usage chart would be displayed here
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Geographic Distribution</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64 flex items-center justify-center text-muted-foreground">
                        Geographic distribution chart would be displayed here
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
              
              <TabsContent value="performance" className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Avg Response Time</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">234ms</p>
                      <p className="text-sm text-green-600">↓ 12% from last week</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Success Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">99.8%</p>
                      <p className="text-sm text-green-600">↑ 0.2% from last week</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Error Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">0.2%</p>
                      <p className="text-sm text-red-600">↑ 0.1% from last week</p>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
              
              <TabsContent value="security" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Security Events</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center space-x-2">
                          <Shield className="h-4 w-4 text-green-500" />
                          <span className="text-sm">Rate limit exceeded</span>
                        </div>
                        <span className="text-xs text-muted-foreground">2 hours ago</span>
                      </div>
                      <div className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm">Successful authentication</span>
                        </div>
                        <span className="text-xs text-muted-foreground">1 day ago</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApiKeyManager;