"""
Notification Preference Management Interface
React component for managing user notification preferences
"""

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { LoadingSpinner } from '../ui/loading-spinner';
import { useToast } from '../ui/use-toast';
import { api } from '../../lib/api';
import { Bell, Mail, MessageSquare, Smartphone, Globe, Shield, Settings, Save, RotateCcw, Info } from 'lucide-react';

interface NotificationPreferences {
  document_processing: {
    enabled: boolean;
    channels: string[];
    priority: string;
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    frequency: string;
    conditions: Record<string, any>;
  };
  verification: {
    enabled: boolean;
    channels: string[];
    priority: string;
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    frequency: string;
    conditions: Record<string, any>;
  };
  billing: {
    enabled: boolean;
    channels: string[];
    priority: string;
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    frequency: string;
    conditions: Record<string, any>;
  };
  security: {
    enabled: boolean;
    channels: string[];
    priority: string;
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    frequency: string;
    conditions: Record<string, any>;
  };
  system: {
    enabled: boolean;
    channels: string[];
    priority: string;
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    frequency: string;
    conditions: Record<string, any>;
  };
  global: {
    enabled_channels: string[];
    timezone: string;
    language: string;
    do_not_disturb: boolean;
    notification_sound: boolean;
    notification_badge: boolean;
    notification_history_days: number;
  };
}

interface ChannelConfig {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  enabled: boolean;
  settings: Record<string, any>;
}

const NOTIFICATION_TYPES = [
  {
    id: 'document_processing',
    name: 'Document Processing',
    description: 'Notifications about document upload, processing, and completion',
    icon: <MessageSquare className="w-5 h-5" />,
    color: 'bg-blue-500'
  },
  {
    id: 'verification',
    name: 'Verification Workflow',
    description: 'Notifications about document verification assignments and completion',
    icon: <Shield className="w-5 h-5" />,
    color: 'bg-green-500'
  },
  {
    id: 'billing',
    name: 'Billing & Payments',
    description: 'Notifications about payments, subscriptions, and billing',
    icon: <Settings className="w-5 h-5" />,
    color: 'bg-yellow-500'
  },
  {
    id: 'security',
    name: 'Security Alerts',
    description: 'Critical security notifications like login failures and suspicious activity',
    icon: <Shield className="w-5 h-5" />,
    color: 'bg-red-500'
  },
  {
    id: 'system',
    name: 'System Status',
    description: 'Notifications about system maintenance, status changes, and updates',
    icon: <Globe className="w-5 h-5" />,
    color: 'bg-purple-500'
  }
];

const CHANNELS: ChannelConfig[] = [
  {
    id: 'email',
    name: 'Email',
    icon: <Mail className="w-5 h-5" />,
    description: 'Receive notifications via email',
    enabled: true,
    settings: {
      frequency: 'immediate',
      digest: false
    }
  },
  {
    id: 'push',
    name: 'Push Notifications',
    icon: <Smartphone className="w-5 h-5" />,
    description: 'Receive push notifications on your device',
    enabled: true,
    settings: {
      sound: true,
      vibration: true,
      badge: true
    }
  },
  {
    id: 'sms',
    name: 'SMS',
    icon: <MessageSquare className="w-5 h-5" />,
    description: 'Receive notifications via text message',
    enabled: false,
    settings: {
      phone_number: '',
      verified: false
    }
  }
];

