import React, { useState, useEffect } from 'react';
import { 
  Users, UserPlus, Search, Filter, MoreVertical, Edit, Trash2, 
  Shield, ShieldCheck, UserCheck, UserX, Download, Upload,
  CheckSquare, Square, AlertCircle, CheckCircle, Settings,
  Activity, Clock, Globe, Database, Key, Bell, Eye,
  Mail, Phone, Calendar, MapPin, Briefcase, UserCog,
  RefreshCw, Download as DownloadIcon, Upload as UploadIcon,
  MessageSquare, Calendar as CalendarIcon, TrendingUp,
  Lock, Unlock, ShieldAlert, ShieldX, EyeOff, Eye as EyeIcon
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { 
  Dialog, DialogContent, DialogDescription, DialogFooter, 
  DialogHeader, DialogTitle 
} from '@/components/ui/dialog';
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuCheckboxItem
} from '@/components/ui/dropdown-menu';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';
import { useNavigate } from 'react-router-dom';

interface EnhancedUser {
  id: string;
  email: string;
  full_name: string;
  status: 'active' | 'inactive' | 'suspended' | 'deleted';
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
  active_sessions: number;
  activity_last_24h: number;
  permissions: string[];
  profile_image_url?: string;
}

interface UserStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  suspended_users: number;
  administrators: number;
  invited_users: number;
  mfa_enabled_users: number;
  new_users_this_month: number;
}

interface UserRole {
  id: string;
  name: string;
  description: string;
  level: number;
  permissions: string[];
}

interface UserInvitation {
  id: string;
  email: string;
  role_name: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invited_at: string;
  expires_at: string;
  invited_by: string;
}

