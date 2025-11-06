import React, { useState, useEffect } from 'react';
import { 
  Shield, ShieldCheck, Key, Users, Plus, Edit, Trash2, 
  Search, Filter, MoreVertical, Save, X, CheckCircle,
  AlertCircle, Lock, Unlock, Eye, Settings, Database,
  UserCheck, UserX, Activity, Clock, Globe, Award,
  ChevronDown, ChevronRight, Copy, Download, Upload
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
import api from '@/lib/api';

interface Permission {
  permission_id: string;
  name: string;
  description: string;
  resource: string;
  action: string;
  conditions?: Record<string, any>;
}

interface Role {
  role_id: string;
  name: string;
  description: string;
  level: number;
  is_system_role: boolean;
  created_at: string;
  permissions: Permission[];
  user_count?: number;
}

interface RoleAssignment {
  assignment_id: string;
  user_id: string;
  role_id: string;
  organization_id?: string;
  assigned_at: string;
  expires_at?: string;
  is_active: boolean;
  role_name?: string;
  user_name?: string;
  user_email?: string;
}

interface PermissionMatrix {
  resource: string;
  permissions: {
    [action: string]: {
      allowed: boolean;
      reason?: string;
    };
  };
}

export default function RBACManagement() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [roleAssignments, setRoleAssignments] = useState<RoleAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentTab, setCurrentTab] = useState('roles');
  
  // Modal states
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showPermissionModal, setShowPermissionModal] = useState(false);
  const [showAssignmentModal, setShowAssignmentModal] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  
  // Form states
  const [roleForm, setRoleForm] = useState({
    name: '',
    description: '',
    level: 0,
    permissions: [] as string[]
  });

  const [permissionForm, setPermissionForm] = useState({
    name: '',
    description: '',
    resource: '',
    action: ''
  });

  const [assignmentForm, setAssignmentForm] = useState({
    user_id: '',
    role_id: '',
    expires_at: ''
  });

  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchRoles(),
        fetchPermissions(),
        fetchRoleAssignments()
      ]);
    } catch (error) {
      console.error('Failed to fetch RBAC data:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load RBAC data"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const response = await api.get('/api/v1/users/roles/available');
      if (response.data) {
        setRoles(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await api.get('/api/v1/users/permissions');
      if (response.data) {
        setPermissions(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    }
  };

  const fetchRoleAssignments = async () => {
    try {
      const response = await api.get('/api/v1/users/role-assignments');
      if (response.data) {
        setRoleAssignments(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch role assignments:', error);
    }
  };

  const handleCreateRole = async () => {
    try {
      const response = await api.post('/api/v1/users/roles', roleForm);
      
      if (response.data) {
        setRoles(prev => [...prev, response.data]);
        setShowRoleModal(false);
        resetRoleForm();
        toast({
          variant: "success",
          title: "Success",
          description: "Role created successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to create role:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to create role"
      });
    }
  };

  const handleUpdateRole = async () => {
    if (!editingRole) return;
    
    try {
      const response = await api.put(`/api/v1/users/roles/${editingRole.role_id}`, roleForm);
      
      if (response.data) {
        setRoles(prev => prev.map(r => r.role_id === editingRole.role_id ? response.data : r));
        setShowRoleModal(false);
        setEditingRole(null);
        resetRoleForm();
        toast({
          variant: "success",
          title: "Success",
          description: "Role updated successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to update role:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to update role"
      });
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    try {
      await api.delete(`/api/v1/users/roles/${roleId}`);
      setRoles(prev => prev.filter(r => r.role_id !== roleId));
      toast({
        variant: "success",
        title: "Success",
        description: "Role deleted successfully"
      });
    } catch (error: any) {
      console.error('Failed to delete role:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete role"
      });
    }
  };

  const handleAssignRole = async () => {
    try {
      const response = await api.post(`/api/v1/users/${assignmentForm.user_id}/roles/${assignmentForm.role_id}`, {
        expires_at: assignmentForm.expires_at || null
      });
      
      if (response.data) {
        await fetchRoleAssignments(); // Refresh assignments
        setShowAssignmentModal(false);
        resetAssignmentForm();
        toast({
          variant: "success",
          title: "Success",
          description: "Role assigned successfully"
        });
      }
    } catch (error: any) {
      console.error('Failed to assign role:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to assign role"
      });
    }
  };

  const handleRevokeRole = async (userId: string, roleId: string, organizationId?: string) => {
    try {
      await api.delete(`/api/v1/users/${userId}/roles/${roleId}`, {
        params: { organization_id: organizationId }
      });
      
      setRoleAssignments(prev => prev.filter(a => 
        !(a.user_id === userId && a.role_id === roleId && a.organization_id === organizationId)
      ));
      
      toast({
        variant: "success",
        title: "Success",
        description: "Role revoked successfully"
      });
    } catch (error: any) {
      console.error('Failed to revoke role:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.response?.data?.detail || "Failed to revoke role"
      });
    }
  };

  const openEditRoleModal = (role: Role) => {
    setEditingRole(role);
    setRoleForm({
      name: role.name,
      description: role.description || '',
      level: role.level,
      permissions: role.permissions?.map(p => p.name) || []
    });
    setShowRoleModal(true);
  };

  const resetRoleForm = () => {
    setRoleForm({
      name: '',
      description: '',
      level: 0,
      permissions: []
    });
    setEditingRole(null);
  };

  const resetAssignmentForm = () => {
    setAssignmentForm({
      user_id: '',
      role_id: '',
      expires_at: ''
    });
  };

  const togglePermission = (permissionName: string) => {
    setRoleForm(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permissionName)
        ? prev.permissions.filter(p => p !== permissionName)
        : [...prev.permissions, permissionName]
    }));
  };

  const getResourcePermissions = (resource: string) => {
    return permissions.filter(p => p.resource === resource);
  };

  const getResources = () => {
    const resources = [...new Set(permissions.map(p => p.resource))];
    return resources.sort();
  };

  const filteredRoles = roles.filter(role =>
    role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredAssignments = roleAssignments.filter(assignment =>
    assignment.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    assignment.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    assignment.role_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading RBAC management...</p>
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
                RBAC Management
              </h1>
              <p className="text-sm text-muted-foreground">
                Role-based access control and permission management
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button 
                variant="pastel-primary" 
                onClick={() => setShowRoleModal(true)}
                className="animate-slide-up"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Role
              </Button>
              <Button 
                variant="pastel-secondary"
                onClick={() => setShowPermissionModal(true)}
              >
                <Key className="h-4 w-4 mr-2" />
                Manage Permissions
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
              <CardTitle className="text-sm font-medium">Total Roles</CardTitle>
              <Shield className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{roles.length}</div>
              <p className="text-xs text-muted-foreground">
                {roles.filter(r => !r.is_system_role).length} custom roles
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Permissions</CardTitle>
              <Key className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{permissions.length}</div>
              <p className="text-xs text-muted-foreground">
                System permissions defined
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Assignments</CardTitle>
              <Users className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{roleAssignments.filter(a => a.is_active).length}</div>
              <p className="text-xs text-muted-foreground">
                Role assignments active
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Resource Types</CardTitle>
              <Database className="h-4 w-4 text-info-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{getResources().length}</div>
              <p className="text-xs text-muted-foreground">
                Protected resources
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="roles">Roles ({roles.length})</TabsTrigger>
            <TabsTrigger value="assignments">Assignments ({roleAssignments.filter(a => a.is_active).length})</TabsTrigger>
            <TabsTrigger value="matrix">Permission Matrix</TabsTrigger>
          </TabsList>

          <TabsContent value="roles" className="space-y-6">
            {/* Search and Filters */}
            <Card>
              <CardContent className="p-6">
                <div className="flex flex-col sm:flex-row gap-4 items-center">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                    <Input
                      placeholder="Search roles..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Roles Table */}
            <Card>
              <CardHeader>
                <CardTitle>Role Management</CardTitle>
                <CardDescription>
                  Define roles with specific permissions for different access levels
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Role Name</TableHead>
                      <TableHead>Level</TableHead>
                      <TableHead>Permissions</TableHead>
                      <TableHead>Users</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRoles.map((role) => (
                      <TableRow key={role.role_id} className="animate-fade-in">
                        <TableCell>
                          <div>
                            <div className="font-medium">{role.name}</div>
                            <div className="text-sm text-muted-foreground">
                              {role.description}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            Level {role.level}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Key className="h-3 w-3 text-muted-foreground" />
                            <span className="text-sm">{role.permissions?.length || 0}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Users className="h-3 w-3 text-muted-foreground" />
                            <span className="text-sm">
                              {roleAssignments.filter(a => a.role_id === role.role_id && a.is_active).length}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={role.is_system_role ? "secondary" : "default"}>
                            {role.is_system_role ? "System" : "Custom"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEditRoleModal(role)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit Role
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => setSelectedRole(role)}>
                                <Shield className="h-4 w-4 mr-2" />
                                View Permissions
                              </DropdownMenuItem>
                              {!role.is_system_role && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem 
                                    onClick={() => handleDeleteRole(role.role_id)}
                                    className="text-red-600"
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete Role
                                  </DropdownMenuItem>
                                </>
                              )}
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

          <TabsContent value="assignments" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Role Assignments</CardTitle>
                <CardDescription>
                  Manage which users have which roles
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Organization</TableHead>
                      <TableHead>Assigned</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAssignments.map((assignment) => (
                      <TableRow key={assignment.assignment_id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{assignment.user_name || 'Unknown User'}</div>
                            <div className="text-sm text-muted-foreground">
                              {assignment.user_email}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{assignment.role_name}</Badge>
                        </TableCell>
                        <TableCell>
                          {assignment.organization_id ? (
                            <Badge variant="secondary">Org #{assignment.organization_id.slice(-8)}</Badge>
                          ) : (
                            <Badge variant="default">Global</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {new Date(assignment.assigned_at).toLocaleDateString()}
                          </div>
                        </TableCell>
                        <TableCell>
                          {assignment.expires_at ? (
                            <div className="text-sm text-muted-foreground">
                              {new Date(assignment.expires_at).toLocaleDateString()}
                            </div>
                          ) : (
                            <span className="text-sm text-muted-foreground">Never</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={assignment.is_active ? "success" : "secondary"}>
                            {assignment.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {assignment.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRevokeRole(assignment.user_id, assignment.role_id, assignment.organization_id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <UserX className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="matrix" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Permission Matrix</CardTitle>
                <CardDescription>
                  Overview of all permissions across resources
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {getResources().map(resource => (
                    <div key={resource} className="border rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-4 capitalize">{resource}</h3>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {getResourcePermissions(resource).map(permission => (
                          <div key={permission.permission_id} className="flex items-center justify-between p-2 border rounded">
                            <div>
                              <div className="text-sm font-medium">{permission.action}</div>
                              <div className="text-xs text-muted-foreground">
                                {permission.description}
                              </div>
                            </div>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Create/Edit Role Modal */}
        <Dialog open={showRoleModal} onOpenChange={setShowRoleModal}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>
                {editingRole ? 'Edit Role' : 'Create New Role'}
              </DialogTitle>
              <DialogDescription>
                {editingRole ? 'Update role permissions and settings.' : 'Create a new role with specific permissions.'}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Role Name</Label>
                  <Input
                    id="name"
                    value={roleForm.name}
                    onChange={(e) => setRoleForm({...roleForm, name: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="level">Hierarchy Level</Label>
                  <Input
                    id="level"
                    type="number"
                    min="0"
                    max="10"
                    value={roleForm.level}
                    onChange={(e) => setRoleForm({...roleForm, level: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={roleForm.description}
                  onChange={(e) => setRoleForm({...roleForm, description: e.target.value})}
                />
              </div>
              
              <div>
                <Label>Permissions</Label>
                <div className="mt-2 max-h-64 overflow-y-auto border rounded p-3 space-y-2">
                  {getResources().map(resource => (
                    <div key={resource} className="border-b pb-2 last:border-b-0">
                      <h4 className="font-medium text-sm mb-2 capitalize">{resource}</h4>
                      <div className="grid grid-cols-2 gap-1">
                        {getResourcePermissions(resource).map(permission => (
                          <div key={permission.permission_id} className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              id={permission.permission_id}
                              checked={roleForm.permissions.includes(permission.name)}
                              onChange={() => togglePermission(permission.name)}
                              className="rounded"
                            />
                            <label 
                              htmlFor={permission.permission_id}
                              className="text-xs cursor-pointer"
                            >
                              {permission.action}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRoleModal(false)}>
                Cancel
              </Button>
              <Button variant="pastel-primary" onClick={editingRole ? handleUpdateRole : handleCreateRole}>
                {editingRole ? 'Update Role' : 'Create Role'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Permission Management Modal */}
        <Dialog open={showPermissionModal} onOpenChange={setShowPermissionModal}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Create Permission</DialogTitle>
              <DialogDescription>
                Add a new permission to the system.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div>
                <Label htmlFor="permission_name">Permission Name</Label>
                <Input
                  id="permission_name"
                  value={permissionForm.name}
                  onChange={(e) => setPermissionForm({...permissionForm, name: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="permission_description">Description</Label>
                <Input
                  id="permission_description"
                  value={permissionForm.description}
                  onChange={(e) => setPermissionForm({...permissionForm, description: e.target.value})}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="resource">Resource</Label>
                  <Input
                    id="resource"
                    value={permissionForm.resource}
                    onChange={(e) => setPermissionForm({...permissionForm, resource: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="action">Action</Label>
                  <Input
                    id="action"
                    value={permissionForm.action}
                    onChange={(e) => setPermissionForm({...permissionForm, action: e.target.value})}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowPermissionModal(false)}>
                Cancel
              </Button>
              <Button variant="pastel-primary">
                Create Permission
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Role Permissions Detail Modal */}
        {selectedRole && (
          <Dialog open={!!selectedRole} onOpenChange={() => setSelectedRole(null)}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>{selectedRole.name} Permissions</DialogTitle>
                <DialogDescription>
                  View all permissions assigned to this role
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  {selectedRole.permissions?.map(permission => (
                    <div key={permission.permission_id} className="flex items-center justify-between p-2 border rounded">
                      <div>
                        <div className="text-sm font-medium">{permission.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {permission.description}
                        </div>
                      </div>
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    </div>
                  )) || (
                    <p className="text-sm text-muted-foreground">No permissions assigned</p>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setSelectedRole(null)}>
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