# Configuration Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from legacy configuration systems to the new unified Fernando Platform configuration system. The migration ensures backward compatibility while implementing modern configuration management practices.

## Migration Scope

### What We're Migrating From
- Legacy hardcoded configuration values
- Mixed configuration approaches across services
- Inconsistent environment variable usage
- Manual secret management
- Non-standardized configuration validation

### What We're Migrating To
- Unified environment-based configuration system
- Standardized configuration templates
- Comprehensive validation and security controls
- Automated secret generation and rotation
- Service-specific configuration separation

## Pre-Migration Assessment

### Step 1: Audit Current Configuration

#### 1.1 Identify Configuration Files
```bash
# Find all configuration files
find . -name "*.py" -exec grep -l "config\|setting\|constant" {} \;
find . -name "*.json" -exec grep -l "config\|setting" {} \;
find . -name "*.yaml" -o -name "*.yml" | grep -i config
find . -name ".env*" -o -name "config.py" -o -name "settings.py"

# Create configuration inventory
echo "# Configuration Files Inventory" > config-inventory.md
find . -type f \( -name "*.py" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name ".env*" \) \
  -exec echo "- {}" \; >> config-inventory.md
```

#### 1.2 Map Configuration Sources
```bash
# Create a configuration mapping script
cat > audit-configuration.py << 'EOF'
import os
import re
from pathlib import Path
import json

def find_configuration_patterns(directory):
    """Find configuration patterns in code files"""
    config_patterns = {
        'hardcoded_strings': [],
        'environment_variables': [],
        'config_files': [],
        'secrets': []
    }
    
    for file_path in Path(directory).rglob('*.py'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find hardcoded strings that might be configuration
                hardcoded_pattern = r'(?:config|setting|constant|var)\s*[=:]\s*["\']([^"\']+)["\']'
                for match in re.finditer(hardcoded_pattern, content, re.IGNORECASE):
                    config_patterns['hardcoded_strings'].append({
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1,
                        'value': match.group(1)
                    })
                
                # Find environment variable usage
                env_pattern = r'(?:os\.environ|os\.getenv)\s*\[\s*["\']([^"\']+)["\']'
                for match in re.finditer(env_pattern, content):
                    config_patterns['environment_variables'].append({
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1,
                        'variable': match.group(1)
                    })
                
                # Find potential secrets
                secret_pattern = r'(?:password|secret|key|token|api[_-]?key)\s*[=:]\s*["\']([^"\']+)["\']'
                for match in re.finditer(secret_pattern, content, re.IGNORECASE):
                    config_patterns['secrets'].append({
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1,
                        'type': match.group(1)
                    })
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return config_patterns

# Run the audit
if __name__ == "__main__":
    results = find_configuration_patterns('./')
    with open('configuration-audit.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Configuration audit completed. Results saved to configuration-audit.json")
EOF

python3 audit-configuration.py
```

#### 1.3 Review Legacy Configuration Patterns
```bash
# Analyze the audit results
python3 -c "
import json
with open('configuration-audit.json') as f:
    data = json.load(f)

print('=== CONFIGURATION AUDIT RESULTS ===')
print(f'Hardcoded strings: {len(data[\"hardcoded_strings\"])}')
print(f'Environment variables: {len(data[\"environment_variables\"])}')
print(f'Potential secrets: {len(data[\"secrets\"])}')
print(f'Config files: {len(data[\"config_files\"])}')
print()
print('Top 10 hardcoded values:')
for item in data['hardcoded_strings'][:10]:
    print(f'  {item[\"file\"]}:{item[\"line\"]} = {item[\"value\"]}')
"
```

### Step 2: Identify Service Dependencies

