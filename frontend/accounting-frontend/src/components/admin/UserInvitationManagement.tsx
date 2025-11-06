import React, { useState, useEffect } from 'react';
import { 
  Mail, Plus, Send, RefreshCw, Trash2, Download, Upload,
  Search, Filter, MoreVertical, Eye, Clock, CheckCircle,
  XCircle, AlertCircle, Users, BarChart3, PieChart,
  Calendar, UserPlus, FileText, Shield, Building,
  Edit, Copy, Settings, TrendingUp, Activity,
  X, Save, Check
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { 
  Dialog, DialogContent, DialogDescription, DialogFooter, 
  DialogHeader, DialogTitle 
} from '@/components/ui/dialog';
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuSeparator 
} from '@/components/ui/dropdown-menu';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';

interface UserInvitation {
  invitation_id: string;
  email: string;
  role_id: string;
  role_name?: string;
  invited_by: string;
  invited_by_name?: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  token: string;
  expires_at: string;
  accepted_at?: string;
  accepted_user_id?: string;
  message?: string;
  organization_id: string;
  created_at: string;
  resent_at?: string;
  resent_by?: string;
}

interface Role {
  role_id: string;
  name: string;
  description: string;
  level: number;
  is_system_role: boolean;
}

interface Organization {
  organization_id: string;
  name: string;
  description?: string;
  subscription_tier: string;
  subscription_status: string;
  max_users: number;
  max_documents: number;
  max_storage_gb: number;
  features: string[];
  settings: Record<string, any>;
  status: string;
  created_at: string;
}

interface InvitationStatistics {
  total_invitations: number;
  pending_invitations: number;
  accepted_invitations: number;
  expired_invitations: number;
  cancelled_invitations: number;
  acceptance_rate: number;
  avg_response_time_hours: number;
  invitations_last_30d: number;
  invitations_last_7d: number;
  invitations_this_month: number;
  top_invited_roles: Record<string, number>;
  monthly_trend: Array<{ month: string; count: number; accepted: number }>;
}

