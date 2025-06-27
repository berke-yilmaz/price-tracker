#!/bin/bash

echo "Checking expo-router v5 for SDK 53..."

# Check if expo-router v5 has different file structure
echo "Searching for context files in expo-router v5..."
find node_modules/expo-router/ -name "*ctx*" -type f

# Check for any environment variable usage
echo "Searching for EXPO_ROUTER_APP_ROOT usage..."
find node_modules/expo-router/ -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" | xargs grep -l "EXPO_ROUTER_APP_ROOT" 2>/dev/null

# Check the new structure
echo "Checking expo-router v5 structure..."
ls -la node_modules/expo-router/

# If context files exist, fix them
if [ -f "node_modules/expo-router/_ctx.web.tsx" ]; then
    echo "Fixing _ctx.web.tsx for v5..."
    echo 'export const ctx = require.context("../../app", true, /\.(js|jsx|ts|tsx)$/);' > node_modules/expo-router/_ctx.web.tsx
fi

if [ -f "node_modules/expo-router/_html-ctx.tsx" ]; then
    echo "Fixing _html-ctx.tsx for v5..."
    echo 'export const ctx = require.context("../../app", true, /\+html\.(js|jsx|ts|tsx)$/);' > node_modules/expo-router/_html-ctx.tsx
fi

# Check for new context patterns in v5
echo "Looking for new context patterns in expo-router v5..."
find node_modules/expo-router/ -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" | xargs grep -l "require\.context" 2>/dev/null

echo "Expo router v5 check complete!"