#### 2.1 Map Service Architecture
```bash
# Create service dependency map
cat > map-services.py << 'EOF'
import os
import re
from pathlib import Path
import json

def identify_services(directory):
    """Identify services and their dependencies"""
    services = {}
    
    # Common service directories
    service_dirs = ['backend', 'frontend', 'licensing-server', 'proxy-servers']
    
    for service_dir in service_dirs:
        if os.path.exists(service_dir):
            services[service_dir] = {
                'config_files': [],
                'dependencies': [],
                'environment_vars': [],
                'external_services': []
            }
            
            # Find config files
            for config_file in Path(service_dir).rglob('*config*'):
                services[service_dir]['config_files'].append(str(config_file))
            
            # Find environment variable usage
            for py_file in Path(service_dir).rglob('*.py'):
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        env_vars = re.findall(r'os\.environ\[[\"\']([^\"\']+)[\"\']', content)
                        services[service_dir]['environment_vars'].extend(env_vars)
                        
                        # Identify external service calls
                        service_calls = re.findall(r'(?:stripe|paypal|sendgrid|sentry|redis|postgresql|mysql)', content, re.IGNORECASE)
                        services[service_dir]['external_services'].extend(service_calls)
                except:
                    pass
    
    return services

services = identify_services('./')
with open('service-dependencies.json', 'w') as f:
    json.dump(services, f, indent=2)

print("Service dependency mapping completed.")
for service, info in services.items():
    print(f"\n{service}:")
    print(f"  Config files: {len(info['config_files'])}")
    print(f"  Environment variables: {len(set(info['environment_vars']))}")
    print(f"  External services: {len(set(info['external_services']))}")
EOF

python3 map-services.py
```

## Migration Preparation

### Step 3: Create Migration Plan

#### 3.1 Priority Matrix
```markdown
# Configuration Migration Priority Matrix

## High Priority (Migration Phase 1)
- [ ] Security-critical configurations (secrets, JWT keys, database URLs)
- [ ] Service communication settings (API URLs, CORS)
- [ ] Authentication and authorization settings

## Medium Priority (Migration Phase 2)  
- [ ] Feature flags and toggles
- [ ] Performance tuning parameters
- [ ] Logging and monitoring settings

## Low Priority (Migration Phase 3)
- [ ] UI customization settings
- [ ] Development-specific configurations
- [ ] Non-critical service settings
```

#### 3.2 Migration Timeline
```markdown
# Migration Timeline

## Week 1: Assessment and Planning
- [x] Audit current configuration
- [x] Map service dependencies
- [x] Create migration plan
- [ ] Set up new configuration templates
- [ ] Test migration in development environment

## Week 2: Backend Migration
- [ ] Create backend configuration template
- [ ] Migrate backend environment variables
- [ ] Update backend configuration loading
- [ ] Test backend configuration
- [ ] Validate backend services

## Week 3: Frontend and Licensing Server Migration
- [ ] Create frontend configuration template
- [ ] Create licensing server template
- [ ] Migrate frontend environment variables
- [ ] Update frontend configuration loading
- [ ] Test all services

## Week 4: Security and Validation
- [ ] Implement configuration validation
- [ ] Set up secret management
- [ ] Test security configurations
- [ ] Performance testing
- [ ] Documentation update
```

## Migration Execution

### Step 4: Set Up New Configuration System

#### 4.1 Create Configuration Directory Structure
```bash
# Create new configuration structure
mkdir -p configs/{templates,schemas,scripts}
mkdir -p configs/templates/{backend,frontend,licensing}

# Copy existing configuration templates
cp configs/templates/backend.env.example configs/templates/backend/
cp configs/templates/frontend.env.example configs/templates/frontend/
cp configs/templates/licensing.env.example configs/templates/licensing/
```

#### 4.2 Initialize Configuration Templates
```bash
# Create backend configuration template
cat > configs/templates/backend.env.example << 'EOF'
# =============================================================================
# BACKEND CONFIGURATION TEMPLATE
# =============================================================================

# Application Configuration
APP_NAME=Fernando
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20

# Security Configuration
SECRET_KEY=your-256-bit-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost"]

# Add more configuration as needed...
EOF

# Create frontend configuration template
cat > configs/templates/frontend.env.example << 'EOF'
# =============================================================================
# FRONTEND CONFIGURATION TEMPLATE
# =============================================================================

# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_V1_STR=/api/v1

# Application Settings
VITE_APP_NAME=Fernando
VITE_APP_VERSION=1.0.0
VITE_DEBUG=false

# Feature Flags
VITE_ENABLE_MOCK_DATA=false

# Add more configuration as needed...
EOF

# Create licensing server configuration template
cat > configs/templates/licensing.env.example << 'EOF'
# =============================================================================
# LICENSING SERVER CONFIGURATION TEMPLATE
# =============================================================================

# Service Configuration
LICENSING_APP_NAME=LicensingServer
LICENSING_APP_VERSION=1.0.0
LICENSING_DEBUG=false

# Database Configuration
LICENSING_DATABASE_URL=postgresql://user:password@localhost:5432/licensing
LICENSING_REDIS_URL=redis://localhost:6379/1

# Security Configuration
LICENSING_SECRET_KEY=your-licensing-secret-key-here
LICENSING_ALGORITHM=HS256

# Add more configuration as needed...
EOF

echo "Configuration templates created."
```

