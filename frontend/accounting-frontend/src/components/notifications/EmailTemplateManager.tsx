import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Plus, 
  Mail, 
  Edit, 
  Trash2, 
  Copy, 
  Eye, 
  Send, 
  Save, 
  X, 
  FileText,
  Template as TemplateIcon,
  Clock,
  CheckCircle,
  AlertCircle,
  Code,
  Image,
  Link
} from 'lucide-react';

interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  content: string;
  html_content?: string;
  category: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  preview_data?: Record<string, any>;
  delivery_stats?: {
    sent: number;
    delivered: number;
    opened: number;
    clicked: number;
    bounced: number;
  };
}

interface EmailTemplateManagerProps {
  onTemplateSelect?: (template: EmailTemplate) => void;
  selectedCategory?: string;
  showTestMode?: boolean;
}

const DEFAULT_TEMPLATES: EmailTemplate[] = [
  {
    id: 'welcome-email',
    name: 'Welcome Email',
    subject: 'Welcome to Fernando Platform - Get Started Today!',
    content: 'Welcome {{user_name}}!\n\nThank you for joining the Fernando platform. Your account has been successfully created.\n\nYour account details:\n- Email: {{user_email}}\n- Account ID: {{account_id}}\n- Plan: {{plan_name}}\n\nGet started by visiting your dashboard: {{dashboard_url}}\n\nBest regards,\nThe Fernando Team',
    html_content: `<html><body><div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;"><h1 style="color: #2563eb;">Welcome {{user_name}}!</h1><p>Thank you for joining the Fernando platform. Your account has been successfully created.</p><div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;"><h3>Your account details:</h3><ul><li><strong>Email:</strong> {{user_email}}</li><li><strong>Account ID:</strong> {{account_id}}</li><li><strong>Plan:</strong> {{plan_name}}</li></ul></div><p>Get started by visiting your <a href="{{dashboard_url}}" style="color: #2563eb;">dashboard</a>.</p><p>Best regards,<br>The Fernando Team</p></div></body></html>`,
    category: 'user_onboarding',
    variables: ['user_name', 'user_email', 'account_id', 'plan_name', 'dashboard_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system'
  },
  {
    id: 'document-processing-complete',
    name: 'Document Processing Complete',
    subject: 'Your document "{{document_name}}" has been processed successfully',
    content: 'Hi {{user_name}},\n\nGreat news! Your document "{{document_name}}" has been successfully processed.\n\nDocument Details:\n- File: {{document_name}}\n- Processing Time: {{processing_time}}\n- Status: Completed\n- Download: {{download_url}}\n\nYou can access your processed document through your dashboard.\n\nBest regards,\nFernando Team',
    category: 'document_processing',
    variables: ['user_name', 'document_name', 'processing_time', 'download_url'],
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: 'system'
  }
];

export function EmailTemplateManager({ 
  onTemplateSelect, 
  selectedCategory = 'all',
  showTestMode = false 
}: EmailTemplateManagerProps) {
  const [templates, setTemplates] = useState<EmailTemplate[]>(DEFAULT_TEMPLATES);
  const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isPreviewDialogOpen, setIsPreviewDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Partial<EmailTemplate> | null>(null);
  const [previewData, setPreviewData] = useState<Record<string, any>>({});
  const [testEmail, setTestEmail] = useState('');
  const [activeTab, setActiveTab] = useState('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'updated_at' | 'category'>('updated_at');

  const categories = [
    { value: 'all', label: 'All Templates' },
    { value: 'user_onboarding', label: 'User Onboarding' },
    { value: 'document_processing', label: 'Document Processing' },
    { value: 'verification', label: 'Verification' },
    { value: 'billing', label: 'Billing' },
    { value: 'system_alerts', label: 'System Alerts' },
    { value: 'security', label: 'Security' }
  ];

  const filteredTemplates = templates
    .filter(template => {
      const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
      const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           template.subject.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
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
      subject: '',
      content: '',
      html_content: '',
      category: 'system_alerts',
      variables: [],
      is_active: true
    });
    setIsCreateDialogOpen(true);
  };

  const handleEditTemplate = (template: EmailTemplate) => {
    setEditingTemplate(template);
    setIsCreateDialogOpen(true);
  };

  const handleSaveTemplate = () => {
    if (!editingTemplate) return;

    const now = new Date().toISOString();
    
    if (selectedTemplate?.id === editingTemplate.id) {
      // Update existing template
      setTemplates(prev => prev.map(template => 
        template.id === editingTemplate.id 
          ? { ...editingTemplate, updated_at: now } as EmailTemplate
          : template
      ));
    } else {
      // Create new template
      const newTemplate: EmailTemplate = {
        ...editingTemplate,
        id: `template-${Date.now()}`,
        created_at: now,
        updated_at: now,
        created_by: 'current-user'
      } as EmailTemplate;
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

  const handleDuplicateTemplate = (template: EmailTemplate) => {
    const duplicate: EmailTemplate = {
      ...template,
      id: `template-${Date.now()}`,
      name: `${template.name} (Copy)`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'current-user'
    };
    setTemplates(prev => [...prev, duplicate]);
  };

  const handlePreviewTemplate = (template: EmailTemplate) => {
    setSelectedTemplate(template);
    
    // Generate sample preview data
    const sampleData = {
      user_name: 'John Doe',
      user_email: 'john.doe@example.com',
      account_id: 'ACC-12345',
      plan_name: 'Professional Plan',
      dashboard_url: 'https://app.fernando.com/dashboard',
      document_name: 'invoice_q4_2024.pdf',
      processing_time: '2 minutes 34 seconds',
      download_url: 'https://app.fernando.com/documents/download/12345'
    };
    
    setPreviewData(sampleData);
    setIsPreviewDialogOpen(true);
  };

  const handleTestTemplate = (template: EmailTemplate) => {
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Email Templates</h2>
          <p className="text-muted-foreground">
            Manage email templates for automated notifications
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
        <Select value={selectedCategory} onValueChange={(value) => onTemplateSelect?.({} as EmailTemplate)}>
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
            <FileText className="h-4 w-4" />
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
                  <TemplateIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No templates found</h3>
                  <p className="text-muted-foreground mb-4">
                    {searchQuery ? 'Try adjusting your search or filters' : 'Create your first email template to get started'}
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
                      <div className="space-y-1">
                        <CardTitle className="flex items-center gap-2">
                          <Mail className="h-5 w-5 text-blue-500" />
                          {template.name}
                          {!template.is_active && (
                            <Badge variant="secondary" className="text-xs">
                              Inactive
                            </Badge>
                          )}
                        </CardTitle>
                        <CardDescription>
                          {template.subject}
                        </CardDescription>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="outline">
                            {categories.find(c => c.value === template.category)?.label || template.category}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            Updated {new Date(template.updated_at).toLocaleDateString()}
                          </span>
                        </div>
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
                      <div className="grid grid-cols-5 gap-4 text-center">
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
                          <div className="text-2xl font-bold text-purple-600">
                            {template.delivery_stats.opened}
                          </div>
                          <div className="text-xs text-muted-foreground">Opened</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-orange-600">
                            {template.delivery_stats.clicked}
                          </div>
                          <div className="text-xs text-muted-foreground">Clicked</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-red-600">
                            {template.delivery_stats.bounced}
                          </div>
                          <div className="text-xs text-muted-foreground">Bounced</div>
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
                <div className="text-2xl font-bold">98.5%</div>
                <p className="text-xs text-muted-foreground">
                  +2.1% from last month
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Open Rate</CardTitle>
                <Eye className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">24.7%</div>
                <p className="text-xs text-muted-foreground">
                  Industry average: 18%
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Template Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate?.id === editingTemplate?.id ? 'Edit Email Template' : 'Create Email Template'}
            </DialogTitle>
            <DialogDescription>
              Create or edit email templates with HTML support and dynamic variables
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="max-h-[60vh]">
            <div className="space-y-6 pr-6">
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
                  <Label htmlFor="template-subject">Email Subject</Label>
                  <Input
                    id="template-subject"
                    value={editingTemplate?.subject || ''}
                    onChange={(e) => setEditingTemplate(prev => prev ? {...prev, subject: e.target.value} : null)}
                    placeholder="Enter email subject line"
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

              <Separator />

              {/* Content Editors */}
              <Tabs defaultValue="plain-text">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="plain-text">Plain Text</TabsTrigger>
                  <TabsTrigger value="html">HTML</TabsTrigger>
                  <TabsTrigger value="variables">Variables</TabsTrigger>
                </TabsList>
                
                <TabsContent value="plain-text" className="space-y-4">
                  <div className="grid gap-2">
                    <Label>Content (Plain Text)</Label>
                    <Textarea
                      value={editingTemplate?.content || ''}
                      onChange={(e) => setEditingTemplate(prev => prev ? {...prev, content: e.target.value} : null)}
                      placeholder="Enter email content in plain text format..."
                      className="min-h-[200px] font-mono"
                    />
                  </div>
                </TabsContent>
                
                <TabsContent value="html" className="space-y-4">
                  <div className="grid gap-2">
                    <Label>HTML Content</Label>
                    <Textarea
                      value={editingTemplate?.html_content || ''}
                      onChange={(e) => setEditingTemplate(prev => prev ? {...prev, html_content: e.target.value} : null)}
                      placeholder="Enter HTML content with styling..."
                      className="min-h-[200px] font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">
                      HTML will be used if available, otherwise plain text content will be sent
                    </p>
                  </div>
                </TabsContent>
                
                <TabsContent value="variables" className="space-y-4">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Use double curly braces for variables: {'{{variable_name}}'}
                    </AlertDescription>
                  </Alert>
                  
                  <div className="grid gap-2">
                    <Label>Available Variables</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {['user_name', 'user_email', 'account_id', 'plan_name', 'dashboard_url', 
                        'document_name', 'processing_time', 'download_url', 'verification_url',
                        'payment_amount', 'subscription_date', 'reset_url'].map(variable => (
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
                  </div>
                </TabsContent>
              </Tabs>

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
          </ScrollArea>
          
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
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Template Preview</DialogTitle>
            <DialogDescription>
              Preview how your email template will look with sample data
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
                  </div>
                  <div>
                    <div className="text-sm font-medium">Subject:</div>
                    <div className="text-muted-foreground">
                      {renderPreview(selectedTemplate.subject, previewData)}
                    </div>
                  </div>
                </div>
              </div>

              <Tabs defaultValue="plain-text">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="plain-text">Plain Text</TabsTrigger>
                  <TabsTrigger value="html">HTML Preview</TabsTrigger>
                </TabsList>
                
                <TabsContent value="plain-text">
                  <div className="p-4 border rounded-lg bg-background">
                    <pre className="whitespace-pre-wrap font-sans text-sm">
                      {renderPreview(selectedTemplate.content, previewData)}
                    </pre>
                  </div>
                </TabsContent>
                
                <TabsContent value="html">
                  {selectedTemplate.html_content ? (
                    <div className="p-4 border rounded-lg bg-background">
                      <div 
                        dangerouslySetInnerHTML={{
                          __html: renderPreview(selectedTemplate.html_content, previewData)
                        }}
                      />
                    </div>
                  ) : (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        No HTML content available for this template
                      </AlertDescription>
                    </Alert>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPreviewDialogOpen(false)}>
              Close
            </Button>
            <Button onClick={() => setIsTestDialogOpen(true)}>
              <Send className="h-4 w-4 mr-2" />
              Test Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Send Dialog */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Test Email</DialogTitle>
            <DialogDescription>
              Send a test email to verify your template
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="test-email">Test Email Address</Label>
              <Input
                id="test-email"
                type="email"
                placeholder="Enter email address"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
              />
            </div>
            
            {selectedTemplate && (
              <Alert>
                <Send className="h-4 w-4" />
                <AlertDescription>
                  This will send an email using the "{selectedTemplate.name}" template to the specified address.
                </AlertDescription>
              </Alert>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTestDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // Simulate test send
              alert(`Test email sent to ${testEmail} using template "${selectedTemplate?.name}"`);
              setIsTestDialogOpen(false);
              setTestEmail('');
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