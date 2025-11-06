import React, { useState, useEffect } from 'react';
import { 
  Building, Plus, Edit, Trash2, Search, Filter, MoreVertical, 
  Users, Settings, Globe, CreditCard, Calendar, TrendingUp,
  AlertCircle, CheckCircle, XCircle, BarChart3, PieChart,
  Activity, Clock, MapPin, Mail, Phone, FileText, Shield,
  Eye, Download, Upload, RefreshCw, Bell, Lock
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

interface Organization {
  organization_id: string;
  name: string;
  description?: string;
  domain?: string;
  subscription_tier: string;
  subscription_status: string;
  max_users: number;
  max_documents: number;
  max_storage_gb: number;
  settings: Record<string, any>;
  features: string[];
  billing_email?: string;
  billing_address?: string;
  tax_id?: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

interface OrganizationStats {
  organization_id: string;
  total_users: number;
  active_users: number;
  inactive_users: number;
  recent_activities_30d: number;
  role_distribution: Record<string, number>;
  subscription_tier: string;
  subscription_status: string;
  max_users: number;
  usage_percentage: number;
  features_enabled: number;
  created_at: string;
}

export default function OrganizationManagement() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [orgStats, setOrgStats] = useState<Record<string, OrganizationStats>>({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [currentTab, setCurrentTab] = useState('overview');
  
  // Modal states
  const [showOrgModal, setShowOrgModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);
  
  // Form states
  const [orgForm, setOrgForm] = useState({
    name: '',
    description: '',
    domain: '',
    subscription_tier: 'basic',
    max_users: 10,
    max_documents: 1000,
    max_storage_gb: 10,
    billing_email: '',
    billing_address: '',
    tax_id: ''
  });

  const { toast } = useToast();

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (organizations.length > 0) {
      fetchOrganizationStats();
    }
  }, [organizations]);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/users/organizations');
      if (response.data) {
        setOrganizations(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch organizations:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load organizations"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchOrganizationStats = async () => {
    try {
      const statsPromises = organizations.map(org =>
        api.get(`/api/v1/users/organizations/${org.organization_id}/statistics`)
          .then(response => ({ orgId: org.organization_id, stats: response.data }))
          .catch(() => ({ orgId: org.organization_id, stats: null }))
      );
      
      const results = await Promise.all(statsPromises);
      const statsMap = results.reduce((acc, { orgId, stats }) => {
        if (stats) acc[orgId] = stats;
        return acc;
      }, {} as Record<string, OrganizationStats>);
      
      setOrgStats(statsMap);
    } catch (error) {
      console.error('Failed to fetch organization stats:', error);
    }
  };

  const handleCreateOrganization = async () => {
    try {
      const response = await api.post('/api/v1/users/organizations', orgForm);
      
      if (response.data) {
        setOrganizations(prev => [...prev, response.data]);
        setShowOrgModal(false);
        resetForm();
        toast({
          variant: "success",
          title: "Success",
          description: "Organization created successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to create organization:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to create organization"
      });
    }
  };

  const handleUpdateOrganization = async () => {
    if (!editingOrg) return;
    
    try {
      const response = await api.put(`/api/v1/users/organizations/${editingOrg.organization_id}`, orgForm);
      
      if (response.data) {
        setOrganizations(prev => prev.map(o => 
          o.organization_id === editingOrg.organization_id ? response.data : o
        ));
        setShowOrgModal(false);
        setEditingOrg(null);
        resetForm();
        toast({
          variant: "success",
          title: "Success",
          description: "Organization updated successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to update organization:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to update organization"
      });
    }
  };

  const handleDeleteOrganization = async (orgId: string) => {
    try {
      await api.delete(`/api/v1/users/organizations/${orgId}`);
      setOrganizations(prev => prev.filter(o => o.organization_id !== orgId));
      setOrgStats(prev => {
        const newStats = { ...prev };
        delete newStats[orgId];
        return newStats;
      });
      toast({
        variant: "success",
        title: "Success",
        description: "Organization deleted successfully"
      });
    } catch (error: any) {
      console.error('Failed to delete organization:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete organization"
      });
    }
  };

  const openEditModal = (org: Organization) => {
    setEditingOrg(org);
    setOrgForm({
      name: org.name,
      description: org.description || '',
      domain: org.domain || '',
      subscription_tier: org.subscription_tier,
      max_users: org.max_users,
      max_documents: org.max_documents,
      max_storage_gb: org.max_storage_gb,
      billing_email: org.billing_email || '',
      billing_address: org.billing_address || '',
      tax_id: org.tax_id || ''
    });
    setShowOrgModal(true);
  };

  const resetForm = () => {
    setOrgForm({
      name: '',
      description: '',
      domain: '',
      subscription_tier: 'basic',
      max_users: 10,
      max_documents: 1000,
      max_storage_gb: 10,
      billing_email: '',
      billing_address: '',
      tax_id: ''
    });
    setEditingOrg(null);
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'success',
      suspended: 'destructive',
      cancelled: 'secondary',
      deleted: 'destructive'
    };
    
    const icons = {
      active: <CheckCircle className="h-3 w-3" />,
      suspended: <XCircle className="h-3 w-3" />,
      cancelled: <AlertCircle className="h-3 w-3" />,
      deleted: <XCircle className="h-3 w-3" />
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

  const getTierBadge = (tier: string) => {
    const variants = {
      basic: 'secondary',
      professional: 'default',
      enterprise: 'destructive'
    };
    
    return (
      <Badge variant={variants[tier as keyof typeof variants] as any}>
        {tier.charAt(0).toUpperCase() + tier.slice(1)}
      </Badge>
    );
  };

  const filteredOrgs = organizations.filter(org => {
    const matchesSearch = org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         org.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || org.status === statusFilter;
    const matchesTier = tierFilter === 'all' || org.subscription_tier === tierFilter;
    return matchesSearch && matchesStatus && matchesTier;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading organization management...</p>
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
                Organization Management
              </h1>
              <p className="text-sm text-muted-foreground">
                Manage multi-tenant organizations and their settings
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button 
                variant="pastel-primary" 
                onClick={() => setShowOrgModal(true)}
                className="animate-slide-up"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Organization
              </Button>
              <Button variant="outline" onClick={() => fetchOrganizations()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Organizations</CardTitle>
              <Building className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{organizations.length}</div>
              <p className="text-xs text-muted-foreground">
                {organizations.filter(o => o.status === 'active').length} active
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {Object.values(orgStats).reduce((sum, stats) => sum + stats.total_users, 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                Across all organizations
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Enterprise Orgs</CardTitle>
              <Shield className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {organizations.filter(o => o.subscription_tier === 'enterprise').length}
              </div>
              <p className="text-xs text-muted-foreground">
                Premium tier organizations
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Licenses</CardTitle>
              <CreditCard className="h-4 w-4 text-info-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {organizations.filter(o => o.subscription_status === 'active').length}
              </div>
              <p className="text-xs text-muted-foreground">
                Current active subscriptions
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Filters and Search */}
        <Card className="mb-8">
          <CardContent className="p-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              <div className="flex flex-col sm:flex-row gap-4 flex-1">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <Input
                    placeholder="Search organizations..."
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
                    <SelectItem value="suspended">Suspended</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
                
                <Select value={tierFilter} onValueChange={setTierFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Filter by tier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Tiers</SelectItem>
                    <SelectItem value="basic">Basic</SelectItem>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="enterprise">Enterprise</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Organizations Table */}
        <Card>
          <CardHeader>
            <CardTitle>Organizations ({filteredOrgs.length})</CardTitle>
            <CardDescription>
              Manage organization settings, users, and subscriptions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Organization</TableHead>
                  <TableHead>Subscription</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOrgs.map((org) => {
                  const stats = orgStats[org.organization_id];
                  return (
                    <TableRow key={org.organization_id} className="animate-fade-in">
                      <TableCell>
                        <div>
                          <div className="font-medium">{org.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {org.description || 'No description'}
                          </div>
                          {org.domain && (
                            <div className="text-xs text-muted-foreground flex items-center gap-1">
                              <Globe className="h-3 w-3" />
                              {org.domain}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {getTierBadge(org.subscription_tier)}
                          <div className="text-xs text-muted-foreground">
                            {org.subscription_status}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="text-sm">
                            {stats?.total_users || 0} / {org.max_users}
                          </div>
                          {stats && (
                            <Progress 
                              value={Math.min((stats.total_users / org.max_users) * 100, 100)} 
                              className="h-2"
                            />
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="text-sm">
                            {stats?.recent_activities_30d || 0} activities
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Last 30 days
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(org.status)}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {new Date(org.created_at).toLocaleDateString()}
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
                            <DropdownMenuItem onClick={() => setSelectedOrg(org)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => openEditModal(org)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit Organization
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Users className="h-4 w-4 mr-2" />
                              Manage Users
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Settings className="h-4 w-4 mr-2" />
                              Settings
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>
                              <Download className="h-4 w-4 mr-2" />
                              Export Data
                            </DropdownMenuItem>
                            {org.status !== 'deleted' && (
                              <DropdownMenuItem 
                                onClick={() => handleDeleteOrganization(org.organization_id)}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Create/Edit Organization Modal */}
        <Dialog open={showOrgModal} onOpenChange={setShowOrgModal}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingOrg ? 'Edit Organization' : 'Create New Organization'}
              </DialogTitle>
              <DialogDescription>
                {editingOrg ? 'Update organization details and settings.' : 'Create a new organization with specific limits and features.'}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Organization Name</Label>
                  <Input
                    id="name"
                    value={orgForm.name}
                    onChange={(e) => setOrgForm({...orgForm, name: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="domain">Domain</Label>
                  <Input
                    id="domain"
                    value={orgForm.domain}
                    onChange={(e) => setOrgForm({...orgForm, domain: e.target.value})}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={orgForm.description}
                  onChange={(e) => setOrgForm({...orgForm, description: e.target.value})}
                />
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="subscription_tier">Subscription Tier</Label>
                  <Select 
                    value={orgForm.subscription_tier} 
                    onValueChange={(value) => setOrgForm({...orgForm, subscription_tier: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic">Basic</SelectItem>
                      <SelectItem value="professional">Professional</SelectItem>
                      <SelectItem value="enterprise">Enterprise</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="max_users">Max Users</Label>
                  <Input
                    id="max_users"
                    type="number"
                    min="1"
                    value={orgForm.max_users}
                    onChange={(e) => setOrgForm({...orgForm, max_users: parseInt(e.target.value)})}
                  />
                </div>
                <div>
                  <Label htmlFor="max_storage_gb">Storage (GB)</Label>
                  <Input
                    id="max_storage_gb"
                    type="number"
                    min="1"
                    value={orgForm.max_storage_gb}
                    onChange={(e) => setOrgForm({...orgForm, max_storage_gb: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="billing_email">Billing Email</Label>
                  <Input
                    id="billing_email"
                    type="email"
                    value={orgForm.billing_email}
                    onChange={(e) => setOrgForm({...orgForm, billing_email: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="tax_id">Tax ID</Label>
                  <Input
                    id="tax_id"
                    value={orgForm.tax_id}
                    onChange={(e) => setOrgForm({...orgForm, tax_id: e.target.value})}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="billing_address">Billing Address</Label>
                <Input
                  id="billing_address"
                  value={orgForm.billing_address}
                  onChange={(e) => setOrgForm({...orgForm, billing_address: e.target.value})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowOrgModal(false)}>
                Cancel
              </Button>
              <Button variant="pastel-primary" onClick={editingOrg ? handleUpdateOrganization : handleCreateOrganization}>
                {editingOrg ? 'Update Organization' : 'Create Organization'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Organization Details Modal */}
        {selectedOrg && (
          <Dialog open={!!selectedOrg} onOpenChange={() => setSelectedOrg(null)}>
            <DialogContent className="sm:max-w-[800px]">
              <DialogHeader>
                <DialogTitle>{selectedOrg.name}</DialogTitle>
                <DialogDescription>
                  Organization details and statistics
                </DialogDescription>
              </DialogHeader>
              <Tabs value={currentTab} onValueChange={setCurrentTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="users">Users</TabsTrigger>
                  <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>
                
                <TabsContent value="overview" className="space-y-4">
                  {orgStats[selectedOrg.organization_id] && (
                    <div className="grid grid-cols-2 gap-4">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">User Statistics</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Total Users</span>
                              <span className="font-bold">{orgStats[selectedOrg.organization_id].total_users}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Active Users</span>
                              <span className="font-bold text-green-600">{orgStats[selectedOrg.organization_id].active_users}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Inactive Users</span>
                              <span className="font-bold text-red-600">{orgStats[selectedOrg.organization_id].inactive_users}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Activity</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Recent Activities</span>
                              <span className="font-bold">{orgStats[selectedOrg.organization_id].recent_activities_30d}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Features Enabled</span>
                              <span className="font-bold">{orgStats[selectedOrg.organization_id].features_enabled}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Usage Percentage</span>
                              <span className="font-bold">{orgStats[selectedOrg.organization_id].usage_percentage.toFixed(1)}%</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </TabsContent>
                
                <TabsContent value="users" className="space-y-4">
                  <div className="text-center py-8 text-muted-foreground">
                    User management would be shown here
                  </div>
                </TabsContent>
                
                <TabsContent value="settings" className="space-y-4">
                  <div className="grid gap-4">
                    <div>
                      <Label>Organization Details</Label>
                      <div className="mt-2 space-y-2">
                        <div className="flex justify-between">
                          <span>Name</span>
                          <span>{selectedOrg.name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Domain</span>
                          <span>{selectedOrg.domain || 'Not set'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Tier</span>
                          <span>{selectedOrg.subscription_tier}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Status</span>
                          <span>{selectedOrg.status}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
              <DialogFooter>
                <Button variant="outline" onClick={() => setSelectedOrg(null)}>
                  Close
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </main>
    </div>
  );
}