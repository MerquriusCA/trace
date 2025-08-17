// Helper script to switch Chrome extension backend URLs
// Run this in Chrome DevTools console on the extension's background page

console.log('🔧 Backend URL Helper Script');
console.log('Current default: PRODUCTION (https://trace-production-79d5.up.railway.app)');

// Use local backend (for development)
function useLocalBackend() {
  chrome.storage.local.set({
    backendUrl: 'http://localhost:8000/api/summarize'
  }, () => {
    console.log('✅ Switched to LOCAL backend');
    console.log('📍 Backend URL: http://localhost:8000');
    console.log('🔄 Reload the extension to apply changes');
  });
}

// Use production backend (this is now the default)
function useProductionBackend() {
  chrome.storage.local.remove(['backendUrl'], () => {
    console.log('✅ Using PRODUCTION backend (default)');
    console.log('📍 Backend URL: https://trace-production-79d5.up.railway.app');
    console.log('🔄 Reload the extension to apply changes');
  });
}

// Quick commands
console.log('Available commands:');
console.log('useLocalBackend()      - Switch to local development');
console.log('useProductionBackend() - Switch back to Railway production (default)');

// Show current backend setting
chrome.storage.local.get(['backendUrl'], (result) => {
  if (result.backendUrl) {
    console.log('📍 Currently using custom backend:', result.backendUrl);
  } else {
    console.log('📍 Currently using default: PRODUCTION');
  }
});