// patch-expo-router.js - Run this script to patch the problematic file
const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'node_modules/expo-router/_ctx.web.tsx');

try {
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Replace the problematic line with a hardcoded path
  content = content.replace(
    'process.env.EXPO_ROUTER_APP_ROOT',
    '"./app"'
  );
  
  fs.writeFileSync(filePath, content);
  console.log('Successfully patched expo-router/_ctx.web.tsx');
} catch (error) {
  console.error('Error patching file:', error);
}