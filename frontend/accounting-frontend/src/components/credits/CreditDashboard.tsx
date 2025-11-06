import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  CreditCard, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  Clock,
  Plus,
  ArrowUpRight,
  ArrowDownLeft,
  BarChart3,
  PieChart
} from 'lucide-react';

interface CreditBalance {
  total_credits: number;
  available_credits: number;
  reserved_credits: number;
  credits_used_this_month: number;
  utilization_rate: number;
  days_until_depletion?: number;
  status: 'healthy' | 'moderate' | 'low' | 'critical' | 'depleted';
}

interface CreditTransaction {
  id: string;
  type: string;
  amount: number;
  description: string;
  timestamp: string;
}

interface CreditAlert {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  triggered_at: string;
}

interface CreditDashboardProps {
  userId: number;
  organizationId?: number;
}

const CreditDashboard: React.FC<CreditDashboardProps> = ({ userId, organizationId }) => {
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<CreditTransaction[]>([]);
  const [alerts, setAlerts] = useState<CreditAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [userId, organizationId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        loadBalance(),
        loadRecentTransactions(),
        loadAlerts()
      ]);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBalance = async () => {
    try {
      const response = await fetch(`/api/credits/balance?user_id=${userId}${organizationId ? `&organization_id=${organizationId}` : ''}`);
      if (response.ok) {
        const data = await response.json();
        setBalance(data);
      }
    } catch (error) {
      console.error('Failed to load balance:', error);
    }
  };

  const loadRecentTransactions = async () => {
    try {
      const response = await fetch(`/api/credits/transactions?user_id=${userId}&limit=10${organizationId ? `&organization_id=${organizationId}` : ''}`);
      if (response.ok) {
        const data = await response.json();
        setRecentTransactions(data);
      }
    } catch (error) {
      console.error('Failed to load transactions:', error);
    }
  };

  const loadAlerts = async () => {
    try {
      const response = await fetch(`/api/credits/alerts?user_id=${userId}&status=active${organizationId ? `&organization_id=${organizationId}` : ''}`);
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'moderate': return 'bg-yellow-500';
      case 'low': return 'bg-orange-500';
      case 'critical': return 'bg-red-500';
      case 'depleted': return 'bg-gray-500';
      default: return 'bg-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '✓';
      case 'moderate': return '⚠';
      case 'low': return '⚠';
      case 'critical': return '🛑';
      case 'depleted': return '❌';
      default: return '?';
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(Math.round(num));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Credit Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your credit balance and usage
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => window.location.href = '/credits/purchase'}>
            <Plus className="h-4 w-4 mr-2" />
            Purchase Credits
          </Button>
          <Button variant="outline" onClick={() => window.location.href = '/credits/transfer'}>
            <ArrowUpRight className="h-4 w-4 mr-2" />
            Transfer Credits
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <Alert key={alert.id} variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>{alert.type}:</strong> {alert.message}
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Main Dashboard */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="usage">Usage Analytics</TabsTrigger>
          <TabsTrigger value="transactions">Transactions</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Balance Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Available Credits</CardTitle>
                <CreditCard className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {balance ? formatNumber(balance.available_credits) : '0'}
                </div>
                {balance && (
                  <div className="flex items-center text-xs text-muted-foreground mt-1">
                    <Badge variant={balance.status === 'healthy' ? 'default' : 'destructive'} className="mr-2">
                      {getStatusIcon(balance.status)} {balance.status}
                    </Badge>
                    {balance.days_until_depletion && (
                      <span>{balance.days_until_depletion} days remaining</span>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {balance ? formatNumber(balance.total_credits) : '0'}
                </div>
                {balance && (
                  <p className="text-xs text-muted-foreground">
                    {formatNumber(balance.reserved_credits)} reserved
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly Usage</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {balance ? formatNumber(balance.credits_used_this_month) : '0'}
                </div>
                {balance && (
                  <>
                    <Progress 
                      value={balance.utilization_rate} 
                      className="mt-2"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {balance.utilization_rate.toFixed(1)}% utilization
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Daily Usage</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {balance ? formatNumber(balance.credits_used_this_month / 30) : '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Average per day
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Balance Status */}
          {balance && (
            <Card>
              <CardHeader>
                <CardTitle>Balance Status</CardTitle>
                <CardDescription>
                  Current credit status and health metrics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Status</span>
                  <Badge variant={balance.status === 'healthy' ? 'default' : 'destructive'}>
                    {balance.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Utilization Rate</span>
                  <span className="text-sm">{balance.utilization_rate.toFixed(1)}%</span>
                </div>
                <Progress value={balance.utilization_rate} />
                {balance.days_until_depletion && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Estimated Days Remaining</span>
                    <span className="text-sm">{balance.days_until_depletion.toFixed(1)} days</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Usage Analytics Tab */}
        <TabsContent value="usage" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Usage Analytics</CardTitle>
              <CardDescription>
                Detailed usage patterns and forecasts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <PieChart className="h-12 w-12 mx-auto mb-4" />
                <p>Usage analytics will be displayed here</p>
                <p className="text-sm">This feature requires backend analytics data</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transactions Tab */}
        <TabsContent value="transactions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Transactions</CardTitle>
              <CardDescription>
                Latest credit transactions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentTransactions.length > 0 ? (
                <div className="space-y-4">
                  {recentTransactions.map((transaction) => (
                    <div key={transaction.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        {transaction.type === 'purchase' ? (
                          <ArrowDownLeft className="h-4 w-4 text-green-500" />
                        ) : transaction.type === 'usage' ? (
                          <ArrowUpRight className="h-4 w-4 text-red-500" />
                        ) : (
                          <CreditCard className="h-4 w-4 text-blue-500" />
                        )}
                        <div>
                          <p className="font-medium">{transaction.description}</p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(transaction.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`font-medium ${transaction.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {transaction.amount > 0 ? '+' : ''}{formatNumber(transaction.amount)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {transaction.type}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <CreditCard className="h-12 w-12 mx-auto mb-4" />
                  <p>No transactions found</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Active Alerts</CardTitle>
              <CardDescription>
                Current credit alerts and notifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              {alerts.length > 0 ? (
                <div className="space-y-4">
                  {alerts.map((alert) => (
                    <div key={alert.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <AlertTriangle className={`h-4 w-4 ${
                          alert.severity === 'critical' ? 'text-red-500' : 
                          alert.severity === 'high' ? 'text-orange-500' : 
                          alert.severity === 'medium' ? 'text-yellow-500' : 'text-blue-500'
                        }`} />
                        <div>
                          <p className="font-medium">{alert.message}</p>
                          <p className="text-sm text-muted-foreground">
                            {alert.type} • {new Date(alert.triggered_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <Badge variant={
                        alert.severity === 'critical' ? 'destructive' :
                        alert.severity === 'high' ? 'default' : 'secondary'
                      }>
                        {alert.severity}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-4" />
                  <p>No active alerts</p>
                  <p className="text-sm">You're in good standing!</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CreditDashboard;