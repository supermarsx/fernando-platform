import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Plus, 
  Bell, 
  Edit, 
  Trash2, 
  Copy, 
  Eye, 
  Send, 
  Save, 
  Smartphone,
  Monitor,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  Template as TemplateIcon,
  Smartphone as MobileIcon,
  Globe,
  Image,
  Volume2,
  Vibrate
} from 'lucide-react';

interface PushTemplate {
  id: string;
  name: string;
  title: string;
  body: string;
  icon_url?: string;
  image_url?: string;
  action_url?: string;
  category: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  platforms: string[];
  sound_enabled: boolean;
  vibration_enabled: boolean;
  badge_enabled: boolean;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  ttl?: number; // Time to live in seconds
  delivery_stats?: {
    sent: number;
    delivered: number;
    clicked: number;
    dismissed: number;
    delivery_rate: number;
  };
}

interface PushTemplateManagerProps {
  onTemplateSelect?: (template: PushTemplate) => void;
  selectedCategory?: string;
  showTestMode?: boolean;
  defaultPlatform?: string;
}

const DEFAULT_PUSH_TEMPLATES: PushTemplate[] = [
  {
    id: 'document-ready',
    name: 'Document Processing Complete',
    title: 'Your document is ready!',
    body: 'Hi {{user_name}}, your document "{{document_name}}" has been processed and is ready for download.',
    icon_url: '/icons/document-ready.png',
    category: 'document_processing',
    variables: ['user_name', 'document_name', 'download_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    platforms: ['web', 'mobile'],
    sound_enabled: true,
    vibration_enabled: true,
    badge_enabled: true,
    priority: 'normal',
    ttl: 3600
  },
  {
    id: 'verification-required',
    name: 'Verification Required',
    title: 'Account verification needed',
    body: 'Please verify your account to continue using Fernando. Tap to complete verification.',
    icon_url: '/icons/verification.png',
    category: 'verification',
    variables: ['user_name', 'verification_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    platforms: ['web', 'mobile'],
    sound_enabled: true,
    vibration_enabled: true,
    badge_enabled: false,
    priority: 'high',
    ttl: 7200
  },
  {
    id: 'payment-reminder',
    name: 'Payment Reminder',
    title: 'Payment due soon',
    body: 'Your Fernando subscription payment of ${{amount}} is due on {{due_date}}. Don\'t miss out!',
    icon_url: '/icons/payment.png',
    image_url: '/images/payment-banner.jpg',
    category: 'billing',
    variables: ['user_name', 'amount', 'due_date', 'payment_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    platforms: ['web', 'mobile'],
    sound_enabled: false,
    vibration_enabled: false,
    badge_enabled: true,
    priority: 'normal',
    ttl: 86400
  }
];

export function PushTemplateManager({ 
  onTemplateSelect, 
  selectedCategory = 'all',
  showTestMode = false,
  defaultPlatform = 'web'
}: PushTemplateManagerProps) {
  const [templates, setTemplates] = useState<PushTemplate[]>(DEFAULT_PUSH_TEMPLATES);
  const [selectedTemplate, setSelectedTemplate] = useState<PushTemplate | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isPreviewDialogOpen, setIsPreviewDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Partial<PushTemplate> | null>(null);
  const [previewData, setPreviewData] = useState<Record<string, any>>({});
  const [selectedPlatform, setSelectedPlatform] = useState(defaultPlatform);
  const [activeTab, setActiveTab] = useState('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'updated_at' | 'category'>('updated_at');

  const categories = [
    { value: 'all', label: 'All Templates' },
    { value: 'document_processing', label: 'Document Processing' },
    { value: 'verification', label: 'Verification' },
    { value: 'billing', label: 'Billing' },
    { value: 'security', label: 'Security' },
    { value: 'system_alerts', label: 'System Alerts' },
    { value: 'user_onboarding', label: 'User Onboarding' },
    { value: 'marketing', label: 'Marketing' }
  ];

  const platforms = [
    { value: 'web', label: 'Web Browser', icon: Monitor },
    { value: 'mobile', label: 'Mobile App', icon: Smartphone }
  ];

  const filteredTemplates = templates
    .filter(template => {
      const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
      const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           template.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesPlatform = template.platforms.includes(selectedPlatform) || template.platforms.length === 0;
      return matchesCategory && matchesSearch && matchesPlatform;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'category':
          return a.category.localeCompare(b.category);
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
    });

  const handleCreateTemplate = () => {
    setEditingTemplate({
      name: '',
      title: '',
      body: '',
      category: 'system_alerts',
      variables: [],
      is_active: true,
      platforms: ['web'],
      sound_enabled: true,
      vibration_enabled: false,
      badge_enabled: true,
      priority: 'normal'
    });
    setIsCreateDialogOpen(true);
  };

  const handleEditTemplate = (template: PushTemplate) => {
    setEditingTemplate(template);
    setIsCreateDialogOpen(true);
  };

  const handleSaveTemplate = () => {
    if (!editingTemplate) return;

    const now = new Date().toISOString();
    const templateWithStats = {
      ...editingTemplate,
      updated_at: now
    } as PushTemplate;
    
    if (selectedTemplate?.id === editingTemplate.id) {
      // Update existing template
      setTemplates(prev => prev.map(template => 
        template.id === editingTemplate.id ? templateWithStats : template
      ));
    } else {
      // Create new template
      const newTemplate: PushTemplate = {
        ...templateWithStats,
        id: `push-template-${Date.now()}`,
        created_at: now,
        created_by: 'current-user'
      };
      setTemplates(prev => [...prev, newTemplate]);
    }

    setEditingTemplate(null);
    setIsCreateDialogOpen(false);
  };

  const handleDeleteTemplate = (templateId: string) => {
    setTemplates(prev => prev.filter(template => template.id !== templateId));
    if (selectedTemplate?.id === templateId) {
      setSelectedTemplate(null);
    }
  };

  const handleDuplicateTemplate = (template: PushTemplate) => {
    const duplicate: PushTemplate = {
      ...template,
      id: `push-template-${Date.now()}`,
      name: `${template.name} (Copy)`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'current-user'
    };
    setTemplates(prev => [...prev, duplicate]);
  };

  const handlePreviewTemplate = (template: PushTemplate) => {
    setSelectedTemplate(template);
    
    // Generate sample preview data
    const sampleData = {
      user_name: 'John Doe',
      document_name: 'invoice_q4_2024.pdf',
      download_url: 'https://app.fernando.com/documents/download/12345',
      verification_url: 'https://app.fernando.com/verify',
      amount: '29.99',
      due_date: 'Dec 15, 2024',
      payment_url: 'https://app.fernando.com/billing/pay'
    };
    
    setPreviewData(sampleData);
    setIsPreviewDialogOpen(true);
  };

  const handleTestTemplate = (template: PushTemplate) => {
    setSelectedTemplate(template);
    setIsTestDialogOpen(true);
  };

  const renderPreview = (text: string, data: Record<string, any>) => {
    let preview = text;
    Object.entries(data).forEach(([key, value]) => {
      const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
      preview = preview.replace(regex, String(value));
    });
    return preview;
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-500';
      case 'high': return 'text-orange-500';
      case 'normal': return 'text-green-500';
      default: return 'text-blue-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Push Notification Templates</h2>
          <p className="text-muted-foreground">
            Manage push notification templates for web and mobile platforms
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreateTemplate} className="gap-2">
            <Plus className="h-4 w-4" />
            New Template
          </Button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="updated_at">Last Updated</SelectItem>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="category">Category</SelectItem>
          </SelectContent>
        </Select>
        <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {platforms.map(platform => {
              const IconComponent = platform.icon;
              return (
                <SelectItem key={platform.value} value={platform.value}>
                  <div className="flex items-center gap-2">
                    <IconComponent className="h-4 w-4" />
                    {platform.label}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
        <Select value={selectedCategory} onValueChange={(value) => onTemplateSelect?.({} as PushTemplate)}>
          <SelectTrigger className="w-48">
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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="templates" className="gap-2">
            <Bell className="h-4 w-4" />
            Templates ({filteredTemplates.length})
          </TabsTrigger>
          <TabsTrigger value="analytics" className="gap-2">
            <CheckCircle className="h-4 w-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="space-y-4">
          {filteredTemplates.length === 0 ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No templates found</h3>
                  <p className="text-muted-foreground mb-4">
                    {searchQuery ? 'Try adjusting your search or filters' : 'Create your first push notification template to get started'}
                  </p>
                  {!searchQuery && (
                    <Button onClick={handleCreateTemplate}>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Template
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredTemplates.map((template) => (
                <Card key={template.id} className="relative">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="space-y-1 flex-1">
                        <CardTitle className="flex items-center gap-2">
                          <Bell className="h-5 w-5 text-purple-500" />
                          {template.name}
                          {!template.is_active && (
                            <Badge variant="secondary" className="text-xs">
                              Inactive
                            </Badge>
                          )}
                        </CardTitle>
                        <CardDescription className="space-y-1">
                          <div><strong>Title:</strong> {template.title}</div>
                          <div><strong>Body:</strong> {template.body.length > 80 
                            ? `${template.body.substring(0, 80)}...` 
                            : template.body}</div>
                        </CardDescription>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="outline">
                            {categories.find(c => c.value === template.category)?.label || template.category}
                          </Badge>
                          <Badge variant="outline" className={getPriorityColor(template.priority)}>
                            {template.priority}
                          </Badge>
                          <div className="flex items-center gap-1">
                            {template.platforms.map(platform => {
                              const platformInfo = platforms.find(p => p.value === platform);
                              const IconComponent = platformInfo?.icon || Monitor;
                              return (
                                <IconComponent key={platform} className="h-3 w-3 text-muted-foreground" />
                              );
                            })}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            Updated {new Date(template.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                        {template.action_url && (
                          <div className="text-xs text-muted-foreground">
                            Action: {template.action_url}
                          </div>
                        )}
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            •••
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handlePreviewTemplate(template)}>
                            <Eye className="h-4 w-4 mr-2" />
                            Preview
                          </DropdownMenuItem>
                          {showTestMode && (
                            <DropdownMenuItem onClick={() => handleTestTemplate(template)}>
                              <Send className="h-4 w-4 mr-2" />
                              Test Send
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem onClick={() => handleEditTemplate(template)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDuplicateTemplate(template)}>
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            onClick={() => handleDeleteTemplate(template.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardHeader>
                  
                  {template.delivery_stats && (
                    <CardContent className="pt-0">
                      <div className="grid grid-cols-4 gap-4 text-center">
                        <div>
                          <div className="text-2xl font-bold text-blue-600">
                            {template.delivery_stats.sent}
                          </div>
                          <div className="text-xs text-muted-foreground">Sent</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-green-600">
                            {template.delivery_stats.delivered}
                          </div>
                          <div className="text-xs text-muted-foreground">Delivered</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-orange-600">
                            {template.delivery_stats.clicked}
                          </div>
                          <div className="text-xs text-muted-foreground">Clicked</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-red-600">
                            {template.delivery_stats.dismissed}
                          </div>
                          <div className="text-xs text-muted-foreground">Dismissed</div>
                        </div>
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Templates</CardTitle>
                <TemplateIcon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{templates.length}</div>
                <p className="text-xs text-muted-foreground">
                  {templates.filter(t => t.is_active).length} active
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Sent</CardTitle>
                <Send className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {templates.reduce((sum, t) => sum + (t.delivery_stats?.sent || 0), 0)}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Click Rate</CardTitle>
                <Bell className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">12.4%</div>
                <p className="text-xs text-muted-foreground">
                  +2.1% from last month
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Platform Split</CardTitle>
                <Smartphone className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">65% / 35%</div>
                <p className="text-xs text-muted-foreground">
                  Mobile / Web
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Template Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate?.id === editingTemplate?.id ? 'Edit Push Template' : 'Create Push Template'}
            </DialogTitle>
            <DialogDescription>
              Create push notification templates for web and mobile platforms
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-6">
            {/* Basic Information */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="template-name">Template Name</Label>
                <Input
                  id="template-name"
                  value={editingTemplate?.name || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, name: e.target.value} : null)}
                  placeholder="Enter template name"
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="template-category">Category</Label>
                <Select 
                  value={editingTemplate?.category || 'system_alerts'}
                  onValueChange={(value) => setEditingTemplate(prev => prev ? {...prev, category: value} : null)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.slice(1).map(category => (
                      <SelectItem key={category.value} value={category.value}>
                        {category.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Notification Content */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="template-title">Title</Label>
                <Input
                  id="template-title"
                  value={editingTemplate?.title || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, title: e.target.value} : null)}
                  placeholder="Enter notification title"
                  maxLength={50}
                />
                <p className="text-xs text-muted-foreground">
                  Keep titles short and concise (max 50 characters)
                </p>
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="template-body">Body</Label>
                <Textarea
                  id="template-body"
                  value={editingTemplate?.body || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, body: e.target.value} : null)}
                  placeholder="Enter notification body text"
                  maxLength={200}
                  className="min-h-[80px] resize-none"
                />
                <p className="text-xs text-muted-foreground">
                  Body text should be informative but concise (max 200 characters)
                </p>
              </div>
            </div>

            {/* Media URLs */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="icon-url">Icon URL</Label>
                <Input
                  id="icon-url"
                  value={editingTemplate?.icon_url || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, icon_url: e.target.value} : null)}
                  placeholder="https://example.com/icon.png"
                  type="url"
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="image-url">Image URL</Label>
                <Input
                  id="image-url"
                  value={editingTemplate?.image_url || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, image_url: e.target.value} : null)}
                  placeholder="https://example.com/image.jpg"
                  type="url"
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="action-url">Action URL</Label>
                <Input
                  id="action-url"
                  value={editingTemplate?.action_url || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, action_url: e.target.value} : null)}
                  placeholder="https://example.com/action"
                  type="url"
                />
              </div>
            </div>

            {/* Variables */}
            <div className="grid gap-2">
              <Label>Available Variables</Label>
              <div className="grid grid-cols-2 gap-2">
                {['user_name', 'document_name', 'download_url', 'verification_url', 'amount', 
                  'due_date', 'payment_url', 'account_id', 'plan_name'].map(variable => (
                  <Badge 
                    key={variable} 
                    variant="outline" 
                    className="justify-start p-2 cursor-pointer hover:bg-muted"
                    onClick={() => {
                      const currentField = editingTemplate?.body || '';
                      const newBody = currentField + `{{${variable}}}`;
                      setEditingTemplate(prev => prev ? {...prev, body: newBody} : null);
                    }}
                  >
                    {variable}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Variables will be replaced with actual values when the notification is sent.
              </p>
            </div>

            {/* Platform Settings */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label>Supported Platforms</Label>
                <div className="flex gap-4">
                  {platforms.map(platform => (
                    <div key={platform.value} className="flex items-center space-x-2">
                      <Checkbox
                        id={`platform-${platform.value}`}
                        checked={editingTemplate?.platforms?.includes(platform.value) || false}
                        onCheckedChange={(checked) => {
                          const current = editingTemplate?.platforms || [];
                          const updated = checked
                            ? [...current, platform.value]
                            : current.filter(p => p !== platform.value);
                          setEditingTemplate(prev => prev ? {...prev, platforms: updated} : null);
                        }}
                      />
                      <Label htmlFor={`platform-${platform.value}`} className="flex items-center gap-2">
                        <platform.icon className="h-4 w-4" />
                        {platform.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="priority">Priority</Label>
                <Select 
                  value={editingTemplate?.priority || 'normal'}
                  onValueChange={(value: any) => setEditingTemplate(prev => prev ? {...prev, priority: value} : null)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="ttl">Time to Live (seconds)</Label>
                <Input
                  id="ttl"
                  type="number"
                  value={editingTemplate?.ttl || ''}
                  onChange={(e) => setEditingTemplate(prev => prev ? {...prev, ttl: parseInt(e.target.value)} : null)}
                  placeholder="3600"
                />
                <p className="text-xs text-muted-foreground">
                  How long to keep the notification if not delivered (0 = no limit)
                </p>
              </div>
            </div>

            {/* Notification Features */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label>Notification Features</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="sound-enabled"
                      checked={editingTemplate?.sound_enabled ?? true}
                      onCheckedChange={(checked) => 
                        setEditingTemplate(prev => prev ? {...prev, sound_enabled: checked} : null)
                      }
                    />
                    <Label htmlFor="sound-enabled" className="flex items-center gap-2">
                      <Volume2 className="h-4 w-4" />
                      Play sound
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="vibration-enabled"
                      checked={editingTemplate?.vibration_enabled ?? false}
                      onCheckedChange={(checked) => 
                        setEditingTemplate(prev => prev ? {...prev, vibration_enabled: checked} : null)
                      }
                    />
                    <Label htmlFor="vibration-enabled" className="flex items-center gap-2">
                      <Vibrate className="h-4 w-4" />
                      Enable vibration (mobile only)
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="badge-enabled"
                      checked={editingTemplate?.badge_enabled ?? true}
                      onCheckedChange={(checked) => 
                        setEditingTemplate(prev => prev ? {...prev, badge_enabled: checked} : null)
                      }
                    />
                    <Label htmlFor="badge-enabled" className="flex items-center gap-2">
                      <Bell className="h-4 w-4" />
                      Show badge
                    </Label>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="is-active"
                checked={editingTemplate?.is_active ?? true}
                onCheckedChange={(checked) => 
                  setEditingTemplate(prev => prev ? {...prev, is_active: checked} : null)
                }
              />
              <Label htmlFor="is-active">Template is active</Label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveTemplate}>
              <Save className="h-4 w-4 mr-2" />
              Save Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={isPreviewDialogOpen} onOpenChange={setIsPreviewDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Push Notification Preview</DialogTitle>
            <DialogDescription>
              Preview how your push notification will look on different platforms
            </DialogDescription>
          </DialogHeader>
          
          {selectedTemplate && (
            <div className="space-y-6">
              {/* Preview Controls */}
              <div className="flex items-center gap-4">
                <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {platforms.map(platform => {
                      const IconComponent = platform.icon;
                      return (
                        <SelectItem key={platform.value} value={platform.value}>
                          <div className="flex items-center gap-2">
                            <IconComponent className="h-4 w-4" />
                            {platform.label}
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
                
                <div className="flex items-center gap-2">
                  {selectedTemplate.sound_enabled && (
                    <Volume2 className="h-4 w-4 text-blue-500" title="Sound enabled" />
                  )}
                  {selectedTemplate.vibration_enabled && selectedPlatform === 'mobile' && (
                    <Vibrate className="h-4 w-4 text-green-500" title="Vibration enabled" />
                  )}
                  {selectedTemplate.badge_enabled && (
                    <Bell className="h-4 w-4 text-purple-500" title="Badge enabled" />
                  )}
                  <Badge variant={getPriorityColor(selectedTemplate.priority) === 'text-red-500' ? 'destructive' : 'secondary'}>
                    {selectedTemplate.priority}
                  </Badge>
                </div>
              </div>

              {/* Platform Preview */}
              <div className="space-y-4">
                {selectedPlatform === 'web' ? (
                  <div className="border rounded-lg p-4 bg-white shadow-sm">
                    <div className="flex items-start gap-3">
                      {selectedTemplate.icon_url && (
                        <img 
                          src={selectedTemplate.icon_url} 
                          alt="Icon" 
                          className="w-10 h-10 rounded"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      )}
                      <div className="flex-1 space-y-1">
                        <div className="text-sm font-medium">
                          {renderPreview(selectedTemplate.title, previewData)}
                        </div>
                        <div className="text-sm text-gray-600">
                          {renderPreview(selectedTemplate.body, previewData)}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span>Fernando</span>
                          <span>•</span>
                          <span>Now</span>
                          <span>•</span>
                          <span>{selectedPlatform}</span>
                        </div>
                      </div>
                      {selectedTemplate.image_url && (
                        <img 
                          src={selectedTemplate.image_url} 
                          alt="Preview" 
                          className="w-16 h-16 rounded object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="border rounded-lg p-4 bg-gray-900 text-white shadow-lg">
                    <div className="flex items-start gap-3">
                      {selectedTemplate.icon_url && (
                        <div className="w-12 h-12 bg-gray-700 rounded-lg flex items-center justify-center">
                          <Smartphone className="h-6 w-6" />
                        </div>
                      )}
                      <div className="flex-1 space-y-1">
                        <div className="text-sm font-medium">
                          {renderPreview(selectedTemplate.title, previewData)}
                        </div>
                        <div className="text-sm text-gray-300">
                          {renderPreview(selectedTemplate.body, previewData)}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span>Fernando</span>
                          <span>•</span>
                          <span>Now</span>
                        </div>
                      </div>
                      {selectedTemplate.image_url && (
                        <div className="w-16 h-16 bg-gray-700 rounded object-cover flex items-center justify-center">
                          <Image className="h-6 w-6" />
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Template Info */}
              <div className="p-4 border rounded-lg bg-muted/50 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{selectedTemplate.name}</Badge>
                  <Badge variant="secondary">{selectedTemplate.category}</Badge>
                </div>
                {selectedTemplate.action_url && (
                  <div className="text-sm">
                    <strong>Action:</strong> {selectedTemplate.action_url}
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  Platform: {selectedTemplate.platforms.join(', ')}
                  {selectedTemplate.ttl && ` • TTL: ${selectedTemplate.ttl}s`}
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPreviewDialogOpen(false)}>
              Close
            </Button>
            {showTestMode && (
              <Button onClick={() => setIsTestDialogOpen(true)}>
                <Send className="h-4 w-4 mr-2" />
                Test Send
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Send Dialog */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Test Push Notification</DialogTitle>
            <DialogDescription>
              Send a test push notification to verify your template
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label>Test Device</Label>
              <Select defaultValue="web">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="web">Web Browser</SelectItem>
                  <SelectItem value="mobile">Mobile App (iOS)</SelectItem>
                  <SelectItem value="mobile-android">Mobile App (Android)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {selectedTemplate && (
              <div className="p-3 border rounded-lg bg-muted/50 space-y-2">
                <div className="text-sm font-medium">Preview:</div>
                <div className="text-sm">
                  <strong>Title:</strong> {renderPreview(selectedTemplate.title, previewData)}
                </div>
                <div className="text-sm">
                  <strong>Body:</strong> {renderPreview(selectedTemplate.body, previewData)}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  {selectedTemplate.sound_enabled && <Volume2 className="h-4 w-4" />}
                  {selectedTemplate.vibration_enabled && <Vibrate className="h-4 w-4" />}
                  {selectedTemplate.badge_enabled && <Bell className="h-4 w-4" />}
                </div>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTestDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // Simulate test send
              alert(`Test push notification sent using template "${selectedTemplate?.name}"`);
              setIsTestDialogOpen(false);
            }}>
              <Send className="h-4 w-4 mr-2" />
              Send Test
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}