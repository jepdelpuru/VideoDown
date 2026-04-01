# VideoDown by KiKoSo

Aplicacion web para descargar videos de mas de 1000 plataformas (YouTube, TikTok, Instagram, Twitter/X, Facebook, Twitch, etc.) con interfaz moderna, sistema de usuarios y gestion avanzada de descargas.

## Caracteristicas principales

- **Descarga de videos** desde 1000+ plataformas usando yt-dlp
- **Multiples formatos**: Video (MP4, MKV, WebM, AVI, MOV, TS) y audio (MP3, WAV, FLAC, AAC, Opus, M4A, OGG)
- **Seleccion de calidad**: 720p, 1080p y mas, con estimacion de tamano
- **Descarga de playlists**: Descarga listas de reproduccion completas con seleccion individual
- **Subtitulos**: Descarga e incrustacion de subtitulos en multiples idiomas
- **Recorte de video**: Extraccion de segmentos especificos con FFmpeg
- **Cola de descargas**: Sistema de cola por usuario con procesamiento en segundo plano
- **Progreso en tiempo real**: Actualizaciones via WebSocket (velocidad, ETA, porcentaje)
- **Colecciones**: Organiza videos descargados en colecciones con colores personalizados
- **Enlaces compartidos**: Genera enlaces publicos para compartir videos sin login
- **Seguimiento de reproduccion**: Guarda la posicion de reproduccion para reanudar donde lo dejaste
- **PWA**: Instalable como app, soporte offline y Share Target API (comparte URLs desde el movil)
- **Panel de administracion**: Gestion de usuarios, cuotas de almacenamiento (hasta 50GB por usuario) y tamano de cola
- **Auto-actualizacion**: yt-dlp se actualiza automaticamente cada 12 horas

## Tech Stack

| Componente | Tecnologia |
|------------|------------|
| Backend | Flask + Flask-SocketIO |
| Autenticacion | Flask-Login con cookies persistentes |
| Base de datos | SQLite3 |
| Motor de descarga | yt-dlp + FFmpeg |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Tiempo real | WebSocket (Socket.IO) |
| PWA | Service Worker + Web App Manifest |
| Contenedores | Docker + Docker Compose |
| Acceso externo | Cloudflare Tunnel |

## Requisitos previos

- Docker y Docker Compose
- Token de Cloudflare Tunnel (opcional, para acceso externo)

## Instalacion

1. Clona el repositorio:
   ```bash
   git clone https://github.com/jepdelpuru/VideoDown.git
   cd VideoDown
   ```

2. **(Opcional)** Si quieres acceso externo via Cloudflare Tunnel, crea el archivo `.env`:
   ```bash
   cp .env.example .env
   # Edita .env con tu token de Cloudflare Tunnel
   ```

3. Levanta los contenedores:
   ```bash
   # Solo la app (uso local):
   docker-compose up -d videodown

   # App + Cloudflare Tunnel (acceso externo, requiere .env):
   docker-compose up -d
   ```

4. Accede a la aplicacion en `http://localhost:5080`

5. Inicia sesion con el usuario admin por defecto:
   - **Usuario:** `caski`
   - **Contrasena:** `pijkl567`
   - Cambia la contrasena desde el panel de administracion despues del primer login

## Estructura del proyecto

```
torrentweb/
├── app.py                 # Aplicacion Flask principal (~2200 lineas)
├── requirements.txt       # Dependencias Python
├── Dockerfile             # Imagen Docker (Python 3.11 + FFmpeg + Deno)
├── docker-compose.yml     # Servicios: Flask + Cloudflare Tunnel
├── templates/
│   ├── login.html         # Pagina de autenticacion
│   ├── index.html         # Interfaz principal (SPA)
│   └── public_player.html # Reproductor publico para enlaces compartidos
├── static/
│   ├── js/app.js          # Logica frontend
│   ├── css/style.css      # Tema oscuro con glass-morphism
│   ├── sw.js              # Service Worker (PWA)
│   └── manifest.json      # Metadata PWA
└── downloads/             # Directorio de almacenamiento
```

## Uso

1. Inicia sesion con tu usuario
2. Pega la URL del video que quieres descargar
3. Selecciona formato y calidad
4. La descarga se anade a tu cola y se procesa automaticamente
5. Descarga, reproduce en el navegador o comparte el enlace

## Docker Compose

El archivo `docker-compose.yml` define dos servicios:

- **videodown**: Aplicacion Flask en el puerto 5080
- **tunnel**: Cloudflare Tunnel para acceso externo seguro (requiere `CF_TUNNEL_TOKEN`)

## Licencia

Proyecto privado.
