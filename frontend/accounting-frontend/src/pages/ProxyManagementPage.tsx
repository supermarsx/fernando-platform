import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Activity, 
  Shield, 
  Zap, 
  Database, 
  Settings,
  BarChart3,
  Key,
  Server,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import {
  ProxyDashboard,
  ApiKeyManager,
  LoadBalancerConfig,
  RateLimitingConfig,
  CircuitBreakerMonitor,
  PerformanceMonitor,
  SecurityManagement,
  AdminControls
} from './index';

const ProxyManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Mock data for system overview
  const systemStatus = {
    overall: 'healthy',
    servers: {
      total: 8,
      running: 7,
      stopped: 1,
      error: 0
    },
    requests: {
      total: 1247892,
      successRate: 99.7,
      averageResponseTime: 145
    },
    security: {
      activePolicies: 12,
      blockedIPs: 23,
      threats: 3
    },
    performance: {
      cpu: 34,
      memory: 67,
      throughput: 2847
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'warning': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return CheckCircle;
      case 'warning': return AlertTriangle;
      case 'critical': return AlertTriangle;
      default: return AlertTriangle;
    }
  };

  const StatusIcon = getStatusIcon(systemStatus.overall);

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold">Proxy Management</h1>
          <p className="text-xl text-muted-foreground mt-2">
            Comprehensive proxy server management and monitoring
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <StatusIcon className={`h-8 w-8 ${getStatusColor(systemStatus.overall)}`} />
          <div className="text-right">
            <p className="text-sm font-medium">System Status</p>
            <p className={`text-lg font-semibold capitalize ${getStatusColor(systemStatus.overall)}`}>
              {systemStatus.overall}
            </p>
          </div>
        </div>
      </div>

      {/* System Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Server Status</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStatus.servers.running}/{systemStatus.servers.total}</div>
            <p className="text-xs text-muted-foreground">
              {systemStatus.servers.error > 0 && (
                <span className="text-red-600">{systemStatus.servers.error} errors</span>
              )}
              {systemStatus.servers.stopped > 0 && (
                <span className="text-yellow-600 ml-2">{systemStatus.servers.stopped} stopped</span>
              )}
            </p>
            <div className="flex space-x-1 mt-2">
              <Badge variant="default" className="text-xs">
                {systemStatus.servers.running} Running
              </Badge>
              {systemStatus.servers.stopped > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {systemStatus.servers.stopped} Stopped
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Request Performance</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStatus.requests.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              {systemStatus.requests.averageResponseTime}ms avg response time
            </p>
            <div className="mt-2">
              <p className="text-xs text-muted-foreground">
                {systemStatus.requests.total.toLocaleString()} total requests
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Security Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStatus.security.activePolicies}</div>
            <p className="text-xs text-muted-foreground">
              Active security policies
            </p>
            <div className="flex space-x-1 mt-2">
              <Badge variant="outline" className="text-xs">
                {systemStatus.security.blockedIPs} Blocked IPs
              </Badge>
              {systemStatus.security.threats > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {systemStatus.security.threats} Threats
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resource Usage</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStatus.performance.throughput}/s</div>
            <p className="text-xs text-muted-foreground">
              {systemStatus.performance.cpu}% CPU • {systemStatus.performance.memory}% Memory
            </p>
            <div className="mt-2">
              <p className="text-xs text-muted-foreground">
                Request throughput
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Management Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-8">
          <TabsTrigger value="dashboard" className="flex items-center space-x-2">
            <Activity className="h-4 w-4" />
            <span className="hidden sm:inline">Dashboard</span>
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="flex items-center space-x-2">
            <Key className="h-4 w-4" />
            <span className="hidden sm:inline">API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="load-balancer" className="flex items-center space-x-2">
            <Database className="h-4 w-4" />
            <span className="hidden sm:inline">Load Balance</span>
          </TabsTrigger>
          <TabsTrigger value="rate-limiting" className="flex items-center space-x-2">
            <Zap className="h-4 w-4" />
            <span className="hidden sm:inline">Rate Limits</span>
          </TabsTrigger>
          <TabsTrigger value="circuit-breaker" className="flex items-center space-x-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Circuit Breaker</span>
          </TabsTrigger>
          <TabsTrigger value="performance" className="flex items-center space-x-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Performance</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="hidden sm:inline">Security</span>
          </TabsTrigger>
          <TabsTrigger value="admin" className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Admin</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <ProxyDashboard />
        </TabsContent>

        <TabsContent value="api-keys">
          <ApiKeyManager />
        </TabsContent>

        <TabsContent value="load-balancer">
          <LoadBalancerConfig />
        </TabsContent>

        <TabsContent value="rate-limiting">
          <RateLimitingConfig />
        </TabsContent>

        <TabsContent value="circuit-breaker">
          <CircuitBreakerMonitor />
        </TabsContent>

        <TabsContent value="performance">
          <PerformanceMonitor />
        </TabsContent>

        <TabsContent value="security">
          <SecurityManagement />
        </TabsContent>

        <TabsContent value="admin">
          <AdminControls />
        </TabsContent>
      </Tabs>

      {/* Quick Actions Footer */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Frequently used proxy management operations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Activity className="h-8 w-8 mb-2 text-blue-600" />
              <span className="text-sm font-medium">View Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab('api-keys')}
              className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Key className="h-8 w-8 mb-2 text-green-600" />
              <span className="text-sm font-medium">Manage API Keys</span>
            </button>
            <button
              onClick={() => setActiveTab('performance')}
              className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <BarChart3 className="h-8 w-8 mb-2 text-purple-600" />
              <span className="text-sm font-medium">Performance Monitor</span>
            </button>
            <button
              onClick={() => setActiveTab('admin')}
              className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Settings className="h-8 w-8 mb-2 text-orange-600" />
              <span className="text-sm font-medium">Admin Controls</span>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProxyManagementPage;