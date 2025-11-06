import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Progress } from '../ui/progress';
import { 
  Line, Bar, Area, Scatter 
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
  Filler,
} from 'chart.js';
import { 
  Activity, 
  Zap, 
  Clock,
  Cpu,
  HardDrive,
  Wifi,
  Database,
  Server,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Download,
  Filter,
  Target,
  Timer,
  BarChart3,
  LineChart,
  Gauge
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
  Filler
);

interface PerformanceMetrics {
  timestamp: string;
  cpuUsage: number;
  memoryUsage: number;
  responseTime: number;
  throughput: number;
  errorRate: number;
  databaseConnections: number;
  activeUsers: number;
  diskUsage: number;
  networkLatency: number;
}

interface PerformanceSummary {
  avgResponseTime: number;
  peakResponseTime: number;
  minResponseTime: number;
  throughputPerSecond: number;
  errorRate: number;
  systemLoad: number;
  performanceScore: number;
  trendDirection: 'up' | 'down' | 'stable';
  trendPercentage: number;
  recommendations: string[];
}

interface PerformanceAnalyticsProps {
  timeRange?: '1h' | '24h' | '7d' | '30d';
  refreshInterval?: number;
  className?: string;
}

const PerformanceAnalytics: React.FC<PerformanceAnalyticsProps> = ({
  timeRange = '24h',
  refreshInterval = 30000,
  className = ''
}) => {
  const [performanceData, setPerformanceData] = useState<PerformanceMetrics[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRange);
  const [selectedMetric, setSelectedMetric] = useState('responseTime');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Mock data generation for demonstration
  const generateMockData = (range: string): PerformanceMetrics[] => {
    const now = new Date();
    let periods: number;
    let interval: string;
    let data: PerformanceMetrics[] = [];

    switch (range) {
      case '1h':
        interval = 'minute';
        periods = 60;
        for (let i = periods - 1; i >= 0; i--) {
          const timestamp = startOfHour(new Date(now.getTime() - i * 60 * 1000));
          data.push({
            timestamp: timestamp.toISOString(),
            cpuUsage: Math.random() * 40 + 20,
            memoryUsage: Math.random() * 30 + 40,
            responseTime: Math.random() * 200 + 100,
            throughput: Math.random() * 500 + 100,
            errorRate: Math.random() * 2,
            databaseConnections: Math.floor(Math.random() * 50) + 20,
            activeUsers: Math.floor(Math.random() * 100) + 50,
            diskUsage: Math.random() * 20 + 60,
            networkLatency: Math.random() * 50 + 20,
          });
        }
        break;
      case '24h':
        interval = 'hour';
        periods = 24;
        for (let i = periods - 1; i >= 0; i--) {
          const timestamp = startOfHour(new Date(now.getTime() - i * 60 * 60 * 1000));
          data.push({
            timestamp: timestamp.toISOString(),
            cpuUsage: Math.random() * 50 + 25,
            memoryUsage: Math.random() * 35 + 45,
            responseTime: Math.random() * 300 + 150,
            throughput: Math.random() * 2000 + 500,
            errorRate: Math.random() * 3,
            databaseConnections: Math.floor(Math.random() * 100) + 50,
            activeUsers: Math.floor(Math.random() * 500) + 200,
            diskUsage: Math.random() * 25 + 65,
            networkLatency: Math.random() * 80 + 30,
          });
        }
        break;
      case '7d':
        interval = 'day';
        periods = 7;
        for (let i = periods - 1; i >= 0; i--) {
          const timestamp = startOfDay(new Date(now.getTime() - i * 24 * 60 * 60 * 1000));
          data.push({
            timestamp: timestamp.toISOString(),
            cpuUsage: Math.random() * 60 + 30,
            memoryUsage: Math.random() * 40 + 50,
            responseTime: Math.random() * 400 + 200,
            throughput: Math.random() * 5000 + 1000,
            errorRate: Math.random() * 4,
            databaseConnections: Math.floor(Math.random() * 200) + 100,
            activeUsers: Math.floor(Math.random() * 2000) + 500,
            diskUsage: Math.random() * 30 + 70,
            networkLatency: Math.random() * 100 + 40,
          });
        }
        break;
      case '30d':
        interval = 'day';
        periods = 30;
        for (let i = periods - 1; i >= 0; i--) {
          const timestamp = startOfDay(new Date(now.getTime() - i * 24 * 60 * 60 * 1000));
          data.push({
            timestamp: timestamp.toISOString(),
            cpuUsage: Math.random() * 70 + 35,
            memoryUsage: Math.random() * 45 + 55,
            responseTime: Math.random() * 500 + 250,
            throughput: Math.random() * 10000 + 2000,
            errorRate: Math.random() * 5,
            databaseConnections: Math.floor(Math.random() * 300) + 150,
            activeUsers: Math.floor(Math.random() * 5000) + 1000,
            diskUsage: Math.random() * 35 + 75,
            networkLatency: Math.random() * 120 + 50,
          });
        }
        break;
    }

    return data;
  };

  const calculateSummary = (data: PerformanceMetrics[]): PerformanceSummary => {
    if (data.length === 0) {
      return {
        avgResponseTime: 0,
        peakResponseTime: 0,
        minResponseTime: 0,
        throughputPerSecond: 0,
        errorRate: 0,
        systemLoad: 0,
        performanceScore: 100,
        trendDirection: 'stable',
        trendPercentage: 0,
        recommendations: [],
      };
    }

    const responseTimes = data.map(d => d.responseTime);
    const errorRates = data.map(d => d.errorRate);
    const cpuUsages = data.map(d => d.cpuUsage);
    const memoryUsages = data.map(d => d.memoryUsage);

    const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
    const peakResponseTime = Math.max(...responseTimes);
    const minResponseTime = Math.min(...responseTimes);
    const avgErrorRate = errorRates.reduce((sum, rate) => sum + rate, 0) / errorRates.length;
    const avgCpu = cpuUsages.reduce((sum, cpu) => sum + cpu, 0) / cpuUsages.length;
    const avgMemory = memoryUsages.reduce((sum, mem) => sum + mem, 0) / memoryUsages.length;

    const throughputPerSecond = data.reduce((sum, d) => sum + d.throughput, 0) / data.length / 
      (selectedTimeRange === '1h' ? 3600 : selectedTimeRange === '24h' ? 86400 : 86400);

    const systemLoad = (avgCpu + avgMemory) / 2;

    // Calculate performance score
    let performanceScore = 100;
    if (avgResponseTime > 500) performanceScore -= 20;
    else if (avgResponseTime > 200) performanceScore -= 10;
    if (avgErrorRate > 2) performanceScore -= 15;
    else if (avgErrorRate > 1) performanceScore -= 8;
    if (avgCpu > 80) performanceScore -= 15;
    else if (avgCpu > 60) performanceScore -= 8;
    if (avgMemory > 85) performanceScore -= 12;
    else if (avgMemory > 70) performanceScore -= 6;

    // Calculate trend
    const midPoint = Math.floor(data.length / 2);
    const firstHalf = data.slice(0, midPoint).map(d => d.responseTime);
    const secondHalf = data.slice(midPoint).map(d => d.responseTime);
    
    const firstHalfAvg = firstHalf.reduce((sum, time) => sum + time, 0) / firstHalf.length;
    const secondHalfAvg = secondHalf.reduce((sum, time) => sum + time, 0) / secondHalf.length;
    
    let trendDirection: 'up' | 'down' | 'stable' = 'stable';
    let trendPercentage = 0;

    if (firstHalfAvg > 0) {
      const change = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100;
      trendPercentage = Math.abs(change);
      if (change > 5) trendDirection = 'up'; // Response time increasing
      else if (change < -5) trendDirection = 'down'; // Response time decreasing
    }

    // Generate recommendations
    const recommendations: string[] = [];
    if (avgResponseTime > 300) {
      recommendations.push('Consider optimizing database queries and API endpoints');
    }
    if (avgErrorRate > 2) {
      recommendations.push('Investigate high error rate - check error logs for patterns');
    }
    if (avgCpu > 70) {
      recommendations.push('CPU usage is high - consider scaling horizontally');
    }
    if (avgMemory > 80) {
      recommendations.push('Memory usage is high - check for memory leaks');
    }
    if (throughputPerSecond < 100) {
      recommendations.push('Low throughput detected - optimize application performance');
    }

    return {
      avgResponseTime,
      peakResponseTime,
      minResponseTime,
      throughputPerSecond,
      errorRate: avgErrorRate,
      systemLoad,
      performanceScore,
      trendDirection,
      trendPercentage,
      recommendations,
    };
  };

  const fetchPerformanceData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // In a real implementation, this would call backend services
      // For now, we'll generate mock data
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      const data = generateMockData(selectedTimeRange);
      setPerformanceData(data);
      setSummary(calculateSummary(data));
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to fetch performance data');
      console.error('Error fetching performance data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData();
  }, [selectedTimeRange, selectedMetric]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchPerformanceData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const performanceChartData = useMemo(() => {
    if (!performanceData.length) return null;

    const labels = performanceData.map(item => {
      const date = new Date(item.timestamp);
      switch (selectedTimeRange) {
        case '1h':
          return format(date, 'HH:mm');
        case '24h':
          return format(date, 'HH:mm');
        case '7d':
          return format(date, 'MMM dd');
        case '30d':
          return format(date, 'MMM dd');
        default:
          return format(date, 'HH:mm');
      }
    });

    const getMetricData = (metric: keyof PerformanceMetrics) => {
      return performanceData.map(item => item[metric]);
    };

    const getMetricLabel = (metric: string) => {
      switch (metric) {
        case 'responseTime': return 'Response Time (ms)';
        case 'throughput': return 'Throughput (req/min)';
        case 'cpuUsage': return 'CPU Usage (%)';
        case 'memoryUsage': return 'Memory Usage (%)';
        case 'errorRate': return 'Error Rate (%)';
        default: return metric;
      }
    };

    const getMetricColor = (metric: string) => {
      switch (metric) {
        case 'responseTime': return 'rgb(239, 68, 68)';
        case 'throughput': return 'rgb(16, 185, 129)';
        case 'cpuUsage': return 'rgb(245, 158, 11)';
        case 'memoryUsage': return 'rgb(59, 130, 246)';
        case 'errorRate': return 'rgb(139, 92, 246)';
        default: return 'rgb(107, 114, 128)';
      }
    };

    return {
      labels,
      datasets: [
        {
          label: getMetricLabel(selectedMetric),
          data: getMetricData(selectedMetric as keyof PerformanceMetrics),
          borderColor: getMetricColor(selectedMetric),
          backgroundColor: getMetricColor(selectedMetric) + '20',
          fill: selectedMetric === 'responseTime' || selectedMetric === 'throughput',
          tension: 0.4,
        },
      ],
    };
  }, [performanceData, selectedTimeRange, selectedMetric]);

  const systemResourcesData = useMemo(() => {
    if (!performanceData.length) return null;

    const latestData = performanceData[performanceData.length - 1];

    return {
      labels: ['CPU', 'Memory', 'Disk', 'Network'],
      datasets: [
        {
          label: 'Resource Usage (%)',
          data: [
            latestData.cpuUsage,
            latestData.memoryUsage,
            latestData.diskUsage,
            Math.min(latestData.networkLatency, 100), // Cap network at 100% for display
          ],
          backgroundColor: [
            latestData.cpuUsage > 80 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(34, 197, 94, 0.8)',
            latestData.memoryUsage > 85 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(34, 197, 94, 0.8)',
            latestData.diskUsage > 90 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(34, 197, 94, 0.8)',
            latestData.networkLatency > 100 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(34, 197, 94, 0.8)',
          ],
          borderColor: [
            latestData.cpuUsage > 80 ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)',
            latestData.memoryUsage > 85 ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)',
            latestData.diskUsage > 90 ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)',
            latestData.networkLatency > 100 ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)',
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [performanceData]);

  const correlationData = useMemo(() => {
    if (!performanceData.length) return null;

    return {
      datasets: [
        {
          label: 'Response Time vs Throughput',
          data: performanceData.map(item => ({
            x: item.throughput,
            y: item.responseTime,
          })),
          backgroundColor: 'rgba(59, 130, 246, 0.6)',
          borderColor: 'rgb(59, 130, 246)',
          pointRadius: 4,
        },
      ],
    };
  }, [performanceData]);

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
          text: selectedMetric === 'responseTime' ? 'Response Time (ms)' : 
                selectedMetric === 'throughput' ? 'Throughput' : 'Percentage',
        },
        beginAtZero: true,
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
  };

  const scatterOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Throughput',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Response Time (ms)',
        },
      },
    },
  };

  const exportData = () => {
    const dataToExport = {
      performance: performanceData,
      summary,
      exportedAt: new Date().toISOString(),
      timeRange: selectedTimeRange,
      selectedMetric,
    };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-analytics-${selectedTimeRange}-${format(new Date(), 'yyyy-MM-dd')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getPerformanceColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
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
            onClick={fetchPerformanceData}
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
          <h2 className="text-2xl font-bold tracking-tight">Performance Analytics</h2>
          <p className="text-muted-foreground">
            Monitor system performance, response times, and resource utilization
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            Last update: {format(lastUpdate, 'HH:mm:ss')}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchPerformanceData}
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

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center">
            <Filter className="h-5 w-5 mr-2" />
            Performance Controls
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
              <label className="text-sm font-medium mb-2 block">Metric</label>
              <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                <SelectTrigger>
                  <SelectValue placeholder="Select metric" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="responseTime">Response Time</SelectItem>
                  <SelectItem value="throughput">Throughput</SelectItem>
                  <SelectItem value="cpuUsage">CPU Usage</SelectItem>
                  <SelectItem value="memoryUsage">Memory Usage</SelectItem>
                  <SelectItem value="errorRate">Error Rate</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Performance Score</CardTitle>
              <Gauge className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getPerformanceColor(summary.performanceScore)}`}>
                {summary.performanceScore}/100
              </div>
              <Progress value={summary.performanceScore} className="mt-2" />
              <div className="flex items-center text-xs text-muted-foreground mt-2">
                {summary.trendDirection === 'up' && <TrendingUp className="h-3 w-3 text-green-500 mr-1" />}
                {summary.trendDirection === 'down' && <TrendingDown className="h-3 w-3 text-red-500 mr-1" />}
                {summary.trendDirection === 'stable' && <CheckCircle2 className="h-3 w-3 text-blue-500 mr-1" />}
                {summary.trendPercentage.toFixed(1)}% {summary.trendDirection}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
              <Timer className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.avgResponseTime.toFixed(0)}ms</div>
              <div className="text-xs text-muted-foreground">
                Min: {summary.minResponseTime.toFixed(0)}ms | Max: {summary.peakResponseTime.toFixed(0)}ms
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Throughput</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.throughputPerSecond.toFixed(1)}/sec</div>
              <div className="text-xs text-muted-foreground">
                Requests per second
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Load</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.systemLoad.toFixed(1)}%</div>
              <div className="text-xs text-muted-foreground">
                CPU + Memory average
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Performance Trends</TabsTrigger>
          <TabsTrigger value="resources">System Resources</TabsTrigger>
          <TabsTrigger value="correlation">Correlation Analysis</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
        </TabsList>
        
        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {performanceChartData && <Line data={performanceChartData} options={chartOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resources" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current System Resources</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {systemResourcesData && <Bar data={systemResourcesData} options={chartOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="correlation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Response Time vs Throughput Correlation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {correlationData && <Scatter data={correlationData} options={scatterOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {summary?.recommendations.length ? (
                  summary.recommendations.map((recommendation, index) => (
                    <div key={index} className="flex items-start space-x-3 p-4 border rounded-lg">
                      <Target className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div>
                        <p className="text-sm">{recommendation}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No recommendations at this time. System performance is optimal.
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

export default PerformanceAnalytics;