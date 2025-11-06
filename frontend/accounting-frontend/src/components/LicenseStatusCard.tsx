import React from 'react';
import { Shield, AlertCircle, CheckCircle, Calendar } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface LicenseInfo {
  tier_name: string;
  tier_display: string;
  status: 'active' | 'expired' | 'expiring_soon';
  expires_at: string;
  documents_used: number;
  documents_limit: number;
  users_count: number;
  users_limit: number;
}

interface LicenseStatusCardProps {
  license?: LicenseInfo;
  loading?: boolean;
}

export const LicenseStatusCard: React.FC<LicenseStatusCardProps> = ({ license, loading }) => {
  if (loading) {
    return (
      <Card className="card-hover">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary-600" />
            <CardTitle>License Status</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded w-3/4"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!license) {
    return (
      <Card className="card-hover border-warning-300 bg-warning-50 dark:bg-warning-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-warning-600" />
            <CardTitle>No License</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No active license found. Please contact your administrator.
          </p>
        </CardContent>
      </Card>
    );
  }

  const daysUntilExpiry = Math.floor(
    (new Date(license.expires_at).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
  );

  const getStatusBadge = () => {
    if (license.status === 'expired') {
      return <Badge className="bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300">Expired</Badge>;
    }
    if (daysUntilExpiry <= 30) {
      return <Badge className="bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300">Expiring Soon</Badge>;
    }
    return <Badge className="bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300">Active</Badge>;
  };

  const documentsPercentage = (license.documents_used / license.documents_limit) * 100;
  const usersPercentage = (license.users_count / license.users_limit) * 100;

  return (
    <Card className="card-hover">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary-600" />
            <CardTitle>License Status</CardTitle>
          </div>
          {getStatusBadge()}
        </div>
        <CardDescription>{license.tier_display} Plan</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Expiry Date */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span>Expires in</span>
          </div>
          <span className="font-semibold">{daysUntilExpiry} days</span>
        </div>

        {/* Document Usage */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span>Documents this month</span>
            <span className="font-semibold">
              {license.documents_used.toLocaleString()} / {license.documents_limit.toLocaleString()}
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                documentsPercentage >= 90
                  ? 'bg-error-500'
                  : documentsPercentage >= 70
                  ? 'bg-warning-500'
                  : 'bg-success-500'
              }`}
              style={{ width: `${Math.min(documentsPercentage, 100)}%` }}
            ></div>
          </div>
        </div>

        {/* User Usage */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span>Active users</span>
            <span className="font-semibold">
              {license.users_count} / {license.users_limit}
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                usersPercentage >= 90
                  ? 'bg-error-500'
                  : usersPercentage >= 70
                  ? 'bg-warning-500'
                  : 'bg-primary-500'
              }`}
              style={{ width: `${Math.min(usersPercentage, 100)}%` }}
            ></div>
          </div>
        </div>

        {/* Warning Messages */}
        {(documentsPercentage >= 90 || usersPercentage >= 90 || daysUntilExpiry <= 30) && (
          <div className="bg-warning-50 dark:bg-warning-900/20 border border-warning-300 dark:border-warning-700 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-warning-600 mt-0.5" />
              <div className="text-xs text-warning-700 dark:text-warning-300 space-y-1">
                {documentsPercentage >= 90 && (
                  <div>Document limit almost reached. Consider upgrading your plan.</div>
                )}
                {usersPercentage >= 90 && (
                  <div>User limit almost reached. Consider upgrading your plan.</div>
                )}
                {daysUntilExpiry <= 30 && (
                  <div>License expires soon. Please renew to avoid service interruption.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
