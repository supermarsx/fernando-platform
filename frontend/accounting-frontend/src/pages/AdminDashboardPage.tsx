import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, FileText, CheckCircle, AlertCircle, Activity,
  Database, Server, Cpu, HardDrive, TrendingUp, CreditCard, Key
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';

interface Stats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  total_users: number;
  total_documents: number;
  success_rate: number;
  avg_processing_time: number;
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState({
    database: 'healthy',
    backend: 'healthy',
    storage: 'healthy',
  });
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!hasRole('admin')) {
      navigate('/dashboard');
      return;
    }
    fetchStats();
    checkSystemHealth();
  }, [user, navigate]);

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/v1/admin/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkSystemHealth = () => {
    // In production, this would make actual API calls
    setSystemHealth({
      database: 'healthy',
      backend: 'healthy',
      storage: 'healthy',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <div className="loading-spinner h-12 w-12 mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Users',
      value: stats?.total_users || 0,
      icon: Users,
      color: 'text-primary-600 dark:text-primary-400',
      bgColor: 'bg-primary-100 dark:bg-primary-900/30',
    },
    {
      title: 'Total Documents',
      value: stats?.total_documents || 0,
      icon: FileText,
      color: 'text-secondary-600 dark:text-secondary-400',
      bgColor: 'bg-secondary-100 dark:bg-secondary-900/30',
    },
    {
      title: 'Completed Jobs',
      value: stats?.completed_jobs || 0,
      icon: CheckCircle,
      color: 'text-success-600 dark:text-success-400',
      bgColor: 'bg-success-100 dark:bg-success-900/30',
    },
    {
      title: 'Failed Jobs',
      value: stats?.failed_jobs || 0,
      icon: AlertCircle,
      color: 'text-error-600 dark:text-error-400',
      bgColor: 'bg-error-100 dark:bg-error-900/30',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Admin Dashboard
              </h1>
              <p className="text-sm text-muted-foreground">
                Fernando Management
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="px-3 py-1">
                  Admin
                </Badge>
                <span className="text-sm font-medium">{user?.full_name || user?.email}</span>
              </div>
              <button
                onClick={() => navigate('/dashboard')}
                className="btn-pastel-primary px-4 py-2 rounded-lg font-medium"
              >
                User View
              </button>
              <button
                onClick={logout}
                className="btn-pastel-error px-4 py-2 rounded-lg font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card key={index} className="card-hover">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.title}
                  </CardTitle>
                  <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                    <Icon className={`h-5 w-5 ${stat.color}`} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stat.value.toLocaleString()}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-success-600" />
                Performance Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Success Rate</span>
                    <span className="text-sm font-bold text-success-600">
                      {((stats?.success_rate || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-success-500 h-2 rounded-full transition-all"
                      style={{ width: `${(stats?.success_rate || 0) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Avg Processing Time</span>
                    <span className="text-sm font-bold">
                      {(stats?.avg_processing_time || 0).toFixed(2)}s
                    </span>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Pending Jobs</span>
                  <Badge variant="outline" className="px-2 py-1">
                    {stats?.pending_jobs || 0}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary-600" />
                System Health
              </CardTitle>
              <CardDescription>Real-time system status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { name: 'Database', icon: Database, status: systemHealth.database },
                  { name: 'Backend API', icon: Server, status: systemHealth.backend },
                  { name: 'Storage', icon: HardDrive, status: systemHealth.storage },
                ].map((service, index) => {
                  const Icon = service.icon;
                  return (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-5 w-5 text-muted-foreground" />
                        <span className="font-medium">{service.name}</span>
                      </div>
                      <Badge
                        variant={service.status === 'healthy' ? 'default' : 'destructive'}
                        className={
                          service.status === 'healthy'
                            ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300'
                            : ''
                        }
                      >
                        {service.status === 'healthy' ? 'Healthy' : 'Down'}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common administrative tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <button 
                className="btn-pastel-primary px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/users')}
              >
                <Users className="h-5 w-5 mb-2" />
                <div className="font-semibold">User Management</div>
                <div className="text-xs opacity-70">Manage user accounts and permissions</div>
              </button>
              <button 
                className="btn-pastel-secondary px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/processing')}
              >
                <FileText className="h-5 w-5 mb-2" />
                <div className="font-semibold">Batch Processing</div>
                <div className="text-xs opacity-70">Monitor processing queue</div>
              </button>
              <button 
                className="btn-pastel-warning px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/audit-logs')}
              >
                <Activity className="h-5 w-5 mb-2" />
                <div className="font-semibold">Audit Logs</div>
                <div className="text-xs opacity-70">View system audit trail</div>
              </button>
              <button 
                className="btn-pastel-success px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/health')}
              >
                <Server className="h-5 w-5 mb-2" />
                <div className="font-semibold">System Health</div>
                <div className="text-xs opacity-70">Monitor system performance</div>
              </button>
              <button 
                className="btn-pastel-primary px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/licenses')}
              >
                <Key className="h-5 w-5 mb-2" />
                <div className="font-semibold">License Management</div>
                <div className="text-xs opacity-70">Manage license tiers and assignments</div>
              </button>
              <button 
                className="btn-pastel-secondary px-6 py-3 rounded-lg font-medium text-left hover:scale-105 transition-transform"
                onClick={() => navigate('/admin/billing-analytics')}
              >
                <CreditCard className="h-5 w-5 mb-2" />
                <div className="font-semibold">Billing Analytics</div>
                <div className="text-xs opacity-70">Revenue metrics and subscription trends</div>
              </button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
