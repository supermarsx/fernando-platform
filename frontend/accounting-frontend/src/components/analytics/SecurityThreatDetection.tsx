import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Progress } from '../ui/progress';
import { 
  Line, Bar, Doughnut, Radar 
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
  RadialLinearScale,
} from 'chart.js';
import { 
  Shield, 
  AlertTriangle, 
  AlertCircle,
  Eye,
  Lock,
  Unlock,
  Users,
  Globe,
  Clock,
  Target,
  Zap,
  TrendingUp,
  RefreshCw,
  Download,
  Filter,
  Search,
  Activity
} from 'lucide-react';
import { format, subHours, subDays, subWeeks, startOfHour, startOfDay, startOfWeek } from 'date-fns';

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
  ArcElement,
  RadialLinearScale
);

interface SecurityEvent {
  id: string;
  timestamp: string;
  eventType: 'authentication_failure' | 'unauthorized_access' | 'malware_detected' | 'ddos_attack' | 'data_breach' | 'suspicious_activity';
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  target: string;
  description: string;
  status: 'active' | 'investigating' | 'resolved' | 'false_positive';
  riskScore: number;
  affectedUsers: number;
  indicators: string[];
  response: string;
}

interface ThreatMetrics {
  totalEvents: number;
  activeThreats: number;
  criticalAlerts: number;
  securityScore: number;
  trendDirection: 'up' | 'down' | 'stable';
  trendPercentage: number;
}

interface SecurityThreatDetectionProps {
  timeRange?: '1h' | '24h' | '7d' | '30d';
  refreshInterval?: number;
  className?: string;
}

