import React, { useEffect, useState } from 'react';
import { Plus, Search, Filter, Download, Eye, Edit, Ban, RotateCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface License {
  license_id: number;
  license_key: string;
  organization_name: string;
  organization_email: string;
  status: 'active' | 'expired' | 'suspended' | 'revoked';
  tier: {
    display_name: string;
    name: string;
  };
  expires_at: string;
  documents_processed_this_month: number;
  created_at: string;
}

export default function LicenseManagementPage() {
  const [licenses, setLicenses] = useState<License[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    fetchLicenses();
  }, []);

  const fetchLicenses = async () => {
    try {
      const response = await api.get('/api/v1/licenses');
      setLicenses(response.data);
    } catch (error) {
      console.error('Failed to fetch licenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
      expired: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
      suspended: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300',
      revoked: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
    };
    return variants[status as keyof typeof variants] || variants.active;
  };

  const filteredLicenses = licenses.filter(license => {
    const matchesSearch = 
      license.organization_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      license.license_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      license.organization_email.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || license.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: licenses.length,
    active: licenses.filter(l => l.status === 'active').length,
    expired: licenses.filter(l => l.status === 'expired').length,
    suspended: licenses.filter(l => l.status === 'suspended').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="loading-spinner h-12 w-12"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">License Management</h1>
          <p className="text-muted-foreground mt-1">
            Manage and monitor all active licenses
          </p>
        </div>
        <Button className="btn-pastel-primary">
          <Plus className="h-4 w-4 mr-2" />
          Create License
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="card-hover">
          <CardHeader className="pb-2">
            <CardDescription>Total Licenses</CardDescription>
            <CardTitle className="text-3xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="card-hover">
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl text-success-600">{stats.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="card-hover">
          <CardHeader className="pb-2">
            <CardDescription>Expired</CardDescription>
            <CardTitle className="text-3xl text-error-600">{stats.expired}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="card-hover">
          <CardHeader className="pb-2">
            <CardDescription>Suspended</CardDescription>
            <CardTitle className="text-3xl text-warning-600">{stats.suspended}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search by organization, email, or license key..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border rounded-lg bg-background"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="suspended">Suspended</option>
              <option value="revoked">Revoked</option>
            </select>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              More Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Licenses Table */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>All Licenses ({filteredLicenses.length})</CardTitle>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium">Organization</th>
                  <th className="text-left py-3 px-4 font-medium">License Key</th>
                  <th className="text-left py-3 px-4 font-medium">Tier</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Usage</th>
                  <th className="text-left py-3 px-4 font-medium">Expires</th>
                  <th className="text-left py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLicenses.map((license) => (
                  <tr key={license.license_id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <div className="font-medium">{license.organization_name}</div>
                        <div className="text-sm text-muted-foreground">{license.organization_email}</div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {license.license_key.substring(0, 24)}...
                      </code>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="secondary">{license.tier.display_name}</Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Badge className={getStatusBadge(license.status)}>
                        {license.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-sm">
                        {license.documents_processed_this_month} docs this month
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-sm">
                        {new Date(license.expires_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" title="View Details">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Edit">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Renew">
                          <RotateCw className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Suspend">
                          <Ban className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
