import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  DollarSign, TrendingUp, Users, CreditCard, FileText,
  AlertCircle, BarChart3, Calendar, RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';

interface BillingAnalytics {
  total_revenue: number;
  monthly_recurring_revenue: number;
  annual_recurring_revenue: number;
  active_subscriptions: number;
  trialing_subscriptions: number;
  canceled_subscriptions: number;
  churn_rate: number;
  average_revenue_per_user: number;
  total_invoices: number;
  paid_invoices: number;
  outstanding_amount: number;
  overdue_invoices: number;
}

interface RevenueByMonth {
  month: string;
  revenue: number;
  subscriptions: number;
  new_subscriptions: number;
  canceled_subscriptions: number;
}

interface DashboardData {
  billing_analytics: BillingAnalytics;
  usage_analytics: {
    total_documents_processed: number;
    total_api_calls: number;
    total_active_users: number;
  };
  revenue_by_month: RevenueByMonth[];
}

export default function BillingAnalyticsPage() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!hasRole('admin')) {
      navigate('/dashboard');
      return;
    }
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      const response = await api.get('/api/v1/billing/analytics/dashboard');
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch billing analytics:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <div className="loading-spinner h-12 w-12 mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading billing analytics...</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 mx-auto text-error-500 mb-4" />
          <p className="text-lg font-semibold">Failed to load analytics data</p>
        </div>
      </div>
    );
  }

  const { billing_analytics, usage_analytics, revenue_by_month } = dashboardData;

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Billing Analytics
              </h1>
              <p className="text-sm text-muted-foreground">
                Revenue metrics and subscription insights
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button
                onClick={fetchDashboardData}
                disabled={refreshing}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <ThemeToggle />
              <span className="text-sm font-medium">{user?.full_name}</span>
              <Button onClick={() => navigate('/admin')} variant="outline">
                Admin Dashboard
              </Button>
              <Button onClick={logout} variant="destructive">
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                MRR
              </CardTitle>
              <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
                <DollarSign className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {billing_analytics.monthly_recurring_revenue.toLocaleString()} EUR
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Monthly Recurring Revenue
              </p>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                ARR
              </CardTitle>
              <div className="p-2 rounded-lg bg-success-100 dark:bg-success-900/30">
                <TrendingUp className="h-5 w-5 text-success-600 dark:text-success-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {billing_analytics.annual_recurring_revenue.toLocaleString()} EUR
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Annual Recurring Revenue
              </p>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active Subscriptions
              </CardTitle>
              <div className="p-2 rounded-lg bg-secondary-100 dark:bg-secondary-900/30">
                <Users className="h-5 w-5 text-secondary-600 dark:text-secondary-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {billing_analytics.active_subscriptions}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                +{billing_analytics.trialing_subscriptions} on trial
              </p>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                ARPU
              </CardTitle>
              <div className="p-2 rounded-lg bg-warning-100 dark:bg-warning-900/30">
                <CreditCard className="h-5 w-5 text-warning-600 dark:text-warning-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {billing_analytics.average_revenue_per_user.toFixed(2)} EUR
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Average Revenue Per User
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Revenue and Churn */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-primary-600" />
                Revenue Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Total Revenue</span>
                    <span className="text-sm font-bold text-primary-600">
                      {billing_analytics.total_revenue.toLocaleString()} EUR
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all"
                      style={{ width: '100%' }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Outstanding Amount</span>
                    <span className="text-sm font-bold text-warning-600">
                      {billing_analytics.outstanding_amount.toLocaleString()} EUR
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-warning-500 h-2 rounded-full transition-all"
                      style={{ 
                        width: `${Math.min(100, (billing_analytics.outstanding_amount / billing_analytics.total_revenue) * 100)}%` 
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-error-600" />
                Churn & Invoices
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-error-50 dark:bg-error-900/20 rounded-lg">
                  <div>
                    <p className="text-sm font-medium">Churn Rate</p>
                    <p className="text-2xl font-bold text-error-600">
                      {billing_analytics.churn_rate.toFixed(1)}%
                    </p>
                  </div>
                  <Badge variant="destructive" className="text-lg px-3 py-1">
                    {billing_analytics.canceled_subscriptions} canceled
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Total Invoices</span>
                  <Badge variant="outline">{billing_analytics.total_invoices}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Paid Invoices</span>
                  <Badge className="bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300">
                    {billing_analytics.paid_invoices}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Overdue Invoices</span>
                  <Badge variant="destructive">{billing_analytics.overdue_invoices}</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Usage Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="text-sm">Total Documents</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary-600">
                {usage_analytics.total_documents_processed.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Documents processed</p>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="text-sm">Total API Calls</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-secondary-600">
                {usage_analytics.total_api_calls.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground mt-1">API requests made</p>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="text-sm">Active Users</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-success-600">
                {usage_analytics.total_active_users}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Users with subscriptions</p>
            </CardContent>
          </Card>
        </div>

        {/* Revenue Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary-600" />
              Revenue Trend (Last 12 Months)
            </CardTitle>
            <CardDescription>Monthly revenue and subscription metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {revenue_by_month.map((monthData, index) => (
                <div key={index} className="flex items-center gap-4">
                  <div className="w-20 text-sm font-medium text-muted-foreground">
                    {new Date(monthData.month + '-01').toLocaleDateString('en-US', { 
                      month: 'short', 
                      year: '2-digit' 
                    })}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm">Revenue</span>
                      <span className="text-sm font-bold">{monthData.revenue.toLocaleString()} EUR</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="bg-primary-500 h-2 rounded-full transition-all"
                        style={{ 
                          width: `${Math.min(100, (monthData.revenue / Math.max(...revenue_by_month.map(m => m.revenue))) * 100)}%` 
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="w-32 text-right text-sm">
                    <span className="text-success-600">+{monthData.new_subscriptions}</span>
                    {monthData.canceled_subscriptions > 0 && (
                      <span className="text-error-600 ml-2">-{monthData.canceled_subscriptions}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
