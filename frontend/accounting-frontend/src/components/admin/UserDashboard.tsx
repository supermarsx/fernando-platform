import React, { useState, useEffect } from 'react';
import { 
  User, Activity, Shield, Key, Settings, Calendar, Clock, 
  Globe, MapPin, Smartphone, Monitor, Eye, EyeOff,
  CheckCircle, XCircle, AlertCircle, TrendingUp,
  BarChart3, PieChart, LineChart, UserCheck, UserX,
  Lock, Unlock, Mail, Phone, Building, Briefcase
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';

interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  status: string;
  organization_id?: string;
  roles: string[];
  email_verified: boolean;
  phone_verified: boolean;
  phone?: string;
  department?: string;
  job_title?: string;
  created_at: string;
  last_login?: string;
  last_password_change?: string;
  mfa_enabled: boolean;
  onboarding_completed: boolean;
  profile_image_url?: string;
  bio?: string;
}

interface UserStatistics {
  total_sessions: number;
  active_sessions: number;
  activity_last_24h: number;
  activity_last_7d: number;
  logins_last_24h: number;
  active_role_assignments: number;
  password_age_days: number;
}

interface UserActivity {
  activity_id: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  success: boolean;
  created_at: string;
}

interface UserSession {
  session_id: string;
  ip_address?: string;
  user_agent?: string;
  device_info?: Record<string, any>;
  location?: Record<string, any>;
  login_at: string;
  last_activity_at: string;
  is_active: boolean;
  mfa_verified: boolean;
}

interface UserDashboardProps {
  userId: string;
  currentUserId?: string;
  canEdit?: boolean;
}

