import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  Line, Bar, Area 
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
  TrendingUp, 
  TrendingDown, 
  Activity,
  Filter,
  Download,
  RefreshCw,
  Calendar,
  Search,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { format, subHours, subDays, subWeeks, subMonths, startOfHour, startOfDay, startOfWeek, startOfMonth } from 'date-fns';

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

interface LogTrendData {
  timestamp: string;
  logCount: number;
  errorCount: number;
  warningCount: number;
  infoCount: number;
  debugCount: number;
  avgResponseTime: number;
  throughput: number;
}

interface TrendMetrics {
  totalLogs: number;
  errorRate: number;
  warningRate: number;
  avgResponseTime: number;
  trendDirection: 'up' | 'down' | 'stable';
  trendPercentage: number;
}

interface LogTrendAnalysisProps {
  timeRange?: '1h' | '24h' | '7d' | '30d';
  refreshInterval?: number;
  className?: string;
}

const LogTrendAnalysis: React.FC<LogTrendAnalysisProps> = ({
  timeRange = '24h',
  refreshInterval = 30000,
  className = ''
}) => {
  const [logTrends, setLogTrends] = useState<LogTrendData[]>([]);
  const [metrics, setMetrics] = useState<TrendMetrics | null>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRange);
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [selectedSource, setSelectedSource] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Mock data generation for demonstration
  const generateMockData = (range: string): LogTrendData[] => {
    const now = new Date();
    let interval: string;
    let periods: number;
    let data: LogTrendData[] = [];

    switch (range) {
      case '1h':
        interval = 'hour';
        periods = 60;
        for (let i = periods - 1; i >= 0; i--) {
          const timestamp = startOfHour(new Date(now.getTime() - i * 60 * 60 * 1000));
          data.push({
            timestamp: timestamp.toISOString(),
            logCount: Math.floor(Math.random() * 1000) + 500,
            errorCount: Math.floor(Math.random() * 50) + 5,
            warningCount: Math.floor(Math.random() * 100) + 20,
            infoCount: Math.floor(Math.random() * 800) + 400,
            debugCount: Math.floor(Math.random() * 200) + 50,
            avgResponseTime: Math.random() * 200 + 100,
            throughput: Math.random() * 1000 + 500,
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
            logCount: Math.floor(Math.random() * 20000) + 10000,
            errorCount: Math.floor(Math.random() * 200) + 50,
            warningCount: Math.floor(Math.random() * 500) + 100,
            infoCount: Math.floor(Math.random() * 15000) + 8000,
            debugCount: Math.floor(Math.random() * 1000) + 200,
            avgResponseTime: Math.random() * 300 + 150,
            throughput: Math.random() * 20000 + 10000,
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
            logCount: Math.floor(Math.random() * 300000) + 150000,
            errorCount: Math.floor(Math.random() * 5000) + 1000,
            warningCount: Math.floor(Math.random() * 10000) + 2000,
            infoCount: Math.floor(Math.random() * 200000) + 100000,
            debugCount: Math.floor(Math.random() * 20000) + 5000,
            avgResponseTime: Math.random() * 400 + 200,
            throughput: Math.random() * 300000 + 150000,
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
            logCount: Math.floor(Math.random() * 1000000) + 500000,
            errorCount: Math.floor(Math.random() * 20000) + 5000,
            warningCount: Math.floor(Math.random() * 50000) + 10000,
            infoCount: Math.floor(Math.random() * 800000) + 400000,
            debugCount: Math.floor(Math.random() * 80000) + 20000,
            avgResponseTime: Math.random() * 500 + 250,
            throughput: Math.random() * 1000000 + 500000,
          });
        }
        break;
    }

    return data;
  };

  const calculateMetrics = (data: LogTrendData[]): TrendMetrics => {
    if (data.length === 0) {
      return {
        totalLogs: 0,
        errorRate: 0,
        warningRate: 0,
        avgResponseTime: 0,
        trendDirection: 'stable',
        trendPercentage: 0,
      };
    }

    const totalLogs = data.reduce((sum, item) => sum + item.logCount, 0);
    const totalErrors = data.reduce((sum, item) => sum + item.errorCount, 0);
    const totalWarnings = data.reduce((sum, item) => sum + item.warningCount, 0);
    const avgResponseTime = data.reduce((sum, item) => sum + item.avgResponseTime, 0) / data.length;

    const errorRate = totalLogs > 0 ? (totalErrors / totalLogs) * 100 : 0;
    const warningRate = totalLogs > 0 ? (totalWarnings / totalLogs) * 100 : 0;

    // Calculate trend direction
    const midPoint = Math.floor(data.length / 2);
    const firstHalf = data.slice(0, midPoint).reduce((sum, item) => sum + item.logCount, 0);
    const secondHalf = data.slice(midPoint).reduce((sum, item) => sum + item.logCount, 0);

    let trendDirection: 'up' | 'down' | 'stable' = 'stable';
    let trendPercentage = 0;

    if (firstHalf > 0) {
      const change = ((secondHalf - firstHalf) / firstHalf) * 100;
      trendPercentage = Math.abs(change);
      if (change > 5) trendDirection = 'up';
      else if (change < -5) trendDirection = 'down';
    }

    return {
      totalLogs,
      errorRate,
      warningRate,
      avgResponseTime,
      trendDirection,
      trendPercentage,
    };
  };

  const fetchLogTrends = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // In a real implementation, this would call the backend ELK services
      // For now, we'll generate mock data
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      const data = generateMockData(selectedTimeRange);
      setLogTrends(data);
      setMetrics(calculateMetrics(data));
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to fetch log trends');
      console.error('Error fetching log trends:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogTrends();
  }, [selectedTimeRange, selectedLevel, selectedSource]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchLogTrends();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const chartData = useMemo(() => {
    if (!logTrends.length) return null;

    const labels = logTrends.map(item => {
      const date = new Date(item.timestamp);
      switch (selectedTimeRange) {
        case '1h':
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

    const filteredData = logTrends.filter(item => {
      if (selectedLevel === 'all') return true;
      switch (selectedLevel) {
        case 'error':
          return item.errorCount > 0;
        case 'warning':
          return item.warningCount > 0;
        case 'info':
          return item.infoCount > 0;
        case 'debug':
          return item.debugCount > 0;
        default:
          return true;
      }
    });

    return {
      labels: labels.slice(-filteredData.length),
      datasets: [
        {
          label: 'Total Logs',
          data: filteredData.map(item => item.logCount),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Errors',
          data: filteredData.map(item => item.errorCount),
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Warnings',
          data: filteredData.map(item => item.warningCount),
          borderColor: 'rgb(245, 158, 11)',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Info',
          data: filteredData.map(item => item.infoCount),
          borderColor: 'rgb(16, 185, 129)',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: false,
          tension: 0.4,
        },
      ],
    };
  }, [logTrends, selectedTimeRange, selectedLevel]);

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
          text: selectedTimeRange === '1h' || selectedTimeRange === '24h' ? 'Time' : 'Date',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Log Count',
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

  const performanceData = useMemo(() => {
    if (!logTrends.length) return null;

    const labels = logTrends.map(item => {
      const date = new Date(item.timestamp);
      return format(date, 'HH:mm');
    });

    return {
      labels,
      datasets: [
        {
          label: 'Avg Response Time (ms)',
          data: logTrends.map(item => item.avgResponseTime),
          borderColor: 'rgb(147, 51, 234)',
          backgroundColor: 'rgba(147, 51, 234, 0.1)',
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Throughput',
          data: logTrends.map(item => item.throughput),
          borderColor: 'rgb(14, 165, 233)',
          backgroundColor: 'rgba(14, 165, 233, 0.1)',
          fill: false,
          tension: 0.4,
          yAxisID: 'y1',
        },
      ],
    };
  }, [logTrends]);

  const performanceOptions = {
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
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Response Time (ms)',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Throughput',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  const exportData = () => {
    const dataToExport = {
      trends: logTrends,
      metrics,
      exportedAt: new Date().toISOString(),
      timeRange: selectedTimeRange,
      filters: {
        level: selectedLevel,
        source: selectedSource,
      },
    };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `log-trends-${selectedTimeRange}-${format(new Date(), 'yyyy-MM-dd')}.json`;
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
            onClick={fetchLogTrends}
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
          <h2 className="text-2xl font-bold tracking-tight">Log Trend Analysis</h2>
          <p className="text-muted-foreground">
            Monitor log volume, error rates, and performance trends over time
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            Last update: {format(lastUpdate, 'HH:mm:ss')}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchLogTrends}
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
              <label className="text-sm font-medium mb-2 block">Log Level</label>
              <Select value={selectedLevel} onValueChange={setSelectedLevel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select log level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="error">Errors Only</SelectItem>
                  <SelectItem value="warning">Warnings Only</SelectItem>
                  <SelectItem value="info">Info Only</SelectItem>
                  <SelectItem value="debug">Debug Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Source</label>
              <Select value={selectedSource} onValueChange={setSelectedSource}>
                <SelectTrigger>
                  <SelectValue placeholder="Select source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="api">API Logs</SelectItem>
                  <SelectItem value="database">Database Logs</SelectItem>
                  <SelectItem value="system">System Logs</SelectItem>
                  <SelectItem value="application">Application Logs</SelectItem>
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
              <CardTitle className="text-sm font-medium">Total Logs</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.totalLogs.toLocaleString()}</div>
              <div className="flex items-center text-xs text-muted-foreground">
                {metrics.trendDirection === 'up' && <TrendingUp className="h-3 w-3 text-green-500 mr-1" />}
                {metrics.trendDirection === 'down' && <TrendingDown className="h-3 w-3 text-red-500 mr-1" />}
                {metrics.trendDirection === 'stable' && <CheckCircle2 className="h-3 w-3 text-blue-500 mr-1" />}
                {metrics.trendPercentage.toFixed(1)}% {metrics.trendDirection}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.errorRate.toFixed(2)}%</div>
              <div className="text-xs text-muted-foreground">
                {(metrics.totalLogs * metrics.errorRate / 100).toLocaleString()} errors
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Warning Rate</CardTitle>
              <AlertCircle className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.warningRate.toFixed(2)}%</div>
              <div className="text-xs text-muted-foreground">
                {(metrics.totalLogs * metrics.warningRate / 100).toLocaleString()} warnings
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.avgResponseTime.toFixed(0)}ms</div>
              <div className="text-xs text-muted-foreground">
                {metrics.avgResponseTime < 200 ? 'Good' : metrics.avgResponseTime < 500 ? 'Fair' : 'Poor'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Log Trends</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>
        
        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Log Volume Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {chartData && <Line data={chartData} options={chartOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {performanceData && <Line data={performanceData} options={performanceOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default LogTrendAnalysis;