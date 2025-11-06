#!/bin/bash

# Telemetry Integration Script
# Automatically adds telemetry tracking to existing components

echo "🔧 Adding telemetry integration to your React components..."

# Function to add telemetry imports and hooks
add_telemetry_to_component() {
    local component_file="$1"
    
    if [ ! -f "$component_file" ]; then
        echo "❌ File not found: $component_file"
        return 1
    fi
    
    echo "📝 Processing: $component_file"
    
    # Create backup
    cp "$component_file" "${component_file}.backup"
    
    # Add imports at the top
    sed -i '1i import {\n  useComponentTelemetry,\n  useFeatureTelemetry,\n  usePerformanceTelemetry\n} from "../hooks/useTelemetry";' "$component_file"
    
    # Add useComponentTelemetry hook after existing hooks
    sed -i '/useEffect.*componentName.*=.*/a\\n  // Telemetry tracking\n  useComponentTelemetry("YourComponentName");' "$component_file"
    
    echo "✅ Telemetry hooks added to $component_file"
}

# Function to add telemetry to all components in a directory
add_telemetry_to_directory() {
    local dir="$1"
    
    echo "🔍 Scanning directory: $dir"
    
    # Find all .tsx files
    find "$dir" -name "*.tsx" -type f | while read -r file; do
        # Skip files that already have telemetry imports
        if ! grep -q "useTelemetry" "$file"; then
            add_telemetry_to_component "$file"
        else
            echo "⏭️  Skipping (already has telemetry): $file"
        fi
    done
}

# Function to show usage
show_usage() {
    echo "🚀 Telemetry Integration Helper"
    echo ""
    echo "Usage: ./integrate-telemetry.sh [command] [target]"
    echo ""
    echo "Commands:"
    echo "  component <file>     Add telemetry to a specific component"
    echo "  directory <path>     Add telemetry to all components in a directory"
    echo "  page <name>          Add telemetry to a specific page"
    echo "  example             Create an example component with telemetry"
    echo "  help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./integrate-telemetry.sh component src/components/MyComponent.tsx"
    echo "  ./integrate-telemetry.sh directory src/components"
    echo "  ./integrate-telemetry.sh page DashboardPage"
    echo ""
}

# Function to add telemetry to a specific page
add_telemetry_to_page() {
    local page_name="$1"
    local page_file="src/pages/${page_name}.tsx"
    
    if [ -f "$page_file" ]; then
        add_telemetry_to_component "$page_file"
    else
        echo "❌ Page not found: $page_file"
        echo "💡 Try: ./integrate-telemetry.sh page LoginPage"
    fi
}

# Function to create example component
create_example_component() {
    cat > src/components/TelemetryExample.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  useComponentTelemetry,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useInteractionTracking,
} from '../hooks/useTelemetry';

export default function TelemetryExample() {
  // Track component lifecycle
  useComponentTelemetry('TelemetryExample', { 
    version: '1.0',
    type: 'example'
  });
  
  // Track feature usage
  const { trackFeatureOpen, trackFeatureUse, trackFeatureClose } = useFeatureTelemetry('example-feature');
  
  // Monitor performance
  const { startOperation, endOperation } = usePerformanceTelemetry('example-operation');
  
  // Track user interactions
  const { trackClick } = useInteractionTracking('example-button', 'example');
  
  const [data, setData] = useState<string>('');
  
  useEffect(() => {
    trackFeatureOpen();
    
    return () => {
      trackFeatureClose(true);
    };
  }, []);
  
  const handleLoadData = async () => {
    startOperation();
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      const result = 'Sample data loaded';
      setData(result);
      
      trackFeatureUse('data_loaded', { 
        dataLength: result.length 
      });
    } catch (error) {
      trackFeatureUse('data_load_error');
    } finally {
      endOperation();
    }
  };
  
  const handleButtonClick = () => {
    trackClick();
    handleLoadData();
  };
  
  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Telemetry Example</h2>
      
      <button
        onClick={handleButtonClick}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Load Data (Tracked)
      </button>
      
      {data && (
        <div className="mt-4 p-4 bg-green-50 rounded">
          <p className="text-green-800">{data}</p>
        </div>
      )}
      
      <div className="mt-4 text-sm text-gray-600">
        <p>This component demonstrates telemetry integration:</p>
        <ul className="list-disc list-inside mt-2">
          <li>Component lifecycle tracking</li>
          <li>Feature usage monitoring</li>
          <li>Performance measurement</li>
          <li>User interaction tracking</li>
        </ul>
      </div>
    </div>
  );
}
EOF
    
    echo "✅ Example component created: src/components/TelemetryExample.tsx"
}

# Main script logic
case "$1" in
    "component")
        if [ -z "$2" ]; then
            echo "❌ Please specify a component file"
            show_usage
            exit 1
        fi
        add_telemetry_to_component "$2"
        ;;
    "directory")
        if [ -z "$2" ]; then
            echo "❌ Please specify a directory"
            show_usage
            exit 1
        fi
        add_telemetry_to_directory "$2"
        ;;
    "page")
        if [ -z "$2" ]; then
            echo "❌ Please specify a page name"
            show_usage
            exit 1
        fi
        add_telemetry_to_page "$2"
        ;;
    "example")
        create_example_component
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    "")
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

echo ""
echo "🎉 Telemetry integration complete!"
echo ""
echo "💡 Next steps:"
echo "1. Check your analytics dashboard at /analytics"
echo "2. Monitor real-time metrics"
echo "3. Review the telemetry README for advanced usage"
echo ""
echo "🆘 Need help? Check:"
echo "- TELEMETRY_README.md for detailed documentation"
echo "- IMPLEMENTATION_SUMMARY.md for feature overview"
echo "- /analytics for the live dashboard"
EOF

chmod +x /workspace/fernando/frontend/accounting-frontend/integrate-telemetry.sh