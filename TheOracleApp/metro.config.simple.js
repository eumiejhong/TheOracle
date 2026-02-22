const {getDefaultConfig} = require('expo/metro-config');
const config = getDefaultConfig(__dirname);

// Reduce file watching to prevent EMFILE errors
config.watchFolders = [];
config.resolver.platforms = ['ios', 'native'];

// Disable file watching for large directories
config.server = {
  ...config.server,
  useGlobalHotkey: false,
};

module.exports = config;