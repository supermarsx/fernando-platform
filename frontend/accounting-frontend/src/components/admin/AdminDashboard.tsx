import React, { useState, useEffect } from 'react';
import { 
  Users, Shield, Building, Key, Activity, BarChart3, 
  TrendingUp, AlertCircle, CheckCircle, Clock, Globe,
  Settings, Bell, Download, RefreshCw, Plus, Search,
  Eye, UserPlus, Mail, Phone, MapPin, Calendar,
  PieChart, LineChart, Monitor, Smartphone, Database,
  Lock, Unlock, UserCheck, UserX, Award, Target,
  Zap, Headphones, MessageSquare, FileText
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';
import { useNavigate } from 'react-router-dom';

interface DashboardStats {
  totalUsers: number;
  activeUsers: number;
  totalOrganizations: number;
  totalRoles: number;
  totalPermissions: number;
  activeSessions: number;
  recentActivities: number;
  mfaAdoption: number;
  securityScore: number;
}

interface RecentActivity {
  id: string;
  action: string;
  user: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
  details?: string;
}

interface SecurityAlert {
  id: string;
  type: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: string;
  acknowledged: boolean;
}

interface SystemHealth {
  database: 'healthy' | 'degraded' | 'down';
  cache: 'healthy' | 'degraded' | 'down';
  api: 'healthy' | 'degraded' | 'down';
  overall: 'healthy' | 'degraded' | 'down';
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [securityAlerts, setSecurityAlerts] = useState<SecurityAlert[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentTab, setCurrentTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);

  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch multiple endpoints in parallel
      const [
        usersRes,
        orgsRes,
        rolesRes,
        activitiesRes,
        healthRes
      ] = await Promise.all([
        api.get('/api/v1/users/', { params: { per_page: 1 } }),
        api.get('/api/v1/users/organizations'),
        api.get('/api/v1/users/roles/available'),
        api.get('/api/v1/users/audit-logs', { params: { per_page: 10 } }),
        api.get('/api/v1/system/status')
      ]);

      // Process user stats
      const usersData = usersRes.data;
      const orgsData = orgsRes.data || [];
      const rolesData = rolesRes.data || [];
      
      // Calculate stats
      const totalUsers = usersData.total || 0;
      const activeUsers = orgsData.reduce((sum: number, org: any) => {
        return sum + (org.active_users || 0);
      }, 0);

      setStats({
        totalUsers,
        activeUsers,
        totalOrganizations: orgsData.length,
        totalRoles: rolesData.length,
        totalPermissions: 24, // Mock value - would come from permissions endpoint
        activeSessions: Math.floor(totalUsers * 0.7), // Mock calculation
        recentActivities: 142, // Mock value
        mfaAdoption: 45, // Mock value
        securityScore: 87 // Mock value
      });

      // Process recent activities
      const activities = (activitiesRes.data || []).slice(0, 8).map((activity: any) => ({
        id: activity.audit_id,
        action: activity.action,
        user: activity.actor_user_id || 'System',
        timestamp: activity.timestamp,
        status: activity.success ? 'success' : 'error' as const,
        details: `${activity.resource_type}: ${activity.resource_id}`
      }));
      
      setRecentActivities(activities);

      // Mock security alerts
      setSecurityAlerts([
        {
          id: '1',
          type: 'medium',
          title: 'Failed Login Attempts',
          description: '3 failed login attempts detected',
          timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          acknowledged: false
        },
        {
          id: '2',
          type: 'low',
          title: 'Password Expiry Warning',
          description: '5 user passwords expire in 7 days',
          timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          acknowledged: false
        }
      ]);

      // Process system health
      const health = healthRes.data;
      setSystemHealth({
        database: health.database === 'connected' ? 'healthy' : 'degraded',
        cache: health.cache === 'healthy' ? 'healthy' : 'degraded',
        api: 'healthy', // Mock value
        overall: health.status === 'healthy' ? 'healthy' : 'degraded'
      });

    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load dashboard data"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchDashboardData();
    setRefreshing(false);
    toast({
      variant: "success",
      title: "Success",
      description: "Dashboard refreshed successfully"
    });
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'down':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getAlertBadge = (type: string) => {
    const variants = {
      low: 'secondary',
      medium: 'default',
      high: 'destructive',
      critical: 'destructive'
    };
    
    const icons = {
      low: <AlertCircle className="h-3 w-3" />,
      medium: <AlertCircle className="h-3 w-3" />,
      high: <AlertCircle className="h-3 w-3" />,
      critical: <AlertCircle className="h-3 w-3" />
    };
    
    return (
      <Badge variant={variants[type as keyof typeof variants] as any}>
        <div className="flex items-center gap-1">
          {icons[type as keyof typeof icons]}
          {type.charAt(0).toUpperCase() + type.slice(1)}
        </div>
      </Badge>
    );
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Admin Dashboard
              </h1>
              <p className="text-sm text-muted-foreground">
                Comprehensive user management and system monitoring
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button 
                variant="outline" 
                onClick={handleRefresh}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button 
                variant="pastel-primary" 
                onClick={() => navigate('/admin/users')}
                className="animate-slide-up"
              >
                <Users className="h-4 w-4 mr-2" />
                Manage Users
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.totalUsers.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                {stats?.activeUsers} active users
              </p>
              <Progress 
                value={stats ? (stats.activeUsers / stats.totalUsers) * 100 : 0} 
                className="h-2 mt-2"
              />
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Organizations</CardTitle>
              <Building className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.totalOrganizations}</div>
              <p className="text-xs text-muted-foreground">
                Multi-tenant setup
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Security Score</CardTitle>
              <Shield className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.securityScore}%</div>
              <p className="text-xs text-muted-foreground">
                {stats?.mfaAdoption}% MFA adoption
              </p>
              <Progress 
                value={stats?.securityScore || 0} 
                className="h-2 mt-2"
              />
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
              <Monitor className="h-4 w-4 text-info-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.activeSessions}</div>
              <p className="text-xs text-muted-foreground">
                Currently logged in
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="activity">Activity</TabsTrigger>
            <TabsTrigger value="system">System</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Activities */}
              <Card>
                <CardHeader>
                  <CardTitle>Recent Activities</CardTitle>
                  <CardDescription>
                    Latest user actions and system events
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {recentActivities.map((activity) => (
                      <div key={activity.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                        <div className={`w-2 h-2 rounded-full ${
                          activity.status === 'success' ? 'bg-green-500' : 
                          activity.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                        }`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {activity.action.replace('_', ' ').toUpperCase()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            by {activity.user} • {formatTimestamp(activity.timestamp)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Security Alerts */}
              <Card>
                <CardHeader>
                  <CardTitle>Security Alerts</CardTitle>
                  <CardDescription>
                    Active security notifications requiring attention
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {securityAlerts.length > 0 ? (
                      securityAlerts.map((alert) => (
                        <div key={alert.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                          {getAlertBadge(alert.type)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{alert.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {alert.description}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatTimestamp(alert.timestamp)}
                            </p>
                          </div>
                          {!alert.acknowledged && (
                            <Button variant="ghost" size="sm">
                              Acknowledge
                            </Button>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                        <p>No active security alerts</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common administrative tasks
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Button 
                    variant="outline" 
                    className="h-20 flex flex-col items-center justify-center space-y-2"
                    onClick={() => navigate('/admin/users')}
                  >
                    <UserPlus className="h-6 w-6" />
                    <span>Add User</span>
                  </Button>
                  <Button 
                    variant="outline" 
                    className="h-20 flex flex-col items-center justify-center space-y-2"
                    onClick={() => navigate('/admin/organizations')}
                  >
                    <Building className="h-6 w-6" />
                    <span>New Org</span>
                  </Button>
                  <Button 
                    variant="outline" 
                    className="h-20 flex flex-col items-center justify-center space-y-2"
                    onClick={() => navigate('/admin/rbac')}
                  >
                    <Shield className="h-6 w-6" />
                    <span>Manage Roles</span>
                  </Button>
                  <Button 
                    variant="outline" 
                    className="h-20 flex flex-col items-center justify-center space-y-2"
                  >
                    <Download className="h-6 w-6" />
                    <span>Export Data</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="users" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>User Management</CardTitle>
                  <CardDescription>
                    Comprehensive user administration
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-12">
                    <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-muted-foreground mb-4">
                      Advanced user management interface
                    </p>
                    <Button onClick={() => navigate('/admin/users')}>
                      Open User Management
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>User Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span>Total Users</span>
                      <span className="font-bold">{stats?.totalUsers}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Active Users</span>
                      <span className="font-bold text-green-600">{stats?.activeUsers}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>MFA Enabled</span>
                      <span className="font-bold">{stats?.mfaAdoption}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Recent Sign-ups</span>
                      <span className="font-bold">12</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="security" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Security Overview</CardTitle>
                  <CardDescription>
                    Current security posture and compliance status
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span>Overall Security Score</span>
                      <div className="flex items-center gap-2">
                        <Progress value={stats?.securityScore || 0} className="w-20 h-2" />
                        <span className="font-bold">{stats?.securityScore}%</span>
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span>MFA Adoption Rate</span>
                      <span className="font-bold">{stats?.mfaAdoption}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Password Compliance</span>
                      <span className="font-bold text-green-600">92%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Account Lockouts (24h)</span>
                      <span className="font-bold text-red-600">3</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Compliance Status</CardTitle>
                  <CardDescription>
                    Regulatory and internal compliance metrics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span>GDPR Compliance</span>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                    <div className="flex justify-between items-center">
                      <span>SOC 2 Controls</span>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Audit Logging</span>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Data Retention</span>
                      <AlertCircle className="h-5 w-5 text-yellow-500" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="activity" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Activity Monitoring</CardTitle>
                <CardDescription>
                  Real-time user activity and system events
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Activity className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground mb-4">
                    Comprehensive activity monitoring and analytics
                  </p>
                  <Button>
                    View All Activities
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="system" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {systemHealth && Object.entries(systemHealth).map(([service, status]) => (
                <Card key={service}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium capitalize">{service}</CardTitle>
                    {getHealthIcon(status)}
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold capitalize">{status}</div>
                    <p className="text-xs text-muted-foreground">
                      {service === 'overall' ? 'System status' : `${service} service status`}
                    </p>
                  </CardContent>
                </Card>
              ))}

              <Card className="md:col-span-2 lg:col-span-3">
                <CardHeader>
                  <CardTitle>System Metrics</CardTitle>
                  <CardDescription>
                    Real-time system performance and resource usage
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold">98.7%</div>
                      <p className="text-sm text-muted-foreground">Uptime</p>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">1.2s</div>
                      <p className="text-sm text-muted-foreground">Avg Response</p>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">2.3GB</div>
                      <p className="text-sm text-muted-foreground">Memory Usage</p>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">156</div>
                      <p className="text-sm text-muted-foreground">Active Requests</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}