export default function EnhancedUserManagementPage() {
  const [users, setUsers] = useState<EnhancedUser[]>([]);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [availableRoles, setAvailableRoles] = useState<UserRole[]>([]);
  const [pendingInvitations, setPendingInvitations] = useState<UserInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [organizationFilter, setOrganizationFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [currentTab, setCurrentTab] = useState('users');
  
  // Modal states
  const [showUserModal, setShowUserModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showInvitationModal, setShowInvitationModal] = useState(false);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [showBulkActionModal, setShowBulkActionModal] = useState(false);
  const [editingUser, setEditingUser] = useState<EnhancedUser | null>(null);
  
  // Form states
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    password: '',
    roles: [] as string[],
    organization_id: '',
    phone: '',
    department: '',
    job_title: '',
    status: 'active' as const,
    send_invitation: false
  });
  
  const [invitationData, setInvitationData] = useState({
    email: '',
    role_id: '',
    message: '',
    expires_in_days: 7
  });

  const { toast } = useToast();
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchUserData();
    fetchAvailableRoles();
    fetchPendingInvitations();
  }, []);

  useEffect(() => {
    fetchUserData();
  }, [searchTerm, statusFilter, roleFilter, organizationFilter]);

  const fetchUserData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/users/', {
        params: {
          search: searchTerm || undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          role: roleFilter !== 'all' ? roleFilter : undefined,
          organization_id: organizationFilter !== 'all' ? organizationFilter : undefined
        }
      });
      
      if (response.data && response.data.users) {
        setUsers(response.data.users);
        // Simulate stats if not available from API
        if (!userStats) {
          setUserStats(calculateStats(response.data.users));
        }
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load users data"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableRoles = async () => {
    try {
      const response = await api.get('/api/v1/users/roles/available');
      if (response.data) {
        setAvailableRoles(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    }
  };

  const fetchPendingInvitations = async () => {
    try {
      const response = await api.get('/api/v1/users/invitations/pending');
      if (response.data) {
        setPendingInvitations(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch invitations:', error);
    }
  };

  const calculateStats = (users: EnhancedUser[]): UserStats => {
    return {
      total_users: users.length,
      active_users: users.filter(u => u.status === 'active').length,
      inactive_users: users.filter(u => u.status === 'inactive').length,
      suspended_users: users.filter(u => u.status === 'suspended').length,
      administrators: users.filter(u => u.roles.includes('admin')).length,
      invited_users: 0, // Would come from invitations API
      mfa_enabled_users: users.filter(u => u.mfa_enabled).length,
      new_users_this_month: users.filter(u => {
        const createdDate = new Date(u.created_at);
        const monthStart = new Date();
        monthStart.setDate(1);
        monthStart.setHours(0, 0, 0, 0);
        return createdDate >= monthStart;
      }).length
    };
  };

  const handleCreateUser = async () => {
    try {
      const userData = {
        ...formData,
        roles: formData.roles.length > 0 ? formData.roles : ['user']
      };
      
      const response = await api.post('/api/v1/users/', userData);
      
      if (response.data) {
        setUsers(prev => [response.data, ...prev]);
        setShowUserModal(false);
        resetForm();
        toast({
          variant: "success",
          title: "Success",
          description: "User created successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to create user:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to create user"
      });
    }
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;
    
    try {
      const updateData = {
        ...formData,
        roles: formData.roles.length > 0 ? formData.roles : undefined
      };
      
      // Remove password from update if not provided
      if (!formData.password) {
        delete (updateData as any).password;
      }
      
      const response = await api.put(`/api/v1/users/${editingUser.id}`, updateData);
      
      if (response.data) {
        setUsers(prev => prev.map(u => u.id === editingUser.id ? response.data : u));
        setShowUserModal(false);
        setEditingUser(null);
        resetForm();
        toast({
          variant: "success",
          title: "Success",
          description: "User updated successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to update user:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to update user"
      });
    }
  };

  const handleDeactivateUser = async (userId: string) => {
    try {
      await api.post(`/api/v1/users/${userId}/deactivate`);
      setUsers(prev => prev.map(u => 
        u.id === userId ? { ...u, status: 'inactive' as const } : u
      ));
      toast({
        variant: "success",
        title: "Success",
        description: "User deactivated successfully"
      });
    } catch (error: any) {
      console.error('Failed to deactivate user:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to deactivate user"
      });
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      await api.delete(`/api/v1/users/${userId}`);
      setUsers(prev => prev.filter(u => u.id !== userId));
      toast({
        variant: "success",
        title: "Success",
        description: "User deleted successfully"
      });
    } catch (error: any) {
      console.error('Failed to delete user:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete user"
      });
    }
  };

  const handleInviteUser = async () => {
    try {
      const response = await api.post('/api/v1/users/invite', invitationData);
      
      if (response.data) {
        setPendingInvitations(prev => [response.data, ...prev]);
        setShowInvitationModal(false);
        setInvitationData({
          email: '',
          role_id: '',
          message: '',
          expires_in_days: 7
        });
        toast({
          variant: "success",
          title: "Success",
          description: "User invitation sent successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to invite user:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to send invitation"
      });
    }
  };

  const handleBulkAction = async (action: string, userIds: string[]) => {
    try {
      await api.post('/api/v1/users/bulk-actions', {
        action,
        user_ids: userIds
      });
      
      // Refresh data
      await fetchUserData();
      setSelectedUsers(new Set());
      setShowBulkActionModal(false);
      
      toast({
        variant: "success",
        title: "Success",
        description: `Bulk ${action} completed successfully`
      });
    } catch (error: any) {
      console.error('Failed to perform bulk action:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || `Failed to perform bulk ${action}`
      });
    }
  };

  const openEditModal = (user: EnhancedUser) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      full_name: user.full_name,
      password: '',
      roles: user.roles,
      organization_id: user.organization_id || '',
      phone: user.phone || '',
      department: user.department || '',
      job_title: user.job_title || '',
      status: user.status,
      send_invitation: false
    });
    setShowUserModal(true);
  };

  const resetForm = () => {
    setFormData({
      email: '',
      full_name: '',
      password: '',
      roles: [],
      organization_id: '',
      phone: '',
      department: '',
      job_title: '',
      status: 'active',
      send_invitation: false
    });
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || user.status === statusFilter;
    const matchesRole = roleFilter === 'all' || user.roles.includes(roleFilter);
    return matchesSearch && matchesStatus && matchesRole;
  });

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'success',
      inactive: 'secondary',
      suspended: 'destructive',
      deleted: 'destructive'
    };
    
    const icons = {
      active: <UserCheck className="h-3 w-3" />,
      inactive: <UserX className="h-3 w-3" />,
      suspended: <ShieldAlert className="h-3 w-3" />,
      deleted: <Trash2 className="h-3 w-3" />
    };
    
    return (
      <Badge variant={variants[status as keyof typeof variants] as any}>
        <div className="flex items-center gap-1">
          {icons[status as keyof typeof icons]}
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </div>
      </Badge>
    );
  };

  const getRoleBadge = (roles: string[]) => {
    const primaryRole = roles[0] || 'user';
    const variants = {
      admin: 'destructive',
      manager: 'default',
      user: 'secondary',
      viewer: 'outline'
    };
    
    return (
      <Badge variant={variants[primaryRole as keyof typeof variants] as any}>
        {primaryRole.charAt(0).toUpperCase() + primaryRole.slice(1)}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading user management...</p>
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
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Enhanced User Management
              </h1>
              <p className="text-sm text-muted-foreground">
                Comprehensive user administration and role management
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Button 
                variant="pastel-primary" 
                onClick={() => {
                  setEditingUser(null);
                  resetForm();
                  setShowUserModal(true);
                }}
                className="animate-slide-up"
              >
                <UserPlus className="h-4 w-4 mr-2" />
                Add User
              </Button>
              <Button 
                variant="pastel-secondary"
                onClick={() => setShowInvitationModal(true)}
              >
                <Mail className="h-4 w-4 mr-2" />
                Invite User
              </Button>
              <Button variant="outline" onClick={() => navigate('/admin')}>
                Back to Admin
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Statistics Cards */}
        {userStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <Card className="card-hover">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                <Users className="h-4 w-4 text-primary-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{userStats.total_users}</div>
                <p className="text-xs text-muted-foreground">
                  +{userStats.new_users_this_month} this month
                </p>
              </CardContent>
            </Card>
            
            <Card className="card-hover">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                <UserCheck className="h-4 w-4 text-success-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{userStats.active_users}</div>
                <p className="text-xs text-muted-foreground">
                  {((userStats.active_users / userStats.total_users) * 100).toFixed(1)}% of total
                </p>
              </CardContent>
            </Card>
            
            <Card className="card-hover">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Administrators</CardTitle>
                <ShieldCheck className="h-4 w-4 text-warning-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{userStats.administrators}</div>
                <p className="text-xs text-muted-foreground">
                  System administrators
                </p>
              </CardContent>
            </Card>
            
            <Card className="card-hover">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">MFA Enabled</CardTitle>
                <Lock className="h-4 w-4 text-success-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{userStats.mfa_enabled_users}</div>
                <p className="text-xs text-muted-foreground">
                  {userStats.total_users > 0 ? ((userStats.mfa_enabled_users / userStats.total_users) * 100).toFixed(1) : 0}% adoption
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content Tabs */}
        <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="invitations">Invitations ({pendingInvitations.length})</TabsTrigger>
            <TabsTrigger value="roles">Roles</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="users" className="space-y-6">
            {/* Filters and Actions */}
            <Card>
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
                  <div className="flex flex-col sm:flex-row gap-4 flex-1">
                    <div className="relative flex-1 max-w-sm">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                      <Input
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Filter by status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                        <SelectItem value="suspended">Suspended</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    <Select value={roleFilter} onValueChange={setRoleFilter}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Filter by role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Roles</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="manager">Manager</SelectItem>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedUsers.size > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {selectedUsers.size} selected
                      </span>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => setShowBulkActionModal(true)}
                      >
                        Bulk Actions
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Users Table */}
            <Card>
              <CardHeader>
                <CardTitle>Users ({filteredUsers.length})</CardTitle>
                <CardDescription>
                  Manage user accounts, roles, permissions, and account settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedUsers.size === filteredUsers.length && filteredUsers.length > 0}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedUsers(new Set(filteredUsers.map(u => u.id)));
                            } else {
                              setSelectedUsers(new Set());
                            }
                          }}
                          className="rounded"
                        />
                      </TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Security</TableHead>
                      <TableHead>Activity</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.map((user) => (
                      <TableRow key={user.id} className="animate-fade-in">
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedUsers.has(user.id)}
                            onChange={(e) => {
                              const newSelected = new Set(selectedUsers);
                              if (e.target.checked) {
                                newSelected.add(user.id);
                              } else {
                                newSelected.delete(user.id);
                              }
                              setSelectedUsers(newSelected);
                            }}
                            className="rounded"
                          />
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{user.full_name}</div>
                            <div className="text-sm text-muted-foreground">{user.email}</div>
                            {user.department && (
                              <div className="text-xs text-muted-foreground">{user.department}</div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(user.status)}</TableCell>
                        <TableCell>{getRoleBadge(user.roles)}</TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {user.phone && (
                              <div className="flex items-center text-xs text-muted-foreground">
                                <Phone className="h-3 w-3 mr-1" />
                                {user.phone}
                              </div>
                            )}
                            <div className="flex items-center text-xs">
                              <Mail className="h-3 w-3 mr-1" />
                              {user.email_verified ? (
                                <CheckCircle className="h-3 w-3 text-green-500" />
                              ) : (
                                <AlertCircle className="h-3 w-3 text-yellow-500" />
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {user.mfa_enabled ? (
                              <Badge variant="success" className="text-xs">
                                <Shield className="h-3 w-3 mr-1" />
                                MFA
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">
                                <Unlock className="h-3 w-3 mr-1" />
                                No MFA
                              </Badge>
                            )}
                            <div className="text-xs text-muted-foreground">
                              {user.active_sessions} sessions
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <div>{user.activity_last_24h} activities</div>
                            {user.last_login && (
                              <div className="text-xs text-muted-foreground">
                                {new Date(user.last_login).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEditModal(user)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit User
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                <Eye className="h-4 w-4 mr-2" />
                                View Profile
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                <Key className="h-4 w-4 mr-2" />
                                Manage Permissions
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                <Activity className="h-4 w-4 mr-2" />
                                Activity Log
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              {user.status === 'active' ? (
                                <DropdownMenuItem 
                                  onClick={() => handleDeactivateUser(user.id)}
                                  className="text-orange-600"
                                >
                                  <UserX className="h-4 w-4 mr-2" />
                                  Deactivate
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem>
                                  <UserCheck className="h-4 w-4 mr-2" />
                                  Reactivate
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem 
                                onClick={() => handleDeleteUser(user.id)}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="invitations" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Pending Invitations</CardTitle>
                <CardDescription>
                  Manage user invitations and onboarding process
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Invited By</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingInvitations.map((invitation) => (
                      <TableRow key={invitation.id}>
                        <TableCell>{invitation.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{invitation.role_name}</Badge>
                        </TableCell>
                        <TableCell>{invitation.invited_by}</TableCell>
                        <TableCell>
                          <Badge variant={invitation.status === 'pending' ? 'default' : 'secondary'}>
                            {invitation.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {new Date(invitation.expires_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem>
                                <Mail className="h-4 w-4 mr-2" />
                                Resend Invitation
                              </DropdownMenuItem>
                              <DropdownMenuItem className="text-red-600">
                                <X className="h-4 w-4 mr-2" />
                                Cancel Invitation
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="roles" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Role Management</CardTitle>
                <CardDescription>
                  Manage user roles and permissions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {availableRoles.map((role) => (
                    <Card key={role.id} className="hover:shadow-md transition-shadow">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">{role.name}</CardTitle>
                        <CardDescription>{role.description}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          <div className="text-sm">
                            <span className="font-medium">Level:</span> {role.level}
                          </div>
                          <div className="text-sm">
                            <span className="font-medium">Permissions:</span> {role.permissions?.length || 0}
                          </div>
                          <div className="flex justify-end space-x-2 pt-2">
                            <Button variant="outline" size="sm">
                              <Edit className="h-3 w-3" />
                            </Button>
                            <Button variant="outline" size="sm">
                              <Users className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>User Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span>New users this month</span>
                      <span className="font-bold">{userStats?.new_users_this_month || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Active sessions</span>
                      <span className="font-bold">
                        {users.reduce((sum, user) => sum + user.active_sessions, 0)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Recent activities</span>
                      <span className="font-bold">
                        {users.reduce((sum, user) => sum + user.activity_last_24h, 0)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>Security Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span>MFA Adoption</span>
                      <span className="font-bold">
                        {userStats?.total_users ? 
                          ((userStats.mfa_enabled_users / userStats.total_users) * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Email Verification</span>
                      <span className="font-bold">
                        {users.filter(u => u.email_verified).length} / {users.length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Onboarding Complete</span>
                      <span className="font-bold">
                        {users.filter(u => u.onboarding_completed).length} / {users.length}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* User Creation/Edit Modal */}
        <Dialog open={showUserModal} onOpenChange={setShowUserModal}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingUser ? 'Edit User' : 'Create New User'}
              </DialogTitle>
              <DialogDescription>
                {editingUser ? 'Update user information and settings.' : 'Add a new user to the system.'}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>
              </div>
              
              {!editingUser && (
                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                  />
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="department">Department</Label>
                  <Input
                    id="department"
                    value={formData.department}
                    onChange={(e) => setFormData({...formData, department: e.target.value})}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="job_title">Job Title</Label>
                <Input
                  id="job_title"
                  value={formData.job_title}
                  onChange={(e) => setFormData({...formData, job_title: e.target.value})}
                />
              </div>
              
              <div>
                <Label>Roles</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {availableRoles.map((role) => (
                    <Badge 
                      key={role.id}
                      variant={formData.roles.includes(role.name) ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => {
                        const newRoles = formData.roles.includes(role.name)
                          ? formData.roles.filter(r => r !== role.name)
                          : [...formData.roles, role.name];
                        setFormData({...formData, roles: newRoles});
                      }}
                    >
                      {role.name}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowUserModal(false)}>
                Cancel
              </Button>
              <Button variant="pastel-primary" onClick={editingUser ? handleUpdateUser : handleCreateUser}>
                {editingUser ? 'Update User' : 'Create User'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* User Invitation Modal */}
        <Dialog open={showInvitationModal} onOpenChange={setShowInvitationModal}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Invite User</DialogTitle>
              <DialogDescription>
                Send an invitation to a user to join your organization.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div>
                <Label htmlFor="invitation_email">Email</Label>
                <Input
                  id="invitation_email"
                  type="email"
                  value={invitationData.email}
                  onChange={(e) => setInvitationData({...invitationData, email: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="role_id">Role</Label>
                <Select value={invitationData.role_id} onValueChange={(value) => setInvitationData({...invitationData, role_id: value})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableRoles.map((role) => (
                      <SelectItem key={role.id} value={role.id}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="message">Message (optional)</Label>
                <Input
                  id="message"
                  value={invitationData.message}
                  onChange={(e) => setInvitationData({...invitationData, message: e.target.value})}
                  placeholder="Personal message for the invitation"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowInvitationModal(false)}>
                Cancel
              </Button>
              <Button variant="pastel-primary" onClick={handleInviteUser}>
                Send Invitation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Action Modal */}
        <Dialog open={showBulkActionModal} onOpenChange={setShowBulkActionModal}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Bulk User Actions</DialogTitle>
              <DialogDescription>
                Perform actions on {selectedUsers.size} selected users.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => handleBulkAction('activate', Array.from(selectedUsers))}
                >
                  <UserCheck className="h-4 w-4 mr-2" />
                  Activate Users
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => handleBulkAction('deactivate', Array.from(selectedUsers))}
                >
                  <UserX className="h-4 w-4 mr-2" />
                  Deactivate Users
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => handleBulkAction('delete', Array.from(selectedUsers))}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Users
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowBulkActionModal(false)}>
                Cancel
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}