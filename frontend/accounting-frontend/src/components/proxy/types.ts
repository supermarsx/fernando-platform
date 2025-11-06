// Proxy Management System Type Definitions

export interface ProxyServer {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'restarting' | 'maintenance' | 'error';
  health: number;
  uptime: string;
  lastRestart: string;
  version: string;
  region: string;
  load: number;
  responseTime: number;
  errorRate: number;
  activeConnections: number;
  configuration: ProxyServerConfiguration;
  resources: ServerResources;
  performance: ServerPerformance;
}

export interface ProxyServerConfiguration {
  port: number;
  ssl: boolean;
  maxConnections: number;
  timeout: number;
  rateLimit: number;
  cacheEnabled: boolean;
  compression: boolean;
}

export interface ServerResources {
  cpu: number;
  memory: number;
  disk: number;
}

export interface ServerPerformance {
  requestsPerSecond: number;
  averageResponseTime: number;
  errorRate: number;
  throughput: number;
}

export interface ProxyMetrics {
  totalRequests: number;
  successRate: number;
  averageResponseTime: number;
  cacheHitRatio: number;
  activeConnections: number;
  errorRate: number;
  throughput: number;
}

// API Key Management Types
export interface ApiKey {
  id: string;
  name: string;
  key: string;
  masked: string;
  status: 'active' | 'inactive' | 'expired' | 'revoked';
  createdAt: string;
  lastUsed: string;
  expiresAt: string;
  permissions: string[];
  usage: ApiKeyUsage;
  rateLimit: ApiKeyRateLimit;
  ipWhitelist: string[];
  ipBlacklist: string[];
}

export interface ApiKeyUsage {
  totalRequests: number;
  dailyLimit: number;
  monthlyLimit: number;
  currentDaily: number;
  currentMonthly: number;
  costThisMonth: number;
}

export interface ApiKeyRateLimit {
  requestsPerMinute: number;
  requestsPerHour: number;
  requestsPerDay: number;
}

// Load Balancer Types
export interface LoadBalancerConfig {
  algorithm: 'round-robin' | 'least-connections' | 'weighted' | 'ip-hash';
  healthCheck: HealthCheckConfig;
  sticky: StickySessionConfig;
  failover: FailoverConfig;
  advanced: AdvancedLoadBalancerConfig;
}

export interface HealthCheckConfig {
  enabled: boolean;
  interval: number;
  timeout: number;
  path: string;
  expectedStatus: number;
  retries: number;
}

export interface StickySessionConfig {
  enabled: boolean;
  cookieName: string;
  ttl: number;
}

export interface FailoverConfig {
  enabled: boolean;
  primaryServers: string[];
  backupServers: string[];
  failoverTimeout: number;
}

export interface AdvancedLoadBalancerConfig {
  maxConnections: number;
  connectionTimeout: number;
  keepAlive: boolean;
  compression: boolean;
  bufferSize: number;
}

export interface BackendServer {
  id: string;
  name: string;
  url: string;
  weight: number;
  health: 'healthy' | 'unhealthy' | 'unknown';
  status: 'active' | 'inactive' | 'draining';
  currentConnections: number;
  totalRequests: number;
  errorRate: number;
  responseTime: number;
  lastHealthCheck: string;
}

// Rate Limiting Types
export interface RateLimitRule {
  id: string;
  name: string;
  type: 'global' | 'api-key' | 'ip' | 'user' | 'endpoint';
  enabled: boolean;
  limits: RateLimitConfig;
  scope: RateLimitScope;
  burstLimit?: number;
  costPerRequest?: number;
  priority: number;
  strategy: 'fixed' | 'sliding' | 'token-bucket';
  description: string;
}

export interface RateLimitConfig {
  perMinute: number;
  perHour: number;
  perDay: number;
  perMonth: number;
}

export interface RateLimitScope {
  apiKeys?: string[];
  ips?: string[];
  users?: string[];
  endpoints?: string[];
  paths?: string[];
}

export interface QuotaSettings {
  dailyBudget?: number;
  monthlyBudget?: number;
  alerting: QuotaAlerting;
  enforcement: QuotaEnforcement;
}

export interface QuotaAlerting {
  enabled: boolean;
  thresholds: {
    warning: number;
    critical: number;
  };
  email?: string[];
}

export interface QuotaEnforcement {
  mode: 'warn' | 'block' | 'upgrade-required';
  gracePeriod: number;
}

export interface RateLimitStats {
  totalRequests: number;
  blockedRequests: number;
  averageRate: number;
  peakRate: number;
  costToday: number;
  costThisMonth: number;
  mostRestrictedEndpoints: Array<{
    endpoint: string;
    blockCount: number;
    blockRate: number;
  }>;
  topBlockedIPs: Array<{
    ip: string;
    blockCount: number;
    blockRate: number;
  }>;
}

// Circuit Breaker Types
export interface CircuitBreakerConfig {
  id: string;
  name: string;
  enabled: boolean;
  service: string;
  endpoint?: string;
  thresholds: CircuitBreakerThresholds;
  timeouts: CircuitBreakerTimeouts;
  strategy: 'failure-rate' | 'response-time' | 'consecutive-failures';
  description: string;
}

export interface CircuitBreakerThresholds {
  failureRate: number;
  responseTime: number;
  consecutiveFailures: number;
  halfOpenMaxCalls: number;
  timeout: number;
}

export interface CircuitBreakerTimeouts {
  resetTimeout: number;
  failureTimeout: number;
}

