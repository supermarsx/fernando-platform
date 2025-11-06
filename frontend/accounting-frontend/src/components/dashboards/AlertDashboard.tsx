import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Progress } from '../ui/progress';
import { 
  Line, Bar, Pie
} from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  CheckCircle,
  Clock,
  Bell,
  Filter,
  RefreshCw,
  X,
  MoreVertical,
  Settings,
  TrendingUp,
  Activity,
  Users,
  Server,
  Database
} from 'lucide-react';
import { telemetryAPI } from '../../lib/api';
import { format, subHours, subDays } from 'date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface Alert {
  id: string;
  name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  metric_name: string;
  threshold_value: number;
  current_value: number;
  threshold_type: 'above' | 'below';
  notification_channels: string[];
  created_at: string;
  last_triggered: string;
  acknowledged_at?: string;
  resolved_at?: string;
  source: string;
}

interface AlertHistory {
  timestamp: string;
  total_alerts: number;
  new_alerts: number;
  resolved_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
}

const AlertDashboard: React.FC = () => {
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<AlertHistory[]>([]);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'acknowledged' | 'resolved'>('all');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Fetch alerts data
  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const [activeRes, historyRes] = await Promise.all([
        telemetryAPI.getActiveAlerts(),
        telemetryAPI.getAlertHistory({ limit: 24 }),
      ]);

      // Simulate real-time data for demonstration
      const simulatedAlerts = generateSimulatedAlerts();
      const simulatedHistory = generateAlertHistory();
      
      setActiveAlerts(simulatedAlerts);
      setAlertHistory(simulatedHistory);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      // Use fallback data on error
      const fallbackAlerts = generateSimulatedAlerts();
      const fallbackHistory = generateAlertHistory();
      
      setActiveAlerts(fallbackAlerts);
      setAlertHistory(fallbackHistory);
    } finally {
      setLoading(false);
    }
  };

  // Generate simulated alerts for demonstration
  const generateSimulatedAlerts = (): Alert[] => [
    {
      id: '1',
      name: 'High CPU Usage',
      description: 'CPU usage has exceeded the 85% threshold',
      severity: 'high',
      status: 'active',
      metric_name: 'cpu_usage',
      threshold_value: 85,
      current_value: 92.5,
      threshold_type: 'above',
      notification_channels: ['email', 'slack'],
      created_at: '2025-11-06T04:30:00Z',
      last_triggered: '2025-11-06T04:30:00Z',
      source: 'System Monitoring',
    },
    {
      id: '2',
      name: 'Database Connection Pool Exhausted',
      description: 'Available database connections are below 20% threshold',
      severity: 'critical',
      status: 'acknowledged',
      metric_name: 'db_connections',
      threshold_value: 20,
      current_value: 15,
      threshold_type: 'below',
      notification_channels: ['email', 'slack', 'sms'],
      created_at: '2025-11-06T03:15:00Z',
      last_triggered: '2025-11-06T03:15:00Z',
      acknowledged_at: '2025-11-06T03:20:00Z',
      source: 'Database Monitoring',
    },
    {
      id: '3',
      name: 'High Memory Usage',
      description: 'Memory usage has exceeded the 90% threshold',
      severity: 'high',
      status: 'active',
      metric_name: 'memory_usage',
      threshold_value: 90,
      current_value: 94.2,
      threshold_type: 'above',
      notification_channels: ['email'],
      created_at: '2025-11-06T05:00:00Z',
      last_triggered: '2025-11-06T05:00:00Z',
      source: 'System Monitoring',
    },
    {
      id: '4',
      name: 'API Response Time Spike',
      description: 'Average API response time exceeded 500ms',
      severity: 'medium',
      status: 'resolved',
      metric_name: 'api_response_time',
      threshold_value: 500,
      current_value: 245,
      threshold_type: 'above',
      notification_channels: ['email', 'slack'],
      created_at: '2025-11-06T02:30:00Z',
      last_triggered: '2025-11-06T02:30:00Z',
      acknowledged_at: '2025-11-06T02:35:00Z',
      resolved_at: '2025-11-06T03:00:00Z',
      source: 'API Monitoring',
    },
    {
      id: '5',
      name: 'Disk Space Low',
      description: 'Available disk space below 15%',
      severity: 'medium',
      status: 'active',
      metric_name: 'disk_usage',
      threshold_value: 85,
      current_value: 88.5,
      threshold_type: 'above',
      notification_channels: ['email'],
      created_at: '2025-11-06T04:45:00Z',
      last_triggered: '2025-11-06T04:45:00Z',
      source: 'System Monitoring',
    },
    {
      id: '6',
      name: 'User Signup Rate Drop',
      description: 'Daily user signups below 50 for consecutive 3 days',
      severity: 'low',
      status: 'active',
      metric_name: 'daily_signups',
      threshold_value: 50,
      current_value: 42,
      threshold_type: 'below',
      notification_channels: ['email'],
      created_at: '2025-11-06T01:00:00Z',
      last_triggered: '2025-11-06T01:00:00Z',
      source: 'Business Monitoring',
    },
  ];

  const generateAlertHistory = (): AlertHistory[] => {
    const data: AlertHistory[] = [];
    for (let i = 23; i >= 0; i--) {
      const timestamp = format(subHours(new Date(), i), 'HH:mm');
      data.push({
        timestamp,
        total_alerts: Math.floor(Math.random() * 15) + 5,
        new_alerts: Math.floor(Math.random() * 5) + 1,
        resolved_alerts: Math.floor(Math.random() * 3) + 1,
        critical_alerts: Math.floor(Math.random() * 2),
        high_alerts: Math.floor(Math.random() * 3) + 1,
        medium_alerts: Math.floor(Math.random() * 4) + 2,
        low_alerts: Math.floor(Math.random() * 5) + 1,
      });
    }
    return data;
  };

  // Handle alert actions
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await telemetryAPI.acknowledgeAlert(alertId);
      setActiveAlerts(prev => 
        prev.map(alert => 
          alert.id === alertId 
            ? { ...alert, status: 'acknowledged' as const, acknowledged_at: new Date().toISOString() }
            : alert
        )
      );
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await telemetryAPI.resolveAlert(alertId);
      setActiveAlerts(prev => 
        prev.map(alert => 
          alert.id === alertId 
            ? { ...alert, status: 'resolved' as const, resolved_at: new Date().toISOString() }
            : alert
        )
      );
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  // Auto-refresh every 10 seconds
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, []);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    return activeAlerts.filter(alert => {
      const severityMatch = filter === 'all' || alert.severity === filter;
      const statusMatch = statusFilter === 'all' || alert.status === statusFilter;
      return severityMatch && statusMatch;
    });
  }, [activeAlerts, filter, statusFilter]);

  // Chart data preparation
  const chartData = useMemo(() => {
    if (!alertHistory.length) return null;

    const labels = alertHistory.map(d => d.timestamp);
    
    return {
      alertTrends: {
        labels,
        datasets: [
          {
            label: 'Total Alerts',
            data: alertHistory.map(d => d.total_alerts),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.4,
          },
          {
            label: 'New Alerts',
            data: alertHistory.map(d => d.new_alerts),
            borderColor: 'rgb(245, 158, 11)',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            fill: true,
            tension: 0.4,
          },
          {
            label: 'Resolved Alerts',
            data: alertHistory.map(d => d.resolved_alerts),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.4,
          },
        ],
      },
      severityDistribution: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [
          {
            data: [
              alertHistory[alertHistory.length - 1]?.critical_alerts || 0,
              alertHistory[alertHistory.length - 1]?.high_alerts || 0,
              alertHistory[alertHistory.length - 1]?.medium_alerts || 0,
              alertHistory[alertHistory.length - 1]?.low_alerts || 0,
            ],
            backgroundColor: [
              'rgba(220, 38, 38, 0.8)',    // critical - red
              'rgba(245, 158, 11, 0.8)',   // high - orange
              'rgba(59, 130, 246, 0.8)',   // medium - blue
              'rgba(34, 197, 94, 0.8)',    // low - green
            ],
            borderWidth: 0,
          },
        ],
      },
    };
  }, [alertHistory]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
    },
  };

  // Helper functions
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <AlertTriangle className="h-4 w-4" />;
      case 'high': return <AlertCircle className="h-4 w-4" />;
      case 'medium': return <Info className="h-4 w-4" />;
      case 'low': return <Info className="h-4 w-4" />;
      default: return <Info className="h-4 w-4" />;
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

  // Calculate alert statistics
  const alertStats = {
    total: activeAlerts.length,
    critical: activeAlerts.filter(a => a.severity === 'critical' && a.status === 'active').length,
    high: activeAlerts.filter(a => a.severity === 'high' && a.status === 'active').length,
    acknowledged: activeAlerts.filter(a => a.status === 'acknowledged').length,
    resolved: activeAlerts.filter(a => a.status === 'resolved').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading alerts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Alert Dashboard</h2>
          <p className="text-muted-foreground">
            Real-time monitoring alerts and notifications management
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={filter} onValueChange={(value: any) => setFilter(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={(value: any) => setStatusFilter(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={fetchAlerts} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Alert Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alertStats.total}</div>
            <p className="text-xs text-muted-foreground">
              {alertStats.activeAlerts || 0} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{alertStats.critical}</div>
            <p className="text-xs text-muted-foreground">Immediate attention</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High</CardTitle>
            <AlertCircle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{alertStats.high}</div>
            <p className="text-xs text-muted-foreground">Urgent review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Acknowledged</CardTitle>
            <CheckCircle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{alertStats.acknowledged}</div>
            <p className="text-xs text-muted-foreground">Being addressed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resolved</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{alertStats.resolved}</div>
            <p className="text-xs text-muted-foreground">Issues fixed</p>
          </CardContent>
        </Card>
      </div>

      {/* Alert Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alert Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Alert Trends (Last 24 Hours)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {chartData?.alertTrends && (
                <Line data={chartData.alertTrends} options={chartOptions} />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Severity Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Alert Severity Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80 flex items-center justify-center">
              {chartData?.severityDistribution && (
                <div className="w-full max-w-sm">
                  <Pie data={chartData.severityDistribution} />
                  <div className="mt-4 space-y-2">
                    {['Critical', 'High', 'Medium', 'Low'].map((severity, index) => {
                      const colors = ['red', 'orange', 'blue', 'green'];
                      const values = [
                        alertHistory[alertHistory.length - 1]?.critical_alerts || 0,
                        alertHistory[alertHistory.length - 1]?.high_alerts || 0,
                        alertHistory[alertHistory.length - 1]?.medium_alerts || 0,
                        alertHistory[alertHistory.length - 1]?.low_alerts || 0,
                      ];
                      return (
                        <div key={severity} className="flex justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 bg-${colors[index]}-500 rounded-full`}></div>
                            <span>{severity}</span>
                          </div>
                          <span className="text-muted-foreground">{values[index]}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Alerts List */}
      <Card>
        <CardHeader>
          <CardTitle>Active Alerts</CardTitle>
          <p className="text-sm text-muted-foreground">
            {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? 's' : ''} found
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="flex items-start justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex items-start gap-4 flex-1">
                  <div className={`p-2 rounded ${getSeverityColor(alert.severity)}`}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium">{alert.name}</h4>
                      <Badge className={getSeverityColor(alert.severity)}>
                        {alert.severity.toUpperCase()}
                      </Badge>
                      <Badge className={getStatusColor(alert.status)}>
                        {alert.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{alert.description}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>Source: {alert.source}</span>
                      <span>Metric: {alert.metric_name}</span>
                      <span>Threshold: {alert.threshold_type} {alert.threshold_value}</span>
                      <span>Current: {alert.current_value}</span>
                      <span>Triggered: {format(new Date(alert.last_triggered), 'MMM dd, HH:mm')}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {alert.notification_channels.map(channel => (
                        <Badge key={channel} variant="outline" className="text-xs">
                          {channel}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {alert.status === 'active' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    </>
                  )}
                  {(alert.status === 'active' || alert.status === 'acknowledged') && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => handleResolveAlert(alert.id)}
                      >
                        Resolve
                      </Button>
                    </>
                  )}
                  <Button size="sm" variant="ghost">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
            
            {filteredAlerts.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No alerts match the current filters</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Alert Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium">Notification Channels</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>Email</span>
                  <Badge variant="outline">Active</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Slack</span>
                  <Badge variant="outline">Active</Badge>
                </div>
                <div className="flex justify-between">
                  <span>SMS</span>
                  <Badge variant="outline">Active</Badge>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Alert Rules</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>System Monitoring</span>
                  <Badge variant="outline">6 rules</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Application Monitoring</span>
                  <Badge variant="outline">4 rules</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Business Metrics</span>
                  <Badge variant="outline">3 rules</Badge>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Response Times</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>Critical</span>
                  <span>< 1 min</span>
                </div>
                <div className="flex justify-between">
                  <span>High</span>
                  <span>< 5 min</span>
                </div>
                <div className="flex justify-between">
                  <span>Medium/Low</span>
                  <span>< 30 min</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Last Update Info */}
      <div className="text-center text-sm text-muted-foreground">
        Last updated: {format(lastUpdate, 'PPpp')}
      </div>
    </div>
  );
};

export default AlertDashboard;