"""
Usage Analytics Component

Comprehensive LLM usage analytics and forecasting dashboard.
"""

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Brain,
  DollarSign,
  Clock,
  AlertTriangle,
  Calendar,
  Download,
  RefreshCw,
  Activity,
  Zap,
  Target,
  BarChart3,
  PieChart as PieChartIcon
} from 'lucide-react';

interface UsageAnalyticsProps {
  userId: number;
  organizationId?: number;
}

interface UsageData {
  date: string;
  tokens: number;
  cost: number;
  requests: number;
  model: string;
}

interface ModelUsage {
  model: string;
  tokens: number;
  cost: number;
  requests: number;
  percentage: number;
  trend: 'up' | 'down' | 'stable';
}

interface ForecastData {
  date: string;
  predictedTokens: number;
  predictedCost: number;
  confidence: number;
}

interface UsageStatistics {
  totalTokens: number;
  totalCost: number;
  totalRequests: number;
  averageTokensPerRequest: number;
  costPerToken: number;
  peakUsageHour: number;
  mostUsedModel: string;
  usageGrowthRate: number;
  costGrowthRate: number;
}

interface AnomalyData {
  date: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  value: number;
  expected: number;
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#8dd1e1', '#d084d0'];

const UsageAnalytics: React.FC<UsageAnalyticsProps> = ({ userId, organizationId }) => {
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState('30d');
  const [selectedMetric, setSelectedMetric] = useState('tokens');
  const [selectedModel, setSelectedModel] = useState('all');
  const [activeTab, setActiveTab] = useState('overview');
  
  const [usageData, setUsageData] = useState<UsageData[]>([]);
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([]);
  const [forecastData, setForecastData] = useState<ForecastData[]>([]);
  const [statistics, setStatistics] = useState<UsageStatistics | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyData[]>([]);
  const [recommendations, setRecommendations] = useState<string[]>([]);

  useEffect(() => {
    loadUsageAnalytics();
  }, [userId, organizationId, timeRange]);

  const loadUsageAnalytics = async () => {
    setLoading(true);
    try {
      // Simulate API calls - replace with actual API calls
      await Promise.all([
        loadUsageData(),
        loadModelUsage(),
        loadForecast(),
        loadStatistics(),
        loadAnomalies(),
        loadRecommendations()
      ]);
    } catch (error) {
      console.error('Error loading usage analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsageData = async () => {
    // Simulate usage data - replace with actual API call
    const mockData: UsageData[] = [];
    const days = parseInt(timeRange.replace('d', ''));
    
    for (let i = days; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      
      mockData.push({
        date: date.toISOString().split('T')[0],
        tokens: Math.floor(Math.random() * 10000) + 1000,
        cost: Math.floor(Math.random() * 50) + 5,
        requests: Math.floor(Math.random() * 100) + 10,
        model: ['gpt-4', 'claude-3', 'gemini-pro'][Math.floor(Math.random() * 3)]
      });
    }
    
    setUsageData(mockData);
  };

  const loadModelUsage = async () => {
    // Simulate model usage data - replace with actual API call
    const models = ['gpt-4', 'claude-3', 'gemini-pro', 'llama-2', 'mistral'];
    const mockData: ModelUsage[] = models.map((model, index) => ({
      model,
      tokens: Math.floor(Math.random() * 50000) + 10000,
      cost: Math.floor(Math.random() * 200) + 50,
      requests: Math.floor(Math.random() * 1000) + 100,
      percentage: Math.floor(Math.random() * 30) + 10,
      trend: ['up', 'down', 'stable'][Math.floor(Math.random() * 3)] as 'up' | 'down' | 'stable'
    }));
    
    setModelUsage(mockData);
  };

  const loadForecast = async () => {
    // Simulate forecast data - replace with actual API call
    const mockData: ForecastData[] = [];
    const today = new Date();
    
    for (let i = 1; i <= 30; i++) {
      const date = new Date(today);
      date.setDate(date.getDate() + i);
      
      mockData.push({
        date: date.toISOString().split('T')[0],
        predictedTokens: Math.floor(Math.random() * 8000) + 2000,
        predictedCost: Math.floor(Math.random() * 40) + 10,
        confidence: Math.floor(Math.random() * 30) + 70
      });
    }
    
    setForecastData(mockData);
  };

  const loadStatistics = async () => {
    // Simulate statistics - replace with actual API call
    const mockStats: UsageStatistics = {
      totalTokens: 1250000,
      totalCost: 850.50,
      totalRequests: 5420,
      averageTokensPerRequest: 230,
      costPerToken: 0.00068,
      peakUsageHour: 14,
      mostUsedModel: 'gpt-4',
      usageGrowthRate: 15.2,
      costGrowthRate: 8.7
    };
    
    setStatistics(mockStats);
  };

  const loadAnomalies = async () => {
    // Simulate anomalies - replace with actual API call
    const mockAnomalies: AnomalyData[] = [
      {
        date: '2024-01-15',
        type: 'usage_spike',
        severity: 'high',
        description: 'Unusual usage spike detected',
        value: 15000,
        expected: 5000
      },
      {
        date: '2024-01-10',
        type: 'cost_increase',
        severity: 'medium',
        description: 'Higher than expected costs',
        value: 120,
        expected: 80
      }
    ];
    
    setAnomalies(mockAnomalies);
  };

  const loadRecommendations = async () => {
    // Simulate recommendations - replace with actual API call
    const mockRecommendations = [
      'Consider optimizing prompts to reduce token usage by up to 20%',
      'Switch to a more cost-effective model for routine tasks',
      'Set up usage alerts to prevent unexpected cost overruns',
      'Batch similar requests to improve efficiency'
    ];
    
    setRecommendations(mockRecommendations);
  };

  const exportData = () => {
    // Implement data export functionality
    const data = {
      usageData,
      modelUsage,
      forecastData,
      statistics,
      exportDate: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `usage-analytics-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getMetricValue = (data: UsageData) => {
    switch (selectedMetric) {
      case 'tokens': return data.tokens;
      case 'cost': return data.cost;
      case 'requests': return data.requests;
      default: return data.tokens;
    }
  };

  const getMetricLabel = () => {
    switch (selectedMetric) {
      case 'tokens': return 'Tokens';
      case 'cost': return 'Cost ($)';
      case 'requests': return 'Requests';
      default: return 'Tokens';
    }
  };

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Key Statistics */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
              <Brain className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.totalTokens.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground flex items-center">
                <TrendingUp className="h-3 w-3 mr-1" />
                +{statistics.usageGrowthRate}% from last period
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${statistics.totalCost.toFixed(2)}</div>
              <p className="text-xs text-muted-foreground flex items-center">
                <TrendingUp className="h-3 w-3 mr-1" />
                +{statistics.costGrowthRate}% from last period
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Requests</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.totalRequests.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                Avg: {statistics.averageTokensPerRequest} tokens/request
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cost per Token</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${statistics.costPerToken.toFixed(4)}</div>
              <p className="text-xs text-muted-foreground">
                Peak usage: {statistics.peakUsageHour}:00
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Usage Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Usage Trend</CardTitle>
          <CardDescription>
            Track your {getMetricLabel().toLowerCase()} over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={usageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey={getMetricValue} 
                  stroke="#8884d8" 
                  fill="#8884d8" 
                  fillOpacity={0.3} 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Model Usage Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Model Usage Distribution</CardTitle>
            <CardDescription>
              Breakdown by AI model
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelUsage}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percentage }) => `${name} ${percentage}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="tokens"
                  >
                    {modelUsage.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model Performance</CardTitle>
            <CardDescription>
              Cost efficiency by model
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelUsage}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="model" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="cost" fill="#82ca9d" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderForecastTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Usage Forecast</CardTitle>
          <CardDescription>
            Predicted usage and costs for the next 30 days
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="predictedTokens" 
                  stroke="#8884d8" 
                  name="Predicted Tokens" 
                />
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="predictedCost" 
                  stroke="#82ca9d" 
                  name="Predicted Cost ($)" 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Forecast Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>High Confidence</span>
                <span>45%</span>
              </div>
              <Progress value={45} className="h-2" />
              <div className="flex justify-between">
                <span>Medium Confidence</span>
                <span>35%</span>
              </div>
              <Progress value={35} className="h-2" />
              <div className="flex justify-between">
                <span>Low Confidence</span>
                <span>20%</span>
              </div>
              <Progress value={20} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Key Predictions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Expected Growth</span>
                <Badge variant="secondary">+12%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Peak Usage Day</span>
                <Badge variant="outline">Tuesday</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Cost Trend</span>
                <Badge variant="destructive">Increasing</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Based on forecast patterns:
              </p>
              <ul className="text-sm space-y-1">
                <li>• Monitor usage on peak days</li>
                <li>• Consider model optimization</li>
                <li>• Set cost alerts</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderAnomaliesTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Anomaly Detection</CardTitle>
          <CardDescription>
            Unusual usage patterns and anomalies detected
          </CardDescription>
        </CardHeader>
        <CardContent>
          {anomalies.length > 0 ? (
            <div className="space-y-4">
              {anomalies.map((anomaly, index) => (
                <Alert key={index} className={
                  anomaly.severity === 'high' ? 'border-red-500' : 
                  anomaly.severity === 'medium' ? 'border-yellow-500' : 'border-blue-500'
                }>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="flex justify-between items-start">
                      <div>
                        <strong>{anomaly.description}</strong>
                        <p className="text-sm text-muted-foreground mt-1">
                          {anomaly.type} - {anomaly.date}
                        </p>
                      </div>
                      <Badge variant={
                        anomaly.severity === 'high' ? 'destructive' : 
                        anomaly.severity === 'medium' ? 'secondary' : 'outline'
                      }>
                        {anomaly.severity}
                      </Badge>
                    </div>
                  </AlertDescription>
                </Alert>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No anomalies detected in the selected period.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Anomaly Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={usageData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="tokens" 
                    stroke="#8884d8" 
                    name="Actual Usage" 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Anomaly Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Usage Spikes</span>
                <Badge variant="destructive">High</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Cost Increases</span>
                <Badge variant="secondary">Medium</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Request Patterns</span>
                <Badge variant="outline">Low</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Model Performance</span>
                <Badge variant="outline">Normal</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderInsightsTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
            <CardDescription>
              AI-powered suggestions to optimize your usage
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <Zap className="h-4 w-4 mt-0.5 text-blue-500" />
                  <p className="text-sm">{recommendation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Optimization Opportunities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm">Prompt Optimization</span>
                <Badge variant="secondary">Save 20%</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Model Switching</span>
                <Badge variant="outline">Save 15%</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Batch Processing</span>
                <Badge variant="outline">Save 10%</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Caching</span>
                <Badge variant="outline">Save 25%</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Usage Efficiency Score</CardTitle>
          <CardDescription>
            Overall assessment of your usage efficiency
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span>Overall Score</span>
              <span className="text-2xl font-bold text-green-600">87/100</span>
            </div>
            <Progress value={87} className="h-3" />
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="font-medium">Cost Efficiency</div>
                <div className="text-lg text-green-600">92</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Token Optimization</div>
                <div className="text-lg text-yellow-600">78</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Model Selection</div>
                <div className="text-lg text-blue-600">85</div>
              </div>
            </div>
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
          <h1 className="text-3xl font-bold">Usage Analytics</h1>
          <p className="text-muted-foreground">
            Comprehensive LLM usage analysis and insights
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setTimeRange(timeRange)}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={exportData}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="90d">Last 90 days</SelectItem>
                  <SelectItem value="1y">Last year</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tokens">Tokens</SelectItem>
                  <SelectItem value="cost">Cost</SelectItem>
                  <SelectItem value="requests">Requests</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Brain className="h-4 w-4 text-muted-foreground" />
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Models</SelectItem>
                  <SelectItem value="gpt-4">GPT-4</SelectItem>
                  <SelectItem value="claude-3">Claude-3</SelectItem>
                  <SelectItem value="gemini-pro">Gemini Pro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">
            <BarChart3 className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="forecast">
            <TrendingUp className="h-4 w-4 mr-2" />
            Forecast
          </TabsTrigger>
          <TabsTrigger value="anomalies">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Anomalies
          </TabsTrigger>
          <TabsTrigger value="insights">
            <Target className="h-4 w-4 mr-2" />
            Insights
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {renderOverviewTab()}
        </TabsContent>

        <TabsContent value="forecast">
          {renderForecastTab()}
        </TabsContent>

        <TabsContent value="anomalies">
          {renderAnomaliesTab()}
        </TabsContent>

        <TabsContent value="insights">
          {renderInsightsTab()}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default UsageAnalytics;