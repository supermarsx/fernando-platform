"""
Balance Alerts Component

Balance monitoring and alert configuration dashboard.
"""

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  Bell,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  TrendingDown,
  TrendingUp,
  Settings,
  Plus,
  Edit,
  Trash2,
  Eye,
  RefreshCw,
  Users,
  Building,
  Shield,
  Mail,
  MessageSquare,
  Smartphone,
  Webhook,
  Volume2,
  VolumeX,
  Calendar,
  Target,
  Zap,
  Activity
} from 'lucide-react';

interface BalanceAlertsProps {
  userId: number;
  organizationId?: number;
}

interface AlertThreshold {
  id: number;
  name: string;
  type: 'low_balance' | 'high_spend' | 'usage_spike' | 'expiration_warning';
  threshold: number;
  unit: 'credits' | 'percentage' | 'hours';
  severity: 'low' | 'medium' | 'high' | 'critical';
  channels: ('email' | 'sms' | 'push' | 'webhook')[];
  isActive: boolean;
  createdAt: string;
  lastTriggered?: string;
  triggerCount: number;
}

interface AlertHistory {
  id: number;
  thresholdId: number;
  thresholdName: string;
  triggeredAt: string;
  currentValue: number;
  thresholdValue: number;
  status: 'active' | 'acknowledged' | 'resolved';
  message: string;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
}

interface AlertSettings {
  emailNotifications: boolean;
  smsNotifications: boolean;
  pushNotifications: boolean;
  webhookNotifications: boolean;
  quietHours: {
    enabled: boolean;
    start: string;
    end: string;
  };
  escalation: {
    enabled: boolean;
    delay: number; // minutes
    escalateTo: number[]; // user IDs
  };
}

interface BalanceStats {
  currentBalance: number;
  dailySpend: number;
  weeklySpend: number;
  monthlySpend: number;
  projectedBalance: number;
  burnRate: number;
  daysUntilZero: number;
  topSpender: string;
}

