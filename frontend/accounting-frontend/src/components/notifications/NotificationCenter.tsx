import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Bell, 
  BellRing, 
  X, 
  Check, 
  CheckCheck, 
  Trash2, 
  Filter,
  Search,
  RefreshCw,
  Settings,
  Clock,
  AlertCircle,
  Info,
  CheckCircle,
  AlertTriangle,
  XCircle,
  MessageSquare,
  FileText,
  User,
  CreditCard,
  Shield,
  Server
} from 'lucide-react';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  category: 'system' | 'document' | 'verification' | 'billing' | 'security' | 'user';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  timestamp: string;
  is_read: boolean;
  is_archived: boolean;
  action_url?: string;
  action_label?: string;
  metadata?: Record<string, any>;
  source: 'webhook' | 'system' | 'user' | 'api';
}

interface NotificationCenterProps {
  maxHeight?: string;
  showHeader?: boolean;
  compact?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onNotificationClick?: (notification: Notification) => void;
  onMarkAsRead?: (notificationIds: string[]) => void;
  onMarkAllAsRead?: () => void;
  onArchive?: (notificationIds: string[]) => void;
  onDelete?: (notificationIds: string[]) => void;
  className?: string;
}

// Mock notifications for demo
const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: '1',
    title: 'Document Processing Complete',
    message: 'Your invoice document "Q4_2024_Invoice.pdf" has been successfully processed and is ready for download.',
    type: 'success',
    category: 'document',
    priority: 'medium',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
    is_read: false,
    is_archived: false,
    action_url: '/documents/download/12345',
    action_label: 'Download',
    metadata: { document_id: '12345', processing_time: '2m 34s' },
    source: 'system'
  },
  {
    id: '2',
    title: 'Account Verification Required',
    message: 'Please verify your email address to continue using all platform features. Verification expires in 24 hours.',
    type: 'warning',
    category: 'verification',
    priority: 'high',
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
    is_read: false,
    is_archived: false,
    action_url: '/verify-email',
    action_label: 'Verify Now',
    source: 'system'
  },
  {
    id: '3',
    title: 'Payment Successful',
    message: 'Your subscription payment of $29.99 has been processed successfully. Thank you for your continued membership.',
    type: 'success',
    category: 'billing',
    priority: 'medium',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    is_read: true,
    is_archived: false,
    action_url: '/billing/receipt/67890',
    action_label: 'View Receipt',
    metadata: { amount: 29.99, currency: 'USD', transaction_id: '67890' },
    source: 'system'
  },
  {
    id: '4',
    title: 'Security Alert',
    message: 'New login detected from Chrome on Windows. If this wasn\'t you, please secure your account immediately.',
    type: 'error',
    category: 'security',
    priority: 'urgent',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
    is_read: false,
    is_archived: false,
    action_url: '/security/login-activity',
    action_label: 'Review Activity',
    metadata: { ip_address: '192.168.1.100', browser: 'Chrome', platform: 'Windows' },
    source: 'system'
  },
  {
    id: '5',
    title: 'Weekly Report Available',
    message: 'Your weekly processing report is now available. You processed 127 documents this week.',
    type: 'info',
    category: 'system',
    priority: 'low',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
    is_read: true,
    is_archived: false,
    action_url: '/reports/weekly',
    action_label: 'View Report',
    metadata: { documents_processed: 127, period: 'weekly' },
    source: 'system'
  }
];

