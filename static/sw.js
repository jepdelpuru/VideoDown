// Self-cleaning service worker v2 - nukes all caches and force-reloads all pages
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(keys.map(k => caches.delete(k))))
            .then(() => self.clients.claim())
            .then(() => self.clients.matchAll({ type: 'window' }))
            .then(clients => {
                // Force-navigate each open page to itself (bypasses old cache)
                clients.forEach(client => {
                    if (client.url && client.navigate) {
                        client.navigate(client.url);
                    }
                });
            })
    );
});

// No fetch handler = zero caching, everything hits the network
