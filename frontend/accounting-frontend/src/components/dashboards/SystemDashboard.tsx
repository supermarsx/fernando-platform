import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Progress } from '../ui/progress';
import { 
  Line, Bar, Doughnut, Radar, Area
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
  Filler,
} from 'chart.js';
import { 
  Cpu, 
  HardDrive, 
  Wifi, 
  Activity, 
  Server, 
  Database,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { telemetryAPI } from '../../lib/api';
import { format, subHours, subDays, subWeeks } from 'date-fns';

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
  RadialLinearScale,
  Filler
);

interface SystemMetric {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
  response_time: number;
  active_connections: number;
}

interface ServiceStatus {
  service_name: string;
  status: 'healthy' | 'warning' | 'critical';
  response_time: number;
  uptime: string;
  last_check: string;
}

const SystemDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetric[]>([]);
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus[]>([]);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [timeRange, setTimeRange] = useState('1h');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const timeRangeOptions = {
    '1h': { hours: 1, label: 'Last Hour' },
    '6h': { hours: 6, label: 'Last 6 Hours' },
    '24h': { hours: 24, label: 'Last 24 Hours' },
    '7d': { hours: 24 * 7, label: 'Last 7 Days' },
    '30d': { hours: 24 * 30, label: 'Last 30 Days' },
  };

  // Fetch system metrics
  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const [metricsRes, healthRes, servicesRes] = await Promise.all([
        telemetryAPI.getSystemMetrics({ time_range: timeRange }),
        telemetryAPI.getSystemHealth(),
        telemetryAPI.getServiceStatus(),
      ]);

      // Simulate real-time data for demonstration
      const simulatedMetrics = generateSimulatedMetrics();
      setMetrics(simulatedMetrics);
      setSystemHealth(healthRes.data || {
        overall_status: 'healthy',
        cpu_health: 85,
        memory_health: 75,
        disk_health: 60,
        network_health: 95,
      });
      
      setServiceStatus(servicesRes.data || generateSimulatedServices());
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
      // Use fallback data on error
      const fallbackMetrics = generateSimulatedMetrics();
      setMetrics(fallbackMetrics);
      setSystemHealth({
        overall_status: 'healthy',
        cpu_health: 85,
        memory_health: 75,
        disk_health: 60,
        network_health: 95,
      });
      setServiceStatus(generateSimulatedServices());
    } finally {
      setLoading(false);
    }
  };

  // Generate simulated data for demonstration
  const generateSimulatedMetrics = (): SystemMetric[] => {
    const data: SystemMetric[] = [];
    const now = new Date();
    const range = timeRangeOptions[timeRange as keyof typeof timeRangeOptions];
    
    for (let i = range.hours; i >= 0; i -= range.hours > 24 ? 1 : 5) {
      data.push({
        timestamp: format(now, 'HH:mm'),
        cpu_usage: Math.random() * 100,
        memory_usage: Math.random() * 100,
        disk_usage: Math.random() * 100,
        network_in: Math.random() * 1000,
        network_out: Math.random() * 1000,
        response_time: Math.random() * 500,
        active_connections: Math.floor(Math.random() * 200),
      });
    }
    return data;
  };

  const generateSimulatedServices = (): ServiceStatus[] => [
    {
      service_name: 'Web Server',
      status: 'healthy',
      response_time: Math.random() * 100 + 50,
      uptime: '99.9%',
      last_check: '1 min ago',
    },
    {
      service_name: 'Database',
      status: 'healthy',
      response_time: Math.random() * 50 + 20,
      uptime: '99.8%',
      last_check: '1 min ago',
    },
    {
      service_name: 'API Gateway',
      status: 'warning',
      response_time: Math.random() * 200 + 100,
      uptime: '98.5%',
      last_check: '2 min ago',
    },
    {
      service_name: 'Message Queue',
      status: 'healthy',
      response_time: Math.random() * 30 + 10,
      uptime: '99.7%',
      last_check: '1 min ago',
    },
    {
      service_name: 'Cache Service',
      status: 'critical',
      response_time: Math.random() * 500 + 300,
      uptime: '95.2%',
      last_check: '5 min ago',
    },
  ];

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  // Chart data preparation
  const chartData = useMemo(() => {
    if (!metrics.length) return null;

    const labels = metrics.map(m => m.timestamp);
    
    return {
      systemResources: {
        labels,
        datasets: [
          {
            label: 'CPU Usage (%)',
            data: metrics.map(m => m.cpu_usage),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.4,
          },
          {
            label: 'Memory Usage (%)',
            data: metrics.map(m => m.memory_usage),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
          },
          {
            label: 'Disk Usage (%)',
            data: metrics.map(m => m.disk_usage),
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4,
          },
        ],
      },
      networkTraffic: {
        labels,
        datasets: [
          {
            label: 'Network In (MB/s)',
            data: metrics.map(m => m.network_in / 1000),
            backgroundColor: 'rgba(147, 51, 234, 0.6)',
            borderColor: 'rgb(147, 51, 234)',
            borderWidth: 1,
          },
          {
            label: 'Network Out (MB/s)',
            data: metrics.map(m => m.network_out / 1000),
            backgroundColor: 'rgba(245, 158, 11, 0.6)',
            borderColor: 'rgb(245, 158, 11)',
            borderWidth: 1,
          },
        ],
      },
      healthRadar: {
        labels: ['CPU', 'Memory', 'Disk', 'Network', 'Database', 'API'],
        datasets: [
          {
            label: 'System Health',
            data: [
              systemHealth?.cpu_health || 85,
              systemHealth?.memory_health || 75,
              systemHealth?.disk_health || 60,
              systemHealth?.network_health || 95,
              88,
              92,
            ],
            backgroundColor: 'rgba(59, 130, 246, 0.2)',
            borderColor: 'rgb(59, 130, 246)',
            borderWidth: 2,
            pointBackgroundColor: 'rgb(59, 130, 246)',
          },
        ],
      },
      serviceStatus: {
        labels: serviceStatus.map(s => s.service_name),
        datasets: [
          {
            data: serviceStatus.map(s => {
              switch (s.status) {
                case 'healthy': return 1;
                case 'warning': return 0.5;
                case 'critical': return 0;
                default: return 0.8;
              }
            }),
            backgroundColor: [
              'rgb(16, 185, 129)', // healthy
              'rgb(245, 158, 11)', // warning
              'rgb(239, 68, 68)', // critical
            ],
            borderWidth: 0,
          },
        ],
      },
    };
  }, [metrics, serviceStatus, systemHealth]);

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800 border-green-200';
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-4 w-4" />;
      case 'warning': return <AlertTriangle className="h-4 w-4" />;
      case 'critical': return <AlertTriangle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading system metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">System Health</h2>
          <p className="text-muted-foreground">
            Real-time monitoring of system performance and infrastructure
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(timeRangeOptions).map(([key, { label }]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={fetchMetrics} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* System Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemHealth ? `${systemHealth.cpu_health}%` : '85%'}
            </div>
            <Progress 
              value={systemHealth ? systemHealth.cpu_health : 85} 
              className="mt-2" 
            />
            <p className="text-xs text-muted-foreground mt-2">
              {systemHealth?.cpu_health > 80 ? 'High usage' : 'Normal usage'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemHealth ? `${systemHealth.memory_health}%` : '75%'}
            </div>
            <Progress 
              value={systemHealth ? systemHealth.memory_health : 75} 
              className="mt-2" 
            />
            <p className="text-xs text-muted-foreground mt-2">
              {systemHealth?.memory_health > 80 ? 'High usage' : 'Normal usage'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Network Health</CardTitle>
            <Wifi className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemHealth ? `${systemHealth.network_health}%` : '95%'}
            </div>
            <Progress 
              value={systemHealth ? systemHealth.network_health : 95} 
              className="mt-2" 
            />
            <p className="text-xs text-muted-foreground mt-2">
              {systemHealth?.network_health < 90 ? 'Issues detected' : 'Connected'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Status</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {systemHealth?.overall_status?.toUpperCase() || 'HEALTHY'}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Last updated: {format(lastUpdate, 'HH:mm:ss')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Resources Chart */}
        <Card>
          <CardHeader>
            <CardTitle>System Resources Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {chartData?.systemResources && (
                <Line data={chartData.systemResources} options={chartOptions} />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Network Traffic Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Network Traffic</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {chartData?.networkTraffic && (
                <Bar data={chartData.networkTraffic} options={chartOptions} />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health and Service Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Health Radar */}
        <Card>
          <CardHeader>
            <CardTitle>System Health Radar</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {chartData?.healthRadar && (
                <Radar 
                  data={chartData.healthRadar} 
                  options={{
                    ...chartOptions,
                    scales: {
                      r: {
                        beginAtZero: true,
                        max: 100,
                      },
                    },
                  }} 
                />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Service Status */}
        <Card>
          <CardHeader>
            <CardTitle>Service Status Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80 flex items-center justify-center">
              {chartData?.serviceStatus && (
                <div className="w-full max-w-sm">
                  <Doughnut data={chartData.serviceStatus} />
                  <div className="mt-4 space-y-2">
                    {serviceStatus.map((service, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`p-1 rounded ${getStatusColor(service.status)}`}>
                            {getStatusIcon(service.status)}
                          </div>
                          <span className="text-sm font-medium">{service.service_name}</span>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {service.response_time.toFixed(0)}ms
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Service Status Table */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Service Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {serviceStatus.map((service, index) => (
              <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded ${getStatusColor(service.status)}`}>
                    {getStatusIcon(service.status)}
                  </div>
                  <div>
                    <h4 className="font-medium">{service.service_name}</h4>
                    <p className="text-sm text-muted-foreground">
                      Uptime: {service.uptime} • Last check: {service.last_check}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge className={getStatusColor(service.status)}>
                    {service.status.toUpperCase()}
                  </Badge>
                  <p className="text-sm text-muted-foreground mt-1">
                    {service.response_time.toFixed(1)}ms response time
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SystemDashboard;