const BalanceAlerts: React.FC<BalanceAlertsProps> = ({ userId, organizationId }) => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('thresholds');
  const [showNewThreshold, setShowNewThreshold] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // Threshold form state
  const [thresholdForm, setThresholdForm] = useState({
    name: '',
    type: 'low_balance' as const,
    threshold: '',
    unit: 'credits' as const,
    severity: 'medium' as const,
    channels: [] as string[],
    isActive: true
  });

  const [thresholds, setThresholds] = useState<AlertThreshold[]>([]);
  const [alertHistory, setAlertHistory] = useState<AlertHistory[]>([]);
  const [settings, setSettings] = useState<AlertSettings | null>(null);
  const [stats, setStats] = useState<BalanceStats | null>(null);
  const [realTimeBalance, setRealTimeBalance] = useState<number>(0);

  useEffect(() => {
    loadAlertData();
    // Set up real-time balance updates
    const interval = setInterval(updateRealTimeBalance, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, [userId, organizationId]);

  const loadAlertData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadThresholds(),
        loadAlertHistory(),
        loadSettings(),
        loadBalanceStats()
      ]);
    } catch (error) {
      console.error('Error loading alert data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadThresholds = async () => {
    // Simulate API call - replace with actual API
    const mockThresholds: AlertThreshold[] = [
      {
        id: 1,
        name: 'Low Balance Warning',
        type: 'low_balance',
        threshold: 1000,
        unit: 'credits',
        severity: 'high',
        channels: ['email', 'push'],
        isActive: true,
        createdAt: '2024-01-10T09:00:00Z',
        lastTriggered: '2024-01-15T14:30:00Z',
        triggerCount: 3
      },
      {
        id: 2,
        name: 'Daily Spend Limit',
        type: 'high_spend',
        threshold: 500,
        unit: 'credits',
        severity: 'medium',
        channels: ['email'],
        isActive: true,
        createdAt: '2024-01-08T15:20:00Z',
        triggerCount: 1
      },
      {
        id: 3,
        name: 'Usage Spike Detection',
        type: 'usage_spike',
        threshold: 200,
        unit: 'percentage',
        severity: 'critical',
        channels: ['email', 'sms', 'push'],
        isActive: true,
        createdAt: '2024-01-05T11:15:00Z',
        triggerCount: 0
      }
    ];
    
    setThresholds(mockThresholds);
  };

  const loadAlertHistory = async () => {
    // Simulate API call - replace with actual API
    const mockHistory: AlertHistory[] = [
      {
        id: 1,
        thresholdId: 1,
        thresholdName: 'Low Balance Warning',
        triggeredAt: '2024-01-15T14:30:00Z',
        currentValue: 850,
        thresholdValue: 1000,
        status: 'active',
        message: 'Your balance has fallen below 1,000 credits'
      },
      {
        id: 2,
        thresholdId: 2,
        thresholdName: 'Daily Spend Limit',
        triggeredAt: '2024-01-14T18:45:00Z',
        currentValue: 520,
        thresholdValue: 500,
        status: 'resolved',
        message: 'Daily spending has exceeded the 500 credit limit',
        acknowledgedAt: '2024-01-14T19:00:00Z',
        acknowledgedBy: 'User'
      }
    ];
    
    setAlertHistory(mockHistory);
  };

  const loadSettings = async () => {
    // Simulate API call - replace with actual API
    const mockSettings: AlertSettings = {
      emailNotifications: true,
      smsNotifications: false,
      pushNotifications: true,
      webhookNotifications: false,
      quietHours: {
        enabled: true,
        start: '22:00',
        end: '08:00'
      },
      escalation: {
        enabled: true,
        delay: 60,
        escalateTo: [123, 456]
      }
    };
    
    setSettings(mockSettings);
  };

  const loadBalanceStats = async () => {
    // Simulate API call - replace with actual API
    const mockStats: BalanceStats = {
      currentBalance: 2450,
      dailySpend: 380,
      weeklySpend: 2100,
      monthlySpend: 8750,
      projectedBalance: 1850,
      burnRate: 285,
      daysUntilZero: 8.6,
      topSpender: 'GPT-4 API'
    };
    
    setStats(mockStats);
    setRealTimeBalance(mockStats.currentBalance);
  };

  const updateRealTimeBalance = async () => {
    // Simulate real-time balance update
    const change = (Math.random() - 0.5) * 100; // Random change between -50 and +50
    setRealTimeBalance(prev => Math.max(0, prev + change));
  };

  const handleThresholdSubmit = async () => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const newThreshold: AlertThreshold = {
        id: Date.now(),
        name: thresholdForm.name,
        type: thresholdForm.type,
        threshold: parseFloat(thresholdForm.threshold),
        unit: thresholdForm.unit,
        severity: thresholdForm.severity,
        channels: thresholdForm.channels as any,
        isActive: thresholdForm.isActive,
        createdAt: new Date().toISOString(),
        triggerCount: 0
      };
      
      setThresholds([newThreshold, ...thresholds]);
      setThresholdForm({
        name: '',
        type: 'low_balance',
        threshold: '',
        unit: 'credits',
        severity: 'medium',
        channels: [],
        isActive: true
      });
      setShowNewThreshold(false);
    } catch (error) {
      console.error('Error creating threshold:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleThresholdToggle = async (thresholdId: number, isActive: boolean) => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setThresholds(thresholds.map(threshold =>
        threshold.id === thresholdId
          ? { ...threshold, isActive }
          : threshold
      ));
    } catch (error) {
      console.error('Error updating threshold:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAlertAcknowledge = async (alertId: number) => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setAlertHistory(alertHistory.map(alert =>
        alert.id === alertId
          ? {
              ...alert,
              status: 'acknowledged' as const,
              acknowledgedAt: new Date().toISOString(),
              acknowledgedBy: 'Current User'
            }
          : alert
      ));
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'bg-blue-100 text-blue-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-red-100 text-red-800';
      case 'acknowledged': return 'bg-yellow-100 text-yellow-800';
      case 'resolved': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'email': return <Mail className="h-4 w-4" />;
      case 'sms': return <MessageSquare className="h-4 w-4" />;
      case 'push': return <Smartphone className="h-4 w-4" />;
      case 'webhook': return <Webhook className="h-4 w-4" />;
      default: return <Bell className="h-4 w-4" />;
    }
  };

  const renderThresholdsTab = () => (
    <div className="space-y-6">
      {/* Balance Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Current Balance</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{realTimeBalance.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                Last updated: {new Date().toLocaleTimeString()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Daily Burn Rate</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.dailySpend}</div>
              <p className="text-xs text-muted-foreground">
                Credits per day
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Days Until Zero</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.daysUntilZero.toFixed(1)}</div>
              <Progress value={(stats.daysUntilZero / 30) * 100} className="h-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Projected Balance</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.projectedBalance.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                In 7 days
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Thresholds Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Alert Thresholds</h3>
        <Button onClick={() => setShowNewThreshold(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Threshold
        </Button>
      </div>

      {/* Active Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle>Configured Thresholds</CardTitle>
          <CardDescription>
            Manage your balance alert thresholds and notification settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          {thresholds.length > 0 ? (
            <div className="space-y-4">
              {thresholds.map(threshold => (
                <div key={threshold.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-medium">{threshold.name}</h4>
                        <Badge className={getSeverityColor(threshold.severity)}>
                          {threshold.severity}
                        </Badge>
                        <Badge variant={threshold.isActive ? 'secondary' : 'outline'}>
                          {threshold.isActive ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span>Type: {threshold.type.replace('_', ' ')}</span>
                        <span>Threshold: {threshold.threshold} {threshold.unit}</span>
                        <span>Triggered: {threshold.triggerCount} times</span>
                        {threshold.lastTriggered && (
                          <span>
                            Last: {new Date(threshold.lastTriggered).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">Channels:</span>
                        {threshold.channels.map(channel => (
                          <div key={channel} className="flex items-center space-x-1">
                            {getChannelIcon(channel)}
                            <span className="text-xs capitalize">{channel}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={threshold.isActive}
                        onCheckedChange={(checked) => 
                          handleThresholdToggle(threshold.id, checked)
                        }
                      />
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No thresholds configured
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderActiveAlertsTab = () => (
    <div className="space-y-6">
      {/* Active Alerts Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Active Alerts</h3>
        <Button variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Active Alerts */}
      <div className="space-y-4">
        {alertHistory
          .filter(alert => alert.status === 'active')
          .map(alert => (
            <Alert key={alert.id} className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="flex justify-between items-start">
                  <div>
                    <strong>{alert.thresholdName}</strong>
                    <p className="text-sm mt-1">{alert.message}</p>
                    <div className="flex items-center space-x-4 text-xs text-muted-foreground mt-2">
                      <span>Current: {alert.currentValue}</span>
                      <span>Threshold: {alert.thresholdValue}</span>
                      <span>Triggered: {new Date(alert.triggeredAt).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className={getStatusColor(alert.status)}>
                      {alert.status}
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAlertAcknowledge(alert.id)}
                      disabled={loading}
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Acknowledge
                    </Button>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          ))}
        
        {alertHistory.filter(alert => alert.status === 'active').length === 0 && (
          <Card>
            <CardContent className="text-center py-8">
              <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
              <p className="text-muted-foreground">No active alerts</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Alert History */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Alert History</CardTitle>
          <CardDescription>
            History of all triggered alerts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Alert</TableHead>
                <TableHead>Triggered</TableHead>
                <TableHead>Values</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alertHistory.map(alert => (
                <TableRow key={alert.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{alert.thresholdName}</p>
                      <p className="text-sm text-muted-foreground">{alert.message}</p>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(alert.triggeredAt).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <div>Current: {alert.currentValue}</div>
                      <div>Threshold: {alert.thresholdValue}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(alert.status)}>
                      {alert.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                      {alert.status === 'active' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleAlertAcknowledge(alert.id)}
                          disabled={loading}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );

  const renderSettingsTab = () => (
    <div className="space-y-6">
      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Settings</CardTitle>
          <CardDescription>
            Configure how you receive balance alerts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {settings && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Mail className="h-4 w-4" />
                    <Label htmlFor="email-notifications">Email Notifications</Label>
                  </div>
                  <Switch
                    id="email-notifications"
                    checked={settings.emailNotifications}
                    onCheckedChange={(checked) => 
                      setSettings({...settings, emailNotifications: checked})
                    }
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <MessageSquare className="h-4 w-4" />
                    <Label htmlFor="sms-notifications">SMS Notifications</Label>
                  </div>
                  <Switch
                    id="sms-notifications"
                    checked={settings.smsNotifications}
                    onCheckedChange={(checked) => 
                      setSettings({...settings, smsNotifications: checked})
                    }
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Smartphone className="h-4 w-4" />
                    <Label htmlFor="push-notifications">Push Notifications</Label>
                  </div>
                  <Switch
                    id="push-notifications"
                    checked={settings.pushNotifications}
                    onCheckedChange={(checked) => 
                      setSettings({...settings, pushNotifications: checked})
                    }
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Webhook className="h-4 w-4" />
                    <Label htmlFor="webhook-notifications">Webhook Notifications</Label>
                  </div>
                  <Switch
                    id="webhook-notifications"
                    checked={settings.webhookNotifications}
                    onCheckedChange={(checked) => 
                      setSettings({...settings, webhookNotifications: checked})
                    }
                  />
                </div>
              </div>

              <Separator />

              {/* Quiet Hours */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Quiet Hours</Label>
                  <Switch
                    checked={settings.quietHours.enabled}
                    onCheckedChange={(checked) => 
                      setSettings({
                        ...settings,
                        quietHours: {...settings.quietHours, enabled: checked}
                      })
                    }
                  />
                </div>
                
                {settings.quietHours.enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="quiet-start">Start Time</Label>
                      <Input
                        id="quiet-start"
                        type="time"
                        value={settings.quietHours.start}
                        onChange={(e) => 
                          setSettings({
                            ...settings,
                            quietHours: {...settings.quietHours, start: e.target.value}
                          })
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor="quiet-end">End Time</Label>
                      <Input
                        id="quiet-end"
                        type="time"
                        value={settings.quietHours.end}
                        onChange={(e) => 
                          setSettings({
                            ...settings,
                            quietHours: {...settings.quietHours, end: e.target.value}
                          })
                        }
                      />
                    </div>
                  </div>
                )}
              </div>

              <Separator />

              {/* Escalation */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Escalation</Label>
                  <Switch
                    checked={settings.escalation.enabled}
                    onCheckedChange={(checked) => 
                      setSettings({
                        ...settings,
                        escalation: {...settings.escalation, enabled: checked}
                      })
                    }
                  />
                </div>
                
                {settings.escalation.enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="escalation-delay">Delay (minutes)</Label>
                      <Input
                        id="escalation-delay"
                        type="number"
                        value={settings.escalation.delay}
                        onChange={(e) => 
                          setSettings({
                            ...settings,
                            escalation: {
                              ...settings.escalation,
                              delay: parseInt(e.target.value)
                            }
                          })
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor="escalate-to">Escalate To (User IDs)</Label>
                      <Input
                        id="escalate-to"
                        value={settings.escalation.escalateTo.join(', ')}
                        onChange={(e) => 
                          setSettings({
                            ...settings,
                            escalation: {
                              ...settings.escalation,
                              escalateTo: e.target.value.split(',').map(id => parseInt(id.trim())).filter(Boolean)
                            }
                          })
                        }
                        placeholder="123, 456"
                      />
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
          
          <div className="flex justify-end">
            <Button disabled={loading}>
              <Settings className="h-4 w-4 mr-2" />
              Save Settings
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Balance Alerts</h1>
          <p className="text-muted-foreground">
            Monitor your balance and configure alert thresholds
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadAlertData}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Real-time Balance Indicator */}
      {stats && (
        <Alert className={
          realTimeBalance < 1000 ? 'border-red-200 bg-red-50' :
          realTimeBalance < 5000 ? 'border-yellow-200 bg-yellow-50' :
          'border-green-200 bg-green-50'
        }>
          <Activity className="h-4 w-4" />
          <AlertDescription>
            <div className="flex justify-between items-center">
              <div>
                <strong>Current Balance: {realTimeBalance.toLocaleString()} credits</strong>
                <p className="text-sm text-muted-foreground">
                  {realTimeBalance < 1000 ? 'Critical: Immediate action required' :
                   realTimeBalance < 5000 ? 'Low: Consider adding credits' :
                   'Healthy: Good balance level'}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                {realTimeBalance < 1000 ? (
                  <VolumeX className="h-4 w-4 text-red-500" />
                ) : (
                  <Volume2 className="h-4 w-4 text-green-500" />
                )}
                <Button size="sm" variant="outline">
                  Add Credits
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="thresholds">
            <Target className="h-4 w-4 mr-2" />
            Thresholds
          </TabsTrigger>
          <TabsTrigger value="active">
            <Bell className="h-4 w-4 mr-2" />
            Active Alerts
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="thresholds">
          {renderThresholdsTab()}
        </TabsContent>

        <TabsContent value="active">
          {renderActiveAlertsTab()}
        </TabsContent>

        <TabsContent value="settings">
          {renderSettingsTab()}
        </TabsContent>
      </Tabs>

      {/* New Threshold Dialog */}
      <Dialog open={showNewThreshold} onOpenChange={setShowNewThreshold}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>New Alert Threshold</DialogTitle>
            <DialogDescription>
              Create a new balance alert threshold
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Threshold Name</Label>
              <Input
                id="name"
                value={thresholdForm.name}
                onChange={(e) => setThresholdForm({...thresholdForm, name: e.target.value})}
                placeholder="e.g., Low Balance Warning"
              />
            </div>
            
            <div>
              <Label htmlFor="type">Alert Type</Label>
              <Select value={thresholdForm.type} onValueChange={(value: any) => 
                setThresholdForm({...thresholdForm, type: value})
              }>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low_balance">Low Balance</SelectItem>
                  <SelectItem value="high_spend">High Spend</SelectItem>
                  <SelectItem value="usage_spike">Usage Spike</SelectItem>
                  <SelectItem value="expiration_warning">Expiration Warning</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="threshold">Threshold Value</Label>
                <Input
                  id="threshold"
                  type="number"
                  value={thresholdForm.threshold}
                  onChange={(e) => setThresholdForm({...thresholdForm, threshold: e.target.value})}
                  placeholder="1000"
                />
              </div>
              <div>
                <Label htmlFor="unit">Unit</Label>
                <Select value={thresholdForm.unit} onValueChange={(value: any) => 
                  setThresholdForm({...thresholdForm, unit: value})
                }>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="credits">Credits</SelectItem>
                    <SelectItem value="percentage">Percentage</SelectItem>
                    <SelectItem value="hours">Hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label htmlFor="severity">Severity</Label>
              <Select value={thresholdForm.severity} onValueChange={(value: any) => 
                setThresholdForm({...thresholdForm, severity: value})
              }>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Notification Channels</Label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {['email', 'sms', 'push', 'webhook'].map(channel => (
                  <div key={channel} className="flex items-center space-x-2">
                    <Switch
                      checked={thresholdForm.channels.includes(channel)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setThresholdForm({
                            ...thresholdForm,
                            channels: [...thresholdForm.channels, channel]
                          });
                        } else {
                          setThresholdForm({
                            ...thresholdForm,
                            channels: thresholdForm.channels.filter(c => c !== channel)
                          });
                        }
                      }}
                    />
                    <Label className="text-sm capitalize">{channel}</Label>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Switch
                id="isActive"
                checked={thresholdForm.isActive}
                onCheckedChange={(checked) => 
                  setThresholdForm({...thresholdForm, isActive: checked})
                }
              />
              <Label htmlFor="isActive">Active</Label>
            </div>
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setShowNewThreshold(false)}>
                Cancel
              </Button>
              <Button onClick={handleThresholdSubmit} disabled={loading}>
                <Plus className="h-4 w-4 mr-2" />
                Create Threshold
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BalanceAlerts;