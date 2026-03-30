/* eslint-disable no-restricted-globals */

const CACHE_NAME = 'academic-task-manager-v2';
const API_CACHE_NAME = 'academic-task-manager-api-v1';
const STATIC_ASSET_PATTERNS = [
  /^\/$/,
  /^\/index\.html$/,
  /^\/manifest\.json$/,
  /^\/logo192\.png$/,
  /^\/logo512\.png$/,
  /^\/static\/js\/.+\.js$/,
  /^\/static\/css\/.+\.css$/
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll([
          '/',
          '/index.html',
          '/manifest.json',
          '/logo192.png',
          '/logo512.png'
        ]);
      })
      .catch((err) => {
        console.log('Cache install failed:', err);
      })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Take control immediately
  self.clients.claim();
});

function shouldBypassApiCache(requestUrl) {
  return (
    requestUrl.includes('/api/users/login') ||
    requestUrl.includes('/api/users/logout') ||
    requestUrl.includes('/api/users/session')
  );
}

function shouldCacheStaticAsset(requestUrl) {
  const { pathname } = new URL(requestUrl);
  return STATIC_ASSET_PATTERNS.some((pattern) => pattern.test(pathname));
}

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API reads: network-first with cached fallback for offline mode
  if (event.request.url.includes('/api/')) {
    if (shouldBypassApiCache(event.request.url)) {
      return;
    }

    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(API_CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(event.request);
          if (cached) return cached;
          return new Response(JSON.stringify({ error: 'Offline and no cached API data available' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          });
        })
    );
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }

        return fetch(event.request).then((response) => {
          // Don't cache non-successful responses
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          if (shouldCacheStaticAsset(event.request.url)) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => {
                cache.put(event.request, responseToCache);
              });
          }

          return response;
        });
      })
      .catch(() => {
        // Return offline page if available
        return caches.match('/index.html');
      })
  );
});

// Background sync for offline task creation
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-tasks') {
    event.waitUntil(syncTasks());
  }
});

async function syncTasks() {
  // Ask the active clients to flush locally queued actions.
  const clientList = await self.clients.matchAll({ includeUncontrolled: true });
  for (const client of clientList) {
    client.postMessage({ type: 'SYNC_OFFLINE_QUEUE' });
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'You have a task reminder!',
    icon: '/logo192.png',
    badge: '/logo192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'view', title: 'View Tasks' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Academic Task Manager', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