export interface CircuitBreakerState {
  id: string;
  name: string;
  currentState: 'closed' | 'open' | 'half-open';
  lastStateChange: string;
  failureCount: number;
  successCount: number;
  totalCalls: number;
  currentFailureRate: number;
  averageResponseTime: number;
  nextAttemptTime?: string;
  statistics: CircuitBreakerStatistics;
}

export interface CircuitBreakerStatistics {
  callsThisHour: number;
  failuresThisHour: number;
  averageResponseTime: number;
  lastFailure?: string;
  lastSuccess?: string;
}

// Performance Monitoring Types
export interface PerformanceMetrics {
  timestamp: string;
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  network: NetworkMetrics;
  requests: RequestMetrics;
  cache: CacheMetrics;
  database: DatabaseMetrics;
}

export interface CpuMetrics {
  usage: number;
  load: number;
}

export interface MemoryMetrics {
  used: number;
  total: number;
  percentage: number;
}

export interface NetworkMetrics {
  bytesIn: number;
  bytesOut: number;
  packetsIn: number;
  packetsOut: number;
  errors: number;
}

export interface RequestMetrics {
  total: number;
  successful: number;
  failed: number;
  averageResponseTime: number;
  throughput: number;
  concurrency: number;
}

export interface CacheMetrics {
  hitRate: number;
  misses: number;
  evictions: number;
  size: number;
}

export interface DatabaseMetrics {
  connections: number;
  queryTime: number;
  queriesPerSecond: number;
  slowQueries: number;
}

export interface EndpointMetrics {
  path: string;
  method: string;
  averageResponseTime: number;
  requestCount: number;
  errorRate: number;
  throughput: number;
}

// Security Management Types
export interface SecurityPolicy {
  id: string;
  name: string;
  enabled: boolean;
  type: 'ip-whitelist' | 'ip-blacklist' | 'rate-limit' | 'rate-limit-advanced' | 'custom';
  rules: SecurityRule[];
  priority: number;
  description: string;
}

export interface SecurityRule {
  id: string;
  pattern: string;
  description: string;
  action: 'allow' | 'deny' | 'monitor' | 'rate-limit';
  weight: number;
}

export interface SecurityEvent {
  id: string;
  timestamp: string;
  type: 'authentication-failure' | 'rate-limit-exceeded' | 'suspicious-activity' | 'ip-blocked' | 'security-policy-violation' | 'ddos-attempt';
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: SecurityEventSource;
  details: SecurityEventDetails;
  resolved: boolean;
  resolvedAt?: string;
  resolvedBy?: string;
}

export interface SecurityEventSource {
  ip: string;
  userAgent?: string;
  userId?: string;
  apiKey?: string;
}

export interface SecurityEventDetails {
  message: string;
  endpoint?: string;
  method?: string;
  payload?: any;
  riskScore: number;
}

export interface ThreatDetection {
  id: string;
  type: 'ddos' | 'brute-force' | 'sql-injection' | 'xss' | 'suspicious-pattern' | 'anomalous-behavior';
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  description: string;
  detectedAt: string;
  blocked: boolean;
  confidence: number;
  indicators: string[];
  mitigation: string;
}

// Admin Control Types
export interface BackupConfig {
  id: string;
  name: string;
  timestamp: string;
  size: number;
  type: 'full' | 'incremental';
  status: 'success' | 'failed' | 'in-progress';
  description?: string;
}

export interface MaintenanceWindow {
  id: string;
  title: string;
  description: string;
  startTime: string;
  endTime: string;
  affectedServices: string[];
  status: 'scheduled' | 'active' | 'completed' | 'cancelled';
  notificationSent: boolean;
}

// Alert and Notification Types
export interface Alert {
  id: string;
  type: 'performance' | 'availability' | 'error' | 'resource';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface ProxyWebSocketMessage extends WebSocketMessage {
  type: 'serverUpdate' | 'metrics' | 'alert' | 'circuitBreaker' | 'securityEvent';
  serverUpdate?: any;
  metrics?: any;
  alert?: Alert;
  circuitBreaker?: CircuitBreakerState;
  securityEvent?: SecurityEvent;
}

// Configuration Export/Import Types
export interface ProxyConfig {
  version: string;
  servers: ProxyServer[];
  loadBalancer: LoadBalancerConfig;
  rateLimits: RateLimitRule[];
  securityPolicies: SecurityPolicy[];
  circuitBreakers: CircuitBreakerConfig[];
  quotas: QuotaSettings;
  createdAt: string;
  metadata?: Record<string, any>;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

// Filter and Query Types
export interface QueryFilters {
  [key: string]: any;
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

// Form Types
export interface CreateApiKeyForm {
  name: string;
  permissions: string[];
  dailyLimit: number;
  monthlyLimit: number;
  expiresInDays: number;
  rateLimit: {
    perMinute: number;
    perHour: number;
    perDay: number;
  };
  ipWhitelist: string[];
  ipBlacklist: string[];
}

export interface CreateRateLimitRuleForm {
  name: string;
  type: RateLimitRule['type'];
  limits: RateLimitConfig;
  scope: RateLimitScope;
  burstLimit: number;
  costPerRequest: number;
  priority: number;
  strategy: RateLimitRule['strategy'];
  description: string;
}

export interface CreateCircuitBreakerForm {
  name: string;
  service: string;
  endpoint?: string;
  strategy: CircuitBreakerConfig['strategy'];
  thresholds: CircuitBreakerThresholds;
  timeouts: CircuitBreakerTimeouts;
  description: string;
}

export interface ScheduleMaintenanceForm {
  title: string;
  description: string;
  startTime: string;
  endTime: string;
  affectedServices: string[];
}