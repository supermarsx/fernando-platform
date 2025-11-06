import React, { useEffect, useState, useRef } from 'react';
import { 
  FileText, Search, Filter, Download, Eye, AlertCircle, 
  Info, CheckCircle, XCircle, Clock, User, Activity,
  RefreshCw, Calendar, Tag, ArrowUpDown
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
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle 
} from '@/components/ui/dialog';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';
import { useNavigate } from 'react-router-dom';

interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  username: string;
  action: string;
  resource: string;
  resource_id?: string;
  status: 'success' | 'error' | 'warning' | 'info';
  ip_address: string;
  user_agent: string;
  details: Record<string, any>;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterAction, setFilterAction] = useState<string>('all');
  const [dateRange, setDateRange] = useState<string>('24h');
  const [sortBy, setSortBy] = useState<string>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [showLogDetails, setShowLogDetails] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(50);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    fetchLogs();
    // Set up real-time updates every 10 seconds
    intervalRef.current = setInterval(fetchLogs, 10000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [user, navigate]);

  useEffect(() => {
    filterAndSortLogs();
  }, [logs, searchTerm, filterStatus, filterSeverity, filterAction, sortBy, sortOrder]);

  const fetchLogs = async () => {
    try {
      if (!refreshing) setLoading(true);
      setRefreshing(true);
      
      const params = new URLSearchParams({
        limit: '1000',
        ...(dateRange !== 'all' && { since: getDateRange(dateRange) }),
        ...(filterAction !== 'all' && { action: filterAction })
      });

      const response = await api.get(`/api/v1/admin/audit-logs?${params}`);
      setLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load audit logs"
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getDateRange = (range: string) => {
    const now = new Date();
    const ranges: Record<string, number> = {
      '1h': 1,
      '24h': 24,
      '7d': 168,
      '30d': 720,
    };
    const hours = ranges[range] || 24;
    const past = new Date(now.getTime() - hours * 60 * 60 * 1000);
    return past.toISOString();
  };

  const filterAndSortLogs = () => {
    let filtered = logs.filter(log => {
      const matchesSearch = 
        log.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.resource.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.ip_address.includes(searchTerm);
      
      const matchesStatus = filterStatus === 'all' || log.status === filterStatus;
      const matchesSeverity = filterSeverity === 'all' || log.severity === filterSeverity;
      
      return matchesSearch && matchesStatus && matchesSeverity;
    });

    // Sort logs
    filtered.sort((a, b) => {
      let aVal, bVal;
      switch (sortBy) {
        case 'timestamp':
          aVal = new Date(a.timestamp).getTime();
          bVal = new Date(b.timestamp).getTime();
          break;
        case 'username':
          aVal = a.username;
          bVal = b.username;
          break;
        case 'action':
          aVal = a.action;
          bVal = b.action;
          break;
        case 'severity':
          const severityOrder = { low: 1, medium: 2, high: 3, critical: 4 };
          aVal = severityOrder[a.severity as keyof typeof severityOrder];
          bVal = severityOrder[b.severity as keyof typeof severityOrder];
          break;
        default:
          aVal = a.timestamp;
          bVal = b.timestamp;
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    setFilteredLogs(filtered);
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const exportLogs = async () => {
    try {
      const response = await api.get(`/api/v1/admin/audit-logs/export`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-logs-${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast({
        variant: "success",
        title: "Success",
        description: "Audit logs exported successfully"
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to export audit logs"
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-4 w-4 text-success-600" />;
      case 'error': return <XCircle className="h-4 w-4 text-error-600" />;
      case 'warning': return <AlertCircle className="h-4 w-4 text-warning-600" />;
      case 'info': return <Info className="h-4 w-4 text-primary-600" />;
      default: return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      success: 'success',
      error: 'error',
      warning: 'warning',
      info: 'primary'
    } as const;
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    );
  };

  const getSeverityBadge = (severity: string) => {
    const variants = {
      low: 'outline',
      medium: 'secondary',
      high: 'warning',
      critical: 'error'
    } as const;
    
    return (
      <Badge variant={variants[severity as keyof typeof variants] || 'outline'}>
        {severity}
      </Badge>
    );
  };

  // Pagination
  const totalPages = Math.ceil(filteredLogs.length / itemsPerPage);
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading audit logs...</p>
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
                Audit Logs
              </h1>
              <p className="text-sm text-muted-foreground">
                System activity monitoring and security audit trail
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Button 
                variant="pastel-secondary" 
                onClick={() => fetchLogs()}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button variant="pastel-primary" onClick={exportLogs}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <Button variant="pastel-secondary" onClick={() => navigate('/admin')}>
                Back to Admin
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Events</CardTitle>
              <FileText className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{logs.length}</div>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Critical Events</CardTitle>
              <AlertCircle className="h-4 w-4 text-error-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {logs.filter(l => l.severity === 'critical').length}
              </div>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Users</CardTitle>
              <User className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {new Set(logs.map(l => l.user_id)).size}
              </div>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Last 24h</CardTitle>
              <Clock className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {logs.filter(l => {
                  const logDate = new Date(l.timestamp);
                  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
                  return logDate > yesterday;
                }).length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
              <Select value={dateRange} onValueChange={setDateRange}>
                <SelectTrigger>
                  <SelectValue placeholder="Time range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">Last Hour</SelectItem>
                  <SelectItem value="24h">Last 24 Hours</SelectItem>
                  <SelectItem value="7d">Last 7 Days</SelectItem>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                  <SelectItem value="all">All Time</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Logs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Audit Log Entries ({filteredLogs.length})</CardTitle>
            <CardDescription>
              Real-time security and system activity monitoring
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead className="text-right">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedLogs.map((log) => (
                  <TableRow 
                    key={log.id} 
                    className="animate-fade-in cursor-pointer hover:bg-muted/50"
                    onClick={() => {
                      setSelectedLog(log);
                      setShowLogDetails(true);
                    }}
                  >
                    <TableCell className="text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{log.username}</div>
                        <div className="text-sm text-muted-foreground">ID: {log.user_id.slice(-8)}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{log.resource}</div>
                        {log.resource_id && (
                          <div className="text-sm text-muted-foreground">ID: {log.resource_id.slice(-8)}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(log.status)}
                        {getStatusBadge(log.status)}
                      </div>
                    </TableCell>
                    <TableCell>
                      {getSeverityBadge(log.severity)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {log.ip_address}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-muted-foreground">
                  Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, filteredLogs.length)} of {filteredLogs.length} entries
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + Math.max(1, currentPage - 2);
                      if (page > totalPages) return null;
                      return (
                        <Button
                          key={page}
                          variant={currentPage === page ? "default" : "outline"}
                          size="sm"
                          onClick={() => setCurrentPage(page)}
                        >
                          {page}
                        </Button>
                      );
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Log Details Modal */}
        <Dialog open={showLogDetails} onOpenChange={setShowLogDetails}>
          <DialogContent className="sm:max-w-[700px]">
            <DialogHeader>
              <DialogTitle>Audit Log Details</DialogTitle>
              <DialogDescription>
                Detailed information about this audit event
              </DialogDescription>
            </DialogHeader>
            {selectedLog && (
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="font-medium">Timestamp</Label>
                    <p className="text-sm text-muted-foreground">
                      {new Date(selectedLog.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <Label className="font-medium">User</Label>
                    <p className="text-sm text-muted-foreground">
                      {selectedLog.username} ({selectedLog.user_id.slice(-8)})
                    </p>
                  </div>
                  <div>
                    <Label className="font-medium">Action</Label>
                    <Badge variant="outline">{selectedLog.action}</Badge>
                  </div>
                  <div>
                    <Label className="font-medium">Resource</Label>
                    <p className="text-sm text-muted-foreground">
                      {selectedLog.resource}
                      {selectedLog.resource_id && ` (${selectedLog.resource_id.slice(-8)})`}
                    </p>
                  </div>
                  <div>
                    <Label className="font-medium">Status</Label>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(selectedLog.status)}
                      {getStatusBadge(selectedLog.status)}
                    </div>
                  </div>
                  <div>
                    <Label className="font-medium">Severity</Label>
                    <div className="mt-1">
                      {getSeverityBadge(selectedLog.severity)}
                    </div>
                  </div>
                  <div>
                    <Label className="font-medium">IP Address</Label>
                    <p className="text-sm font-mono text-muted-foreground">
                      {selectedLog.ip_address}
                    </p>
                  </div>
                  <div>
                    <Label className="font-medium">User Agent</Label>
                    <p className="text-sm text-muted-foreground truncate">
                      {selectedLog.user_agent}
                    </p>
                  </div>
                </div>
                <div>
                  <Label className="font-medium">Additional Details</Label>
                  <pre className="text-xs bg-muted p-3 rounded-lg mt-1 overflow-auto max-h-40">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}