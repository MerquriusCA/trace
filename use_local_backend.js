// Helper script to switch Chrome extension backend URLs
// Run this in Chrome DevTools console on the extension's background page

console.log('🔧 Backend URL Helper Script');
console.log('Current default: LOCAL (http://localhost:8000)');

// Use local backend (this is now the default)
function useLocalBackend() {
  chrome.storage.local.remove(['backendUrl'], () => {
    console.log('✅ Using LOCAL backend (default)');
    console.log('📍 Backend URL: http://localhost:8000');
    console.log('🔄 Reload the extension to apply changes');
  });
}

// Use production backend
function useProductionBackend() {
  chrome.storage.local.set({
    backendUrl: 'https://trace-api-production.up.railway.app/api/summarize'
  }, () => {
    console.log('✅ Backend URL set to PRODUCTION server');
    console.log('📍 Backend URL: https://trace-api-production.up.railway.app');
    console.log('🔄 Reload the extension to apply changes');
  });
}

// Quick commands
console.log('Available commands:');
console.log('useLocalBackend()      - Switch to local development');
console.log('useProductionBackend() - Switch to Railway production');

// Auto-run local backend setup
useLocalBackend();