export function NotificationPreferencesManager() {
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedType, setSelectedType] = useState('document_processing');
  const [channels, setChannels] = useState<ChannelConfig[]>(CHANNELS);
  const [summary, setSummary] = useState<any>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const { toast } = useToast();

  // Load user preferences
  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const [prefsRes, summaryRes] = await Promise.all([
        api.get('/api/notifications/preferences/USER_ID'), // Replace with actual user ID
        api.get('/api/notifications/preferences/USER_ID/summary')
      ]);
      
      setPreferences(prefsRes.data);
      setSummary(summaryRes.data);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to load preferences:', error);
      toast({
        title: "Error",
        description: "Failed to load notification preferences",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const savePreferences = async () => {
    if (!preferences) return;

    try {
      setSaving(true);
      await api.put(`/api/notifications/preferences/USER_ID`, preferences); // Replace with actual user ID
      setHasChanges(false);
      
      // Reload summary
      const summaryRes = await api.get('/api/notifications/preferences/USER_ID/summary');
      setSummary(summaryRes.data);
      
      toast({
        title: "Success",
        description: "Notification preferences saved successfully"
      });
    } catch (error) {
      console.error('Failed to save preferences:', error);
      toast({
        title: "Error",
        description: "Failed to save notification preferences",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const resetPreferences = async () => {
    try {
      await api.post('/api/notifications/preferences/USER_ID/reset'); // Replace with actual user ID
      await loadPreferences();
      setResetDialogOpen(false);
      
      toast({
        title: "Success",
        description: "Preferences reset to defaults"
      });
    } catch (error) {
      console.error('Failed to reset preferences:', error);
      toast({
        title: "Error",
        description: "Failed to reset preferences",
        variant: "destructive"
      });
    }
  };

  const updatePreference = (type: string, updates: any) => {
    if (!preferences) return;
    
    setPreferences(prev => ({
      ...prev!,
      [type]: { ...prev![type], ...updates }
    }));
    setHasChanges(true);
  };

  const updateGlobalSetting = (key: string, value: any) => {
    if (!preferences) return;
    
    setPreferences(prev => ({
      ...prev!,
      global: { ...prev!.global, [key]: value }
    }));
    setHasChanges(true);
  };

  const updateChannelSetting = (channelId: string, key: string, value: any) => {
    setChannels(prev => prev.map(channel => 
      channel.id === channelId 
        ? { ...channel, settings: { ...channel.settings, [key]: value } }
        : channel
    ));
    setHasChanges(true);
  };

  const toggleChannelEnabled = (channelId: string, enabled: boolean) => {
    setChannels(prev => prev.map(channel => 
      channel.id === channelId ? { ...channel, enabled } : channel
    ));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!preferences) {
    return (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Failed to load notification preferences. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notification Preferences</h1>
          <p className="text-muted-foreground">
            Manage how and when you receive notifications
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          {hasChanges && (
            <Button
              variant="outline"
              onClick={() => loadPreferences()}
              disabled={saving}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset Changes
            </Button>
          )}
          
          <Button
            onClick={savePreferences}
            disabled={!hasChanges || saving}
          >
            {saving ? (
              <LoadingSpinner size="sm" className="mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Save Preferences
          </Button>
          
          <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" variant="outline">
                Reset to Defaults
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Reset to Defaults</DialogTitle>
                <DialogDescription>
                  This will reset all your notification preferences to their default values. This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setResetDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={resetPreferences}>
                  Reset Preferences
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Card */}
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Preferences Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {summary.total_notification_types}
                </div>
                <div className="text-sm text-muted-foreground">Notification Types</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {summary.enabled_notification_types}
                </div>
                <div className="text-sm text-muted-foreground">Enabled Types</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {summary.enabled_channels.length}
                </div>
                <div className="text-sm text-muted-foreground">Active Channels</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {summary.quiet_hours_enabled ? 'On' : 'Off'}
                </div>
                <div className="text-sm text-muted-foreground">Quiet Hours</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs value={selectedType} onValueChange={setSelectedType} className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          {NOTIFICATION_TYPES.map((type) => (
            <TabsTrigger key={type.id} value={type.id} className="text-xs">
              {type.icon}
              <span className="ml-1 hidden sm:inline">{type.name}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Notification Type Tabs */}
        {NOTIFICATION_TYPES.map((type) => (
          <TabsContent key={type.id} value={type.id} className="space-y-4">
            <NotificationTypeConfig
              type={type}
              config={preferences[type.id as keyof NotificationPreferences] as any}
              onUpdate={(updates) => updatePreference(type.id, updates)}
              channels={channels}
              onChannelUpdate={updateChannelSetting}
              onChannelToggle={toggleChannelEnabled}
            />
          </TabsContent>
        ))}
      </Tabs>

      {/* Global Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Global Settings</CardTitle>
          <CardDescription>
            Settings that apply to all notification types
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Enabled Channels */}
          <div>
            <Label className="text-base font-medium">Enabled Channels</Label>
            <p className="text-sm text-muted-foreground mb-4">
              Select which channels you want to receive notifications on
            </p>
            <div className="space-y-3">
              {channels.map((channel) => (
                <div key={channel.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    {channel.icon}
                    <div>
                      <div className="font-medium">{channel.name}</div>
                      <div className="text-sm text-muted-foreground">{channel.description}</div>
                    </div>
                  </div>
                  <Switch
                    checked={channel.enabled}
                    onCheckedChange={(checked) => toggleChannelEnabled(channel.id, checked)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Do Not Disturb */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Do Not Disturb</Label>
              <p className="text-sm text-muted-foreground">
                Temporarily disable all notifications
              </p>
            </div>
            <Switch
              checked={preferences.global.do_not_disturb}
              onCheckedChange={(checked) => updateGlobalSetting('do_not_disturb', checked)}
            />
          </div>

          {/* Other Global Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="timezone">Timezone</Label>
              <Select
                value={preferences.global.timezone}
                onValueChange={(value) => updateGlobalSetting('timezone', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTC">UTC</SelectItem>
                  <SelectItem value="America/New_York">Eastern Time</SelectItem>
                  <SelectItem value="America/Chicago">Central Time</SelectItem>
                  <SelectItem value="America/Denver">Mountain Time</SelectItem>
                  <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                  <SelectItem value="Europe/London">London</SelectItem>
                  <SelectItem value="Europe/Paris">Paris</SelectItem>
                  <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="language">Language</Label>
              <Select
                value={preferences.global.language}
                onValueChange={(value) => updateGlobalSetting('language', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                  <SelectItem value="fr">Français</SelectItem>
                  <SelectItem value="de">Deutsch</SelectItem>
                  <SelectItem value="it">Italiano</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface NotificationTypeConfigProps {
  type: any;
  config: any;
  onUpdate: (updates: any) => void;
  channels: ChannelConfig[];
  onChannelUpdate: (channelId: string, key: string, value: any) => void;
  onChannelToggle: (channelId: string, enabled: boolean) => void;
}

function NotificationTypeConfig({
  type,
  config,
  onUpdate,
  channels,
  onChannelUpdate,
  onChannelToggle
}: NotificationTypeConfigProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className={`p-2 rounded-full text-white ${type.color}`}>
            {type.icon}
          </div>
          {type.name}
        </CardTitle>
        <CardDescription>{type.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable/Disable */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label className="text-base">Enable Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Turn {type.name.toLowerCase()} notifications on or off
            </p>
          </div>
          <Switch
            checked={config.enabled}
            onCheckedChange={(checked) => onUpdate({ enabled: checked })}
          />
        </div>

        {config.enabled && (
          <>
            {/* Priority */}
            <div>
              <Label htmlFor={`priority-${type.id}`}>Priority</Label>
              <Select
                value={config.priority}
                onValueChange={(value) => onUpdate({ priority: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low - Only important updates</SelectItem>
                  <SelectItem value="normal">Normal - Standard notifications</SelectItem>
                  <SelectItem value="high">High - Immediate attention required</SelectItem>
                  <SelectItem value="critical">Critical - Urgent notifications</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Frequency */}
            <div>
              <Label htmlFor={`frequency-${type.id}`}>Frequency</Label>
              <Select
                value={config.frequency}
                onValueChange={(value) => onUpdate({ frequency: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="immediate">Immediate - As soon as possible</SelectItem>
                  <SelectItem value="hourly">Hourly - Bundle notifications</SelectItem>
                  <SelectItem value="daily">Daily - Daily digest</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Quiet Hours */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Quiet Hours</Label>
                  <p className="text-sm text-muted-foreground">
                    Disable notifications during specified hours
                  </p>
                </div>
                <Switch
                  checked={config.quiet_hours.enabled}
                  onCheckedChange={(checked) => 
                    onUpdate({ quiet_hours: { ...config.quiet_hours, enabled: checked } })
                  }
                />
              </div>

              {config.quiet_hours.enabled && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pl-4 border-l-2">
                  <div>
                    <Label htmlFor={`quiet-start-${type.id}`}>Start Time</Label>
                    <Input
                      id={`quiet-start-${type.id}`}
                      type="time"
                      value={config.quiet_hours.start}
                      onChange={(e) => 
                        onUpdate({ 
                          quiet_hours: { ...config.quiet_hours, start: e.target.value }
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor={`quiet-end-${type.id}`}>End Time</Label>
                    <Input
                      id={`quiet-end-${type.id}`}
                      type="time"
                      value={config.quiet_hours.end}
                      onChange={(e) => 
                        onUpdate({ 
                          quiet_hours: { ...config.quiet_hours, end: e.target.value }
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor={`quiet-tz-${type.id}`}>Timezone</Label>
                    <Select
                      value={config.quiet_hours.timezone}
                      onValueChange={(value) => 
                        onUpdate({ 
                          quiet_hours: { ...config.quiet_hours, timezone: value }
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UTC">UTC</SelectItem>
                        <SelectItem value="America/New_York">Eastern Time</SelectItem>
                        <SelectItem value="America/Chicago">Central Time</SelectItem>
                        <SelectItem value="America/Denver">Mountain Time</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </div>

            {/* Specific Conditions */}
            {type.id === 'document_processing' && (
              <div className="space-y-4">
                <Label>Document Processing Conditions</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="process-only-failures"
                      checked={config.conditions.process_only_failures || false}
                      onCheckedChange={(checked) => 
                        onUpdate({ 
                          conditions: { ...config.conditions, process_only_failures: checked }
                        })
                      }
                    />
                    <Label htmlFor="process-only-failures" className="text-sm">
                      Only notify on processing failures
                    </Label>
                  </div>
                  
                  <div>
                    <Label htmlFor="confidence-threshold">Minimum Confidence Score</Label>
                    <Input
                      id="confidence-threshold"
                      type="number"
                      min="0"
                      max="1"
                      step="0.1"
                      value={config.conditions.min_confidence_threshold || 0.8}
                      onChange={(e) => 
                        onUpdate({ 
                          conditions: { 
                            ...config.conditions, 
                            min_confidence_threshold: parseFloat(e.target.value)
                          }
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            )}

            {type.id === 'verification' && (
              <div className="space-y-4">
                <Label>Verification Conditions</Label>
                <div className="space-y-2">
                  {['notify_on_assignment', 'notify_on_completion', 'notify_on_escalation'].map((key) => (
                    <div key={key} className="flex items-center space-x-2">
                      <Checkbox
                        id={key}
                        checked={config.conditions[key] !== false}
                        onCheckedChange={(checked) => 
                          onUpdate({ 
                            conditions: { ...config.conditions, [key]: checked }
                          })
                        }
                      />
                      <Label htmlFor={key} className="text-sm">
                        {key.replace('notify_', '').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {type.id === 'security' && (
              <div className="space-y-4">
                <Label>Security Conditions</Label>
                <div className="space-y-2">
                  <div>
                    <Label htmlFor="risk-threshold">Risk Threshold</Label>
                    <Input
                      id="risk-threshold"
                      type="number"
                      min="0"
                      max="1"
                      step="0.1"
                      value={config.conditions.risk_threshold || 0.7}
                      onChange={(e) => 
                        onUpdate({ 
                          conditions: { 
                            ...config.conditions, 
                            risk_threshold: parseFloat(e.target.value)
                          }
                        })
                      }
                    />
                    <p className="text-sm text-muted-foreground">
                      Only notify for activities with risk score above this threshold
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default NotificationPreferencesManager;