export function NotificationCenter({
  maxHeight = '600px',
  showHeader = true,
  compact = false,
  autoRefresh = true,
  refreshInterval = 30000,
  onNotificationClick,
  onMarkAsRead,
  onMarkAllAsRead,
  onArchive,
  onDelete,
  className = ''
}: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
  const [filteredNotifications, setFilteredNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
  const [selectedNotifications, setSelectedNotifications] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'unread' | 'archived'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket connection for real-time notifications
  useEffect(() => {
    connectWebSocket();
    return () => {
      disconnectWebSocket();
    };
  }, []);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(() => {
        refreshNotifications();
      }, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // Filter notifications based on current filters
  useEffect(() => {
    filterNotifications();
  }, [notifications, filter, categoryFilter, searchQuery]);

  const connectWebSocket = () => {
    try {
      // Mock WebSocket connection - in real app, use actual WebSocket URL
      const wsUrl = `ws://localhost:8080/notifications`;
      
      // Simulate WebSocket connection
      setTimeout(() => {
        setIsConnected(true);
        console.log('WebSocket connected to notifications service');
        
        // Simulate receiving new notifications
        setTimeout(() => {
          addNewNotification({
            title: 'New Document Uploaded',
            message: 'You have uploaded a new document for processing.',
            type: 'info' as const,
            category: 'document' as const,
            priority: 'low' as const
          });
        }, 10000);
      }, 1000);

    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setIsConnected(false);
    }
  };

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setIsConnected(false);
  };

  const filterNotifications = () => {
    let filtered = notifications;

    // Apply status filter
    if (filter === 'unread') {
      filtered = filtered.filter(n => !n.is_read && !n.is_archived);
    } else if (filter === 'archived') {
      filtered = filtered.filter(n => n.is_archived);
    } else {
      filtered = filtered.filter(n => !n.is_archived);
    }

    // Apply category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(n => n.category === categoryFilter);
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(n => 
        n.title.toLowerCase().includes(query) ||
        n.message.toLowerCase().includes(query)
      );
    }

    // Sort by timestamp (newest first)
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    setFilteredNotifications(filtered);
  };

  const refreshNotifications = async () => {
    setIsLoading(true);
    try {
      // In real app, fetch from API
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to refresh notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const addNewNotification = (notificationData: Partial<Notification>) => {
    const newNotification: Notification = {
      id: `notif-${Date.now()}`,
      title: notificationData.title || 'New Notification',
      message: notificationData.message || '',
      type: notificationData.type || 'info',
      category: notificationData.category || 'system',
      priority: notificationData.priority || 'medium',
      timestamp: new Date().toISOString(),
      is_read: false,
      is_archived: false,
      source: 'system'
    };

    setNotifications(prev => [newNotification, ...prev]);
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markAsRead([notification.id]);
    }
    onNotificationClick?.(notification);
  };

  const markAsRead = (notificationIds: string[]) => {
    setNotifications(prev => prev.map(notification => 
      notificationIds.includes(notification.id) 
        ? { ...notification, is_read: true }
        : notification
    ));
    onMarkAsRead?.(notificationIds);
  };

  const markAllAsRead = () => {
    const unreadIds = notifications.filter(n => !n.is_read && !n.is_archived).map(n => n.id);
    setNotifications(prev => prev.map(notification => ({ ...notification, is_read: true })));
    onMarkAllAsRead?.();
  };

  const archiveNotifications = (notificationIds: string[]) => {
    setNotifications(prev => prev.map(notification => 
      notificationIds.includes(notification.id) 
        ? { ...notification, is_archived: true }
        : notification
    ));
    onArchive?.(notificationIds);
    setSelectedNotifications(new Set());
  };

  const deleteNotifications = (notificationIds: string[]) => {
    setNotifications(prev => prev.filter(notification => !notificationIds.includes(notification.id)));
    onDelete?.(notificationIds);
    setSelectedNotifications(new Set());
  };

  const toggleNotificationSelection = (notificationId: string) => {
    setSelectedNotifications(prev => {
      const newSet = new Set(prev);
      if (newSet.has(notificationId)) {
        newSet.delete(notificationId);
      } else {
        newSet.add(notificationId);
      }
      return newSet;
    });
  };

  const getNotificationIcon = (type: string, category: string) => {
    switch (category) {
      case 'document': return FileText;
      case 'verification': return CheckCircle;
      case 'billing': return CreditCard;
      case 'security': return Shield;
      case 'user': return User;
      case 'system': return Server;
      default: return Info;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-green-500';
      case 'warning': return 'text-orange-500';
      case 'error': return 'text-red-500';
      default: return 'text-blue-500';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'border-l-red-500 bg-red-50';
      case 'high': return 'border-l-orange-500 bg-orange-50';
      case 'medium': return 'border-l-blue-500 bg-blue-50';
      default: return 'border-l-gray-300 bg-gray-50';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const unreadCount = notifications.filter(n => !n.is_read && !n.is_archived).length;
  const totalCount = notifications.filter(n => !n.is_archived).length;

  const categories = [
    { value: 'all', label: 'All Categories' },
    { value: 'document', label: 'Documents' },
    { value: 'verification', label: 'Verification' },
    { value: 'billing', label: 'Billing' },
    { value: 'security', label: 'Security' },
    { value: 'user', label: 'User' },
    { value: 'system', label: 'System' }
  ];

  if (compact) {
    return (
      <div className={`space-y-2 ${className}`}>
        {/* Compact Header */}
        <div className="flex items-center justify-between p-2 border-b">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            <span className="text-sm font-medium">Notifications</span>
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs px-1">
                {unreadCount}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {isConnected ? (
              <div className="w-2 h-2 bg-green-500 rounded-full" title="Connected" />
            ) : (
              <div className="w-2 h-2 bg-red-500 rounded-full" title="Disconnected" />
            )}
          </div>
        </div>

        {/* Compact Notification List */}
        <ScrollArea className="h-64">
          <div className="space-y-1 p-2">
            {filteredNotifications.slice(0, 10).map((notification) => {
              const IconComponent = getNotificationIcon(notification.type, notification.category);
              return (
                <div
                  key={notification.id}
                  className={`p-2 rounded cursor-pointer hover:bg-muted border-l-2 ${
                    getPriorityColor(notification.priority)
                  } ${!notification.is_read ? 'font-medium' : ''}`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="flex items-start gap-2">
                    <IconComponent className={`h-4 w-4 mt-0.5 ${getTypeColor(notification.type)}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm truncate">{notification.title}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {notification.message}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatTimestamp(notification.timestamp)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>

        {/* Compact Actions */}
        <div className="flex items-center justify-between p-2 border-t">
          <Button variant="ghost" size="sm" onClick={markAllAsRead}>
            <CheckCheck className="h-3 w-3 mr-1" />
            Mark all read
          </Button>
          <Button variant="ghost" size="sm">
            <Settings className="h-3 w-3" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {showHeader && (
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Notifications</h2>
            <p className="text-muted-foreground">
              Stay updated with important events and updates
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1 text-sm ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refreshNotifications}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      )}

      {/* Connection Status Alert */}
      {!isConnected && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Real-time notifications are currently unavailable. The system will attempt to reconnect automatically.
          </AlertDescription>
        </Alert>
      )}

      {/* Filters and Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex items-center gap-2 flex-1">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search notifications..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          <Select value={filter} onValueChange={(value: any) => setFilter(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All ({totalCount})</SelectItem>
              <SelectItem value="unread">Unread ({unreadCount})</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {categories.map(category => (
                <SelectItem key={category.value} value={category.value}>
                  {category.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {selectedNotifications.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selectedNotifications.size} selected
            </span>
            <Button variant="outline" size="sm" onClick={() => markAsRead(Array.from(selectedNotifications))}>
              <Check className="h-3 w-3 mr-1" />
              Mark Read
            </Button>
            <Button variant="outline" size="sm" onClick={() => archiveNotifications(Array.from(selectedNotifications))}>
              Archive
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => deleteNotifications(Array.from(selectedNotifications))}
              className="text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Delete
            </Button>
          </div>
        )}
      </div>

      {/* Bulk Actions */}
      {selectedNotifications.size === 0 && unreadCount > 0 && (
        <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
          <span className="text-sm text-muted-foreground">
            You have {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
          </span>
          <Button variant="outline" size="sm" onClick={markAllAsRead}>
            <CheckCheck className="h-3 w-3 mr-1" />
            Mark all as read
          </Button>
        </div>
      )}

      {/* Notification List */}
      <Card>
        <CardContent className="p-0">
          <ScrollArea style={{ maxHeight }}>
            {filteredNotifications.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">
                    {searchQuery || filter !== 'all' || categoryFilter !== 'all' 
                      ? 'No notifications found' 
                      : 'No notifications yet'
                    }
                  </h3>
                  <p className="text-muted-foreground">
                    {searchQuery || filter !== 'all' || categoryFilter !== 'all'
                      ? 'Try adjusting your search or filters'
                      : 'You\'ll see notifications here when important events occur'
                    }
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y">
                {filteredNotifications.map((notification) => {
                  const IconComponent = getNotificationIcon(notification.type, notification.category);
                  const isSelected = selectedNotifications.has(notification.id);
                  
                  return (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-muted/50 cursor-pointer transition-colors border-l-4 ${
                        getPriorityColor(notification.priority)
                      } ${isSelected ? 'bg-muted' : ''}`}
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleNotificationSelection(notification.id);
                          }}
                          className="mt-1"
                        />
                        
                        <div className={`p-2 rounded-full ${
                          notification.type === 'success' ? 'bg-green-100' :
                          notification.type === 'warning' ? 'bg-orange-100' :
                          notification.type === 'error' ? 'bg-red-100' :
                          'bg-blue-100'
                        }`}>
                          <IconComponent className={`h-4 w-4 ${getTypeColor(notification.type)}`} />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className={`text-sm ${!notification.is_read ? 'font-semibold' : ''}`}>
                              {notification.title}
                            </h4>
                            <div className="flex items-center gap-1">
                              {!notification.is_read && (
                                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                              )}
                              <Badge variant="outline" className="text-xs">
                                {categories.find(c => c.value === notification.category)?.label || notification.category}
                              </Badge>
                              <Badge variant="secondary" className="text-xs">
                                {notification.priority}
                              </Badge>
                            </div>
                          </div>
                          
                          <p className={`text-sm mb-2 ${!notification.is_read ? 'text-foreground' : 'text-muted-foreground'}`}>
                            {notification.message}
                          </p>
                          
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {formatTimestamp(notification.timestamp)}
                              <span>•</span>
                              <span className="capitalize">{notification.source}</span>
                            </div>
                            
                            {notification.action_url && (
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  window.open(notification.action_url, '_blank');
                                }}
                              >
                                {notification.action_label || 'View'}
                              </Button>
                            )}
                          </div>
                        </div>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (!notification.is_read) {
                              markAsRead([notification.id]);
                            } else {
                              deleteNotifications([notification.id]);
                            }
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Showing {filteredNotifications.length} of {totalCount} notifications
        </span>
        <span>
          Last updated: {lastUpdate.toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}