"""
Credit Transfer Component

Interface for transferring credits between users and managing transfer permissions.
"""

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Avatar, AvatarFallback, AvatarInitials } from '@/components/ui/avatar';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  ArrowRightLeft,
  Send,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  User,
  Building,
  Shield,
  Settings,
  Plus,
  Search,
  Filter,
  Download,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  Users,
  CreditCard,
  TrendingUp,
  TrendingDown,
  Calendar,
  DollarSign
} from 'lucide-react';

interface CreditTransferProps {
  userId: number;
  organizationId?: number;
}

interface TransferRequest {
  id: number;
  fromUserId: number;
  fromUserName: string;
  toUserId: number;
  toUserName: string;
  amount: number;
  status: 'pending' | 'approved' | 'rejected' | 'completed' | 'failed';
  reason: string;
  createdAt: string;
  approvedAt?: string;
  approvalNotes?: string;
}

interface Permission {
  id: number;
  fromUserId: number;
  fromUserName: string;
  toUserId: number;
  toUserName: string;
  permissionType: 'allow_transfer' | 'require_approval' | 'rate_limit' | 'conditional_transfer';
  maxAmount?: number;
  maxFrequency?: number;
  timeLimitHours?: number;
  isActive: boolean;
  createdAt: string;
}

interface TransferStats {
  totalTransferred: number;
  totalReceived: number;
  pendingApprovals: number;
  successRate: number;
  averageTransferSize: number;
  mostActiveRecipient: string;
}