export default function UserDashboard({ userId, currentUserId, canEdit = false }: UserDashboardProps) {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [userStats, setUserStats] = useState<UserStatistics | null>(null);
  const [userActivities, setUserActivities] = useState<UserActivity[]>([]);
  const [userSessions, setUserSessions] = useState<UserSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const { toast } = useToast();

  useEffect(() => {
    if (userId) {
      fetchUserData();
    }
  }, [userId]);

  const fetchUserData = async () => {
    try {
      setLoading(true);
      
      // Fetch user profile and stats
      const [profileRes, statsRes, activitiesRes, sessionsRes] = await Promise.all([
        api.get(`/api/v1/users/${userId}`),
        api.get(`/api/v1/users/${userId}/statistics`),
        api.get(`/api/v1/users/${userId}/activity?limit=20`),
        api.get(`/api/v1/users/${userId}/sessions?active_only=false`)
      ]);
      
      setUserProfile(profileRes.data);
      setUserStats(statsRes.data);
      setUserActivities(activitiesRes.data || []);
      setUserSessions(sessionsRes.data || []);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load user data"
      });
    } finally {
      setLoading(false);
    }
  };

  const getDeviceIcon = (userAgent?: string) => {
    if (!userAgent) return <Monitor className="h-4 w-4" />;
    
    const ua = userAgent.toLowerCase();
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
      return <Smartphone className="h-4 w-4" />;
    }
    return <Monitor className="h-4 w-4" />;
  };

  const getActivityIcon = (action: string) => {
    if (action.includes('login')) return <UserCheck className="h-4 w-4 text-green-500" />;
    if (action.includes('logout')) return <UserX className="h-4 w-4 text-red-500" />;
    if (action.includes('password')) return <Key className="h-4 w-4 text-blue-500" />;
    if (action.includes('role')) return <Shield className="h-4 w-4 text-purple-500" />;
    return <Activity className="h-4 w-4 text-gray-500" />;
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'success',
      inactive: 'secondary',
      suspended: 'destructive'
    };
    
    return (
      <Badge variant={variants[status as keyof typeof variants] as any}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const formatLastActivity = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getPasswordAgeColor = (ageDays?: number) => {
    if (!ageDays) return 'success';
    if (ageDays < 30) return 'success';
    if (ageDays < 90) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!userProfile || !userStats) {
    return (
      <div className="text-center py-12">
        <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <p className="text-muted-foreground">User not found</p>
      </div>
    );
  }

  const isOwnProfile = currentUserId === userId;
  const canViewSensitiveInfo = canEdit || isOwnProfile;

  return (
    <div className="space-y-6">
      {/* User Header */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gradient-primary rounded-full flex items-center justify-center">
                <User className="h-8 w-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">{userProfile.full_name}</h2>
                <p className="text-muted-foreground">{userProfile.email}</p>
                <div className="flex items-center space-x-2 mt-2">
                  {getStatusBadge(userProfile.status)}
                  {userProfile.email_verified && (
                    <Badge variant="success" className="text-xs">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Email Verified
                    </Badge>
                  )}
                  {userProfile.mfa_enabled && (
                    <Badge variant="success" className="text-xs">
                      <Shield className="h-3 w-3 mr-1" />
                      MFA Enabled
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            {canEdit && (
              <Button variant="outline">
                <Settings className="h-4 w-4 mr-2" />
                Edit Profile
              </Button>
            )}
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">{userStats.total_sessions}</div>
              <div className="text-sm text-muted-foreground">Total Sessions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{userStats.activity_last_7d}</div>
              <div className="text-sm text-muted-foreground">This Week</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning">{userStats.active_role_assignments}</div>
              <div className="text-sm text-muted-foreground">Roles</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-info">{userStats.logins_last_24h}</div>
              <div className="text-sm text-muted-foreground">Logins (24h)</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* User Information */}
            <Card>
              <CardHeader>
                <CardTitle>User Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Department</span>
                  <span>{userProfile.department || 'Not specified'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Job Title</span>
                  <span>{userProfile.job_title || 'Not specified'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Phone</span>
                  <span>{userProfile.phone || 'Not provided'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Organization</span>
                  <span>{userProfile.organization_id || 'Not assigned'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Member Since</span>
                  <span>{new Date(userProfile.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Last Login</span>
                  <span>
                    {userProfile.last_login 
                      ? formatLastActivity(userProfile.last_login)
                      : 'Never'
                    }
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Activity Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Activity Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">24h Activity</span>
                    <span className="text-sm font-medium">{userStats.activity_last_24h}</span>
                  </div>
                  <Progress value={(userStats.activity_last_24h / 100) * 100} />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">7d Activity</span>
                    <span className="text-sm font-medium">{userStats.activity_last_7d}</span>
                  </div>
                  <Progress value={(userStats.activity_last_7d / 500) * 100} />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">Active Sessions</span>
                    <span className="text-sm font-medium">{userStats.active_sessions}</span>
                  </div>
                  <Progress value={(userStats.active_sessions / 5) * 100} />
                </div>
              </CardContent>
            </Card>

            {/* Recent Activities */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recent Activities</CardTitle>
                <CardDescription>Latest user actions and events</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {userActivities.slice(0, 10).map((activity) => (
                    <div key={activity.activity_id} className="flex items-start space-x-3 p-3 rounded-lg border">
                      <div className="mt-1">
                        {getActivityIcon(activity.action)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium">
                            {activity.action.replace('_', ' ').toUpperCase()}
                          </p>
                          <span className="text-xs text-muted-foreground">
                            {formatLastActivity(activity.created_at)}
                          </span>
                        </div>
                        {activity.resource_type && (
                          <p className="text-xs text-muted-foreground">
                            Resource: {activity.resource_type}
                          </p>
                        )}
                        {activity.ip_address && canViewSensitiveInfo && (
                          <p className="text-xs text-muted-foreground">
                            IP: {activity.ip_address}
                          </p>
                        )}
                      </div>
                      <div>
                        {activity.success ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="activity" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Activity Timeline</CardTitle>
              <CardDescription>Complete history of user actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {userActivities.map((activity) => (
                  <div key={activity.activity_id} className="border-l-2 border-primary/20 pl-4 pb-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <div className="mt-1">
                          {getActivityIcon(activity.action)}
                        </div>
                        <div>
                          <p className="font-medium">{activity.action.replace('_', ' ')}</p>
                          {activity.details && Object.keys(activity.details).length > 0 && (
                            <div className="mt-1 text-sm text-muted-foreground">
                              {JSON.stringify(activity.details, null, 2)}
                            </div>
                          )}
                          <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                            <span>{formatLastActivity(activity.created_at)}</span>
                            {activity.resource_type && (
                              <span>Resource: {activity.resource_type}</span>
                            )}
                            {activity.ip_address && canViewSensitiveInfo && (
                              <span>IP: {activity.ip_address}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div>
                        {activity.success ? (
                          <Badge variant="success" className="text-xs">Success</Badge>
                        ) : (
                          <Badge variant="destructive" className="text-xs">Failed</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sessions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>User Sessions</CardTitle>
              <CardDescription>Active and historical login sessions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {userSessions.map((session) => (
                  <div key={session.session_id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted">
                        {getDeviceIcon(session.user_agent)}
                      </div>
                      <div>
                        <p className="font-medium">
                          {session.device_info?.device || 'Unknown Device'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {session.device_info?.browser || 'Unknown Browser'}
                        </p>
                        {session.location && (
                          <div className="flex items-center text-xs text-muted-foreground mt-1">
                            <MapPin className="h-3 w-3 mr-1" />
                            {session.location.city}, {session.location.country}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">
                        {formatLastActivity(session.last_activity_at)}
                      </p>
                      {canViewSensitiveInfo && session.ip_address && (
                        <p className="text-xs text-muted-foreground">{session.ip_address}</p>
                      )}
                      <div className="flex items-center justify-end space-x-2 mt-1">
                        {session.is_active && (
                          <Badge variant="success" className="text-xs">Active</Badge>
                        )}
                        {session.mfa_verified && (
                          <Badge variant="default" className="text-xs">MFA</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Security Status */}
            <Card>
              <CardHeader>
                <CardTitle>Security Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>Email Verification</span>
                  <div className="flex items-center">
                    {userProfile.email_verified ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mr-2" />
                    )}
                    {userProfile.email_verified ? 'Verified' : 'Unverified'}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span>Phone Verification</span>
                  <div className="flex items-center">
                    {userProfile.phone_verified ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mr-2" />
                    )}
                    {userProfile.phone_verified ? 'Verified' : 'Unverified'}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span>Multi-Factor Authentication</span>
                  <div className="flex items-center">
                    {userProfile.mfa_enabled ? (
                      <Shield className="h-4 w-4 text-green-500 mr-2" />
                    ) : (
                      <Unlock className="h-4 w-4 text-red-500 mr-2" />
                    )}
                    {userProfile.mfa_enabled ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span>Password Age</span>
                  <div className="flex items-center">
                    <Badge variant={getPasswordAgeColor(userStats.password_age_days) as any}>
                      {userStats.password_age_days ? `${userStats.password_age_days} days` : 'Unknown'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Roles and Permissions */}
            <Card>
              <CardHeader>
                <CardTitle>Roles & Permissions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Current Roles</h4>
                  <div className="space-y-2">
                    {userProfile.roles.map((role) => (
                      <Badge key={role} variant="outline" className="mr-2">
                        {role}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span>Role Assignments</span>
                  <span className="font-medium">{userStats.active_role_assignments}</span>
                </div>
                {isOwnProfile && (
                  <Button variant="outline" className="w-full">
                    <Key className="h-4 w-4 mr-2" />
                    View My Permissions
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Security Events */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recent Security Events</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Password changes */}
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      <Key className="h-5 w-5 text-green-600" />
                      <div>
                        <p className="font-medium">Password Changed</p>
                        <p className="text-sm text-muted-foreground">
                          Password was updated successfully
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">
                        {userProfile.last_password_change 
                          ? formatLastActivity(userProfile.last_password_change)
                          : 'Unknown'
                        }
                      </p>
                      <Badge variant="success" className="text-xs">Success</Badge>
                    </div>
                  </div>

                  {/* Login events */}
                  {userStats.logins_last_24h > 0 && (
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border">
                      <div className="flex items-center space-x-3">
                        <UserCheck className="h-5 w-5 text-blue-600" />
                        <div>
                          <p className="font-medium">Successful Login</p>
                          <p className="text-sm text-muted-foreground">
                            {userStats.logins_last_24h} successful login{userStats.logins_last_24h !== 1 ? 's' : ''} in the last 24 hours
                          </p>
                        </div>
                      </div>
                      <Badge variant="default" className="text-xs">Info</Badge>
                    </div>
                  )}

                  {/* MFA status */}
                  <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      <Shield className="h-5 w-5 text-purple-600" />
                      <div>
                        <p className="font-medium">Multi-Factor Authentication</p>
                        <p className="text-sm text-muted-foreground">
                          {userProfile.mfa_enabled ? 'MFA is enabled and active' : 'MFA is not configured'}
                        </p>
                      </div>
                    </div>
                    <Badge variant={userProfile.mfa_enabled ? 'success' : 'secondary'} className="text-xs">
                      {userProfile.mfa_enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}