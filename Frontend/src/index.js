import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const shouldResetLocalApp = new URLSearchParams(window.location.search).has('reset');

// Local setup/debug shortcut: open http://localhost:3000/?reset=1 to clear
// saved login/session state and force the app back to the login screen.
if (shouldResetLocalApp) {
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState({}, document.title, window.location.pathname);
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// In development, remove any previously installed localhost service worker only
// when explicitly requested via ?reset=1. Running this on every load can make
// Edge/Chrome behave like the page is constantly refreshing while an old PWA
// worker is being detached.
if (shouldResetLocalApp && process.env.NODE_ENV !== 'production' && 'serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.unregister()));

      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
      }

      if (registrations.length > 0) {
        console.log('Development cleanup: removed existing service workers and caches.');
      }
    } catch (error) {
      console.log('Development service worker cleanup failed:', error);
    }
  });
}

// Register the PWA service worker only in production.
// During `npm start`, an active service worker can cache stale dev assets and
// cause reload loops on localhost.
if (process.env.NODE_ENV === 'production' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope);
      })
      .catch((error) => {
        console.log('SW registration failed:', error);
      });
  });
}
