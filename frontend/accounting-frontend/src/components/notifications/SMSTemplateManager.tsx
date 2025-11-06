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
import { Progress } from '@/components/ui/progress';
import { 
  Plus, 
  MessageSquare, 
  Edit, 
  Trash2, 
  Copy, 
  Eye, 
  Send, 
  Save, 
  Phone,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  Template as TemplateIcon,
  Globe,
  Smartphone
} from 'lucide-react';

interface SMSTemplate {
  id: string;
  name: string;
  content: string;
  category: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  character_count: number;
  delivery_stats?: {
    sent: number;
    delivered: number;
    failed: number;
    delivery_rate: number;
  };
  supported_regions?: string[];
  max_length: number;
}

interface SMSTemplateManagerProps {
  onTemplateSelect?: (template: SMSTemplate) => void;
  selectedCategory?: string;
  showTestMode?: boolean;
  defaultRegion?: string;
}

const DEFAULT_SMS_TEMPLATES: SMSTemplate[] = [
  {
    id: 'verification-code',
    name: 'Verification Code',
    content: 'Your Fernando verification code is {{verification_code}}. This code expires in {{expiry_minutes}} minutes. DO NOT share this code with anyone.',
    category: 'verification',
    variables: ['verification_code', 'expiry_minutes', 'user_name'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    character_count: 0,
    max_length: 160,
    supported_regions: ['US', 'CA', 'UK', 'AU']
  },
  {
    id: 'document-ready',
    name: 'Document Ready',
    content: 'Hi {{user_name}}, your document "{{document_name}}" is ready for download. Visit: {{download_url}}',
    category: 'document_processing',
    variables: ['user_name', 'document_name', 'download_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    character_count: 0,
    max_length: 160,
    supported_regions: ['US', 'CA', 'UK', 'AU', 'DE', 'FR']
  },
  {
    id: 'payment-reminder',
    name: 'Payment Reminder',
    content: 'Reminder: Your Fernando subscription payment of ${{amount}} is due on {{due_date}}. Pay securely: {{payment_url}}',
    category: 'billing',
    variables: ['amount', 'due_date', 'payment_url', 'user_name'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system',
    character_count: 0,
    max_length: 160,
    supported_regions: ['US', 'CA', 'UK']
  }
];

export function SMSTemplateManager({ 
  onTemplateSelect, 
  selectedCategory = 'all',
  showTestMode = false,
  defaultRegion = 'US'
}: SMSTemplateManagerProps) {
  const [templates, setTemplates] = useState<SMSTemplate[]>(DEFAULT_SMS_TEMPLATES.map(t => ({
    ...t,
    character_count: t.content.length
  })));
  const [selectedTemplate, setSelectedTemplate] = useState<SMSTemplate | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isPreviewDialogOpen, setIsPreviewDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Partial<SMSTemplate> | null>(null);
  const [previewData, setPreviewData] = useState<Record<string, any>>({});
  const [testPhoneNumber, setTestPhoneNumber] = useState('');
  const [selectedRegion, setSelectedRegion] = useState(defaultRegion);
  const [activeTab, setActiveTab] = useState('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'updated_at' | 'category'>('updated_at');

  const categories = [
    { value: 'all', label: 'All Templates' },
    { value: 'verification', label: 'Verification' },
    { value: 'document_processing', label: 'Document Processing' },
    { value: 'billing', label: 'Billing' },
    { value: 'security', label: 'Security' },
    { value: 'system_alerts', label: 'System Alerts' },
    { value: 'user_onboarding', label: 'User Onboarding' }
  ];

  const regions = [
    { value: 'US', label: 'United States', code: '+1' },
    { value: 'CA', label: 'Canada', code: '+1' },
    { value: 'UK', label: 'United Kingdom', code: '+44' },
    { value: 'AU', label: 'Australia', code: '+61' },
    { value: 'DE', label: 'Germany', code: '+49' },
    { value: 'FR', label: 'France', code: '+33' },
    { value: 'JP', label: 'Japan', code: '+81' }
  ];

  const filteredTemplates = templates
    .filter(template => {
      const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
      const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           template.content.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRegion = !selectedRegion || 
                           !template.supported_regions || 
                           template.supported_regions.includes(selectedRegion);
      return matchesCategory && matchesSearch && matchesRegion;
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
      content: '',
      category: 'system_alerts',
      variables: [],
      is_active: true,
      max_length: 160,
      supported_regions: regions.map(r => r.value)
    });
    setIsCreateDialogOpen(true);
  };

  const handleEditTemplate = (template: SMSTemplate) => {
    setEditingTemplate(template);
    setIsCreateDialogOpen(true);
  };

  const handleSaveTemplate = () => {
    if (!editingTemplate) return;

    const now = new Date().toISOString();
    const templateWithStats = {
      ...editingTemplate,
      character_count: editingTemplate.content?.length || 0,
      updated_at: now
    } as SMSTemplate;
    
    if (selectedTemplate?.id === editingTemplate.id) {
      // Update existing template
      setTemplates(prev => prev.map(template => 
        template.id === editingTemplate.id ? templateWithStats : template
      ));
    } else {
      // Create new template
      const newTemplate: SMSTemplate = {
        ...templateWithStats,
        id: `sms-template-${Date.now()}`,
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

  const handleDuplicateTemplate = (template: SMSTemplate) => {
    const duplicate: SMSTemplate = {
      ...template,
      id: `sms-template-${Date.now()}`,
      name: `${template.name} (Copy)`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'current-user'
    };
    setTemplates(prev => [...prev, duplicate]);
  };

  const handlePreviewTemplate = (template: SMSTemplate) => {
    setSelectedTemplate(template);
    
    // Generate sample preview data
    const sampleData = {
      user_name: 'John Doe',
      verification_code: '123456',
      expiry_minutes: '10',
      document_name: 'invoice_q4_2024.pdf',
      download_url: 'https://app.fernando.com/documents/download/12345',
      amount: '29.99',
      due_date: 'Dec 15, 2024',
      payment_url: 'https://app.fernando.com/billing/pay'
    };
    
    setPreviewData(sampleData);
    setIsPreviewDialogOpen(true);
  };

  const handleTestTemplate = (template: SMSTemplate) => {
    setSelectedTemplate(template);
    setIsTestDialogOpen(true);
  };

  const renderPreview = (content: string, data: Record<string, any>) => {
    let preview = content;
    Object.entries(data).forEach(([key, value]) => {
      const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
      preview = preview.replace(regex, String(value));
    });
    return preview;
  };

  const getCharacterCountColor = (count: number, maxLength: number) => {
    const percentage = (count / maxLength) * 100;
    if (percentage >= 90) return 'text-red-500';
    if (percentage >= 75) return 'text-orange-500';
    return 'text-green-500';
  };

  const getCharacterCountProgress = (count: number, maxLength: number) => {
    return Math.min((count / maxLength) * 100, 100);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">SMS Templates</h2>
          <p className="text-muted-foreground">
            Manage SMS templates for mobile notifications
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
        <Select value={selectedRegion} onValueChange={setSelectedRegion}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {regions.map(region => (
              <SelectItem key={region.value} value={region.value}>
                {region.code} {region.value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={selectedCategory} onValueChange={(value) => onTemplateSelect?.({} as SMSTemplate)}>
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
            <MessageSquare className="h-4 w-4" />
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
                  <Smartphone className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No templates found</h3>
                  <p className="text-muted-foreground mb-4">
                    {searchQuery ? 'Try adjusting your search or filters' : 'Create your first SMS template to get started'}
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
                          <MessageSquare className="h-5 w-5 text-green-500" />
                          {template.name}
                          {!template.is_active && (
                            <Badge variant="secondary" className="text-xs">
                              Inactive
                            </Badge>
                          )}
                        </CardTitle>
                        <CardDescription className="max-w-md">
                          {template.content.length > 100 
                            ? `${template.content.substring(0, 100)}...` 
                            : template.content}
                        </CardDescription>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="outline">
                            {categories.find(c => c.value === template.category)?.label || template.category}
                          </Badge>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <span className={getCharacterCountColor(template.character_count, template.max_length)}>
                              {template.character_count}/{template.max_length}
                            </span>
                            characters
                          </div>
                          <span className="text-xs text-muted-foreground">
                            Updated {new Date(template.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                        {template.supported_regions && (
                          <div className="flex items-center gap-1 mt-1">
                            <Globe className="h-3 w-3 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">
                              {template.supported_regions.join(', ')}
                            </span>
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
                      <div className="grid grid-cols-3 gap-4 text-center">
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
                          <div className="text-2xl font-bold text-red-600">
                            {template.delivery_stats.failed}
                          </div>
                          <div className="text-xs text-muted-foreground">Failed</div>
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
                <CardTitle className="text-sm font-medium">Delivery Rate</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">96.2%</div>
                <p className="text-xs text-muted-foreground">
                  +1.8% from last month
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg. Length</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(templates.reduce((sum, t) => sum + t.character_count, 0) / templates.length)}
                </div>
                <p className="text-xs text-muted-foreground">
                  characters per SMS
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Template Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate?.id === editingTemplate?.id ? 'Edit SMS Template' : 'Create SMS Template'}
            </DialogTitle>
            <DialogDescription>
              Create SMS templates with character limits and variable support
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
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

            {/* SMS Content */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="template-content">SMS Content</Label>
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${getCharacterCountColor(editingTemplate?.content?.length || 0, editingTemplate?.max_length || 160)}`}>
                    {editingTemplate?.content?.length || 0}/{editingTemplate?.max_length || 160}
                  </span>
                  <Progress 
                    value={getCharacterCountProgress(editingTemplate?.content?.length || 0, editingTemplate?.max_length || 160)} 
                    className="w-24 h-2"
                  />
                </div>
              </div>
              <Textarea
                id="template-content"
                value={editingTemplate?.content || ''}
                onChange={(e) => setEditingTemplate(prev => prev ? {...prev, content: e.target.value} : null)}
                placeholder="Enter SMS content..."
                className="min-h-[100px] font-mono text-sm resize-none"
                maxLength={editingTemplate?.max_length || 160}
              />
              <p className="text-xs text-muted-foreground">
                SMS messages are limited to {editingTemplate?.max_length || 160} characters. Consider shorter messages for better delivery rates.
              </p>
            </div>

            {/* Variables */}
            <div className="grid gap-2">
              <Label>Available Variables</Label>
              <div className="grid grid-cols-2 gap-2">
                {['user_name', 'verification_code', 'expiry_minutes', 'document_name', 'download_url', 
                  'amount', 'due_date', 'payment_url', 'account_id', 'plan_name'].map(variable => (
                  <Badge 
                    key={variable} 
                    variant="outline" 
                    className="justify-start p-2 cursor-pointer hover:bg-muted"
                    onClick={() => {
                      if (editingTemplate?.content) {
                        const current = editingTemplate.content;
                        const cursorPos = current.length;
                        const beforeCursor = current.substring(0, cursorPos);
                        const afterCursor = current.substring(cursorPos);
                        const newContent = beforeCursor + `{{${variable}}}` + afterCursor;
                        setEditingTemplate(prev => prev ? {...prev, content: newContent} : null);
                      }
                    }}
                  >
                    {variable}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Variables will be replaced with actual values when the SMS is sent.
              </p>
            </div>

            {/* Settings */}
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="max-length">Max Length</Label>
                <Select 
                  value={String(editingTemplate?.max_length || 160)}
                  onValueChange={(value) => setEditingTemplate(prev => prev ? {...prev, max_length: parseInt(value)} : null)}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="160">160 chars</SelectItem>
                    <SelectItem value="320">320 chars</SelectItem>
                    <SelectItem value="480">480 chars</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Supported Regions</Label>
                <div className="flex flex-wrap gap-2">
                  {regions.map(region => (
                    <Badge 
                      key={region.value} 
                      variant={editingTemplate?.supported_regions?.includes(region.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => {
                        const current = editingTemplate?.supported_regions || [];
                        const updated = current.includes(region.value)
                          ? current.filter(r => r !== region.value)
                          : [...current, region.value];
                        setEditingTemplate(prev => prev ? {...prev, supported_regions: updated} : null);
                      }}
                    >
                      {region.code} {region.value}
                    </Badge>
                  ))}
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
            <DialogTitle>SMS Template Preview</DialogTitle>
            <DialogDescription>
              Preview how your SMS template will look with sample data
            </DialogDescription>
          </DialogHeader>
          
          {selectedTemplate && (
            <div className="space-y-6">
              {/* Preview Header */}
              <div className="p-4 border rounded-lg bg-muted/50">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{selectedTemplate.name}</Badge>
                    <Badge variant="secondary">{selectedTemplate.category}</Badge>
                    <Badge variant="outline" className="text-xs">
                      {selectedTemplate.character_count} chars
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Region:</span>
                    <span className="text-sm font-medium">{selectedRegion}</span>
                  </div>
                </div>
              </div>

              {/* SMS Preview */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">SMS Preview ({selectedRegion})</span>
                </div>
                
                <div className="relative">
                  <div className="p-4 border-2 border-green-500 rounded-lg bg-green-50 max-w-sm">
                    <div className="space-y-2">
                      <div className="text-xs text-green-600 flex items-center gap-1">
                        <Smartphone className="h-3 w-3" />
                        +1 555-0123
                        <span className="text-green-400">•</span>
                        Now
                      </div>
                      <div className="text-sm text-gray-800 whitespace-pre-wrap">
                        {renderPreview(selectedTemplate.content, previewData)}
                      </div>
                    </div>
                  </div>
                  
                  {/* Character count indicator */}
                  <div className="absolute -bottom-2 -right-2">
                    <Badge 
                      variant={getCharacterCountProgress(selectedTemplate.character_count, selectedTemplate.max_length) > 80 ? "destructive" : "secondary"}
                      className="text-xs"
                    >
                      {selectedTemplate.character_count}/{selectedTemplate.max_length}
                    </Badge>
                  </div>
                </div>

                {selectedTemplate.supported_regions && !selectedTemplate.supported_regions.includes(selectedRegion) && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      This template is not configured for {regions.find(r => r.value === selectedRegion)?.label}.
                    </AlertDescription>
                  </Alert>
                )}
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
            <DialogTitle>Send Test SMS</DialogTitle>
            <DialogDescription>
              Send a test SMS to verify your template
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="test-phone">Phone Number</Label>
              <div className="flex gap-2">
                <Select value={selectedRegion} onValueChange={setSelectedRegion}>
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {regions.map(region => (
                      <SelectItem key={region.value} value={region.value}>
                        {region.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="test-phone"
                  placeholder="Enter phone number"
                  value={testPhoneNumber}
                  onChange={(e) => setTestPhoneNumber(e.target.value)}
                  className="flex-1"
                />
              </div>
            </div>
            
            {selectedTemplate && (
              <div className="p-3 border rounded-lg bg-muted/50">
                <div className="text-sm font-medium mb-1">Preview Message:</div>
                <div className="text-sm text-muted-foreground">
                  {renderPreview(selectedTemplate.content, previewData)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {selectedTemplate.character_count} characters
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
              alert(`Test SMS sent to +${regions.find(r => r.value === selectedRegion)?.code} ${testPhoneNumber} using template "${selectedTemplate?.name}"`);
              setIsTestDialogOpen(false);
              setTestPhoneNumber('');
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