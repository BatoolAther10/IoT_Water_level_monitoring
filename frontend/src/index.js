import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// ============================================================================
// GLOBAL ERROR HANDLER
// ============================================================================

// Catch all unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('❌ UNHANDLED PROMISE REJECTION:', event.reason);
  // Prevent default error handling
  event.preventDefault();
});

// Catch all console errors
const originalError = console.error;
console.error = function(...args) {
  originalError.apply(console, args);
  // Also log to a visible place
  if (args[0] && typeof args[0] === 'object') {
    console.error('ERROR OBJECT:', JSON.stringify(args[0], null, 2));
  }
};

// ============================================================================
// RENDER APP
// ============================================================================

const root = ReactDOM.createRoot(document.getElementById('root'));

try {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  console.log('✅ React app mounted successfully');
} catch (error) {
  console.error('❌ FATAL ERROR IN APP MOUNT:', error);
  document.body.innerHTML = `
    <div style="padding: 20px; font-family: monospace; background: #fee; color: #c00;">
      <h1>❌ Application Error</h1>
      <p><strong>Error:</strong> ${error.message}</p>
      <p><strong>Stack:</strong> ${error.stack}</p>
      <p>Check browser console for more details.</p>
      <button onclick="location.reload()">Reload Page</button>
    </div>
  `;
}