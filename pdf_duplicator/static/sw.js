const CACHE_NAME = 'pdf-studio-pro-v17';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/apple_style.css',
  '/static/js/app.js',
  '/static/js/store.js',
  '/static/fonts/Poppins-Regular.ttf',
  '/static/fonts/Poppins-Medium.ttf',
  '/static/fonts/Poppins-SemiBold.ttf',
  '/static/fonts/Poppins-Bold.ttf',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pre-caching static app shell');
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Clearing old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Network first with cache fallback for API endpoints, Stale-while-revalidate for static assets
  // API calls and saved PDFs (/output/...) always go to the server: caching a download would
  // keep serving a stale copy and fill the browser's storage with documents.
  const path = new URL(event.request.url).pathname;
  if (event.request.method !== 'GET' || path.startsWith('/api/') || path.startsWith('/output/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