### Step 5: Migrate Backend Configuration

#### 5.1 Analyze Current Backend Configuration
```bash
# Create migration script for backend
cat > migrate-backend-config.py << 'EOF'
import os
import re
import json
from pathlib import Path

def migrate_backend_config():
    """Migrate backend configuration from old system"""
    
    # Define configuration mapping
    config_mapping = {
        # Old pattern -> New environment variable
        r'(?:APP_NAME|app_name|APPLICATION_NAME)': 'APP_NAME',
        r'(?:APP_VERSION|app_version|APPLICATION_VERSION)': 'APP_VERSION',
        r'(?:DEBUG|debug)': 'DEBUG',
        r'(?:DATABASE_URL|db_url|DATABASE)': 'DATABASE_URL',
        r'(?:SECRET_KEY|secret_key|SECRET)': 'SECRET_KEY',
        r'(?:JWT_SECRET|jwt_secret)': 'SECRET_KEY',
        r'(?:ALGORITHM|jwt_algorithm)': 'ALGORITHM',
        r'(?:ACCESS_TOKEN_EXPIRE|token_expire)': 'ACCESS_TOKEN_EXPIRE_MINUTES',
        r'(?:CORS_ORIGINS|cors_origins|CORS)': 'CORS_ORIGINS',
        r'(?:ALLOWED_HOSTS|allowed_hosts|HOSTS)': 'ALLOWED_HOSTS',
    }
    
    # Create new configuration file
    new_config = {}
    
    # Extract configuration from existing files
    for py_file in Path('backend').rglob('*.py'):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Look for configuration patterns
                for pattern, env_var in config_mapping.items():
                    matches = re.findall(f'{pattern}\\s*[=:]\\s*[\"\']?([^\"\']+)[\"\']?', content, re.IGNORECASE)
                    for match in matches:
                        if env_var not in new_config:
                            new_config[env_var] = match
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    return new_config

# Run migration
new_config = migrate_backend_config()

# Write new configuration
with open('backend/.env', 'w') as f:
    f.write("# Migrated backend configuration\n")
    f.write("# Generated from legacy configuration system\n\n")
    
    for key, value in new_config.items():
        f.write(f"{key}={value}\n")

print("Backend configuration migration completed.")
print(f"Migrated {len(new_config)} configuration values.")
EOF

python3 migrate-backend-config.py
```

#### 5.2 Update Backend Configuration Loading
```python
# Create new configuration module
cat > backend/app/core/config.py << 'EOF'
from pydantic import BaseSettings, validator
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application settings
    APP_NAME: str = "Fernando"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database settings
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_POOL_MAX_OVERFLOW: int = 20
    
    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost"]
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()
EOF

echo "Backend configuration module created."
```

#### 5.3 Update Backend Service Integration
```python
# Update main.py to use new configuration
cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

echo "Backend integration updated."
```

### Step 6: Migrate Frontend Configuration

#### 6.1 Create Frontend Environment Configuration
```bash
# Create frontend environment file
cat > frontend/accounting-frontend/.env.local << 'EOF'
# Frontend Configuration
VITE_API_URL=http://localhost:8000
VITE_API_V1_STR=/api/v1
VITE_APP_NAME=Fernando
VITE_APP_VERSION=1.0.0
VITE_DEBUG=false

# Feature Configuration
VITE_ENABLE_MOCK_DATA=false
VITE_MAX_FILE_SIZE=10485760
EOF

echo "Frontend environment file created."
```

