"""
Frontend Alert Management Interface

React components for managing alerts, viewing dashboard, and configuring rules.
"""

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Settings,
  Filter,
  Search,
  RefreshCw,
  Bell,
  BellOff,
  AlertCircle,
  Info,
  TrendingUp,
  TrendingDown,
  Users,
  Shield,
  Server,
  Database,
  Activity,
  Eye,
  EyeOff,
  ExternalLink,
  Download,
  Trash2,
  Plus,
  Edit,
  Play,
  Pause
} from 'lucide-react';


// Alert Dashboard Component
const AlertDashboard: React.FC = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    status: 'all',
    severity: 'all',
    type: 'all',
    search: ''
  });

  useEffect(() => {
    fetchAlerts();
    fetchStats();
    const interval = setInterval(() => {
      fetchAlerts();
      fetchStats();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [filters]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/alerts/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setAlerts(data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/alerts/statistics', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await fetch(`/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ note: 'Acknowledged from dashboard' })
      });
      fetchAlerts();
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await fetch(`/api/v1/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ resolution_notes: 'Resolved from dashboard' })
      });
      fetchAlerts();
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'bg-red-500',
      high: 'bg-orange-500',
      medium: 'bg-yellow-500',
      low: 'bg-blue-500',
      info: 'bg-gray-500'
    };
    return colors[severity] || 'bg-gray-500';
  };

  const getStatusColor = (status: string) => {
    const colors = {
      active: 'bg-red-100 text-red-800',
      acknowledged: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      suppressed: 'bg-gray-100 text-gray-800',
      escalated: 'bg-purple-100 text-purple-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status: string) => {
    const icons = {
      active: <AlertTriangle className="h-4 w-4" />,
      acknowledged: <Clock className="h-4 w-4" />,
      resolved: <CheckCircle className="h-4 w-4" />,
      suppressed: <BellOff className="h-4 w-4" />,
      escalated: <Zap className="h-4 w-4" />
    };
    return icons[status] || <AlertCircle className="h-4 w-4" />;
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filters.status !== 'all' && alert.status !== filters.status) return false;
    if (filters.severity !== 'all' && alert.severity !== filters.severity) return false;
    if (filters.type !== 'all' && alert.alert_type !== filters.type) return false;
    if (filters.search && !alert.title.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading alerts...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Alert Dashboard</h1>
          <p className="text-gray-600">Monitor and manage system alerts</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={fetchAlerts} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <CreateAlertDialog onAlertCreated={fetchAlerts} />
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
              <Bell className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_alerts}</div>
              <p className="text-xs text-muted-foreground">
                Active: {stats.active_alerts}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Alerts</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.critical_alerts}</div>
              <p className="text-xs text-muted-foreground">
                High: {stats.high_alerts} | Medium: {stats.medium_alerts}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resolution Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.total_alerts > 0 ? Math.round((stats.resolved_alerts / stats.total_alerts) * 100) : 0}%
              </div>
              <p className="text-xs text-muted-foreground">
                Avg time: {stats.average_resolution_time ? Math.round(stats.average_resolution_time) : 0} min
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Response Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.average_resolution_time ? Math.round(stats.average_resolution_time) : 0}m
              </div>
              <p className="text-xs text-muted-foreground">
                Average resolution time
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-3 h-4 w-4 text-gray-400" />
                <Input
                  id="search"
                  placeholder="Search alerts..."
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="pl-8"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="status">Status</Label>
              <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="acknowledged">Acknowledged</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="suppressed">Suppressed</SelectItem>
                  <SelectItem value="escalated">Escalated</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="severity">Severity</Label>
              <Select value={filters.severity} onValueChange={(value) => setFilters({ ...filters, severity: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="All severities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All severities</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="type">Type</Label>
              <Select value={filters.type} onValueChange={(value) => setFilters({ ...filters, type: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="application">Application</SelectItem>
                  <SelectItem value="business">Business</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alerts List */}
      <Card>
        <CardHeader>
          <CardTitle>Alerts ({filteredAlerts.length})</CardTitle>
          <CardDescription>
            {filteredAlerts.length} of {alerts.length} alerts shown
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-96">
            <div className="space-y-4">
              {filteredAlerts.map((alert) => (
                <AlertCard
                  key={alert.alert_id}
                  alert={alert}
                  onAcknowledge={acknowledgeAlert}
                  onResolve={resolveAlert}
                  onViewDetails={setSelectedAlert}
                />
              ))}
              {filteredAlerts.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No alerts found matching the current filters.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Alert Details Dialog */}
      {selectedAlert && (
        <AlertDetailsDialog
          alert={selectedAlert}
          open={!!selectedAlert}
          onOpenChange={(open) => !open && setSelectedAlert(null)}
          onAcknowledge={acknowledgeAlert}
          onResolve={resolveAlert}
        />
      )}
    </div>
  );
};


// Alert Card Component
interface AlertCardProps {
  alert: any;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
  onViewDetails: (alert: any) => void;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onAcknowledge, onResolve, onViewDetails }) => {
  const getSeverityIcon = (severity: string) => {
    const icons = {
      critical: <AlertTriangle className="h-4 w-4 text-red-500" />,
      high: <AlertTriangle className="h-4 w-4 text-orange-500" />,
      medium: <AlertCircle className="h-4 w-4 text-yellow-500" />,
      low: <Info className="h-4 w-4 text-blue-500" />,
      info: <Info className="h-4 w-4 text-gray-500" />
    };
    return icons[severity] || <Info className="h-4 w-4 text-gray-500" />;
  };

  const getTypeIcon = (type: string) => {
    const icons = {
      system: <Server className="h-4 w-4" />,
      application: <Activity className="h-4 w-4" />,
      business: <TrendingUp className="h-4 w-4" />,
      security: <Shield className="h-4 w-4" />,
      custom: <Settings className="h-4 w-4" />
    };
    return icons[type] || <AlertCircle className="h-4 w-4" />;
  };

  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="mt-1">
            {getSeverityIcon(alert.severity)}
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-sm">{alert.title}</h3>
              <Badge className={`text-xs ${alert.status === 'active' ? 'bg-red-100 text-red-800' : 
                alert.status === 'acknowledged' ? 'bg-yellow-100 text-yellow-800' :
                alert.status === 'resolved' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                {alert.status}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {alert.severity}
              </Badge>
            </div>
            <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
              <span className="flex items-center">
                {getTypeIcon(alert.alert_type)}
                <span className="ml-1">{alert.alert_type}</span>
              </span>
              <span>
                {new Date(alert.triggered_at).toLocaleString()}
              </span>
              {alert.metric_value && (
                <span>
                  Value: {alert.metric_value}
                  {alert.threshold_value && ` / ${alert.threshold_value}`}
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex space-x-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onViewDetails(alert)}
          >
            <Eye className="h-4 w-4" />
          </Button>
          {alert.status === 'active' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onAcknowledge(alert.alert_id)}
            >
              <Clock className="h-4 w-4" />
            </Button>
          )}
          {alert.status !== 'resolved' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onResolve(alert.alert_id)}
            >
              <CheckCircle className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};


// Alert Details Dialog Component
interface AlertDetailsDialogProps {
  alert: any;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
}

const AlertDetailsDialog: React.FC<AlertDetailsDialogProps> = ({
  alert,
  open,
  onOpenChange,
  onAcknowledge,
  onResolve
}) => {
  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'border-red-200 bg-red-50',
      high: 'border-orange-200 bg-orange-50',
      medium: 'border-yellow-200 bg-yellow-50',
      low: 'border-blue-200 bg-blue-50',
      info: 'border-gray-200 bg-gray-50'
    };
    return colors[severity] || 'border-gray-200 bg-gray-50';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <span>Alert Details</span>
            <Badge className={getSeverityColor(alert.severity)}>
              {alert.severity}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Detailed information about this alert
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label className="text-sm font-medium">Title</Label>
            <p className="text-sm">{alert.title}</p>
          </div>

          <div>
            <Label className="text-sm font-medium">Message</Label>
            <p className="text-sm text-gray-600">{alert.message}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-sm font-medium">Status</Label>
              <Badge className="mt-1">{alert.status}</Badge>
            </div>
            <div>
              <Label className="text-sm font-medium">Type</Label>
              <p className="text-sm mt-1">{alert.alert_type}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-sm font-medium">Triggered</Label>
              <p className="text-sm mt-1">
                {new Date(alert.triggered_at).toLocaleString()}
              </p>
            </div>
            {alert.acknowledged_at && (
              <div>
                <Label className="text-sm font-medium">Acknowledged</Label>
                <p className="text-sm mt-1">
                  {new Date(alert.acknowledged_at).toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {alert.metric_value && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium">Current Value</Label>
                <p className="text-sm mt-1">{alert.metric_value}</p>
              </div>
              {alert.threshold_value && (
                <div>
                  <Label className="text-sm font-medium">Threshold</Label>
                  <p className="text-sm mt-1">{alert.threshold_value}</p>
                </div>
              )}
            </div>
          )}

          {alert.context && Object.keys(alert.context).length > 0 && (
            <div>
              <Label className="text-sm font-medium">Context</Label>
              <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                {JSON.stringify(alert.context, null, 2)}
              </pre>
            </div>
          )}

          {alert.labels && Object.keys(alert.labels).length > 0 && (
            <div>
              <Label className="text-sm font-medium">Labels</Label>
              <div className="flex flex-wrap gap-1 mt-1">
                {Object.entries(alert.labels).map(([key, value]) => (
                  <Badge key={key} variant="outline" className="text-xs">
                    {key}: {value}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {alert.runbook_url && (
            <div>
              <Label className="text-sm font-medium">Runbook</Label>
              <a
                href={alert.runbook_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline text-sm flex items-center"
              >
                View Runbook
                <ExternalLink className="h-3 w-3 ml-1" />
              </a>
            </div>
          )}
        </div>

        <DialogFooter>
          {alert.status === 'active' && (
            <Button
              onClick={() => {
                onAcknowledge(alert.alert_id);
                onOpenChange(false);
              }}
            >
              <Clock className="h-4 w-4 mr-2" />
              Acknowledge
            </Button>
          )}
          {alert.status !== 'resolved' && (
            <Button
              variant="outline"
              onClick={() => {
                onResolve(alert.alert_id);
                onOpenChange(false);
              }}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Resolve
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


// Create Alert Dialog Component
interface CreateAlertDialogProps {
  onAlertCreated: () => void;
}

const CreateAlertDialog: React.FC<CreateAlertDialogProps> = ({ onAlertCreated }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    message: '',
    description: '',
    severity: 'medium',
    alert_type: 'system',
    runbook_url: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await fetch('/api/v1/alerts/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      setOpen(false);
      onAlertCreated();
      setFormData({
        title: '',
        message: '',
        description: '',
        severity: 'medium',
        alert_type: 'system',
        runbook_url: ''
      });
    } catch (error) {
      console.error('Error creating alert:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Alert
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create New Alert</DialogTitle>
          <DialogDescription>
            Create a manual alert for testing or immediate notification
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div>
            <Label htmlFor="message">Message</Label>
            <Textarea
              id="message"
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              required
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="severity">Severity</Label>
              <Select value={formData.severity} onValueChange={(value) => setFormData({ ...formData, severity: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="type">Type</Label>
              <Select value={formData.alert_type} onValueChange={(value) => setFormData({ ...formData, alert_type: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="application">Application</SelectItem>
                  <SelectItem value="business">Business</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="runbook_url">Runbook URL (optional)</Label>
            <Input
              id="runbook_url"
              type="url"
              value={formData.runbook_url}
              onChange={(e) => setFormData({ ...formData, runbook_url: e.target.value })}
            />
          </div>

          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Alert'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};


// Alert Rules Management Component
const AlertRulesManager: React.FC = () => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/alerts/rules/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setRules(data);
    } catch (error) {
      console.error('Error fetching rules:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Alert Rules</h1>
          <p className="text-gray-600">Configure and manage alert rules</p>
        </div>
        <CreateRuleDialog onRuleCreated={fetchRules} />
      </div>

      {/* Rules List */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Rules ({rules.length})</CardTitle>
          <CardDescription>
            Manage alert rules and their configurations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="h-6 w-6 animate-spin" />
              <span className="ml-2">Loading rules...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {rules.map((rule) => (
                <RuleCard key={rule.rule_id} rule={rule} onRuleUpdated={fetchRules} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};


// Rule Card Component
interface RuleCardProps {
  rule: any;
  onRuleUpdated: () => void;
}

const RuleCard: React.FC<RuleCardProps> = ({ rule, onRuleUpdated }) => {
  const toggleRule = async (enabled: boolean) => {
    try {
      await fetch(`/api/v1/alerts/rules/${rule.rule_id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enabled })
      });
      onRuleUpdated();
    } catch (error) {
      console.error('Error updating rule:', error);
    }
  };

  const testRule = async () => {
    try {
      await fetch(`/api/v1/alerts/rules/${rule.rule_id}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      // Show success message
    } catch (error) {
      console.error('Error testing rule:', error);
    }
  };

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h3 className="font-semibold">{rule.name}</h3>
            <Badge variant={rule.enabled ? "default" : "secondary"}>
              {rule.enabled ? "Enabled" : "Disabled"}
            </Badge>
            <Badge variant="outline">{rule.severity}</Badge>
            <Badge variant="outline">{rule.alert_type}</Badge>
          </div>
          <p className="text-sm text-gray-600 mt-1">{rule.description}</p>
          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
            <span>Alerts triggered: {rule.alert_count || 0}</span>
            <span>Evaluation: every {rule.evaluation_frequency}s</span>
            <span>Sustained: {rule.sustained_duration}s</span>
          </div>
        </div>
        
        <div className="flex space-x-2">
          <Switch
            checked={rule.enabled}
            onCheckedChange={toggleRule}
          />
          <Button size="sm" variant="outline" onClick={testRule}>
            <Play className="h-4 w-4" />
          </Button>
          <EditRuleDialog rule={rule} onRuleUpdated={onRuleUpdated} />
        </div>
      </div>
    </div>
  );
};


// Create Rule Dialog Component
interface CreateRuleDialogProps {
  onRuleCreated: () => void;
}

const CreateRuleDialog: React.FC<CreateRuleDialogProps> = ({ onRuleCreated }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    alert_type: 'system',
    severity: 'medium',
    condition: {},
    channels: [],
    enabled: true
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await fetch('/api/v1/alerts/rules/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      setOpen(false);
      onRuleCreated();
    } catch (error) {
      console.error('Error creating rule:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Rule
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Alert Rule</DialogTitle>
          <DialogDescription>
            Create a new alert rule with custom conditions
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="alert_type">Type</Label>
              <Select value={formData.alert_type} onValueChange={(value) => setFormData({ ...formData, alert_type: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="application">Application</SelectItem>
                  <SelectItem value="business">Business</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="severity">Severity</Label>
              <Select value={formData.severity} onValueChange={(value) => setFormData({ ...formData, severity: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};


// Edit Rule Dialog Component (placeholder)
interface EditRuleDialogProps {
  rule: any;
  onRuleUpdated: () => void;
}

const EditRuleDialog: React.FC<EditRuleDialogProps> = ({ rule, onRuleUpdated }) => {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Edit className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Alert Rule</DialogTitle>
          <DialogDescription>
            Modify the alert rule configuration
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-gray-600">
            Rule editing functionality would be implemented here with a comprehensive form.
          </p>
        </div>
        <DialogFooter>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


// Main Alert System Component
const AlertSystem: React.FC = () => {
  return (
    <Tabs defaultValue="dashboard" className="space-y-6">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
        <TabsTrigger value="rules">Rules</TabsTrigger>
        <TabsTrigger value="settings">Settings</TabsTrigger>
      </TabsList>
      
      <TabsContent value="dashboard">
        <AlertDashboard />
      </TabsContent>
      
      <TabsContent value="rules">
        <AlertRulesManager />
      </TabsContent>
      
      <TabsContent value="settings">
        <div className="space-y-6">
          <h2 className="text-2xl font-bold">Alert Settings</h2>
          <p className="text-gray-600">Alert system configuration and settings will be implemented here.</p>
        </div>
      </TabsContent>
    </Tabs>
  );
};

export default AlertSystem;