const SecurityThreatDetection: React.FC<SecurityThreatDetectionProps> = ({
  timeRange = '24h',
  refreshInterval = 30000,
  className = ''
}) => {
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [metrics, setMetrics] = useState<ThreatMetrics | null>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRange);
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Mock data generation for demonstration
  const generateMockData = (range: string): SecurityEvent[] => {
    const now = new Date();
    let periods: number;
    let events: SecurityEvent[] = [];
    
    const eventTypes: SecurityEvent['eventType'][] = [
      'authentication_failure',
      'unauthorized_access', 
      'malware_detected',
      'ddos_attack',
      'data_breach',
      'suspicious_activity'
    ];
    
    const severities: SecurityEvent['severity'][] = ['low', 'medium', 'high', 'critical'];
    const statuses: SecurityEvent['status'][] = ['active', 'investigating', 'resolved', 'false_positive'];
    const sources = ['192.168.1.100', '203.0.113.45', '198.51.100.23', 'internal_network', 'unknown'];
    const targets = ['api_server', 'database', 'web_app', 'user_account', 'admin_panel'];

    switch (range) {
      case '1h':
        periods = 60;
        break;
      case '24h':
        periods = 24;
        break;
      case '7d':
        periods = 7;
        break;
      case '30d':
        periods = 30;
        break;
      default:
        periods = 24;
    }

    // Generate random events
    const eventCount = Math.floor(Math.random() * periods * 2) + periods;
    
    for (let i = 0; i < eventCount; i++) {
      const timestamp = new Date(now.getTime() - Math.random() * (periods * 24 * 60 * 60 * 1000));
      const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
      const severity = severities[Math.floor(Math.random() * severities.length)];
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      const source = sources[Math.floor(Math.random() * sources.length)];
      const target = targets[Math.floor(Math.random() * targets.length)];
      
      let riskScore = 0;
      let affectedUsers = 0;
      let description = '';

      switch (eventType) {
        case 'authentication_failure':
          riskScore = Math.random() * 30 + 10;
          affectedUsers = Math.floor(Math.random() * 5) + 1;
          description = `Failed login attempts from ${source} to ${target}`;
          break;
        case 'unauthorized_access':
          riskScore = Math.random() * 40 + 30;
          affectedUsers = Math.floor(Math.random() * 10) + 1;
          description = `Unauthorized access attempt from ${source} to ${target}`;
          break;
        case 'malware_detected':
          riskScore = Math.random() * 30 + 70;
          affectedUsers = Math.floor(Math.random() * 20) + 5;
          description = `Malware detected in ${target} from ${source}`;
          break;
        case 'ddos_attack':
          riskScore = Math.random() * 20 + 80;
          affectedUsers = Math.floor(Math.random() * 1000) + 100;
          description = `DDoS attack detected from ${source} targeting ${target}`;
          break;
        case 'data_breach':
          riskScore = Math.random() * 10 + 90;
          affectedUsers = Math.floor(Math.random() * 10000) + 1000;
          description = `Potential data breach detected in ${target}`;
          break;
        case 'suspicious_activity':
          riskScore = Math.random() * 50 + 20;
          affectedUsers = Math.floor(Math.random() * 50) + 5;
          description = `Suspicious activity detected from ${source} to ${target}`;
          break;
      }

      // Adjust risk score based on severity
      const severityMultiplier = { low: 0.5, medium: 0.7, high: 0.85, critical: 1.0 }[severity];
      riskScore *= severityMultiplier;

      events.push({
        id: `event_${i}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: timestamp.toISOString(),
        eventType,
        severity,
        status,
        source,
        target,
        description,
        riskScore: Math.round(riskScore),
        affectedUsers,
        indicators: [
          'unusual_pattern',
          'multiple_failed_attempts',
          'geographic_anomaly',
          'time_based_anomaly'
        ].slice(0, Math.floor(Math.random() * 3) + 1),
        response: status === 'resolved' ? 'Automated response executed' : 'Pending investigation',
      });
    }

    return events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  };

  const calculateMetrics = (events: SecurityEvent[]): ThreatMetrics => {
    if (events.length === 0) {
      return {
        totalEvents: 0,
        activeThreats: 0,
        criticalAlerts: 0,
        securityScore: 100,
        trendDirection: 'stable',
        trendPercentage: 0,
      };
    }

    const totalEvents = events.length;
    const activeThreats = events.filter(e => e.status === 'active').length;
    const criticalAlerts = events.filter(e => e.severity === 'critical' && e.status !== 'resolved').length;
    
    // Calculate security score based on events
    const highRiskEvents = events.filter(e => e.riskScore >= 80).length;
    const mediumRiskEvents = events.filter(e => e.riskScore >= 50 && e.riskScore < 80).length;
    const lowRiskEvents = events.filter(e => e.riskScore < 50).length;
    
    const securityScore = Math.max(0, 100 - (highRiskEvents * 15) - (mediumRiskEvents * 8) - (lowRiskEvents * 2));

    // Calculate trend
    const midPoint = Math.floor(events.length / 2);
    const firstHalf = events.slice(0, midPoint);
    const secondHalf = events.slice(midPoint);
    
    const firstHalfRisk = firstHalf.reduce((sum, e) => sum + e.riskScore, 0) / firstHalf.length;
    const secondHalfRisk = secondHalf.reduce((sum, e) => sum + e.riskScore, 0) / secondHalf.length;
    
    let trendDirection: 'up' | 'down' | 'stable' = 'stable';
    let trendPercentage = 0;

    if (firstHalfRisk > 0) {
      const change = ((secondHalfRisk - firstHalfRisk) / firstHalfRisk) * 100;
      trendPercentage = Math.abs(change);
      if (change > 5) trendDirection = 'up';
      else if (change < -5) trendDirection = 'down';
    }

    return {
      totalEvents,
      activeThreats,
      criticalAlerts,
      securityScore: Math.round(securityScore),
      trendDirection,
      trendPercentage,
    };
  };

  const fetchSecurityEvents = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // In a real implementation, this would call the backend forensic services
      // For now, we'll generate mock data
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      const data = generateMockData(selectedTimeRange);
      setSecurityEvents(data);
      setMetrics(calculateMetrics(data));
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to fetch security events');
      console.error('Error fetching security events:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityEvents();
  }, [selectedTimeRange, selectedSeverity, selectedStatus]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchSecurityEvents();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const filteredEvents = useMemo(() => {
    return securityEvents.filter(event => {
      if (selectedSeverity !== 'all' && event.severity !== selectedSeverity) return false;
      if (selectedStatus !== 'all' && event.status !== selectedStatus) return false;
      return true;
    });
  }, [securityEvents, selectedSeverity, selectedStatus]);

  const eventTrendData = useMemo(() => {
    if (!filteredEvents.length) return null;

    const now = new Date();
    const periods = selectedTimeRange === '1h' ? 60 : selectedTimeRange === '24h' ? 24 : 7;
    const labels = [];
    const data = [];

    for (let i = periods - 1; i >= 0; i--) {
      const timestamp = selectedTimeRange === '1h' 
        ? startOfHour(new Date(now.getTime() - i * 60 * 60 * 1000))
        : startOfDay(new Date(now.getTime() - i * 24 * 60 * 60 * 1000));
      
      const label = selectedTimeRange === '1h' ? format(timestamp, 'HH:mm') : format(timestamp, 'MMM dd');
      labels.push(label);
      
      const eventsInPeriod = filteredEvents.filter(event => {
        const eventDate = new Date(event.timestamp);
        return eventDate >= timestamp && 
               eventDate < new Date(timestamp.getTime() + 
                 (selectedTimeRange === '1h' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000));
      }).length;
      
      data.push(eventsInPeriod);
    }

    return {
      labels,
      datasets: [
        {
          label: 'Security Events',
          data,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    };
  }, [filteredEvents, selectedTimeRange]);

  const threatDistributionData = useMemo(() => {
    if (!filteredEvents.length) return null;

    const distribution = filteredEvents.reduce((acc, event) => {
      acc[event.eventType] = (acc[event.eventType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      labels: Object.keys(distribution),
      datasets: [
        {
          data: Object.values(distribution),
          backgroundColor: [
            'rgba(239, 68, 68, 0.8)',
            'rgba(245, 158, 11, 0.8)',
            'rgba(59, 130, 246, 0.8)',
            'rgba(16, 185, 129, 0.8)',
            'rgba(139, 92, 246, 0.8)',
            'rgba(236, 72, 153, 0.8)',
          ],
          borderColor: [
            'rgb(239, 68, 68)',
            'rgb(245, 158, 11)',
            'rgb(59, 130, 246)',
            'rgb(16, 185, 129)',
            'rgb(139, 92, 246)',
            'rgb(236, 72, 153)',
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [filteredEvents]);

  const severityDistributionData = useMemo(() => {
    if (!filteredEvents.length) return null;

    const distribution = filteredEvents.reduce((acc, event) => {
      acc[event.severity] = (acc[event.severity] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const order = ['low', 'medium', 'high', 'critical'];
    
    return {
      labels: order,
      datasets: [
        {
          label: 'Events by Severity',
          data: order.map(severity => distribution[severity] || 0),
          backgroundColor: [
            'rgba(16, 185, 129, 0.8)',
            'rgba(245, 158, 11, 0.8)',
            'rgba(239, 68, 68, 0.8)',
            'rgba(127, 29, 29, 0.8)',
          ],
          borderColor: [
            'rgb(16, 185, 129)',
            'rgb(245, 158, 11)',
            'rgb(239, 68, 68)',
            'rgb(127, 29, 29)',
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [filteredEvents]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Event Count',
        },
        beginAtZero: true,
      },
    },
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'bg-green-500';
      case 'medium': return 'bg-yellow-500';
      case 'high': return 'bg-orange-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType) {
      case 'authentication_failure': return <Lock className="h-4 w-4" />;
      case 'unauthorized_access': return <Unlock className="h-4 w-4" />;
      case 'malware_detected': return <Shield className="h-4 w-4" />;
      case 'ddos_attack': return <Zap className="h-4 w-4" />;
      case 'data_breach': return <AlertTriangle className="h-4 w-4" />;
      case 'suspicious_activity': return <Eye className="h-4 w-4" />;
      default: return <Activity className="h-4 w-4" />;
    }
  };

  const exportData = () => {
    const dataToExport = {
      events: filteredEvents,
      metrics,
      exportedAt: new Date().toISOString(),
      timeRange: selectedTimeRange,
      filters: {
        severity: selectedSeverity,
        status: selectedStatus,
      },
    };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-events-${selectedTimeRange}-${format(new Date(), 'yyyy-MM-dd')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">{error}</span>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchSecurityEvents}
            className="ml-auto"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Security Threat Detection</h2>
          <p className="text-muted-foreground">
            Monitor security events, detect threats, and track incident response
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            Last update: {format(lastUpdate, 'HH:mm:ss')}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchSecurityEvents}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportData}>
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center">
            <Filter className="h-5 w-5 mr-2" />
            Filters & Controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Time Range</label>
              <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select time range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">Last Hour</SelectItem>
                  <SelectItem value="24h">Last 24 Hours</SelectItem>
                  <SelectItem value="7d">Last 7 Days</SelectItem>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Severity</label>
              <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                <SelectTrigger>
                  <SelectValue placeholder="Select severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="investigating">Investigating</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="false_positive">False Positive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Security Score</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.securityScore}/100</div>
              <Progress value={metrics.securityScore} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Threats</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.activeThreats}</div>
              <div className="text-xs text-muted-foreground">
                {metrics.criticalAlerts} critical
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Events</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.totalEvents}</div>
              <div className="flex items-center text-xs text-muted-foreground">
                <TrendingUp className="h-3 w-3 mr-1" />
                {metrics.trendPercentage.toFixed(1)}% {metrics.trendDirection}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Alerts</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.criticalAlerts}</div>
              <div className="text-xs text-muted-foreground">
                Require immediate attention
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Event Trends</TabsTrigger>
          <TabsTrigger value="distribution">Distribution</TabsTrigger>
          <TabsTrigger value="events">Recent Events</TabsTrigger>
        </TabsList>
        
        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Event Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {eventTrendData && <Line data={eventTrendData} options={chartOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="distribution" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Threat Types</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  {threatDistributionData && <Doughnut data={threatDistributionData} options={{ responsive: true, maintainAspectRatio: false }} />}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Severity Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  {severityDistributionData && <Bar data={severityDistributionData} options={chartOptions} />}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="events" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Security Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {filteredEvents.slice(0, 10).map(event => (
                  <div key={event.id} className="flex items-start justify-between p-4 border rounded-lg">
                    <div className="flex items-start space-x-3">
                      <div className={`p-2 rounded-full ${getSeverityColor(event.severity)} text-white`}>
                        {getEventTypeIcon(event.eventType)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium">{event.description}</h4>
                          <Badge variant={event.severity === 'critical' ? 'destructive' : event.severity === 'high' ? 'secondary' : 'outline'}>
                            {event.severity}
                          </Badge>
                          <Badge variant="outline">{event.status}</Badge>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground mt-1">
                          <span className="flex items-center">
                            <Clock className="h-3 w-3 mr-1" />
                            {format(new Date(event.timestamp), 'MMM dd, HH:mm:ss')}
                          </span>
                          <span className="flex items-center">
                            <Target className="h-3 w-3 mr-1" />
                            Risk: {event.riskScore}
                          </span>
                          <span className="flex items-center">
                            <Users className="h-3 w-3 mr-1" />
                            {event.affectedUsers} affected
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Source: {event.source} → Target: {event.target}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {filteredEvents.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    No security events found for the selected filters.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SecurityThreatDetection;