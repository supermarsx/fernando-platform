# Fernando Desktop Client

A comprehensive Electron-based desktop application for document processing, designed to work offline with seamless synchronization capabilities.

## Features

### Core Functionality
- **Document Processing**: OCR and PDF text extraction with confidence scoring
- **Offline Operation**: Complete offline functionality with local SQLite database
- **File System Integration**: Drag-and-drop document processing
- **System Tray**: Minimal system tray with quick access and notifications
- **Auto-updater**: Automatic update checking and installation

### Advanced Features
- **Multi-platform Support**: Windows, macOS, and Linux compatibility
- **Code Signing**: Prepared for production code signing and notarization
- **Local Storage**: Secure local data storage with encryption options
- **Synchronization**: Bi-directional sync with web application
- **User Authentication**: Local and server-based authentication
- **Batch Processing**: Process multiple documents simultaneously

## Architecture

### Technology Stack
- **Main Process**: Node.js with Electron core APIs
- **Renderer Process**: React with TypeScript and Vite
- **Database**: SQLite with WAL mode for performance
- **Build System**: electron-vite and electron-builder
- **Security**: Context isolation and preload scripts

### Components

#### Main Process (`src/main/`)
- `main.js` - Main application controller
- `database-manager.js` - SQLite operations and schema management
- `file-processor.js` - Document processing and OCR
- `sync-manager.js` - Server synchronization and offline support
- `notification-manager.js` - System notifications
- `system-tray-manager.js` - System tray functionality
- `auto-updater.js` - Update management and installation

#### Renderer Process (`src/renderer/`)
- `index.html` - Main application UI
- `index.ts` - UI logic and event handling
- React components for modular UI

#### Security
- Context isolation enabled
- Node integration disabled in renderer
- Secure IPC communication via preload script
- File system access restricted to application directory

## Development Setup

### Prerequisites
- Node.js 18.0.0 or higher
- Python 3.8+ (for native dependencies)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/fernando-desktop.git
cd fernando-desktop

# Install dependencies
npm install

# Install additional system dependencies for OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS:
brew install tesseract

# Windows:
# Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Building for Production

### Platform-Specific Builds

```bash
# Build for current platform
npm run build

# Build for specific platforms (requires cross-platform setup)
npm run build -- --win    # Windows
npm run build -- --mac    # macOS
npm run build -- --linux  # Linux
```

### Code Signing Setup

#### macOS Code Signing
1. Obtain Developer ID Application certificate from Apple Developer Portal
2. Export certificate as .p12 file
3. Set environment variables:
   ```bash
   export CSC_NAME="Developer ID Application: Your Name (TEAM_ID)"
   export APPLE_ID="your-apple-id@example.com"
   export APPLE_ID_PASSWORD="app-specific-password"
   export APPLE_TEAM_ID="YOUR_TEAM_ID"
   ```

#### Windows Code Signing
1. Obtain code signing certificate from trusted CA
2. Export certificate as .p12 file
3. Set environment variables:
   ```bash
   export CERTIFICATE_PATH="path/to/certificate.p12"
   export CERTIFICATE_PASSWORD="certificate-password"
   ```

#### Linux Code Signing
Linux applications don't require code signing, but you can set up repository signing for package distribution.

### Distribution

#### GitHub Releases
Configure automatic releases by setting up GitHub Actions:
1. Create `.github/workflows/release.yml`
2. Set repository secrets for signing certificates
3. Tag releases to trigger automatic builds

#### Direct Distribution
Distribute via your website or enterprise distribution system:
1. Build installers for target platforms
2. Host on secure CDN or internal server
3. Configure auto-updater to point to update server

## Configuration

### Environment Variables

```bash
# API Configuration
API_URL=https://api.fernando.com
UPDATE_SERVER_URL=https://updates.fernando.com

# Development
NODE_ENV=production
ELECTRON_RENDERER_URL=http://localhost:3000
```

### Application Settings

The application uses `electron-store` for persistent settings:

```javascript
// Default settings
{
  updatesEnabled: true,
  autoDownload: true,
  autoInstall: false,
  checkOnStartup: true,
  checkFrequency: 'daily',
  theme: 'light',
  language: 'en',
  offlineMode: false
}
```

## File Structure

```
desktop/
├── src/
│   ├── main/
│   │   ├── main.js                 # Main process
│   │   ├── database-manager.js     # SQLite operations
│   │   ├── file-processor.js       # Document processing
│   │   ├── sync-manager.js         # Synchronization
│   │   ├── notification-manager.js # System notifications
│   │   ├── system-tray-manager.js  # System tray
│   │   └── auto-updater.js         # Update management
│   ├── preload/
│   │   └── preload.js              # Secure IPC bridge
│   └── renderer/
│       ├── index.html              # Main UI
│       └── index.ts                # UI logic
├── build/
│   ├── entitlements.mac.plist      # macOS entitlements
│   ├── icon.icns                   # macOS icon
│   ├── icon.png                    # Windows/Linux icon
│   └── certificate.p12             # Code signing certificate
├── scripts/
│   ├── notarize.js                 # macOS notarization
│   └── sign.js                     # Windows signing
├── dist/                           # Built application
├── release/                        # Distribution packages
├── package.json
├── vite.config.js
├── tsconfig.json
└── README.md
```

## Security Considerations

### Code Signing
- All production builds should be code signed
- Use trusted certificate authorities
- Implement notarization for macOS (required for distribution outside Mac App Store)

### Data Protection
- Local database encryption for sensitive data
- Secure token storage
- HTTPS-only API communications
- Input validation and sanitization

### Permissions
- Minimal required permissions in production
- Secure file system access patterns
- Network communication restrictions

## Troubleshooting

### Common Issues

#### OCR Not Working
```bash
# Verify Tesseract installation
tesseract --version

# Check language data
tesseract --list-langs

# Install additional languages if needed
sudo apt-get install tesseract-ocr-[language-code]
```

#### Database Errors
```bash
# Clear application data
# macOS: ~/Library/Application Support/fernando-desktop
# Windows: %APPDATA%/fernando-desktop
# Linux: ~/.config/fernando-desktop

# Reset application data
rm -rf ~/Library/Application\ Support/fernando-desktop/
```

#### Build Issues
```bash
# Clear node modules and rebuild
rm -rf node_modules package-lock.json
npm install

# Clear electron-builder cache
rm -rf ~/.electron-builder

# Clear Vite cache
rm -rf node_modules/.vite
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=1

# Run with Electron DevTools
npm run dev

# Access renderer DevTools
# Press F12 or Cmd+Option+I in the application
```

### Log Files

Application logs are stored in:
- **macOS**: `~/Library/Logs/fernando-desktop/`
- **Windows**: `%APPDATA%/fernando-desktop/logs/`
- **Linux**: `~/.config/fernando-desktop/logs/`

## Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run linting and type checking
5. Submit a pull request

### Code Standards
- TypeScript for all new code
- ESLint and Prettier for code formatting
- Comprehensive error handling
- Documentation for public APIs
- Security best practices

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Email: support@fernando.com
- Documentation: https://docs.fernando.com
- GitHub Issues: https://github.com/your-org/fernando-desktop/issues