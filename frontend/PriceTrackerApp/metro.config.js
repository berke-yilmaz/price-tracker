const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

// Get the default configuration from Expo.
const config = getDefaultConfig(__dirname);

// --- START: Monorepo Configuration ---

// 1. Find the project's root directory. In your structure, this is two levels up.
const projectRoot = path.resolve(__dirname, '../..');

// 2. Add the project root to the watchlist.
// This allows Metro to "see" files outside of the `frontend/PriceTrackerApp` directory,
// which is essential for resolving the shared_config.json.
config.watchFolders = [projectRoot];

// 3. Configure the resolver to look for modules in the project root's node_modules.
// This prevents issues if you have dependencies installed at the top level.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(__dirname, 'node_modules'),
];

// --- END: Monorepo Configuration ---

module.exports = config;