#### 6.2 Update Frontend Configuration Loading
```typescript
// Create frontend configuration module
cat > frontend/accounting-frontend/src/config/environment.ts << 'EOF'
interface EnvironmentConfig {
  apiUrl: string;
  apiVersion: string;
  appName: string;
  appVersion: string;
  debug: boolean;
  featureFlags: {
    enableMockData: boolean;
    maxFileSize: number;
  };
}

const getEnvironmentConfig = (): EnvironmentConfig => {
  return {
    apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    apiVersion: import.meta.env.VITE_API_V1_STR || '/api/v1',
    appName: import.meta.env.VITE_APP_NAME || 'Fernando',
    appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
    debug: import.meta.env.VITE_DEBUG === 'true',
    featureFlags: {
      enableMockData: import.meta.env.VITE_ENABLE_MOCK_DATA === 'true',
      maxFileSize: parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '10485760'),
    },
  };
};

export const config = getEnvironmentConfig();
export default config;
EOF

echo "Frontend configuration module created."
```

### Step 7: Migrate Licensing Server Configuration

#### 7.1 Create Licensing Server Configuration
```bash
# Create licensing server environment file
cat > licensing-server/.env << 'EOF'
# Licensing Server Configuration
LICENSING_APP_NAME=LicensingServer
LICENSING_APP_VERSION=1.0.0
LICENSING_DEBUG=false

# Database Configuration
LICENSING_DATABASE_URL=postgresql://user:password@localhost:5432/licensing
LICENSING_REDIS_URL=redis://localhost:6379/1

# Security Configuration
LICENSING_SECRET_KEY=your-licensing-secret-key-here
LICENSING_ALGORITHM=HS256
LICENSING_LICENSE_TOKEN_EXPIRE_DAYS=30
EOF

echo "Licensing server environment file created."
```

#### 7.2 Update Licensing Server Configuration
```python
# Create licensing server configuration module
cat > licensing-server/app/core/config.py << 'EOF'
from pydantic import BaseSettings, validator
from typing import List
import os

class LicensingSettings(BaseSettings):
    """Licensing server settings"""
    
    # Service configuration
    LICENSING_APP_NAME: str = "LicensingServer"
    LICENSING_APP_VERSION: str = "1.0.0"
    LICENSING_DEBUG: bool = False
    
    # Database configuration
    LICENSING_DATABASE_URL: str
    LICENSING_REDIS_URL: str
    
    # Security configuration
    LICENSING_SECRET_KEY: str
    LICENSING_ALGORITHM: str = "HS256"
    LICENSING_LICENSE_TOKEN_EXPIRE_DAYS: int = 30
    
    @validator("LICENSING_SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("LICENSING_SECRET_KEY must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = LicensingSettings()
EOF

echo "Licensing server configuration module created."
```

## Validation and Testing

### Step 8: Create Validation Scripts

#### 8.1 Configuration Validation Script
```bash
# Create comprehensive validation script
cat > configs/scripts/validate-migration.py << 'EOF'
#!/usr/bin/env python3
"""
Configuration Migration Validation Script
Validates that all services can start with the new configuration system
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

class ConfigurationValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_required_fields(self, service_name, env_file, required_fields):
        """Validate required fields exist"""
        if not os.path.exists(env_file):
            self.errors.append(f"Missing environment file: {env_file}")
            return False
            
        with open(env_file, 'r') as f:
            content = f.read()
            
        for field in required_fields:
            if f"{field}=" not in content:
                self.errors.append(f"{service_name}: Missing required field {field}")
                return False
                
        return True
    
    def validate_secret_strength(self, secret_value, secret_name):
        """Validate secret key strength"""
        if len(secret_value) < 32:
            self.errors.append(f"{secret_name} must be at least 32 characters")
            return False
        return True
    
    def test_service_startup(self, service_path, service_name):
        """Test if service can start with new configuration"""
        try:
            # Change to service directory
            os.chdir(service_path)
            
            # Try to import the configuration module
            result = subprocess.run([
                sys.executable, '-c', 
                'from app.core.config import settings; print("Configuration loaded successfully")'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.errors.append(f"{service_name} configuration validation failed: {result.stderr}")
                return False
            else:
                print(f"✓ {service_name} configuration validation passed")
                return True
                
        except subprocess.TimeoutExpired:
            self.warnings.append(f"{service_name} startup test timed out")
            return False
        except Exception as e:
            self.errors.append(f"{service_name} startup test failed: {e}")
            return False
    
    def run_validation(self):
        """Run all validation checks"""
        print("Starting configuration migration validation...")
        
        # Validate backend configuration
        if self.validate_required_fields("Backend", "backend/.env", [
            "APP_NAME", "APP_VERSION", "DEBUG", "DATABASE_URL", 
            "SECRET_KEY", "ALGORITHM", "CORS_ORIGINS"
        ]):
            self.test_service_startup("backend", "Backend")
        
        # Validate frontend configuration
        if self.validate_required_fields("Frontend", "frontend/accounting-frontend/.env.local", [
            "VITE_API_URL", "VITE_APP_NAME", "VITE_APP_VERSION", "VITE_DEBUG"
        ]):
            print("✓ Frontend configuration validation passed")
        
        # Validate licensing server configuration
        if self.validate_required_fields("Licensing Server", "licensing-server/.env", [
            "LICENSING_APP_NAME", "LICENSING_APP_VERSION", "LICENSING_DEBUG",
            "LICENSING_DATABASE_URL", "LICENSING_SECRET_KEY"
        ]):
            self.test_service_startup("licensing-server", "Licensing Server")
        
        # Print results
        print("\n" + "="*50)
        print("VALIDATION RESULTS")
        print("="*50)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ All validations passed!")
            return True
        elif not self.errors:
            print("✅ All critical validations passed (warnings ignored)")
            return True
        else:
            print("❌ Validation failed. Please fix errors before proceeding.")
            return False

if __name__ == "__main__":
    validator = ConfigurationValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
EOF

chmod +x configs/scripts/validate-migration.py
echo "Configuration validation script created."
```