const CreditTransfer: React.FC<CreditTransferProps> = ({ userId, organizationId }) => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('transfer');
  const [showNewTransfer, setShowNewTransfer] = useState(false);
  const [showNewPermission, setShowNewPermission] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Transfer form state
  const [transferForm, setTransferForm] = useState({
    toUserId: '',
    amount: '',
    reason: '',
    requiresApproval: false,
    urgent: false
  });
  
  // Permission form state
  const [permissionForm, setPermissionForm] = useState({
    toUserId: '',
    permissionType: 'allow_transfer' as const,
    maxAmount: '',
    maxFrequency: '',
    timeLimitHours: '',
    conditions: ''
  });

  const [transfers, setTransfers] = useState<TransferRequest[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [stats, setStats] = useState<TransferStats | null>(null);
  const [transferHistory, setTransferHistory] = useState<TransferRequest[]>([]);

  useEffect(() => {
    loadTransferData();
  }, [userId, organizationId]);

  const loadTransferData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadTransfers(),
        loadPermissions(),
        loadStats(),
        loadTransferHistory()
      ]);
    } catch (error) {
      console.error('Error loading transfer data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTransfers = async () => {
    // Simulate API call - replace with actual API
    const mockTransfers: TransferRequest[] = [
      {
        id: 1,
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: 123,
        toUserName: 'John Doe',
        amount: 1000,
        status: 'pending',
        reason: 'Team budget allocation',
        createdAt: '2024-01-15T10:30:00Z'
      },
      {
        id: 2,
        fromUserId: 456,
        fromUserName: 'Jane Smith',
        toUserId: userId,
        toUserName: 'You',
        amount: 500,
        status: 'approved',
        reason: 'Credit adjustment',
        createdAt: '2024-01-14T15:20:00Z',
        approvedAt: '2024-01-14T16:45:00Z'
      }
    ];
    
    setTransfers(mockTransfers);
  };

  const loadPermissions = async () => {
    // Simulate API call - replace with actual API
    const mockPermissions: Permission[] = [
      {
        id: 1,
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: 123,
        toUserName: 'John Doe',
        permissionType: 'allow_transfer',
        maxAmount: 2000,
        maxFrequency: 10,
        isActive: true,
        createdAt: '2024-01-10T09:00:00Z'
      },
      {
        id: 2,
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: 789,
        toUserName: 'Bob Wilson',
        permissionType: 'require_approval',
        maxAmount: 1000,
        isActive: true,
        createdAt: '2024-01-08T14:30:00Z'
      }
    ];
    
    setPermissions(mockPermissions);
  };

  const loadStats = async () => {
    // Simulate API call - replace with actual API
    const mockStats: TransferStats = {
      totalTransferred: 15000,
      totalReceived: 8500,
      pendingApprovals: 3,
      successRate: 94.5,
      averageTransferSize: 1250,
      mostActiveRecipient: 'John Doe'
    };
    
    setStats(mockStats);
  };

  const loadTransferHistory = async () => {
    // Simulate API call - replace with actual API
    const mockHistory: TransferRequest[] = [
      {
        id: 3,
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: 123,
        toUserName: 'John Doe',
        amount: 2000,
        status: 'completed',
        reason: 'Monthly allocation',
        createdAt: '2024-01-10T08:00:00Z',
        approvedAt: '2024-01-10T08:15:00Z'
      },
      {
        id: 4,
        fromUserId: 456,
        fromUserName: 'Jane Smith',
        toUserId: userId,
        toUserName: 'You',
        amount: 750,
        status: 'completed',
        reason: 'Emergency transfer',
        createdAt: '2024-01-09T12:30:00Z',
        approvedAt: '2024-01-09T12:45:00Z'
      }
    ];
    
    setTransferHistory(mockHistory);
  };

  const handleTransferSubmit = async () => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const newTransfer: TransferRequest = {
        id: Date.now(),
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: parseInt(transferForm.toUserId),
        toUserName: 'Selected User',
        amount: parseFloat(transferForm.amount),
        status: transferForm.requiresApproval ? 'pending' : 'approved',
        reason: transferForm.reason,
        createdAt: new Date().toISOString()
      };
      
      setTransfers([newTransfer, ...transfers]);
      setTransferForm({
        toUserId: '',
        amount: '',
        reason: '',
        requiresApproval: false,
        urgent: false
      });
      setShowNewTransfer(false);
    } catch (error) {
      console.error('Error creating transfer:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionSubmit = async () => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const newPermission: Permission = {
        id: Date.now(),
        fromUserId: userId,
        fromUserName: 'You',
        toUserId: parseInt(permissionForm.toUserId),
        toUserName: 'Selected User',
        permissionType: permissionForm.permissionType,
        maxAmount: permissionForm.maxAmount ? parseFloat(permissionForm.maxAmount) : undefined,
        maxFrequency: permissionForm.maxFrequency ? parseInt(permissionForm.maxFrequency) : undefined,
        timeLimitHours: permissionForm.timeLimitHours ? parseInt(permissionForm.timeLimitHours) : undefined,
        isActive: true,
        createdAt: new Date().toISOString()
      };
      
      setPermissions([newPermission, ...permissions]);
      setPermissionForm({
        toUserId: '',
        permissionType: 'allow_transfer',
        maxAmount: '',
        maxFrequency: '',
        timeLimitHours: '',
        conditions: ''
      });
      setShowNewPermission(false);
    } catch (error) {
      console.error('Error creating permission:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (transferId: number, approved: boolean, notes?: string) => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setTransfers(transfers.map(transfer => 
        transfer.id === transferId 
          ? { 
              ...transfer, 
              status: approved ? 'approved' as const : 'rejected' as const,
              approvedAt: new Date().toISOString(),
              approvalNotes: notes 
            }
          : transfer
      ));
    } catch (error) {
      console.error('Error processing approval:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock className="h-4 w-4" />;
      case 'approved': return <CheckCircle className="h-4 w-4" />;
      case 'rejected': return <XCircle className="h-4 w-4" />;
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'failed': return <XCircle className="h-4 w-4" />;
      default: return <AlertCircle className="h-4 w-4" />;
    }
  };

  const renderTransferTab = () => (
    <div className="space-y-6">
      {/* Transfer Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Transferred</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalTransferred.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                Credits sent this month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Received</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalReceived.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                Credits received this month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.pendingApprovals}</div>
              <p className="text-xs text-muted-foreground">
                Awaiting your approval
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.successRate}%</div>
              <p className="text-xs text-muted-foreground">
                Successful transfers
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* New Transfer Button */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Transfer Requests</h3>
        <Button onClick={() => setShowNewTransfer(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Transfer
        </Button>
      </div>

      {/* Transfer Requests */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Transfers</CardTitle>
          <CardDescription>
            Transfers requiring your approval or action
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transfers.filter(t => ['pending', 'approved'].includes(t.status)).length > 0 ? (
            <div className="space-y-4">
              {transfers
                .filter(t => ['pending', 'approved'].includes(t.status))
                .map(transfer => (
                  <div key={transfer.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Avatar className="h-8 w-8">
                            <AvatarFallback>
                              {transfer.fromUserId === userId ? 'You' : transfer.fromUserName.charAt(0)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">
                              {transfer.fromUserId === userId ? 'You' : transfer.fromUserName} → 
                              {transfer.toUserId === userId ? 'You' : transfer.toUserName}
                            </p>
                            <p className="text-sm text-muted-foreground">{transfer.reason}</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                          <span className="flex items-center">
                            <DollarSign className="h-3 w-3 mr-1" />
                            {transfer.amount} credits
                          </span>
                          <span className="flex items-center">
                            <Calendar className="h-3 w-3 mr-1" />
                            {new Date(transfer.createdAt).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge className={getStatusColor(transfer.status)}>
                          {getStatusIcon(transfer.status)}
                          <span className="ml-1 capitalize">{transfer.status}</span>
                        </Badge>
                        {transfer.status === 'pending' && transfer.toUserId === userId && (
                          <div className="flex space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleApproval(transfer.id, true)}
                              disabled={loading}
                            >
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleApproval(transfer.id, false)}
                              disabled={loading}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No pending transfers
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderPermissionsTab = () => (
    <div className="space-y-6">
      {/* Permissions Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Transfer Permissions</h3>
        <Button onClick={() => setShowNewPermission(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Permission
        </Button>
      </div>

      {/* Active Permissions */}
      <Card>
        <CardHeader>
          <CardTitle>Active Permissions</CardTitle>
          <CardDescription>
            Manage who can transfer credits to and from your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          {permissions.length > 0 ? (
            <div className="space-y-4">
              {permissions.map(permission => (
                <div key={permission.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            {permission.toUserName.charAt(0)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">{permission.toUserName}</p>
                          <p className="text-sm text-muted-foreground capitalize">
                            {permission.permissionType.replace('_', ' ')}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        {permission.maxAmount && (
                          <span>Max: {permission.maxAmount} credits</span>
                        )}
                        {permission.maxFrequency && (
                          <span>Max: {permission.maxFrequency}/day</span>
                        )}
                        {permission.timeLimitHours && (
                          <span>Expires: {permission.timeLimitHours}h</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={permission.isActive ? 'secondary' : 'outline'}>
                        {permission.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                      <Button size="sm" variant="outline">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No permissions configured
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderHistoryTab = () => (
    <div className="space-y-6">
      {/* History Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Transfer History</h3>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      {/* History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Transfers</CardTitle>
          <CardDescription>
            Complete history of all credit transfers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transferHistory.map(transfer => (
                <TableRow key={transfer.id}>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Avatar className="h-6 w-6">
                        <AvatarFallback className="text-xs">
                          {transfer.fromUserName.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <span>{transfer.fromUserId === userId ? 'You' : transfer.fromUserName}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Avatar className="h-6 w-6">
                        <AvatarFallback className="text-xs">
                          {transfer.toUserName.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <span>{transfer.toUserId === userId ? 'You' : transfer.toUserName}</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">
                    {transfer.amount} credits
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(transfer.status)}>
                      {getStatusIcon(transfer.status)}
                      <span className="ml-1 capitalize">{transfer.status}</span>
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(transfer.createdAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );

  const renderAnalyticsTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Transfer Analytics</CardTitle>
          <CardDescription>
            Insights into your transfer patterns and efficiency
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold">{stats?.averageTransferSize || 0}</div>
              <p className="text-sm text-muted-foreground">Average Transfer Size</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{stats?.mostActiveRecipient || 'N/A'}</div>
              <p className="text-sm text-muted-foreground">Most Active Recipient</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{stats?.successRate || 0}%</div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Credit Transfer</h1>
          <p className="text-muted-foreground">
            Transfer credits and manage permissions
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadTransferData}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="transfer">
            <ArrowRightLeft className="h-4 w-4 mr-2" />
            Transfer
          </TabsTrigger>
          <TabsTrigger value="permissions">
            <Shield className="h-4 w-4 mr-2" />
            Permissions
          </TabsTrigger>
          <TabsTrigger value="history">
            <Clock className="h-4 w-4 mr-2" />
            History
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <TrendingUp className="h-4 w-4 mr-2" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="transfer">
          {renderTransferTab()}
        </TabsContent>

        <TabsContent value="permissions">
          {renderPermissionsTab()}
        </TabsContent>

        <TabsContent value="history">
          {renderHistoryTab()}
        </TabsContent>

        <TabsContent value="analytics">
          {renderAnalyticsTab()}
        </TabsContent>
      </Tabs>

      {/* New Transfer Dialog */}
      <Dialog open={showNewTransfer} onOpenChange={setShowNewTransfer}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>New Credit Transfer</DialogTitle>
            <DialogDescription>
              Transfer credits to another user or organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="toUser">Recipient</Label>
              <Select value={transferForm.toUserId} onValueChange={(value) => 
                setTransferForm({...transferForm, toUserId: value})
              }>
                <SelectTrigger>
                  <SelectValue placeholder="Select recipient" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="123">John Doe</SelectItem>
                  <SelectItem value="789">Bob Wilson</SelectItem>
                  <SelectItem value="456">Jane Smith</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="amount">Amount (credits)</Label>
              <Input
                id="amount"
                type="number"
                value={transferForm.amount}
                onChange={(e) => setTransferForm({...transferForm, amount: e.target.value})}
                placeholder="Enter amount"
              />
            </div>
            
            <div>
              <Label htmlFor="reason">Reason</Label>
              <Textarea
                id="reason"
                value={transferForm.reason}
                onChange={(e) => setTransferForm({...transferForm, reason: e.target.value})}
                placeholder="Reason for transfer"
              />
            </div>
            
            <div className="flex items-center space-x-2">
              <Switch
                id="requiresApproval"
                checked={transferForm.requiresApproval}
                onCheckedChange={(checked) => 
                  setTransferForm({...transferForm, requiresApproval: checked})
                }
              />
              <Label htmlFor="requiresApproval">Require approval</Label>
            </div>
            
            <div className="flex items-center space-x-2">
              <Switch
                id="urgent"
                checked={transferForm.urgent}
                onCheckedChange={(checked) => 
                  setTransferForm({...transferForm, urgent: checked})
                }
              />
              <Label htmlFor="urgent">Urgent transfer</Label>
            </div>
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setShowNewTransfer(false)}>
                Cancel
              </Button>
              <Button onClick={handleTransferSubmit} disabled={loading}>
                <Send className="h-4 w-4 mr-2" />
                Transfer
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* New Permission Dialog */}
      <Dialog open={showNewPermission} onOpenChange={setShowNewPermission}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>New Transfer Permission</DialogTitle>
            <DialogDescription>
              Configure permissions for credit transfers
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="permUser">User</Label>
              <Select value={permissionForm.toUserId} onValueChange={(value) => 
                setPermissionForm({...permissionForm, toUserId: value})
              }>
                <SelectTrigger>
                  <SelectValue placeholder="Select user" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="123">John Doe</SelectItem>
                  <SelectItem value="789">Bob Wilson</SelectItem>
                  <SelectItem value="456">Jane Smith</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="permType">Permission Type</Label>
              <Select value={permissionForm.permissionType} onValueChange={(value: any) => 
                setPermissionForm({...permissionForm, permissionType: value})
              }>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="allow_transfer">Allow Direct Transfer</SelectItem>
                  <SelectItem value="require_approval">Require Approval</SelectItem>
                  <SelectItem value="rate_limit">Rate Limited</SelectItem>
                  <SelectItem value="conditional_transfer">Conditional Transfer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="maxAmount">Max Amount (optional)</Label>
              <Input
                id="maxAmount"
                type="number"
                value={permissionForm.maxAmount}
                onChange={(e) => setPermissionForm({...permissionForm, maxAmount: e.target.value})}
                placeholder="Maximum transfer amount"
              />
            </div>
            
            <div>
              <Label htmlFor="maxFrequency">Max Frequency (optional)</Label>
              <Input
                id="maxFrequency"
                type="number"
                value={permissionForm.maxFrequency}
                onChange={(e) => setPermissionForm({...permissionForm, maxFrequency: e.target.value})}
                placeholder="Transfers per day"
              />
            </div>
            
            <div>
              <Label htmlFor="timeLimit">Time Limit Hours (optional)</Label>
              <Input
                id="timeLimit"
                type="number"
                value={permissionForm.timeLimitHours}
                onChange={(e) => setPermissionForm({...permissionForm, timeLimitHours: e.target.value})}
                placeholder="Hours until permission expires"
              />
            </div>
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setShowNewPermission(false)}>
                Cancel
              </Button>
              <Button onClick={handlePermissionSubmit} disabled={loading}>
                <Shield className="h-4 w-4 mr-2" />
                Create Permission
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CreditTransfer;