export default function UserInvitationManagement() {
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [stats, setStats] = useState<InvitationStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(25);
  const [totalInvitations, setTotalInvitations] = useState(0);
  const [currentTab, setCurrentTab] = useState('overview');

  // Modal states
  const [showSendModal, setShowSendModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showResendModal, setShowResendModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedInvitation, setSelectedInvitation] = useState<UserInvitation | null>(null);
  const [selectedInvitations, setSelectedInvitations] = useState<string[]>([]);

  // Form states
  const [invitationForm, setInvitationForm] = useState({
    email: '',
    role_id: '',
    message: '',
    expires_in_days: 7
  });

  const [bulkForm, setBulkForm] = useState({
    csv_content: '',
    role_id: '',
    expires_in_days: 7,
    message: ''
  });

  const { toast } = useToast();

  useEffect(() => {
    loadInvitations();
    loadRoles();
    loadOrganizations();
    loadStats();
  }, [currentPage, statusFilter, roleFilter]);

  useEffect(() => {
    if (searchTerm) {
      const timeoutId = setTimeout(() => {
        setCurrentPage(1);
        loadInvitations();
      }, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm]);

  const loadInvitations = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString()
      });

      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await api.get(`/users/invitations?${params}`);
      setInvitations(response.data);
      setTotalInvitations(response.headers['x-total-count'] || 0);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to load invitations",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const loadRoles = async () => {
    try {
      const response = await api.get('/users/roles/available');
      setRoles(response.data);
    } catch (error: any) {
      console.error('Failed to load roles:', error);
    }
  };

  const loadOrganizations = async () => {
    try {
      const response = await api.get('/users/organizations');
      setOrganizations(response.data);
    } catch (error: any) {
      console.error('Failed to load organizations:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await api.get('/users/invitations/stats');
      setStats(response.data);
    } catch (error: any) {
      console.error('Failed to load invitation statistics:', error);
    }
  };

  const handleSendInvitation = async () => {
    try {
      if (!invitationForm.email || !invitationForm.role_id) {
        toast({
          title: "Validation Error",
          description: "Email and role are required",
          variant: "destructive"
        });
        return;
      }

      await api.post('/users/invite', {
        email: invitationForm.email,
        role_id: invitationForm.role_id,
        message: invitationForm.message,
        expires_in_days: invitationForm.expires_in_days
      });

      toast({
        title: "Success",
        description: "Invitation sent successfully"
      });

      setShowSendModal(false);
      setInvitationForm({
        email: '',
        role_id: '',
        message: '',
        expires_in_days: 7
      });
      loadInvitations();
      loadStats();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send invitation",
        variant: "destructive"
      });
    }
  };

  const handleBulkInvite = async () => {
    try {
      if (!bulkForm.csv_content || !bulkForm.role_id) {
        toast({
          title: "Validation Error",
          description: "CSV content and role are required",
          variant: "destructive"
        });
        return;
      }

      // Parse CSV and send invitations
      const emails = bulkForm.csv_content
        .split('\n')
        .map(line => line.trim())
        .filter(line => line && line.includes('@'));

      if (emails.length === 0) {
        toast({
          title: "Validation Error",
          description: "No valid email addresses found",
          variant: "destructive"
        });
        return;
      }

      // Send bulk invitations
      const promises = emails.map(email =>
        api.post('/users/invite', {
          email,
          role_id: bulkForm.role_id,
          message: bulkForm.message,
          expires_in_days: bulkForm.expires_in_days
        })
      );

      await Promise.all(promises);

      toast({
        title: "Success",
        description: `Sent ${emails.length} invitations successfully`
      });

      setShowBulkModal(false);
      setBulkForm({
        csv_content: '',
        role_id: '',
        expires_in_days: 7,
        message: ''
      });
      loadInvitations();
      loadStats();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send bulk invitations",
        variant: "destructive"
      });
    }
  };

  const handleResendInvitation = async () => {
    try {
      if (!selectedInvitation) return;

      await api.post(`/users/invitations/${selectedInvitation.invitation_id}/resend`);

      toast({
        title: "Success",
        description: "Invitation resent successfully"
      });

      setShowResendModal(false);
      setSelectedInvitation(null);
      loadInvitations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to resend invitation",
        variant: "destructive"
      });
    }
  };

  const handleDeleteInvitation = async () => {
    try {
      if (!selectedInvitation) return;

      await api.delete(`/users/invitations/${selectedInvitation.invitation_id}`);

      toast({
        title: "Success",
        description: "Invitation deleted successfully"
      });

      setShowDeleteModal(false);
      setSelectedInvitation(null);
      loadInvitations();
      loadStats();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete invitation",
        variant: "destructive"
      });
    }
  };

  const handleRevokeInvitation = async (invitation: UserInvitation) => {
    try {
      await api.post(`/users/invitations/${invitation.invitation_id}/cancel`);

      toast({
        title: "Success",
        description: "Invitation cancelled successfully"
      });

      loadInvitations();
      loadStats();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to cancel invitation",
        variant: "destructive"
      });
    }
  };

  const handleExportInvitations = async () => {
    try {
      const response = await api.get('/users/invitations', {
        responseType: 'blob'
      });

      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invitations-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast({
        title: "Success",
        description: "Invitations exported successfully"
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: "Failed to export invitations",
        variant: "destructive"
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-orange-500" />;
      case 'accepted':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'expired':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      pending: 'secondary',
      accepted: 'default',
      expired: 'destructive',
      cancelled: 'outline'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>
        {status}
      </Badge>
    );
  };

  const isExpired = (expiresAt: string) => {
    return new Date(expiresAt) < new Date();
  };

  const filteredInvitations = invitations.filter(invitation => {
    const matchesSearch = invitation.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (invitation.role_name?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false);
    const matchesRole = roleFilter === 'all' || invitation.role_id === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Invitations</h1>
          <p className="text-muted-foreground">
            Manage user invitations and onboarding workflow
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleExportInvitations}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => setShowBulkModal(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Bulk Invite
          </Button>
          <Button onClick={() => setShowSendModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Send Invitation
          </Button>
        </div>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Invitations</CardTitle>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_invitations}</div>
              <p className="text-xs text-muted-foreground">
                +{stats.invitations_last_30d} this month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {stats.pending_invitations}
              </div>
              <p className="text-xs text-muted-foreground">
                Awaiting response
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Accepted</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {stats.accepted_invitations}
              </div>
              <p className="text-xs text-muted-foreground">
                {stats.acceptance_rate.toFixed(1)}% acceptance rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Expired</CardTitle>
              <XCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {stats.expired_invitations}
              </div>
              <p className="text-xs text-muted-foreground">
                No longer valid
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="invitations">All Invitations</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Common invitation management tasks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Button
                  variant="outline"
                  className="h-20 flex-col space-y-2"
                  onClick={() => setShowSendModal(true)}
                >
                  <Plus className="h-6 w-6" />
                  <span>Send Single Invitation</span>
                </Button>
                
                <Button
                  variant="outline"
                  className="h-20 flex-col space-y-2"
                  onClick={() => setShowBulkModal(true)}
                >
                  <Users className="h-6 w-6" />
                  <span>Bulk Invite from CSV</span>
                </Button>

                <Button
                  variant="outline"
                  className="h-20 flex-col space-y-2"
                  onClick={handleExportInvitations}
                >
                  <Download className="h-6 w-6" />
                  <span>Export All Data</span>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Invitations</CardTitle>
              <CardDescription>
                Latest invitation activity
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {invitations.slice(0, 5).map((invitation) => (
                  <div key={invitation.invitation_id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(invitation.status)}
                      <div>
                        <p className="text-sm font-medium">{invitation.email}</p>
                        <p className="text-sm text-muted-foreground">
                          {invitation.role_name} • {new Date(invitation.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    {getStatusBadge(invitation.status)}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="invitations" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="Search invitations..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="max-w-sm"
                  />
                </div>
                
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="accepted">Accepted</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Roles</SelectItem>
                    {roles.map((role) => (
                      <SelectItem key={role.role_id} value={role.role_id}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Invitations Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>All Invitations</CardTitle>
                  <CardDescription>
                    {filteredInvitations.length} of {totalInvitations} invitations
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Expires</TableHead>
                        <TableHead>Invited By</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="w-[50px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredInvitations.map((invitation) => (
                        <TableRow key={invitation.invitation_id}>
                          <TableCell className="font-medium">
                            {invitation.email}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <Shield className="h-4 w-4 text-muted-foreground" />
                              <span>{invitation.role_name}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              {getStatusIcon(invitation.status)}
                              {getStatusBadge(invitation.status)}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className={`text-sm ${isExpired(invitation.expires_at) && invitation.status === 'pending' ? 'text-red-600' : ''}`}>
                              {new Date(invitation.expires_at).toLocaleDateString()}
                            </div>
                            {isExpired(invitation.expires_at) && invitation.status === 'pending' && (
                              <div className="text-xs text-red-500">Expired</div>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">{invitation.invited_by_name || invitation.invited_by}</div>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {new Date(invitation.created_at).toLocaleDateString()}
                            </div>
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="h-8 w-8 p-0">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() => {
                                    navigator.clipboard.writeText(
                                      `${window.location.origin}/invitation/${invitation.token}`
                                    );
                                    toast({
                                      title: "Copied",
                                      description: "Invitation link copied to clipboard"
                                    });
                                  }}
                                >
                                  <Copy className="mr-2 h-4 w-4" />
                                  Copy Link
                                </DropdownMenuItem>
                                
                                {invitation.status === 'pending' && !isExpired(invitation.expires_at) && (
                                  <DropdownMenuItem
                                    onClick={() => {
                                      setSelectedInvitation(invitation);
                                      setShowResendModal(true);
                                    }}
                                  >
                                    <RefreshCw className="mr-2 h-4 w-4" />
                                    Resend
                                  </DropdownMenuItem>
                                )}
                                
                                {invitation.status === 'pending' && (
                                  <DropdownMenuItem
                                    onClick={() => handleRevokeInvitation(invitation)}
                                    className="text-orange-600"
                                  >
                                    <XCircle className="mr-2 h-4 w-4" />
                                    Revoke
                                  </DropdownMenuItem>
                                )}
                                
                                {invitation.status !== 'accepted' && (
                                  <DropdownMenuSeparator />
                                )}
                                
                                {invitation.status !== 'accepted' && (
                                  <DropdownMenuItem
                                    onClick={() => {
                                      setSelectedInvitation(invitation);
                                      setShowDeleteModal(true);
                                    }}
                                    className="text-red-600"
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Delete
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  <div className="flex items-center justify-between space-x-2 py-4">
                    <div className="text-sm text-muted-foreground">
                      Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalInvitations)} of {totalInvitations} results
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        disabled={currentPage * itemsPerPage >= totalInvitations}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          {/* Analytics Content */}
          {stats && (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Acceptance Trends</CardTitle>
                  <CardDescription>
                    Invitation acceptance over time
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {stats.monthly_trend.map((month, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <span className="text-sm">{month.month}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-muted-foreground">
                            {month.accepted}/{month.count}
                          </span>
                          <Progress 
                            value={month.count > 0 ? (month.accepted / month.count) * 100 : 0}
                            className="w-20"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Popular Roles</CardTitle>
                  <CardDescription>
                    Most frequently invited roles
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(stats.top_invited_roles).map(([role, count]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className="text-sm">{role}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-muted-foreground">{count}</span>
                          <Progress 
                            value={(count / Math.max(...Object.values(stats.top_invited_roles))) * 100}
                            className="w-20"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Send Invitation Modal */}
      <Dialog open={showSendModal} onOpenChange={setShowSendModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Send User Invitation</DialogTitle>
            <DialogDescription>
              Invite a new user to join your organization
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={invitationForm.email}
                onChange={(e) => setInvitationForm(prev => ({ ...prev, email: e.target.value }))}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="role">Role</Label>
              <Select
                value={invitationForm.role_id}
                onValueChange={(value) => setInvitationForm(prev => ({ ...prev, role_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.role_id} value={role.role_id}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="expires">Expires in (days)</Label>
              <Select
                value={invitationForm.expires_in_days.toString()}
                onValueChange={(value) => setInvitationForm(prev => ({ ...prev, expires_in_days: parseInt(value) }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 days</SelectItem>
                  <SelectItem value="7">7 days</SelectItem>
                  <SelectItem value="14">14 days</SelectItem>
                  <SelectItem value="30">30 days</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="message">Message (Optional)</Label>
              <Input
                id="message"
                placeholder="Add a personal message..."
                value={invitationForm.message}
                onChange={(e) => setInvitationForm(prev => ({ ...prev, message: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSendModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendInvitation}>
              <Send className="mr-2 h-4 w-4" />
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Invitation Modal */}
      <Dialog open={showBulkModal} onOpenChange={setShowBulkModal}>
        <DialogContent className="sm:max-w-[525px]">
          <DialogHeader>
            <DialogTitle>Bulk User Invitations</DialogTitle>
            <DialogDescription>
              Invite multiple users at once using CSV format
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Email Addresses (one per line)</Label>
              <textarea
                className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="user1@example.com&#10;user2@example.com&#10;user3@example.com"
                value={bulkForm.csv_content}
                onChange={(e) => setBulkForm(prev => ({ ...prev, csv_content: e.target.value }))}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="bulk_role">Default Role</Label>
              <Select
                value={bulkForm.role_id}
                onValueChange={(value) => setBulkForm(prev => ({ ...prev, role_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.role_id} value={role.role_id}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="bulk_expires">Expires in (days)</Label>
              <Select
                value={bulkForm.expires_in_days.toString()}
                onValueChange={(value) => setBulkForm(prev => ({ ...prev, expires_in_days: parseInt(value) }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 days</SelectItem>
                  <SelectItem value="14">14 days</SelectItem>
                  <SelectItem value="30">30 days</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="bulk_message">Message (Optional)</Label>
              <Input
                id="bulk_message"
                placeholder="Message to include with all invitations..."
                value={bulkForm.message}
                onChange={(e) => setBulkForm(prev => ({ ...prev, message: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleBulkInvite}>
              <Users className="mr-2 h-4 w-4" />
              Send Bulk Invitations
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resend Invitation Modal */}
      <Dialog open={showResendModal} onOpenChange={setShowResendModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resend Invitation</DialogTitle>
            <DialogDescription>
              Are you sure you want to resend this invitation to {selectedInvitation?.email}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResendModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleResendInvitation}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Resend Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Invitation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Invitation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the invitation for {selectedInvitation?.email}? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteInvitation}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}