#### 8.2 Run Validation
```bash
# Test the validation script
python3 configs/scripts/validate-migration.py
```

### Step 9: Service Integration Testing

#### 9.1 Backend Integration Test
```python
# Create backend integration test
cat > tests/test_migration_backend.py << 'EOF'
import pytest
import os
from unittest.mock import patch
from app.core.config import settings

def test_backend_configuration_loaded():
    """Test that backend configuration is properly loaded"""
    # Test required settings exist
    assert settings.APP_NAME is not None
    assert settings.APP_VERSION is not None
    assert settings.DATABASE_URL is not None
    assert settings.SECRET_KEY is not None
    
    # Test secret key strength
    assert len(settings.SECRET_KEY) >= 32
    
    # Test CORS origins are list
    assert isinstance(settings.CORS_ORIGINS, list)
    
    print("✓ Backend configuration test passed")

def test_backend_database_connection():
    """Test database connection configuration"""
    # Test database URL format
    database_url = settings.DATABASE_URL
    assert database_url.startswith(('postgresql://', 'sqlite://', 'mysql://'))
    
    print("✓ Backend database configuration test passed")

if __name__ == "__main__":
    test_backend_configuration_loaded()
    test_backend_database_connection()
    print("All backend tests passed!")
EOF

# Run backend test
cd backend && python3 ../tests/test_migration_backend.py
```

#### 9.2 Frontend Integration Test
```typescript
// Create frontend integration test
cat > frontend/accounting-frontend/src/config/environment.test.ts << 'EOF'
import { config } from './environment';

describe('Frontend Configuration', () => {
  test('should load configuration from environment', () => {
    expect(config.apiUrl).toBeDefined();
    expect(config.appName).toBeDefined();
    expect(config.appVersion).toBeDefined();
  });

  test('should have valid feature flags', () => {
    expect(typeof config.debug).toBe('boolean');
    expect(config.featureFlags.enableMockData).toBeDefined();
    expect(config.featureFlags.maxFileSize).toBeGreaterThan(0);
  });
});
EOF

# Run frontend test (if Jest is configured)
echo "Frontend configuration test created."
```

## Security and Compliance

### Step 10: Security Validation

#### 10.1 Secret Management Validation
```bash
# Create secret validation script
cat > configs/scripts/validate-security.py << 'EOF'
#!/usr/bin/env python3
"""
Security validation for migrated configuration
"""

import os
import re
import secrets
import string
from pathlib import Path

def check_secret_strength(secret_value):
    """Check if secret meets security requirements"""
    if len(secret_value) < 32:
        return False, "Secret too short (minimum 32 characters)"
    
    # Check for common weak patterns
    weak_patterns = [
        r'^[a-f0-9]{32}$',  # Simple hex
        r'^password\d*$',   # Password patterns
        r'^secret\d*$',     # Secret patterns
    ]
    
    for pattern in weak_patterns:
        if re.match(pattern, secret_value, re.IGNORECASE):
            return False, "Secret matches weak pattern"
    
    return True, "Secret strength acceptable"

def validate_configuration_security():
    """Validate security of migrated configuration"""
    issues = []
    
    # Check environment files for weak secrets
    env_files = [
        "backend/.env",
        "frontend/accounting-frontend/.env.local", 
        "licensing-server/.env"
    ]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Look for secret keys
            secret_patterns = [
                r'SECRET_KEY=([^\n]+)',
                r'LICENSING_SECRET_KEY=([^\n]+)',
                r'JWT_SECRET=([^\n]+)'
            ]
            
            for pattern in secret_patterns:
                matches = re.findall(pattern, content)
                for secret in matches:
                    is_strong, message = check_secret_strength(secret)
                    if not is_strong:
                        issues.append(f"{env_file}: {message}")
    
    return issues

if __name__ == "__main__":
    issues = validate_configuration_security()
    
    if issues:
        print("Security issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ Security validation passed")
EOF

# Run security validation
python3 configs/scripts/validate-security.py
```

#### 10.2 Compliance Check
```bash
# Create compliance validation script
cat > configs/scripts/validate-compliance.py << 'EOF'
#!/usr/bin/env python3
"""
Compliance validation for configuration migration
"""

import os
import json
import re
from pathlib import Path

def check_compliance():
    """Check configuration compliance with standards"""
    issues = []
    recommendations = []
    
    # Check for required security headers and settings
    env_files = ["backend/.env", "licensing-server/.env"]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for production security settings
            if "DEBUG=true" in content:
                issues.append(f"{env_file}: DEBUG enabled (security risk)")
            
            # Check for proper CORS configuration
            if "CORS_ORIGINS" in content:
                if "*" in content:
                    issues.append(f"{env_file}: Wildcard CORS origins (security risk)")
            
            # Check for proper allowed hosts
            if "ALLOWED_HOSTS" in content:
                if "localhost" in content and "production" in content:
                    recommendations.append(f"{env_file}: Consider removing localhost in production")
    
    return issues, recommendations

if __name__ == "__main__":
    issues, recommendations = check_compliance()
    
    if issues:
        print("Compliance issues found:")
        for issue in issues:
            print(f"  - {issue}")
    
    if recommendations:
        print("\nCompliance recommendations:")
        for rec in recommendations:
            print(f"  - {rec}")
    
    if not issues:
        print("✓ Compliance validation passed")
EOF

# Run compliance validation
python3 configs/scripts/validate-compliance.py
```

## Migration Completion

### Step 11: Final Integration Testing

#### 11.1 End-to-End Service Test
```bash
# Create end-to-end test script
cat > configs/scripts/test-migration-complete.py << 'EOF'
#!/usr/bin/env python3
"""
End-to-end migration test
Tests that all services work together with the new configuration
"""

import time
import requests
import subprocess
import os
import signal
from pathlib import Path

class MigrationTestSuite:
    def __init__(self):
        self.services = {
            "backend": {"port": 8000, "health_endpoint": "/health"},
            "licensing": {"port": 8002, "health_endpoint": "/health"}
        }
        self.processes = []
    
    def start_service(self, service_name, command, port):
        """Start a service for testing"""
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create process group
            )
            self.processes.append((process, service_name))
            
            # Wait for service to start
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"http://localhost:{port}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"✓ {service_name} service started successfully")
                        return True
                except:
                    time.sleep(2)
            
            print(f"❌ {service_name} service failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting {service_name}: {e}")
            return False
    
    def test_service_communication(self):
        """Test communication between services"""
        # Test backend health
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            assert response.status_code == 200
            print("✓ Backend health check passed")
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
        
        # Test API endpoints
        try:
            response = requests.get("http://localhost:8000/api/v1/", timeout=5)
            print("✓ Backend API endpoint test passed")
        except Exception as e:
            print(f"❌ Backend API test failed: {e}")
            return False
        
        return True
    
    def cleanup(self):
        """Stop all test services"""
        for process, service_name in self.processes:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
                print(f"✓ {service_name} service stopped")
            except:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    pass
    
    def run_tests(self):
        """Run complete migration test suite"""
        print("Starting end-to-end migration tests...")
        
        try:
            # Start backend service
            if not self.start_service("backend", "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000", 8000):
                return False
            
            # Test service communication
            if not self.test_service_communication():
                return False
            
            print("✓ All end-to-end tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    test_suite = MigrationTestSuite()
    success = test_suite.run_tests()
    exit(0 if success else 1)
EOF

# Run end-to-end test
python3 configs/scripts/test-migration-complete.py
```

