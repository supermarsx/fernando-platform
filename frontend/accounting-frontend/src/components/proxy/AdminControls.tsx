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
import { Progress } from '@/components/ui/progress';
import { 
  Server, 
  Power, 
  RefreshCw, 
  Settings,
  Download,
  Upload,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Pause,
  Play,
  RotateCcw,
  Shield,
  Clock,
  Activity,
  Database,
  Zap,
  AlertCircle,
  FileText,
  Upload as UploadIcon,
  Trash2
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';

interface ProxyServer {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'restarting' | 'maintenance' | 'error';
  health: number;
  version: string;
  uptime: string;
  lastRestart: string;
  configuration: {
    port: number;
    ssl: boolean;
    maxConnections: number;
    timeout: number;
    rateLimit: number;
    cacheEnabled: boolean;
    compression: boolean;
  };
  resources: {
    cpu: number;
    memory: number;
    disk: number;
  };
  performance: {
    requestsPerSecond: number;
    averageResponseTime: number;
    errorRate: number;
    throughput: number;
  };
}

interface BackupConfig {
  id: string;
  name: string;
  timestamp: string;
  size: number;
  type: 'full' | 'incremental';
  status: 'success' | 'failed' | 'in-progress';
  description?: string;
}

interface MaintenanceWindow {
  id: string;
  title: string;
  description: string;
  startTime: string;
  endTime: string;
  affectedServices: string[];
  status: 'scheduled' | 'active' | 'completed' | 'cancelled';
  notificationSent: boolean;
}

const AdminControls: React.FC = () => {
  const [servers, setServers] = useState<ProxyServer[]>([]);
  const [backups, setBackups] = useState<BackupConfig[]>([]);
  const [maintenanceWindows, setMaintenanceWindows] = useState<MaintenanceWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedServer, setSelectedServer] = useState<string>('');
  const [showShutdownDialog, setShowShutdownDialog] = useState(false);
  const [showMaintenanceDialog, setShowMaintenanceDialog] = useState(false);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [globalMaintenance, setGlobalMaintenance] = useState(false);
  const [shutdownReason, setShutdownReason] = useState('');
  const [maintenanceWindow, setMaintenanceWindow] = useState({
    title: '',
    description: '',
    startTime: '',
    endTime: '',
    affectedServices: [] as string[]
  });
  const { toast } = useToast();
  
  const { connected, data: wsData } = useWebSocket('/ws/proxy/admin');

  useEffect(() => {
    loadAdminData();
  }, []);

  useEffect(() => {
    if (wsData) {
      // Update server states in real-time
      if (wsData.serverUpdate) {
        setServers(prev => 
          prev.map(server => 
            server.id === wsData.serverUpdate.id 
              ? { ...server, ...wsData.serverUpdate }
              : server
          )
        );
      }
      if (wsData.emergencyMode !== undefined) {
        setEmergencyMode(wsData.emergencyMode);
      }
      if (wsData.globalMaintenance !== undefined) {
        setGlobalMaintenance(wsData.globalMaintenance);
      }
    }
  }, [wsData]);

  const loadAdminData = async () => {
    try {
      const [serversResponse, backupsResponse, maintenanceResponse] = await Promise.all([
        fetch('/api/proxy/admin/servers'),
        fetch('/api/proxy/admin/backups'),
        fetch('/api/proxy/admin/maintenance')
      ]);
      
      if (serversResponse.ok) {
        const serversData = await serversResponse.json();
        setServers(serversData);
      }
      
      if (backupsResponse.ok) {
        const backupsData = await backupsResponse.json();
        setBackups(backupsData);
      }
      
      if (maintenanceResponse.ok) {
        const maintenanceData = await maintenanceResponse.json();
        setMaintenanceWindows(maintenanceData.windows || []);
        setEmergencyMode(maintenanceData.emergencyMode || false);
        setGlobalMaintenance(maintenanceData.globalMaintenance || false);
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load admin data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const serverAction = async (serverId: string, action: string, options?: any) => {
    try {
      const response = await fetch(`/api/proxy/admin/servers/${serverId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options || {})
      });
      
      if (response.ok) {
        const result = await response.json();
        toast({
          title: 'Success',
          description: `Server ${action} initiated successfully`
        });
        loadAdminData(); // Refresh data
      } else {
        throw new Error('Action failed');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: `Failed to ${action} server`,
        variant: 'destructive'
      });
    }
  };

  const createBackup = async (type: 'full' | 'incremental', description?: string) => {
    try {
      const response = await fetch('/api/proxy/admin/backups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, description })
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Backup creation initiated'
        });
        loadAdminData(); // Refresh data
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create backup',
        variant: 'destructive'
      });
    }
  };

  const downloadBackup = async (backupId: string) => {
    try {
      const response = await fetch(`/api/proxy/admin/backups/${backupId}/download`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proxy-backup-${backupId}.tar.gz`;
      a.click();
      
      toast({
        title: 'Success',
        description: 'Backup downloaded successfully'
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to download backup',
        variant: 'destructive'
      });
    }
  };

  const deleteBackup = async (backupId: string) => {
    try {
      const response = await fetch(`/api/proxy/admin/backups/${backupId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setBackups(prev => prev.filter(backup => backup.id !== backupId));
        toast({
          title: 'Success',
          description: 'Backup deleted successfully'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete backup',
        variant: 'destructive'
      });
    }
  };

  const restoreBackup = async (backupId: string) => {
    try {
      const response = await fetch(`/api/proxy/admin/restore/${backupId}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Backup restoration initiated'
        });
        loadAdminData(); // Refresh data
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to restore backup',
        variant: 'destructive'
      });
    }
  };

  const uploadConfiguration = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('config', file);
      
      const response = await fetch('/api/proxy/admin/config/upload', {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Configuration uploaded successfully'
        });
        loadAdminData(); // Refresh data
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to upload configuration',
        variant: 'destructive'
      });
    }
  };

  const downloadConfiguration = async () => {
    try {
      const response = await fetch('/api/proxy/admin/config/download');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'proxy-configuration.json';
      a.click();
      
      toast({
        title: 'Success',
        description: 'Configuration downloaded successfully'
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to download configuration',
        variant: 'destructive'
      });
    }
  };

  const toggleEmergencyMode = async () => {
    try {
      const response = await fetch('/api/proxy/admin/emergency-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !emergencyMode })
      });
      
      if (response.ok) {
        setEmergencyMode(!emergencyMode);
        toast({
          title: 'Success',
          description: `Emergency mode ${!emergencyMode ? 'enabled' : 'disabled'}`
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to toggle emergency mode',
        variant: 'destructive'
      });
    }
  };

  const toggleGlobalMaintenance = async () => {
    try {
      const response = await fetch('/api/proxy/admin/maintenance/global', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !globalMaintenance })
      });
      
      if (response.ok) {
        setGlobalMaintenance(!globalMaintenance);
        toast({
          title: 'Success',
          description: `Global maintenance ${!globalMaintenance ? 'enabled' : 'disabled'}`
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to toggle global maintenance',
        variant: 'destructive'
      });
    }
  };

  const scheduleMaintenanceWindow = async () => {
    try {
      const response = await fetch('/api/proxy/admin/maintenance/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(maintenanceWindow)
      });
      
      if (response.ok) {
        const window = await response.json();
        setMaintenanceWindows(prev => [window, ...prev]);
        setShowMaintenanceDialog(false);
        resetMaintenanceForm();
        toast({
          title: 'Success',
          description: 'Maintenance window scheduled'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to schedule maintenance window',
        variant: 'destructive'
      });
    }
  };

  const resetMaintenanceForm = () => {
    setMaintenanceWindow({
      title: '',
      description: '',
      startTime: '',
      endTime: '',
      affectedServices: []
    });
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary'> = {
      running: 'default',
      stopped: 'secondary',
      restarting: 'secondary',
      maintenance: 'secondary',
      error: 'destructive'
    };
    const icons = {
      running: Play,
      stopped: Pause,
      restarting: RefreshCw,
      maintenance: Settings,
      error: AlertCircle
    };
    const Icon = icons[status] || AlertCircle;
    
    return (
      <Badge variant={variants[status] || 'secondary'} className="flex items-center space-x-1">
        <Icon className="h-3 w-3" />
        <span className="capitalize">{status}</span>
      </Badge>
    );
  };

  const getBackupStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'secondary'> = {
      success: 'default',
      failed: 'destructive',
      'in-progress': 'secondary'
    };
    const icons = {
      success: CheckCircle,
      failed: XCircle,
      'in-progress': RefreshCw
    };
    const Icon = icons[status] || RefreshCw;
    
    return (
      <Badge variant={variants[status] || 'secondary'} className="flex items-center space-x-1">
        <Icon className="h-3 w-3" />
        <span className="capitalize">{status}</span>
      </Badge>
    );
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin h-8 w-8" />
        <span className="ml-2">Loading admin controls...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Admin Controls</h1>
          <p className="text-muted-foreground">Manage proxy server operations and configuration</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={connected ? 'default' : 'destructive'}>
            {connected ? 'Live' : 'Offline'}
          </Badge>
          <Button variant="outline" onClick={loadAdminData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Emergency Controls */}
      <Card className={emergencyMode ? 'border-red-200 bg-red-50' : ''}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>Emergency Controls</span>
            {emergencyMode && <Badge variant="destructive">EMERGENCY MODE ACTIVE</Badge>}
          </CardTitle>
          <CardDescription>
            Critical system controls for emergency situations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-semibold">Emergency Mode</p>
                <p className="text-sm text-muted-foreground">
                  {emergencyMode ? 'System in emergency mode' : 'All systems normal'}
                </p>
              </div>
              <Switch
                checked={emergencyMode}
                onCheckedChange={toggleEmergencyMode}
              />
            </div>
            
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-semibold">Global Maintenance</p>
                <p className="text-sm text-muted-foreground">
                  {globalMaintenance ? 'Maintenance mode active' : 'All services available'}
                </p>
              </div>
              <Switch
                checked={globalMaintenance}
                onCheckedChange={toggleGlobalMaintenance}
              />
            </div>
            
            <Dialog open={showShutdownDialog} onOpenChange={setShowShutdownDialog}>
              <DialogTrigger asChild>
                <Button variant="destructive" className="w-full">
                  <XCircle className="h-4 w-4 mr-2" />
                  Emergency Shutdown
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Emergency Shutdown</DialogTitle>
                  <DialogDescription>
                    This will immediately stop all proxy servers. Use with extreme caution.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="shutdownReason">Reason for shutdown</Label>
                    <Input
                      id="shutdownReason"
                      value={shutdownReason}
                      onChange={(e) => setShutdownReason(e.target.value)}
                      placeholder="Describe the reason for emergency shutdown"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowShutdownDialog(false)}>Cancel</Button>
                  <Button variant="destructive" onClick={() => {
                    serverAction('all', 'emergency-shutdown', { reason: shutdownReason });
                    setShowShutdownDialog(false);
                  }}>
                    Confirm Shutdown
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="servers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="servers">Server Management</TabsTrigger>
          <TabsTrigger value="backups">Backup & Restore</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="servers" className="space-y-4">
          <div className="space-y-3">
            {servers.map((server) => (
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
                        Version {server.version} • Uptime: {server.uptime} • 
                        Last restart: {new Date(server.lastRestart).toLocaleString()}
                      </CardDescription>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => serverAction(server.id, 'start')}
                        disabled={server.status === 'running'}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Start
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => serverAction(server.id, 'stop')}
                        disabled={server.status !== 'running'}
                      >
                        <Pause className="h-4 w-4 mr-1" />
                        Stop
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => serverAction(server.id, 'restart')}
                        disabled={server.status === 'restarting'}
                      >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Restart
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Health</p>
                      <p className="text-lg font-semibold">{server.health}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">CPU Usage</p>
                      <p className="text-lg font-semibold">{server.resources.cpu}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Memory Usage</p>
                      <p className="text-lg font-semibold">{server.resources.memory}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Response Time</p>
                      <p className="text-lg font-semibold">{server.performance.averageResponseTime}ms</p>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t">
                    <h4 className="font-semibold mb-2">Configuration</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Port</p>
                        <p className="font-semibold">{server.configuration.port}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">SSL</p>
                        <p className="font-semibold">{server.configuration.ssl ? 'Enabled' : 'Disabled'}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Max Connections</p>
                        <p className="font-semibold">{server.configuration.maxConnections}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="backups" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Configuration Backups</h3>
            <div className="flex space-x-2">
              <Button variant="outline" onClick={() => createBackup('incremental')}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Incremental Backup
              </Button>
              <Button onClick={() => createBackup('full')}>
                <Database className="h-4 w-4 mr-2" />
                Full Backup
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            {backups.map((backup) => (
              <Card key={backup.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-semibold">{backup.name}</h4>
                        {getBackupStatusBadge(backup.status)}
                        <Badge variant="outline">{backup.type}</Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm text-muted-foreground">
                        <span>Created: {new Date(backup.timestamp).toLocaleString()}</span>
                        <span>Size: {formatBytes(backup.size)}</span>
                        {backup.description && <span>Description: {backup.description}</span>}
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {backup.status === 'success' && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => downloadBackup(backup.id)}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => restoreBackup(backup.id)}
                          >
                            <RefreshCw className="h-4 w-4 mr-1" />
                            Restore
                          </Button>
                        </>
                      )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteBackup(backup.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="maintenance" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Maintenance Windows</h3>
            <Dialog open={showMaintenanceDialog} onOpenChange={setShowMaintenanceDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Clock className="h-4 w-4 mr-2" />
                  Schedule Maintenance
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Schedule Maintenance Window</DialogTitle>
                  <DialogDescription>
                    Plan and schedule system maintenance activities
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div>
                    <Label htmlFor="title">Title</Label>
                    <Input
                      id="title"
                      value={maintenanceWindow.title}
                      onChange={(e) => setMaintenanceWindow(prev => ({ ...prev, title: e.target.value }))}
                      placeholder="Database Server Upgrade"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={maintenanceWindow.description}
                      onChange={(e) => setMaintenanceWindow(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Upgrade database server to latest version"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="startTime">Start Time</Label>
                      <Input
                        id="startTime"
                        type="datetime-local"
                        value={maintenanceWindow.startTime}
                        onChange={(e) => setMaintenanceWindow(prev => ({ ...prev, startTime: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="endTime">End Time</Label>
                      <Input
                        id="endTime"
                        type="datetime-local"
                        value={maintenanceWindow.endTime}
                        onChange={(e) => setMaintenanceWindow(prev => ({ ...prev, endTime: e.target.value }))}
                      />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowMaintenanceDialog(false)}>Cancel</Button>
                  <Button onClick={scheduleMaintenanceWindow}>Schedule</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-3">
            {maintenanceWindows.map((window) => (
              <Card key={window.id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-semibold">{window.title}</h4>
                        <Badge variant="outline">{window.status}</Badge>
                        {window.notificationSent && <Badge variant="default">Notified</Badge>}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{window.description}</p>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span>Start: {new Date(window.startTime).toLocaleString()}</span>
                        <span>End: {new Date(window.endTime).toLocaleString()}</span>
                        <span>Services: {window.affectedServices.join(', ')}</span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {window.status === 'scheduled' && (
                        <Button variant="outline" size="sm">
                          Activate
                        </Button>
                      )}
                      {window.status === 'active' && (
                        <Button variant="outline" size="sm">
                          Complete
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Download className="h-5 w-5" />
                  <span>Export Configuration</span>
                </CardTitle>
                <CardDescription>
                  Download current proxy server configuration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button onClick={downloadConfiguration} className="w-full">
                  <Download className="h-4 w-4 mr-2" />
                  Download Configuration
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <UploadIcon className="h-5 w-5" />
                  <span>Import Configuration</span>
                </CardTitle>
                <CardDescription>
                  Upload and apply proxy server configuration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <input
                    type="file"
                    accept=".json,.yaml,.yml"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) uploadConfiguration(file);
                    }}
                    className="w-full"
                  />
                  <p className="text-sm text-muted-foreground">
                    Supported formats: JSON, YAML
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>System Information</CardTitle>
              <CardDescription>
                Current system status and resource usage
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Servers</p>
                  <p className="text-2xl font-bold">{servers.length}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Running Servers</p>
                  <p className="text-2xl font-bold text-green-600">
                    {servers.filter(s => s.status === 'running').length}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">System Load</p>
                  <p className="text-2xl font-bold">
                    {servers.reduce((sum, s) => sum + s.resources.cpu, 0) / servers.length || 0}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active Backups</p>
                  <p className="text-2xl font-bold">
                    {backups.filter(b => b.status === 'in-progress').length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdminControls;