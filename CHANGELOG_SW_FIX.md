# Fix: Pantalla en blanco en Android al reabrir la PWA

## Problema

Al abrir la webapp instalada en Android desde la multitarea, ocasionalmente aparecía una pantalla en blanco. Refrescar no solucionaba el problema; era necesario cerrar la app desde multitarea y volver a abrirla.

## Causa raíz

El service worker (`static/sw.js`) tenía un `fetch` event listener registrado que no hacía nada:

```js
self.addEventListener('fetch', (event) => {
    return; // No llama a event.respondWith()
});
```

En Android, cuando el sistema mata el proceso WebView para liberar memoria y el usuario reabre la PWA, el navegador intenta cargar la página a través del service worker. Como el fetch handler estaba registrado pero nunca respondía con `event.respondWith()`, el navegador quedaba esperando una respuesta que nunca llegaba, resultando en pantalla en blanco.

## Cambios realizados

### 1. `static/sw.js` — Reescrito completo

- **Cache del app shell**: Al instalarse, cachea `/`, `/static/css/style.css` y `/static/js/app.js`.
- **Estrategia network-first**: Intenta cargar de red; si falla, sirve la versión cacheada.
- **Exclusiones**: No cachea peticiones de Socket.IO (`/socket.io`) ni API (`/api`).
- **Limpieza automática**: Al activarse, elimina caches con nombre distinto al actual.
- **Versionado**: Cambiar `CACHE_NAME` (ej: `vd-v1` → `vd-v2`) fuerza la actualización de archivos cacheados.

### 2. `app.py` — Header Cache-Control en `/sw.js`

Añadido `Cache-Control: no-cache` para que el navegador siempre compruebe si hay una versión nueva del service worker.

## Notas de despliegue

- La primera vez que los usuarios abran la app tras el deploy, el SW se actualizará automáticamente.
- Para forzar la limpieza del SW viejo en un dispositivo concreto: desinstalar y reinstalar la PWA.
- Para futuras actualizaciones de archivos estáticos, incrementar `CACHE_NAME` en `sw.js`.