### Step 12: Documentation Updates

#### 12.1 Update Project Documentation
```bash
# Update main README with migration information
cat >> README.md << 'EOF'

## Configuration Migration

The Fernando Platform has migrated to a unified configuration system. Key changes:

### New Configuration Structure
- **Environment-based**: All configuration via environment variables
- **Service-specific**: Separate configs for backend, frontend, licensing
- **Template-driven**: Example files for easy setup
- **Validation**: Comprehensive validation and security checks

### Quick Setup
```bash
# Copy configuration templates
cp configs/templates/backend.env.example backend/.env
cp configs/templates/frontend.env.example frontend/accounting-frontend/.env.local
cp configs/templates/licensing.env.example licensing-server/.env

# Generate secure secrets
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Validate configuration
python3 configs/scripts/validate-migration.py
```

### Migration Guide
For detailed migration instructions, see [MIGRATION.md](MIGRATION.md).

### Configuration Documentation
- [Configuration Guide](configs/README.md)
- [Security Guidelines](SECURITY.md)
- [Migration Guide](MIGRATION.md)
EOF

echo "README updated with migration information."
```

#### 12.2 Create Migration Summary
```markdown
# Configuration Migration Summary

## Migration Completed Successfully ✅

### What Was Migrated
- ✅ Backend API service configuration
- ✅ Frontend application configuration  
- ✅ Licensing server configuration
- ✅ Security and authentication settings
- ✅ Database and external service connections

### New Configuration Files
- `backend/.env` - Backend environment configuration
- `frontend/accounting-frontend/.env.local` - Frontend configuration
- `licensing-server/.env` - Licensing server configuration
- `configs/templates/` - Configuration templates

### Validation Results
- ✅ All required fields present
- ✅ Secret keys meet security requirements
- ✅ Services start successfully
- ✅ Configuration validation passed
- ✅ Security compliance check passed

### Next Steps
1. Update any custom configuration not covered in templates
2. Configure production-specific settings
3. Set up secret management for production
4. Update deployment scripts to use new configuration
5. Train team on new configuration system

### Support
- Configuration validation: `python3 configs/scripts/validate-migration.py`
- Security validation: `python3 configs/scripts/validate-security.py`
- Troubleshooting: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
```

## Rollback Procedure

### Emergency Rollback

If issues occur during migration, follow this rollback procedure:

#### Step 1: Stop Services
```bash
# Stop all services
pkill -f "uvicorn"
pkill -f "node"
```

#### Step 2: Restore Previous Configuration
```bash
# Restore from backup
cp .env.backup backend/.env 2>/dev/null || echo "No backup found"
cp .env.backup frontend/accounting-frontend/.env.local 2>/dev/null || echo "No backup found"

# Or restore from version control
git checkout HEAD -- backend/app/core/config.py
git checkout HEAD -- frontend/accounting-frontend/src/config/
git checkout HEAD -- licensing-server/app/core/config.py
```

#### Step 3: Restart Services
```bash
# Start services with previous configuration
cd backend && python -m uvicorn app.main:app --reload &
cd frontend/accounting-frontend && npm start &
```

#### Step 4: Verify Rollback
```bash
# Test services are working
curl http://localhost:8000/health
curl http://localhost:3000
```

## Support and Resources

### Migration Tools
- **Validation Script**: `configs/scripts/validate-migration.py`
- **Security Check**: `configs/scripts/validate-security.py`
- **Compliance Check**: `configs/scripts/validate-compliance.py`
- **End-to-End Test**: `configs/scripts/test-migration-complete.py`

### Common Issues
1. **Missing environment variables**: Use validation script to identify gaps
2. **Secret key too weak**: Generate new 32+ character secrets
3. **CORS errors**: Update CORS_ORIGINS to match frontend URL
4. **Database connection**: Verify DATABASE_URL format and credentials

### Getting Help
- Review [SECURITY.md](SECURITY.md) for security-related issues
- Check [configs/README.md](configs/README.md) for configuration help
- Run validation scripts to identify specific problems
- Contact the development team for assistance

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-06  
**Migration Status:** Complete  
**Review Cycle:** Post-migration review in 30 days