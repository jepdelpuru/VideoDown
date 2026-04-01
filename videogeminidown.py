import os
import sys
import time
import asyncio
import hashlib
import subprocess
import logging
import io
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
import requests
import threading
from ast import literal_eval  # Para leer la lista de config.py de forma segura
import json

import yt_dlp
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ForceReply
)
from pyrogram.errors import MessageNotModified, FloodWait
from pyrogram.errors import PeerIdInvalid
import validators

# --- Configuración Inicial ---
try:
    from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_USER_ID, FFMPEG_PATH, FFPROBE_PATH, IOS_QSV_GLOBAL_QUALITY
    # Cargamos ALLOWED_USERS dinámicamente al inicio
    with open("config.py", "r", encoding="utf-8") as f:
        config_content = f.read()
    match = re.search(r"^\s*ALLOWED_USERS\s*=\s*(\[.*?\])", config_content, re.MULTILINE | re.DOTALL)
    if match:
        ALLOWED_USERS = literal_eval(match.group(1))
    else:
        # Fallback si no se encuentra, aunque debería estar
        from config import ALLOWED_USERS as DEFAULT_ALLOWED_USERS
        ALLOWED_USERS = DEFAULT_ALLOWED_USERS
        logging.warning("No se pudo leer ALLOWED_USERS dinámicamente de config.py, usando valor por defecto.")

except ImportError:
    logging.error("Error: El archivo 'config.py' no se encontró o faltan variables esenciales.")
    sys.exit(1)
except Exception as e:
    logging.error(f"Error al cargar la configuración: {e}")
    sys.exit(1)

# --- Configuración del Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # También muestra logs en la consola
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING) # Reduce verbosidad de pyrogram
log = logging.getLogger(__name__)

# --- Variables Globales ---
bot = Client("video_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
download_tasks = {}  # Almacena información sobre descargas activas: {chat_id: {"message": msg, "cancel_event": event}}
user_requests = {}   # {video_id: {"url": url, "chat_id": chat_id, "os": None, "message_id": message_id}}
CONFIG_LOCK = asyncio.Lock() # Para evitar escritura simultánea en config.py
COOKIE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagram_cookies.txt")

if not os.path.exists(COOKIE_FILE_PATH):
    log.warning(f"¡ATENCIÓN! No se encontró el archivo de cookies en {COOKIE_FILE_PATH}. Las descargas de Instagram/privadas fallarán.")
else:
    log.info(f"Archivo de cookies cargado desde: {COOKIE_FILE_PATH}")

# Asegúrate de que ADMIN_USER_ID sea accesible, importándolo si es necesario
try:
    from config import ADMIN_USER_ID as CONFIG_ADMIN_ID # Usa un alias si prefieres
except ImportError:
    CONFIG_ADMIN_ID = "ID_Admin_Desconocido"
    log.warning("No se pudo importar ADMIN_USER_ID para get_help_text.")

def get_help_text():
    """Genera y devuelve el texto de ayuda como una cadena."""
    admin_id = CONFIG_ADMIN_ID # Usa la variable cargada/importada
    help_content = (
        "ℹ️ **Ayuda del Bot Descargador** ℹ️\n\n"
        "**Cómo usar:**\n"
        "1. Envía el enlace (URL) del video que quieres descargar.\n"
        "2. Selecciona si tu dispositivo es Android o iOS (Apple).\n"
        "3. Elige la resolución deseada o la opción 'Solo Audio (MP3)'.\n"
        "4. Espera mientras descargo, proceso (si es necesario) y subo el archivo.\n\n"
        "**Comandos:**\n"
        "`/start` - Muestra el mensaje de bienvenida.\n"
        "`/help` - Muestra este mensaje de ayuda.\n"
        # Comandos de admin
        f"`/add_user <ID>` - (Solo Admin: {admin_id}) Añade un usuario.\n"
        f"`/remove_user <ID>` - (Solo Admin: {admin_id}) Elimina un usuario.\n"
        f"`/list_users` - (Solo Admin: {admin_id}) Muestra usuarios permitidos.\n\n"
        "**Notas:**\n"
        "- Se intentará re-codificar los videos para iOS para asegurar la compatibilidad.\n"
        "- Hay un límite de tamaño de archivo de ~2GB para subidas a Telegram.\n"
        "- Las descargas/codificaciones pueden tardar dependiendo del tamaño y la carga del servidor.\n\n"
        "**Sitios Soportados (Ejemplos Comunes):**\n"
        "El bot utiliza `yt-dlp`, que es compatible con cientos de páginas web. El éxito real depende de la URL específica, las protecciones anti-descarga del sitio y si el contenido requiere inicio de sesión.\n"
        "Algunos ejemplos populares incluyen:\n"
        "- **Plataformas Principales:** YouTube, Vimeo, Dailymotion\n"
        "- **Redes Sociales:** Facebook, Twitter/X, Instagram, TikTok, Reddit, Pinterest\n"
        "- **Streaming/VOD:** Twitch (VODs/Clips), Kick (VODs/Clips)\n"
        "- **Música/Audio:** SoundCloud, Bandcamp\n"
        "- **Otros:** Muchas webs de noticias (BBC, CNN...), educativas (Khan Academy...) y sitios con vídeos incrustados.\n\n"
        "*Importante: La compatibilidad puede variar y requiere mantener la librería `yt-dlp` actualizada. Sitios con fuertes protecciones o contenido de pago pueden no funcionar.*"
    )
    return help_content

# --- Funciones Auxiliares ---
def format_duration(seconds: int | float | None) -> str:
    """Formatea segundos a una cadena HH:MM:SS o MM:SS."""
    if seconds is None or not isinstance(seconds, (int, float)) or seconds <= 0:
        return "" # Devuelve cadena vacía si la duración no es válida o no existe
    try:
        seconds = int(seconds) # Convertir a entero por si acaso
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            # Formato HH:MM:SS si hay horas
            return f"{h:d}:{m:02d}:{s:02d}"
        else:
            # Formato MM:SS si solo hay minutos y segundos
            return f"{m:02d}:{s:02d}"
    except Exception as e:
         # Registrar un warning si ocurre un error inesperado al formatear
         log.warning(f"Error al formatear la duración {seconds}: {e}")
         return "" # Devolver cadena vacía en caso de error

async def update_config_allowed_users(user_id_to_add=None, user_id_to_remove=None):
    """Actualiza la lista ALLOWED_USERS en config.py de forma segura."""
    async with CONFIG_LOCK:
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config.py")
            with open(config_path, "r", encoding="utf-8") as f:
                config_content = f.read()

            # Usar regex para encontrar la línea de ALLOWED_USERS
            pattern = r"^\s*(ALLOWED_USERS\s*=\s*)(\[.*?\])"
            match = re.search(pattern, config_content, re.MULTILINE | re.DOTALL)

            if not match:
                log.error("No se encontró la línea 'ALLOWED_USERS = [...]' en config.py")
                return False

            prefix = match.group(1)
            current_list_str = match.group(2)

            try:
                current_list = literal_eval(current_list_str)
                if not isinstance(current_list, list):
                    raise ValueError("ALLOWED_USERS no es una lista válida en config.py")
            except (ValueError, SyntaxError) as e:
                log.error(f"Error al parsear ALLOWED_USERS desde config.py: {e}")
                return False

            list_changed = False
            if user_id_to_add and user_id_to_add not in current_list:
                current_list.append(user_id_to_add)
                list_changed = True
                log.info(f"Añadiendo usuario {user_id_to_add} a ALLOWED_USERS.")

            if user_id_to_remove and user_id_to_remove in current_list:
                current_list.remove(user_id_to_remove)
                list_changed = True
                log.info(f"Eliminando usuario {user_id_to_remove} de ALLOWED_USERS.")

            if list_changed:
                current_list = sorted(list(set(current_list))) # Ordenar y eliminar duplicados
                # Reconstruir la línea con formato adecuado
                new_list_str = "[\n"
                for i, user_id in enumerate(current_list):
                    new_list_str += f"    {user_id},"
                    if (i + 1) % 5 == 0: # Añadir salto de línea cada 5 IDs (opcional)
                      new_list_str += "\n"
                    elif i < len(current_list) -1:
                         new_list_str += " " # Espacio si no es el último ni fin de línea
                new_list_str += "\n]" if not new_list_str.endswith("\n") else "]"


                # Reemplazar la vieja lista con la nueva en el contenido del archivo
                new_config_content = re.sub(pattern, prefix + new_list_str, config_content, count=1, flags=re.MULTILINE | re.DOTALL)

                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(new_config_content)

                # Actualizar la variable global en memoria
                global ALLOWED_USERS
                ALLOWED_USERS = current_list
                log.info("Archivo config.py actualizado y variable global ALLOWED_USERS recargada.")
                return True
            else:
                log.info("No hubo cambios en ALLOWED_USERS.")
                return True # No hubo error, simplemente no se cambió nada

        except FileNotFoundError:
            log.error(f"Error: No se encontró el archivo de configuración en {config_path}")
            return False
        except Exception as e:
            log.error(f"Error inesperado actualizando config.py: {e}")
            return False

def is_authorized(user_id: int) -> bool:
    """Comprueba si un ID de usuario está en la lista global ALLOWED_USERS."""
    return user_id in ALLOWED_USERS

async def edit_message_safe(message: Message, text: str, reply_markup=None):
    """Edita un mensaje de forma segura, ignorando MessageNotModified."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.MARKDOWN)
    except MessageNotModified:
        pass # Ignorar si el texto es el mismo
    except FloodWait as e:
        log.warning(f"FloodWait al editar mensaje: esperando {e.x} segundos.")
        await asyncio.sleep(e.x)
        await edit_message_safe(message, text, reply_markup) # Reintentar
    except Exception as e:
        log.error(f"Error al editar mensaje {message.id}: {e}")

def create_progress_bar(percentage: float, total_segments: int = 15) -> str:
    """Crea una barra de progreso textual."""
    filled = int(total_segments * percentage / 100)
    # Usa diferentes bloques para descarga y subida/codificación si quieres
    bar = "🟥" * filled + "⬜" * (total_segments - filled)
    return bar

# --- Clase para el Hook de Progreso de yt-dlp ---
class ProgressHook:
    def __init__(self, message: Message, loop: asyncio.AbstractEventLoop, cancel_event: threading.Event, video_id: str):
        self.message = message
        self.loop = loop
        self.cancel_event = cancel_event
        self.video_id = video_id
        self.start_time = time.time()
        # --- Nuevos parámetros y estado ---
        self.update_interval = 3.0
        self.min_percentage_change = 1.0
        self.last_percentage = -1.0 # Empezar en -1 para forzar la primera actualización
        self.last_update_time = 0.0
        # --- Fin nuevos parámetros ---

    def __call__(self, d):
        """
        Hook llamado por yt-dlp durante la descarga.
        Actualiza el mensaje de progreso usando lógica AND para throttling.
        """
        # 1. Comprobar cancelación primero
        if self.cancel_event.is_set():
            log.warning(f"[{self.video_id}] Cancelación detectada en progress_hook.")
            raise yt_dlp.utils.DownloadError("Descarga cancelada por el usuario.") # Detiene yt-dlp

        # 2. Procesar estado 'downloading'
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)

            # Solo proceder si tenemos datos válidos para calcular porcentaje
            if total_bytes and total_bytes > 0 and downloaded_bytes >= 0:
                percentage = (downloaded_bytes / total_bytes) * 100
                now = time.time()
                should_update = False

                # --- Lógica AND Refinada para decidir si actualizar ---
                current_pct = percentage
                last_saved = self.last_percentage
                last_time = self.last_update_time

                is_final_update = (current_pct >= 100.0)
                # Primera actualización si antes no teníamos % válido (era < 0)
                is_first_update = (last_saved < 0 and current_pct >= 0)
                time_passed = (now - last_time >= self.update_interval)
                change_is_significant = (abs(current_pct - last_saved) >= self.min_percentage_change)

                # Actualizar si es la primera, la última, O si AMBAS (tiempo Y cambio) se cumplen
                if is_final_update or is_first_update or (time_passed and change_is_significant):
                    # Adicional: Solo actualizar si el % es diferente al último guardado
                    # O si es la actualización final (para asegurar el 100%)
                    if current_pct != last_saved or is_final_update:
                        should_update = True
                # --- Fin Lógica AND ---

                if should_update:
                    # Actualizar estado para la próxima comprobación
                    self.last_update_time = now
                    self.last_percentage = current_pct # Guardar el % calculado actual

                    # --- Formatear Mensaje ---
                    # Asegurar que no mostramos más de 100%
                    display_pct = min(100.0, current_pct)
                    try:
                        # Asume que tienes definida create_progress_bar
                        bar = create_progress_bar(display_pct)
                    except NameError:
                        log.error("La función create_progress_bar no está definida.")
                        bar = "[ progreso ]" # Fallback

                    speed = d.get('speed')
                    eta = d.get('eta')
                    speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A"
                    eta_str = f"{int(eta // 60)}m {int(eta % 60):02d}s" if eta is not None else "N/A"
                    downloaded_mb = downloaded_bytes / 1024 / 1024
                    total_mb = total_bytes / 1024 / 1024

                    text = (
                        f"📥 **Descargando...**\n"
                        f"`{bar}`\n"
                        f"`{display_pct:.1f}%` de `{total_mb:.2f} MB`\n"
                        f"Velocidad: `{speed_str}` | ETA: `{eta_str}`"
                    )

                    # --- Programar Edición del Mensaje ---
                    cancel_button = InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Cancelar Descarga", callback_data=f"cancel_dl|{self.video_id}")
                    ]])

                    # Usar call_soon_threadsafe porque este hook se ejecuta en el hilo de yt-dlp
                    try:
                        self.loop.call_soon_threadsafe(
                            asyncio.create_task,
                            edit_message_safe(self.message, text, reply_markup=cancel_button)
                        )
                    except Exception as e:
                        log.error(f"[{self.video_id}] Error programando edición de mensaje desde hook: {e}")

        # 3. Manejar otros estados (opcional)
        elif d['status'] == 'finished':
            log.info(f"[{self.video_id}] yt-dlp hook reportó 'finished'. Duración: {time.time() - self.start_time:.2f}s")
            # Es mejor que el mensaje final ("Descarga completa", "Recodificando", etc.)
            # lo ponga la función principal que llamó a la descarga, no el hook.

        elif d['status'] == 'error':
            # El error real se captura donde se llama a ydl.download()
            log.error(f"[{self.video_id}] yt-dlp hook reportó un error: {d.get('filename') or 'N/A'} - {d.get('error')}")
# --- Función de Progreso para Subida de Pyrogram ---
async def upload_progress_callback(current, total, message: Message, start_time, video_id: str, action: str = "Subiendo"):
    update_interval = 3.0
    min_percentage_change = 1.0
    percentage = (current / total) * 100
    now = time.time()
    elapsed_time = now - start_time
    if elapsed_time == 0: elapsed_time = 1 # Evitar división por cero

    speed = current / elapsed_time
    speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
    eta = (total - current) / speed if speed > 0 else 0
    eta_str = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 0 else "N/A"
    current_mb = current / 1024 / 1024
    total_mb = total / 1024 / 1024

    bar = create_progress_bar(percentage)

    text = (
        f"⏫ **{action}...**\n"
        f"`{bar}`\n"
        f"`{percentage:.1f}%` de `{total_mb:.2f} MB`\n"
        f"Velocidad: `{speed_str}` | ETA: `{eta_str}`"
    )

    # Actualizar el mensaje (ya estamos en el loop de asyncio aquí)
    # Añadir un try-except simple para FloodWait aquí también
    try:
        # Evitar demasiadas actualizaciones, pyrogram puede manejarlo internamente
        # pero podemos limitar un poco si es necesario
        # Evitar demasiadas actualizaciones, actualizar cada 5 segundos
       if not hasattr(message, 'last_upload_update_time') or now - message.last_upload_update_time > 5:
           await edit_message_safe(message, text)
           message.last_upload_update_time = now
    except FloodWait as e:
        log.warning(f"[{video_id}] FloodWait durante la subida: {e.x}s")
        await asyncio.sleep(e.x)
    except Exception as e:
        # Ignorar MessageNotModified u otros errores menores aquí
        if "MessageNotModified" not in str(e):
            log.warning(f"[{video_id}] Error menor actualizando progreso de subida: {e}")
        pass


# Asume que estas variables/funciones están definidas en otra parte:
log = logging.getLogger(__name__) # Asegúrate de tener un logger configurado
FFMPEG_PATH = "ffmpeg" # O la ruta completa a tu ejecutable ffmpeg
FFPROBE_PATH = "ffprobe" # O la ruta completa a tu ejecutable ffprobe
# async def edit_message_safe(message: Message, text: str, reply_markup=None): ... # Tu función segura para editar mensajes
# def create_progress_bar(percentage: float) -> str: ... # Tu función para crear la barra

# --- Constante para el tamaño del chunk ---
CHUNK_SIZE = 1024 # Leer hasta 1KB a la vez

# --- Función auxiliar para procesar una línea completa de FFmpeg ---
# Esta función es síncrona, toma la línea y el estado actual,
# y devuelve información para que el bucle principal actúe.
def parse_ffmpeg_progress_line(line: str, video_id: str, total_duration_ms: int) -> tuple[float, bool]:
    """
    Parsea una línea de progreso de FFmpeg y calcula el porcentaje.

    Args:
        line: La línea de texto decodificada.
        video_id: ID del video para logging.
        total_duration_ms: Duración total del video en ms.

    Returns:
        Una tupla: (percentage, is_progress_end_signal)
        - percentage: El porcentaje calculado (0-100) o -1 si no es una línea de tiempo/fin.
        - is_progress_end_signal: True si la línea es "progress=end", False en caso contrario.
    """
    current_ms = -1
    percentage = -1.0
    is_progress_end_signal = False

    # Comprobar si es la señal de fin
    if line == "progress=end":
        log.info(f"[{video_id}] Línea 'progress=end' detectada por el parser.")
        is_progress_end_signal = True
        percentage = 100.0 # Considerar 100% al final
        return percentage, is_progress_end_signal

    # Parsear tiempo si la línea es relevante
    if line.startswith("out_time_ms="):
        parts = line.split("=", 1)
        if len(parts) == 2:
            val = parts[1].strip()
            if val.upper() != "N/A":
                try:
                    current_ms = int(val)
                    # log.debug(f"[{video_id}] Helper: Parsed out_time_ms: {current_ms}")
                except ValueError:
                    log.warning(f"[{video_id}] Helper: No se pudo parsear out_time_ms desde '{line}'")
    elif line.startswith("out_time="):
        parts = line.split("=", 1)
        if len(parts) > 1:
             time_str = parts[1].split()[0]
             if time_str.upper() != "N/A":
                try:
                    if "." in time_str:
                        h, m, s_ms = time_str.split(":")
                        s, ms_str = s_ms.split(".")
                        ms = int(ms_str.ljust(6, '0')[:6]) // 1000
                        current_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + ms
                    else:
                         h, m, s = map(int, time_str.split(':'))
                         current_ms = (h * 3600 + m * 60 + s) * 1000
                    # log.debug(f"[{video_id}] Helper: Parsed out_time: {current_ms}")
                except Exception as parse_err:
                    log.warning(f"[{video_id}] Helper: Error parseando out_time '{line}': {parse_err}")
        else:
             log.warning(f"[{video_id}] Helper: Formato inesperado para out_time: '{line}'")

    # Calcular porcentaje si se obtuvo tiempo
    if current_ms >= 0:
        # log.debug(f"[{video_id}] Helper: Values before calc: current_ms={current_ms}, total_duration_ms={total_duration_ms}")
        if total_duration_ms > 0:
            raw_pct = (current_ms / total_duration_ms) * 100
            # log.debug(f"[{video_id}] Helper: Calculated raw_pct: {raw_pct:.4f}")
            percentage = min(100.0, raw_pct) # Simple capping
            # log.debug(f"[{video_id}] Helper: Final percentage (non-monotonic): {percentage:.2f}")
        else:
            percentage = 0.0 # Devolver 0% si la duración es 0 en lugar de -1
            log.debug(f"[{video_id}] Helper: Percentage set to 0.0 (total_duration_ms <= 0)")

    # Devolver -1 si no se pudo calcular un porcentaje válido en esta línea
    return percentage, is_progress_end_signal


async def recode_video_ios(input_path: str, output_path: str, message: Message, video_id: str, cancel_event: threading.Event, yt_dlp_info: dict):
    """Recodifica el video a H.264 compatible con iOS usando FFmpeg, mostrando progreso (lectura por chunks)."""
    log.info(f"[{video_id}] Iniciando recodificación para iOS: {input_path} -> {output_path}")

    # --- 1. Obtener duración total ---
    duration_sec = 0.0 # Inicializar como float
    # Intento 1: Usar ffprobe (más preciso si funciona)
    try:
        log.info(f"[{video_id}] Intentando obtener duración con ffprobe...")
        ffprobe_cmd = [
            FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', input_path
        ]
        process_probe = await asyncio.create_subprocess_exec(
            *ffprobe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_probe, stderr_probe = await process_probe.communicate()
        if process_probe.returncode == 0 and stdout_probe:
            duration_str = stdout_probe.decode().strip()
            try: # Añadir try-except para la conversión a float
                 duration_sec = float(duration_str)
                 log.info(f"[{video_id}] Duración obtenida por ffprobe: {duration_sec:.2f}s")
            except ValueError:
                 log.warning(f"[{video_id}] ffprobe devolvió una duración no numérica: '{duration_str}'")
                 duration_sec = 0.0
        else:
            log.warning(f"[{video_id}] ffprobe no pudo obtener duración (código: {process_probe.returncode}). Stderr: {stderr_probe.decode(errors='ignore')}")
    except FileNotFoundError:
        log.error(f"[{video_id}] Error: '{FFPROBE_PATH}' no encontrado. Asegúrate de que ffprobe está instalado y en el PATH o configurado.")
    except Exception as e:
        log.error(f"[{video_id}] Error inesperado al ejecutar ffprobe: {e}")

    # Intento 2: Usar duración de yt-dlp info como fallback
    if duration_sec <= 0 and yt_dlp_info:
        log.warning(f"[{video_id}] Usando duración de yt-dlp como fallback.")
        duration_from_yt = yt_dlp_info.get('duration')
        if not duration_from_yt and 'entries' in yt_dlp_info and yt_dlp_info['entries']:
            duration_from_yt = yt_dlp_info['entries'][0].get('duration')

        # Asegurarse que la duración de yt-dlp es numérica
        if isinstance(duration_from_yt, (int, float)) and duration_from_yt > 0:
            duration_sec = float(duration_from_yt)
            log.info(f"[{video_id}] Duración obtenida de yt-dlp info: {duration_sec:.2f}s")
        else:
            log.warning(f"[{video_id}] No se pudo obtener duración válida de yt-dlp info (valor: {duration_from_yt}).")
            duration_sec = 0.0 # Asegurar que es float

    # Asignación y log de duración final
    if duration_sec <= 0:
        log.error(f"[{video_id}] No se pudo obtener una duración válida. Progreso no será preciso.")
        # Asignar un valor por defecto > 0 para evitar división por cero, aunque el % será incorrecto
        total_duration_ms = 60000 # Ej: 60 segundos por defecto si falla todo
        log.warning(f"[{video_id}] Usando duración por defecto: {total_duration_ms} ms")
    else:
        total_duration_ms = int(duration_sec * 1000)
        log.info(f"[{video_id}] Duración total para cálculo de progreso: {total_duration_ms} ms ({duration_sec:.2f}s)")


    # --- 2. Comando FFmpeg ---
    # --- 2. Comando FFmpeg ---
    ffmpeg_cmd = [
        FFMPEG_PATH,
        # Input
        '-i', input_path,
        # Codec de Video por CPU y calidad
        '-c:v', 'libx264',                   # CAMBIADO: Usamos el codificador de CPU libx264
        '-preset', 'medium',                 # MANTENIDO: Un buen balance entre velocidad y compresión para CPU
        '-crf', '23',                        # CAMBIADO: Control de calidad para libx264 (valor común, 18-28)
        # Codec de Audio - Copiar
        '-c:a', 'copy',
        # Otros flags
        '-movflags', '+faststart',
        '-progress', 'pipe:1',
        '-y',
        output_path
    ]

    log.info(f"[{video_id}] Comando FFmpeg final a ejecutar: {' '.join(ffmpeg_cmd)}")

    
    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Añadir potencialmente 'creationflags' en Windows para evitar ventana de consola
            # creationflags=asyncio.subprocess.CREATE_NO_WINDOW
        )
    except FileNotFoundError:
        log.error(f"[{video_id}] Error: '{FFMPEG_PATH}' no encontrado.")
        await edit_message_safe(message, "❌ Error: `ffmpeg` no encontrado.")
        return False
    except Exception as proc_err:
        log.error(f"[{video_id}] Error al iniciar el proceso ffmpeg: {proc_err}")
        await edit_message_safe(message, f"❌ Error al iniciar ffmpeg: `{proc_err}`")
        return False

    # --- 3. Leer progreso y actualizar mensaje (MODIFICADO PARA CHUNKS) ---
    pid = process.pid
    log.info(f"[{video_id}] Proceso FFmpeg iniciado (PID: {pid})")

    # Parámetros de actualización y estado local
    update_interval = 3.0
    min_percentage_change = 1.0
    progress_state = {
        'last_update_time': 0.0,
        'last_saved_pct': -1.0, # Empezar en -1 para forzar primera update
        'current_percentage': 0.0
    }
    stdout_buffer = b""
    exit_loop_signal = False
    # Tarea para monitorizar cancelación (sin cambios)
    async def check_cancel():
        while process.returncode is None:
            if cancel_event.is_set():
                log.warning(f"[{video_id}] Cancelación detectada durante recodificación. Terminando FFmpeg (PID: {pid}).")
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    log.warning(f"[{video_id}] FFmpeg no terminó tras terminate, forzando kill.")
                    process.kill() # Usar kill si terminate falla
                except ProcessLookupError:
                     log.warning(f"[{video_id}] Proceso FFmpeg ya había terminado al intentar cancelar.")
                except Exception as kill_err:
                    log.error(f"[{video_id}] Error matando FFmpeg: {kill_err}")
                return True # Indica que se intentó cancelar
            await asyncio.sleep(0.5) # Comprobar cancelación más a menudo
        return False # Indica que no se canceló aquí

    cancel_monitor_task = asyncio.create_task(check_cancel())

    log.debug(f"[{video_id}] Entering progress reading loop (Chunk Mode)...")
    while not exit_loop_signal:
        # 1) Comprobar cancelación externa (Tarea)
        if cancel_monitor_task.done():
             was_cancelled_by_task = cancel_monitor_task.result()
             if was_cancelled_by_task:
                 log.warning(f"[{video_id}] Cancelación detectada por la tarea check_cancel. Saliendo del bucle.")
                 exit_loop_signal = True # Salir del bucle principal
                 continue # Ir al final del bucle para salir limpiamente

        # 2) Leer un chunk de stdout
        chunk = b''
        try:
            # Esperar máximo 0.5 segundos por datos nuevos para mantener responsividad
            chunk = await asyncio.wait_for(process.stdout.read(CHUNK_SIZE), timeout=0.5)
            # log.debug(f"[{video_id}] Read chunk size: {len(chunk)}") # Log opcional

        except asyncio.TimeoutError:
            # Es normal no recibir datos en 0.5s, no es un error
            if process.returncode is not None:
                log.info(f"[{video_id}] Proceso terminó (código {process.returncode}) durante timeout de lectura. Saliendo.")
                exit_loop_signal = True
            continue # No hay datos nuevos, volver a iterar (comprobar cancel, etc.)

        except asyncio.CancelledError:
             log.warning(f"[{video_id}] Tarea de lectura cancelada.")
             exit_loop_signal = True # Salir si la tarea principal se cancela

        except Exception as err:
            # Podría ser BrokenPipeError si el proceso muere inesperadamente
            log.error(f"[{video_id}] Error leyendo chunk de stdout: {err}")
            exit_loop_signal = True # Salir del bucle

        # Si read() devuelve vacío, es EOF
        if not chunk and not exit_loop_signal: # Solo si no estamos ya saliendo
            log.info(f"[{video_id}] stdout.read() retornó EOF.")
            # Esperar un instante por si el proceso termina justo después
            await asyncio.sleep(0.1)
            if process.returncode is not None:
                 log.info(f"[{video_id}] Proceso confirmado terminado (código {process.returncode}) tras EOF.")
            else:
                 log.warning(f"[{video_id}] EOF recibido pero el proceso sigue vivo? (returncode={process.returncode})")
            exit_loop_signal = True # Señal para salir

        # 3) Procesar el buffer acumulado + nuevo chunk
        stdout_buffer += chunk
        while b'\n' in stdout_buffer and not exit_loop_signal:
            line_bytes, stdout_buffer = stdout_buffer.split(b'\n', 1)
            line_str = line_bytes.decode('utf-8', errors='ignore').strip()

            if line_str: # Solo procesar líneas no vacías
                # log.debug(f"[{video_id}] Processing line: '{line_str}'")
                percentage_from_line, is_end = parse_ffmpeg_progress_line(line_str, video_id, total_duration_ms)

                if is_end:
                    exit_loop_signal = True # Señal para salir de ambos bucles
                    progress_state['current_percentage'] = 100.0 # Forzar 100% al final
                    # No romper el bucle interno aquí, permitir que la actualización ocurra abajo
                elif percentage_from_line >= 0: # Actualizar solo si es válido
                     progress_state['current_percentage'] = percentage_from_line

        # --- Fin del bucle interno de procesamiento de líneas ---

        # 4) Decidir si actualizar el mensaje (fuera del bucle interno)
        now = time.time()
        should_update = False
        # Usar max para asegurar que no mostramos < 0% y mantenemos 100% si se alcanzó
        current_pct = max(0.0, progress_state['current_percentage'])
        last_saved = progress_state['last_saved_pct']
        last_time = progress_state['last_update_time']

        # Criterios para actualizar:
        is_final_update = exit_loop_signal and current_pct >= 100.0 # Actualizar si salimos y es 100%
        is_time_to_update = (now - last_time > update_interval)
        is_significant_change = (current_pct - last_saved >= min_percentage_change)
        is_first_real_update = (last_saved < 0 and current_pct >= 0) # Primera vez que tenemos %

        if is_final_update or is_time_to_update or is_significant_change or is_first_real_update:
             # Solo actualizar si el porcentaje realmente cambió o si es la actualización final
             if current_pct != last_saved or is_final_update:
                 should_update = True

        # 5) Enviar actualización si procede
        if should_update:
            # Asegurarse de no exceder 100% visualmente
            display_pct = min(100.0, current_pct)

            log.info(f"[{video_id}] Actualizando mensaje con porcentaje {display_pct:.1f}%")
            progress_state['last_update_time'] = now
            progress_state['last_saved_pct'] = display_pct # Guardar el % mostrado
            # Actualizar también el estado externo si aún lo usas
            # message._last_recode_percentage = display_pct # Opcional

            bar = create_progress_bar(display_pct)
            text = (
                f"📱 **Recodificando para iOS...**\n"
                f"`{bar}`\n"
                f"`{display_pct:.1f}%` completado"
            )
            # Mostrar botón de cancelar solo si no hemos terminado
            current_reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancelar Re-Codificación", callback_data=f"cancel_dl|{video_id}")
            ]]) if not exit_loop_signal else None # Quitar botón al final

            # Realizar la actualización asíncrona
            try:
                 await edit_message_safe(message, text, reply_markup=current_reply_markup)
            except Exception as edit_err:
                 log.warning(f"[{video_id}] Error al editar mensaje: {edit_err}")

    # --- Fin del bucle principal 'while not exit_loop_signal:' ---

    # Procesar cualquier resto en el buffer (opcional, podría ser redundante)
    # if stdout_buffer:
    #    log.debug(f"[{video_id}] Procesando buffer restante final: {stdout_buffer!r}")
    #    # ... (lógica similar de procesar líneas si es necesario) ...

    log.info(f"[{video_id}] Salió del bucle de progreso (Chunk Mode). Esperando finalización...")

    # --- 4. Esperar finalización y comprobar resultado ---
    # Cancelar explícitamente la tarea monitora si sigue corriendo
    if not cancel_monitor_task.done():
        cancel_monitor_task.cancel()
        try:
            await cancel_monitor_task # Esperar a que se complete la cancelación
        except asyncio.CancelledError:
            log.debug(f"[{video_id}] Tarea check_cancel cancelada correctamente.")
        except Exception as task_err:
             log.warning(f"[{video_id}] Error esperado al cancelar check_cancel: {task_err}")


    # Verificar si la cancelación ocurrió ANTES de communicate
    was_cancelled_by_flag = cancel_event.is_set()
    if was_cancelled_by_flag:
         log.warning(f"[{video_id}] Cancelación detectada ANTES de communicate().")
         # Asegurarse que el proceso realmente terminó
         if process.returncode is None:
              log.warning(f"[{video_id}] Proceso aún vivo tras cancelación, intentando communicate/kill...")
              try:
                   # Intentar communicate con timeout corto para obtener stderr
                   _, stderr_cancel = await asyncio.wait_for(process.communicate(), timeout=2.0)
                   log.warning(f"[{video_id}] FFmpeg stderr tras cancelación: {stderr_cancel.decode(errors='ignore')}")
              except asyncio.TimeoutError:
                   log.warning(f"[{video_id}] Timeout en communicate tras cancelación, forzando kill.")
                   try: process.kill()
                   except Exception: pass
              except Exception as e:
                   log.error(f"[{video_id}] Error en communicate/kill tras cancelación: {e}")
         return False # Retornar fallo por cancelación


    # Proceder a communicate si no hubo cancelación previa
    try:
        log.info(f"[{video_id}] Esperando process.communicate() (PID: {pid})...")
        stdout_rem, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
        return_code = process.returncode
        log.info(f"[{video_id}] FFmpeg (PID: {pid}) terminó con código {return_code}.")

        # Verificar si la cancelación ocurrió JUSTO ANTES de que terminara
        if return_code != 0 and cancel_event.is_set():
             log.warning(f"[{video_id}] FFmpeg terminó con error ({return_code}) posiblemente debido a cancelación tardía.")
             stderr_decoded = stderr.decode(errors='ignore')
             log.warning(f"[{video_id}] FFmpeg stderr (cancelación tardía):\n{stderr_decoded}")
             # Considerar retornar False por cancelación aquí también
             # await edit_message_safe(message, "⚠️ Recodificación cancelada durante finalización.") # Mensaje opcional
             return False

        # Procesar resultado normal
        if return_code != 0:
            log.error(f"[{video_id}] Error en FFmpeg (PID: {pid}). Código: {return_code}")
            stderr_decoded = stderr.decode(errors='ignore')
            stdout_decoded = stdout_rem.decode(errors='ignore')
            log.error(f"[{video_id}] FFmpeg stderr:\n{stderr_decoded}")
            if stdout_decoded.strip():
                 log.error(f"[{video_id}] FFmpeg stdout restante:\n{stdout_decoded}")
            error_summary = stderr_decoded.strip().split('\n')[-1] if stderr_decoded.strip() else f"Código de error {return_code}"
            await edit_message_safe(message, f"❌ **Error durante la recodificación para iOS.**\n`{error_summary}`\nConsulta logs.")
            return False
        else:
            log.info(f"[{video_id}] Recodificación para iOS completada con éxito.")
            stderr_decoded = stderr.decode(errors='ignore')
            stdout_decoded = stdout_rem.decode(errors='ignore')
            if stderr_decoded.strip():
                 log.info(f"[{video_id}] FFmpeg stderr final (éxito):\n{stderr_decoded}")
            if stdout_decoded.strip():
                 log.info(f"[{video_id}] FFmpeg stdout final (éxito):\n{stdout_decoded}")
            await edit_message_safe(message, "✅ Recodificación completa. Preparando subida...", reply_markup=None)
            return True

    except asyncio.TimeoutError:
        log.error(f"[{video_id}] Timeout esperando process.communicate() (PID: {pid}). Forzando kill.")
        if process.returncode is None:
            try: process.kill()
            except Exception as kill_err: log.error(f"[{video_id}] Error al forzar kill: {kill_err}")
        await edit_message_safe(message, "❌ Error: FFmpeg no respondió al finalizar.")
        return False
    except Exception as e:
        log.error(f"[{video_id}] Error inesperado en communicate() (PID: {pid}): {e}")
        await edit_message_safe(message, f"❌ Error al finalizar ffmpeg: `{e}`")
        return False

# --- Comandos del Bot ---

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        log.info(f"Usuario no autorizado {message.from_user.id} ({message.from_user.username}) intentó usar /start.")
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🙏 Solicitar Acceso", callback_data="request_access")
        ]])
        await message.reply_text(
            "🚫 **Acceso Denegado** 🚫\n\n"
            "No tienes permiso para usar este bot.\n"
            "Si crees que esto es un error, puedes solicitar acceso al administrador.",
            reply_markup=markup
        )
        return

    log.info(f"Usuario autorizado {user_id} ({message.from_user.username}) usó /start.")

    # --- INICIO: Añadir botón de ayuda ---
    # Crear el botón
    help_button = InlineKeyboardButton(
        text="ℹ️ Mostrar Ayuda",
        callback_data="show_help"  # Identificador único para este botón
    )
    # Crear el teclado inline con el botón
    start_markup = InlineKeyboardMarkup(
        [[help_button]] # Una fila con un botón
    )

    # Texto de bienvenida
    start_text = (
        f"👋 ¡Hola {message.from_user.first_name}!\n\n"
        "Soy tu asistente para descargar videos.\n"
        "Simplemente envíame un enlace de video (YouTube, Twitter, etc.) y te ayudaré a descargarlo.\n\n"
        "Pulsa el botón de abajo o usa /help para ver los comandos y más información." # Texto ligeramente modificado
    )

    # Enviar el mensaje con el texto y el teclado
    await message.reply_text(
        start_text,
        reply_markup=start_markup
    )
    # --- FIN: Añadir botón de ayuda ---

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await message.reply_text("🚫 No tienes permiso para ver la ayuda.")
        return

    help_text_content = get_help_text() # Obtener el texto de la función auxiliar
    await message.reply_text(help_text_content, parse_mode=enums.ParseMode.MARKDOWN)
# --- Comandos de Administración ---

@bot.on_message(filters.command("add_user") & filters.private)
async def add_user_command(client: Client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        return # Ignorar silenciosamente si no es admin

    if len(message.command) != 2:
        await message.reply_text("❌ Uso incorrecto. Ejemplo: `/add_user 123456789`")
        return

    try:
        user_id_to_add = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ El ID de usuario debe ser un número entero.")
        return

    if user_id_to_add in ALLOWED_USERS:
        await message.reply_text(f"ℹ️ El usuario `{user_id_to_add}` ya está autorizado.")
        return

    success = await update_config_allowed_users(user_id_to_add=user_id_to_add)
    if success:
        await message.reply_text(f"✅ Usuario `{user_id_to_add}` añadido correctamente a la lista de permitidos.")
        log.info(f"Admin {ADMIN_USER_ID} añadió al usuario {user_id_to_add}.")
        # Opcional: Notificar al usuario añadido
        try:
            await client.send_message(user_id_to_add, "🎉 ¡Buenas noticias! Has sido autorizado para usar el bot de descargas.")
        except Exception as e:
            log.warning(f"No se pudo notificar al usuario recién añadido {user_id_to_add}: {e}")
    else:
        await message.reply_text("❌ Ocurrió un error al actualizar el archivo de configuración.")

@bot.on_message(filters.command("remove_user") & filters.private)
async def remove_user_command(client: Client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    if len(message.command) != 2:
        await message.reply_text("❌ Uso incorrecto. Ejemplo: `/remove_user 123456789`")
        return

    try:
        user_id_to_remove = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ El ID de usuario debe ser un número entero.")
        return

    if user_id_to_remove == ADMIN_USER_ID:
        await message.reply_text("❌ No puedes eliminar al administrador principal.")
        return

    if user_id_to_remove not in ALLOWED_USERS:
        await message.reply_text(f"ℹ️ El usuario `{user_id_to_remove}` no se encuentra en la lista de autorizados.")
        return

    success = await update_config_allowed_users(user_id_to_remove=user_id_to_remove)
    if success:
        await message.reply_text(f"✅ Usuario `{user_id_to_remove}` eliminado correctamente de la lista de permitidos.")
        log.info(f"Admin {ADMIN_USER_ID} eliminó al usuario {user_id_to_remove}.")
        # Opcional: Notificar al usuario eliminado
        try:
            await client.send_message(user_id_to_remove, "ℹ️ Tu acceso al bot de descargas ha sido revocado.")
        except Exception as e:
            log.warning(f"No se pudo notificar al usuario eliminado {user_id_to_remove}: {e}")
    else:
        await message.reply_text("❌ Ocurrió un error al actualizar el archivo de configuración.")

@bot.on_message(filters.command("list_users") & filters.private)
async def list_users_command(client: Client, message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    # Es buena idea ordenar los IDs para una lista consistente
    sorted_user_ids = sorted(ALLOWED_USERS)

    if not sorted_user_ids:
        await message.reply_text("ℹ️ No hay usuarios autorizados (aparte del admin).")
        return

    user_list_text = "👥 **Usuarios Autorizados:**\n\n"
    user_details = {} # Diccionario para guardar los detalles {id: user_object}

    # --- Intenta obtener detalles de todos los usuarios en una sola llamada (más eficiente) ---
    try:
        # get_users puede aceptar una lista de IDs
        fetched_users = await client.get_users(user_ids=sorted_user_ids)
        # Crea un diccionario para fácil acceso por ID
        for user in fetched_users:
            if user: # Asegurarse de que el objeto User no sea None
              user_details[user.id] = user
    except Exception as e:
        log.error(f"Ocurrió un error al intentar obtener detalles de usuarios para /list_users: {e}")
        # Si falla la obtención masiva, se mostrará "(Info no disponible)" para todos
        pass # Continúa para mostrar al menos los IDs

    # --- Construye el texto final ---
    for user_id in sorted_user_ids:
        admin_tag = " (Admin)" if user_id == ADMIN_USER_ID else ""
        user_info_str = "" # String para la info del usuario (nick/nombre)

        user = user_details.get(user_id) # Busca el usuario en los detalles obtenidos

        if user:
            # Formatea la información: Prioriza @username, si no, nombre completo
            if user.username:
                user_info_str = f" (@{user.username})"
            elif user.first_name:
                user_info_str = f" ({user.first_name}"
                if user.last_name:
                    user_info_str += f" {user.last_name}"
                user_info_str += ")"
            elif user.last_name: # Por si solo tiene apellido (raro)
                 user_info_str = f" ({user.last_name})"
            else:
                # Si no hay username ni nombre (ej. cuenta eliminada pero ID aún en lista)
                user_info_str = " (Nombre desconocido)"
        else:
            # Si no se encontraron detalles para este ID (ej. fallo en get_users o ID inválido)
            user_info_str = " (Info no disponible)"

        # Añade la línea formateada a la lista
        user_list_text += f"- `{user_id}`{user_info_str}{admin_tag}\n"

    # Envía el mensaje completo
    await message.reply_text(user_list_text, parse_mode=enums.ParseMode.MARKDOWN)


# --- Manejador Principal de Mensajes (URLs) ---

@bot.on_message(filters.text & filters.private)
async def handle_url(client: Client, message: Message):
    # Verificar si el texto empieza con '/' para ignorar comandos no manejados explícitamente
    if message.text and message.text.startswith('/'):
        log.info(f"Ignorando comando no reconocido explícitamente: {message.text.split()[0]}")
        return # Ignorar comandos desconocidos para que no se procesen como URL

    user_id = message.from_user.id
    if not is_authorized(user_id):
        log.info(f"Usuario no autorizado {user_id} ({message.from_user.username}) envió texto: {message.text[:50]}...")
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🙏 Solicitar Acceso", callback_data="request_access")
        ]])
        await message.reply_text(
            "🚫 **Acceso Denegado** 🚫\n\n"
            "No tienes permiso para usar este bot.",
            reply_markup=markup
        )
        return
    
    # --- INICIO: Extracción de URL mejorada ---
    full_text = message.text.strip()
    potential_url = None
    url = None # Definir url aquí

    # 1. Buscar un enlace explícito (http/https)
    #    Regex: r'https?://[^\s]+' (http o https, seguido de caracteres que no sean espacio)
    #    re.IGNORECASE por si alguien escribe Https://
    url_match = re.search(r'https?://[^\s]+', full_text, re.IGNORECASE)

    if url_match:
        # Extraer el enlace y quitar puntuación final común (., !, ?, ,, ;)
        extracted = url_match.group(0)
        potential_url = extracted.rstrip('.,!?;:')
    else:
        # 2. Si no hay http/https, buscar palabras que puedan ser un enlace (ej. www. o .com)
        words = full_text.split()
        for word in words:
            # Quitar puntuación final
            cleaned_word = word.rstrip('.,!?;:')
            # Intentar añadir https y validar (validators es bueno con www. y dominios)
            url_to_validate = "https://" + cleaned_word
            
            # Comprobación simple: debe tener al menos un punto y no ser solo 'https://.'
            if "." in cleaned_word and len(cleaned_word) > 3 and validators.url(url_to_validate):
                potential_url = url_to_validate # ¡Encontrado!
                break # Usar el primero que parezca válido

    # 3. Validar la URL encontrada
    if potential_url and validators.url(potential_url):
        url = potential_url # Usamos la URL validada
        log.info(f"Usuario {user_id} envió URL (extraída de texto): {url}")
    else:
        # Si no se encontró nada válido
        await message.reply_text(
            "❌ **Enlace no encontrado.**\n"
            "No pude encontrar un enlace web válido en tu mensaje. "
            "Por favor, asegúrate de que el enlace sea correcto."
        )
        return

    chat_id = message.chat.id

    # Comprobar si ya hay una tarea para este chat
    if chat_id in download_tasks:
        await message.reply_text("⏳ Ya estoy procesando una solicitud tuya. Por favor, espera a que termine o cancela la operación actual.")
        return

    # Generar un ID único para esta solicitud/video
    # Usamos hash de URL + timestamp para más unicidad si se pide la misma URL rápido
    video_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]

    status_msg = await message.reply_text("🔍 Analizando enlace...", quote=True)

    # Guardar estado inicial
    user_requests[video_id] = {
        "url": url,
        "chat_id": chat_id,
        "os": None,
        "message_id": status_msg.id,
        "info": None, # Para guardar info de yt-dlp
        "resolutions": []
    }

    # Extraer información del video (SIN descargar) - Ejecutar en ThreadPoolExecutor
    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
        #'skip_download': True,
        'extract_flat': 'in_playlist', # Extraer info básica rápido si es playlist
        'forcejson': True, # Obtener output como JSON
    }

    if os.path.exists(COOKIE_FILE_PATH):
        ydl_opts_info['cookiefile'] = COOKIE_FILE_PATH

    try:
        log.info(f"[{video_id}] Extrayendo información con yt-dlp para {url}")
        loop = asyncio.get_running_loop()
        # yt-dlp puede bloquear, ejecutar en executor
        info_json = await loop.run_in_executor(
            None, # Usa el ThreadPoolExecutor por defecto
            lambda: yt_dlp.YoutubeDL(ydl_opts_info).extract_info(url, download=False)
        )
        # info = json.loads(info_json) # yt-dlp con forcejson ya podría devolver dict
        info = info_json # Asumimos que devuelve dict

        user_requests[video_id]["info"] = info # Guardar info completa
        log.info(f"[{video_id}] Información extraída con éxito.")

    except yt_dlp.utils.DownloadError as e:
        log.error(f"[{video_id}] Error de yt-dlp al extraer info: {e}")
        error_message = f"❌ No pude obtener información del video.\n\n**Razón:** {e}"
        # Simplificar mensajes de error comunes
        if "Unsupported URL" in str(e):
            error_message = "❌ Lo siento, esta URL no es compatible."
        elif "Video unavailable" in str(e):
             error_message = "❌ Este video no está disponible."
        elif "Private video" in str(e):
            error_message = "❌ Este es un video privado, no puedo acceder a él."
        elif "Sign in to confirm your age" in str(e):
            error_message = "❌ Este video tiene restricción de edad."

        await edit_message_safe(status_msg, error_message)
        del user_requests[video_id]
        return
    except Exception as e:
        log.exception(f"[{video_id}] Error inesperado extrayendo info: {e}")
        await edit_message_safe(status_msg, f"❌ Ocurrió un error inesperado al analizar el enlace.\n`{e}`")
        del user_requests[video_id]
        return

    # --- Procesar información y preguntar OS ---
    title = info.get('title', 'Video Desconocido')
    uploader = info.get('uploader', '')
    

    # Comprobar si es un directo (Live)
    is_live = info.get('is_live')
    if is_live:
        log.warning(f"[{video_id}] Intento de descargar un directo (Live Stream). URL: {url}. Rechazado.")
        await edit_message_safe(status_msg, "🚫 **No se pueden descargar transmisiones en vivo.**\nPor favor, envía el enlace de un video grabado.")
        # Limpiar estado
        if video_id in user_requests:
            del user_requests[video_id]
        return # Detener el procesamiento

    # Comprobar si es una lista de reproducción (playlist)
    # Una playlist puede ser tipo 'playlist' o tener múltiples 'entries'
    is_playlist = info.get('_type') == 'playlist' or ('entries' in info and isinstance(info.get('entries'), list) and len(info['entries']) > 1)
    if is_playlist:
        playlist_count = info.get('playlist_count') or len(info.get('entries', []))
        log.warning(f"[{video_id}] Intento de descargar una lista de reproducción con {playlist_count} videos. URL: {url}. Rechazado.")
        await edit_message_safe(status_msg, f"🚫 **Las descargas de listas de reproducción no están permitidas.**\nEsta URL contiene {playlist_count} videos. Por favor, envía el enlace de un video individual.")
        # Limpiar estado
        if video_id in user_requests:
            del user_requests[video_id]
        return # Detener el procesamiento
    
    # --- *** INICIO: EXTRACCIÓN Y FORMATEO DE DURACIÓN *** ---
    duration_sec = info.get('duration') # Obtener duración en segundos (puede ser None)
    duration_str = format_duration(duration_sec) # Formatear usando la función auxiliar
    # --- *** FIN: EXTRACCIÓN Y FORMATEO DE DURACIÓN *** ---

    # Mensaje inicial con título e info básica
    display_title = title[:80] + "..." if len(title) > 80 else title
    msg_text = f"🎬 **Video Encontrado:**\n`{display_title}`"
    if uploader:
        msg_text += f"\n👤 Por: `{uploader}`"
    # --- *** INICIO: AÑADIR DURACIÓN AL MENSAJE *** ---
    if duration_str: # Solo añadir si la duración se pudo formatear
        msg_text += f"\n⏱️ Duración: `{duration_str}`"
    # --- *** FIN: AÑADIR DURACIÓN AL MENSAJE *** ---
    

    msg_text += "\n\n📱 **¿En qué tipo de dispositivo verás el video?**\n*(Seleccionar iOS aplica una conversión para máxima compatibilidad)*"

    # Botones para OS
    os_buttons = [
        InlineKeyboardButton("🤖 Android / Otros", callback_data=f"os|{video_id}|android"),
        InlineKeyboardButton("🍏 iOS (iPhone/iPad)", callback_data=f"os|{video_id}|ios")
    ]
    markup = InlineKeyboardMarkup([os_buttons])

    await edit_message_safe(status_msg, msg_text, reply_markup=markup)


# --- Manejadores de Callback Query (Botones) ---

@bot.on_callback_query()
async def handle_callback_query(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    message = callback_query.message
    chat_id = message.chat.id

    log.debug(f"Callback recibido de {user_id}: {data}")

    # --- Callback de Solicitud de Acceso ---
    if data == "request_access":
        if user_id == ADMIN_USER_ID:
            await callback_query.answer("Eres el administrador, ya tienes acceso.", show_alert=True)
            return

        # Informar al usuario
        await callback_query.answer("Tu solicitud ha sido enviada al administrador.", show_alert=True)
        # Enviar mensaje al admin
        user_info = callback_query.from_user
        username = f"@{user_info.username}" if user_info.username else "N/A"
        log.info(f"Usuario {user_id} ({username}) solicitó acceso.")

        admin_text = (
            f"⚠️ **Solicitud de Acceso Nueva VideodownBot** ⚠️\n\n"
            f"El usuario:\n"
            f"- **Nombre:** {user_info.first_name} {user_info.last_name or ''}\n"
            f"- **Username:** {username}\n"
            f"- **ID:** `{user_id}`\n\n"
            f"Quiere usar el bot. ¿Le concedes acceso?"
        )
        admin_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Aceptar", callback_data=f"admin_accept|{user_id}"),
             InlineKeyboardButton("❌ Rechazar", callback_data=f"admin_reject|{user_id}")]
        ])

        try:
            await client.send_message(ADMIN_USER_ID, admin_text, reply_markup=admin_markup, parse_mode=enums.ParseMode.MARKDOWN)
            # Editar el mensaje original del usuario no autorizado para quitar el botón
            await edit_message_safe(message, message.text.split('\n\n')[0] + "\n\n*Solicitud enviada al administrador.*")
        except Exception as e:
            log.error(f"Error al notificar al admin {ADMIN_USER_ID} sobre solicitud de {user_id}: {e}")
            await edit_message_safe(message, message.text.split('\n\n')[0] + "\n\n*Error al enviar la solicitud. Contacta al administrador manualmente.*")
        return

    # --- Callbacks de Decisión del Admin ---
    if data.startswith("admin_accept|"):
        if user_id != ADMIN_USER_ID: return # Solo admin puede aceptar/rechazar
        user_id_to_accept = int(data.split("|")[1])

        log.info(f"Admin {user_id} aceptando acceso para {user_id_to_accept}")
        success = await update_config_allowed_users(user_id_to_add=user_id_to_accept)

        if success:
            await callback_query.answer("Usuario aceptado.", show_alert=False)
            await edit_message_safe(message, message.text + "\n\n✅ **Acceso concedido.**")
            # Notificar al usuario
            try:
                await client.send_message(user_id_to_accept, "🎉 ¡Tu solicitud de acceso ha sido aprobada! Ya puedes usar el bot.")
            except Exception as e:
                log.warning(f"No se pudo notificar al usuario aceptado {user_id_to_accept}: {e}")
        else:
            await callback_query.answer("Error al actualizar configuración.", show_alert=True)
            await edit_message_safe(message, message.text + "\n\n❌ **Error al guardar el cambio.**")
        return

    if data.startswith("admin_reject|"):
        if user_id != ADMIN_USER_ID: return
        user_id_to_reject = int(data.split("|")[1])
        log.info(f"Admin {user_id} rechazando acceso para {user_id_to_reject}")
        await callback_query.answer("Usuario rechazado.", show_alert=False)
        await edit_message_safe(message, message.text + "\n\n❌ **Acceso rechazado.**")
        # Notificar al usuario
        try:
            await client.send_message(user_id_to_reject, "😔 Lo siento, tu solicitud de acceso ha sido rechazada.")
        except Exception as e:
            log.warning(f"No se pudo notificar al usuario rechazado {user_id_to_reject}: {e}")
        return
        
    elif data == "show_help":
        # Comprobar autorización por si acaso
        if not is_authorized(user_id):
             await callback_query.answer("🚫 Acción no permitida.", show_alert=True)
             return

        log.info(f"Usuario {user_id} solicitó ayuda desde el botón de /start.")
        help_text_content = get_help_text() # Obtener texto de la función auxiliar

        try:
            # Editar el mensaje de /start para mostrar la ayuda en su lugar
            await callback_query.edit_message_text(
                text=help_text_content,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=None # Opcional: quitar el botón después de mostrar la ayuda
            )
            await callback_query.answer() # Confirmar que se presionó el botón (silencioso)
        except MessageNotModified:
            # Si el usuario presiona el botón muy rápido dos veces
            await callback_query.answer("Ya se está mostrando la ayuda.")
        except Exception as e:
            log.error(f"Error al editar mensaje para mostrar ayuda vía botón: {e}")
            await callback_query.answer("Error al mostrar la ayuda.", show_alert=True)
        return # Importante: terminar aquí para no seguir con otros callbacks

    # --- Resto de Callbacks (OS, Descarga, Cancelar) ---

    # Verificar autorización para el resto de callbacks
    if not is_authorized(user_id):
        await callback_query.answer("🚫 No tienes permiso para realizar esta acción.", show_alert=True)
        return

    # --- Selección de OS ---
    if data.startswith("os|"):
        parts = data.split("|")
        if len(parts) != 3: return # Formato incorrecto
        _, video_id, selected_os = parts

        if video_id not in user_requests:
            await callback_query.answer("⚠️ Solicitud no encontrada o expirada.", show_alert=True)
            await edit_message_safe(message, "❌ Esta solicitud ya no es válida.")
            return

        if user_requests[video_id]["chat_id"] != chat_id:
            await callback_query.answer("No puedes interactuar con la solicitud de otro usuario.", show_alert=True)
            return

        user_requests[video_id]["os"] = selected_os
        log.info(f"[{video_id}] OS seleccionado: {selected_os}")

        # Ahora obtener resoluciones reales (puede tardar un poco más)
        url = user_requests[video_id]["url"]
        info = user_requests[video_id]["info"] # Usar info ya extraída

        await edit_message_safe(message, f"{message.text.split('📱')[0]}\n⚙️ Obteniendo calidades disponibles...")

        resolutions = []
        has_audio = False

        try:
            log.info(f"[{video_id}] Reutilizando formatos detallados ya extraídos de la variable 'info'.")
            
            # --- INICIO DE LA CORRECCIÓN ---
            # No hacemos una nueva llamada de red. 
            # Reutilizamos la variable 'info' que ya contiene toda la información de formatos.
            formats_info = info
            # --- FIN DE LA CORRECCIÓN ---

            # Si es playlist, buscar formatos comunes o los del primer video como fallback

            # Si es playlist, buscar formatos comunes o los del primer video como fallback
            # --- INICIO LÓGICA MEJORADA PARA PLAYLISTS/MULTI-ITEM ---
            all_resolutions_set = set() # Usar un set para alturas únicas
            has_audio = False
            entries = formats_info.get('entries', [])

            # Si no hay 'entries' en la respuesta principal, significa que formats_info
            # representa una única entrada (no una playlist). Lo ponemos en una lista
            # para poder iterar de forma consistente.
            if not entries and isinstance(formats_info.get('formats'), list):
                 entries = [formats_info]

            log.info(f"[{video_id}] Procesando {len(entries)} entrada(s) para encontrar formatos...")

            for entry in entries:
                 entry_formats = entry.get('formats', [])
                 if not entry_formats:
                      continue # Saltar entradas sin formatos

                 # Buscar resoluciones de video en esta entrada
                 for f in entry_formats:
                      # Comprobar si es un formato de video válido con altura
                      if f.get('vcodec') != 'none' and f.get('height'):
                           all_resolutions_set.add(f['height'])

                      # Comprobar si hay algún formato de solo audio en esta entrada
                      if not has_audio and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                           has_audio = True # Marcar que encontramos audio en al menos una entrada

            # Convertir el set de alturas a una lista ordenada de strings "XXXp"
            if all_resolutions_set:
                # Filtrar alturas None o 0 que pudieran colarse
                valid_heights = {h for h in all_resolutions_set if h and h > 0}
                resolutions = sorted([f"{h}p" for h in valid_heights], key=lambda x: int(x.rstrip('p')), reverse=True)
                user_requests[video_id]["resolutions"] = resolutions # Guardar resoluciones encontradas
                log.info(f"[{video_id}] Resoluciones encontradas en total: {resolutions}")
            else:
                 resolutions = [] # Asegurar que es una lista vacía si no se encontró nada
                 user_requests[video_id]["resolutions"] = []
                 log.warning(f"[{video_id}] No se encontraron alturas de video válidas en ninguna entrada.")
            # 'has_audio' ya está actualizado basado en todas las entradas

            # (Aquí iría el código opcional para calcular tamaños estimados si lo tuvieras)
            # user_requests[video_id]["quality_sizes"] = calculate_all_estimated_sizes(...)

            # --- FIN LÓGICA MEJORADA ---

        except Exception as e:
            log.exception(f"[{video_id}] Error obteniendo formatos detallados: {e}")
            await edit_message_safe(message, f"{message.text.split('⚙️')[0]}\n❌ Error al obtener las calidades disponibles.")
            # Limpiar estado si falla aquí? Podríamos permitir reintentar OS?
            # Por ahora, dejamos el estado para posible debug o reintento manual
            return


        # (Código anterior para extraer resolutions y has_audio)

        # Construir botones de calidad
        buttons = []
        if resolutions:
            # Agrupar botones en filas de 2
            row = []
            for res in resolutions:
                # (Opcional: añadir tamaño estimado si lo tienes)
                # size_bytes = quality_sizes.get(res)
                # size_str = f" (~{size_bytes / 1024 / 1024:.0f} MB)" if size_bytes is not None else ""
                size_str = "" # Mantener simple por ahora
                row.append(InlineKeyboardButton(f"📺 {res}{size_str}", callback_data=f"dl|{video_id}|{res}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row: # Añadir la última fila si no está llena
                buttons.append(row)

        if has_audio:
            size_str = "" # Mantener simple por ahora
            # Crear dos botones para las opciones de audio
            audio_buttons = [
                InlineKeyboardButton(f"🎵 Audio (Original)", callback_data=f"dl|{video_id}|audio_original"),
                InlineKeyboardButton(f"🎵 Audio (MP3)", callback_data=f"dl|{video_id}|audio_mp3")
            ]
            buttons.append(audio_buttons)

        # --- *** COMPROBACIÓN MOVIDA AQUÍ *** ---
        # Verificar si se generó algún botón de calidad ANTES de añadir el de Cancelar
        if not buttons:
            log.warning(f"[{video_id}] No se generaron botones de calidad (Resolutions: {resolutions}, HasAudio: {has_audio}). Probablemente formatos no estándar.")
            # Editar mensaje para indicar el error claramente
            await edit_message_safe(message, f"{message.text.split('⚙️')[0]}\n❌ No encontré formatos de video o audio estándar descargables para esta URL.")
            # Limpiar estado ya que no hay opciones válidas
            if video_id in user_requests: del user_requests[video_id]
            await callback_query.answer("❌ Formatos no encontrados", show_alert=True) # Notificar al usuario
            return # Salir de la función callback
        # --- *** FIN COMPROBACIÓN MOVIDA *** ---

        # Botón de cancelar general (se añade DESPUÉS de verificar que hay opciones)
        buttons.append([InlineKeyboardButton("🔙 Cancelar Selección", callback_data=f"cancel_sel|{video_id}")])

        # --- ELIMINAR LA COMPROBACIÓN ANTIGUA DE AQUÍ ---
        # if not buttons: # <--- ESTA LÍNEA YA NO ES NECESARIA AQUÍ
        #      ...

        markup = InlineKeyboardMarkup(buttons)
        # Editar el mensaje para mostrar los botones de calidad (y el de cancelar)
        await edit_message_safe(message, f"{message.text.split('⚙️')[0]}\n✅ **Elige la calidad deseada:**", reply_markup=markup)
        await callback_query.answer() # Confirmar recepción del callback OS

    # --- Inicio de Descarga ---
    elif data.startswith("dl|"):
        parts = data.split("|")
        if len(parts) != 3: return
        _, video_id, quality = parts

        if video_id not in user_requests:
            await callback_query.answer("⚠️ Solicitud no encontrada o expirada.", show_alert=True)
            await edit_message_safe(message, "❌ Esta solicitud ya no es válida.")
            return

        if user_requests[video_id]["chat_id"] != chat_id:
            await callback_query.answer("No puedes interactuar con la solicitud de otro usuario.", show_alert=True)
            return

        # --- Comprobar si ya hay una descarga activa para este chat ---
        if chat_id in download_tasks:
            await callback_query.answer("⏳ Ya hay otra operación en curso. Por favor, espera.", show_alert=True)
            return

        # --- Preparar descarga ---
        url = user_requests[video_id]["url"]
        device_os = user_requests[video_id]["os"]
        info = user_requests[video_id]["info"] # Info básica ya extraída
        title = info.get('title', 'video')

        log.info(f"[{video_id}] Iniciando descarga para {url} con calidad '{quality}' para OS '{device_os}'")

        # Crear evento de cancelación para esta descarga específica
        cancel_event = threading.Event()
        download_tasks[chat_id] = {"message": message, "cancel_event": cancel_event, "video_id": video_id}

        # Actualizar mensaje indicando inicio
        await edit_message_safe(message, f"⏳ Preparando descarga para '{quality}'...", reply_markup=None) # Quitar botones anteriores

        # Crear directorio de descargas si no existe
        os.makedirs("downloads", exist_ok=True)

        # Nombre de archivo temporal y final
        # Añadir timestamp al nombre base para evitar colisiones si se descarga lo mismo rápido
        base_filename = f"{video_id}_{int(time.time())}"
        # Extensión inicial (yt-dlp podría cambiarla)
        temp_ext = ".mp4" if quality != "audio" else ".webm" # yt-dlp suele preferir webm/opus para audio
        temp_filepath_pattern = os.path.join("downloads", f"{base_filename}.%(ext)s")


        # --- Opciones de yt-dlp para la descarga ---
        ydl_opts = {
            'outtmpl': temp_filepath_pattern,
            'retries': 5,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'quiet': True, # Silencioso, el progreso lo manejamos nosotros
            'no_warnings': True,
            'noprogress': True, # Desactivar barra de progreso de yt-dlp
            'postprocessors': [], # Inicializar vacío
             # Hook de progreso personalizado
            'progress_hooks': [ProgressHook(message, asyncio.get_running_loop(), cancel_event, video_id)],
            'merge_output_format': 'mp4', # Preferir mp4 si se fusionan video y audio
            # 'noplaylist': True, # Manejaremos playlists explícitamente si es necesario
        }

        if os.path.exists(COOKIE_FILE_PATH):
            ydl_opts['cookiefile'] = COOKIE_FILE_PATH

        # --- Formato específico ---
        if quality == "audio_mp3":
            # Opción 1: El usuario quiere MP3 (convertir)
            ydl_opts['format'] = 'bestaudio/best'
            # Añadir post-procesador para forzar la conversión a MP3
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            final_extension = ".mp3"
        
        elif quality == "audio_original":
            # Opción 2: El usuario quiere el formato original (sin convertir)
            ydl_opts['format'] = 'bestaudio/best'
            # No se añade ningún post-procesador
            final_extension = None # No sabemos la extensión final

        else: # Opción 3: Es una resolución de video
            # Formato: mejor video con esa altura exacta + mejor audio / mejor video solo / mejor audio solo
            # Añadir filtro por tamaño si la info está disponible? Podría ser complejo.
            # Usar H.264 si es posible para mayor compatibilidad inicial
            height = quality.rstrip('p')
            if device_os == "ios":
                # Para iOS, forzamos H.264 (avc) para máxima compatibilidad
                log.info(f"[{video_id}] Usando formato compatible con iOS (priorizando avc).")
                ydl_opts['format'] = (f"bestvideo[height={height}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/"
                                      f"best[height={height}]/best")
            else:
                # Para Android/Otros, usamos un formato estándar (dejará que yt-dlp elija vp9 o avc)
                log.info(f"[{video_id}] Usando formato estándar (Android/Otros).")
                ydl_opts['format'] = (f"bestvideo[height={height}]+bestaudio/"
                                      f"best[height={height}]/best")

            final_extension = ".mp4"

        # --- Ejecutar la descarga en un hilo separado ---
        actual_temp_filepath = None
        download_success = False
        try:
            log.info(f"[{video_id}] Lanzando yt-dlp.download en executor con opts: {ydl_opts}")
            loop = asyncio.get_running_loop()

            # Función que se ejecutará en el hilo
            def download_sync():
                nonlocal actual_temp_filepath # Para poder modificarla desde el hilo
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # El hook de progreso comprobará cancel_event
                        ydl.download([url])
                        
                        # Lógica de búsqueda de archivo mejorada
                        # Si tenemos una extensión esperada (videos), la buscamos primero.
                        if final_extension:
                            for file in os.listdir("downloads"):
                                if file.startswith(base_filename) and file.endswith(final_extension):
                                    actual_temp_filepath = os.path.join("downloads", file)
                                    log.info(f"[{video_id}] Archivo con extensión esperada encontrado: {actual_temp_filepath}")
                                    return True # Éxito

                        # Para audios (final_extension es None) o como fallback para videos,
                        # buscamos CUALQUIER archivo que coincida con el nombre base.
                        log.info(f"[{video_id}] Buscando archivo final por nombre base '{base_filename}'...")
                        for file in os.listdir("downloads"):
                            if file.startswith(base_filename):
                                actual_temp_filepath = os.path.join("downloads", file)
                                log.info(f"[{video_id}] Encontrado archivo de audio/fallback: {actual_temp_filepath}")
                                return True # Éxito

                        log.error(f"[{video_id}] No se encontró NINGÚN archivo final tras la descarga.")
                        return False # No se encontró nada

                except yt_dlp.utils.DownloadError as de:
                    # Comprobar si fue por cancelación
                    if "Descarga cancelada por el usuario" in str(de):
                        log.warning(f"[{video_id}] Descarga cancelada explícitamente vía hook.")
                        # El evento ya está puesto, la tarea principal lo detectará
                    else:
                        log.error(f"[{video_id}] Error de yt-dlp durante la descarga: {de}")
                    return False # Indicar fallo
                except Exception as thread_exc:
                    log.exception(f"[{video_id}] Excepción inesperada en el hilo de descarga: {thread_exc}")
                    return False # Indicar fallo

            download_success = await loop.run_in_executor(None, download_sync)

            # Comprobar si se canceló justo al final o durante la espera del hilo
            if cancel_event.is_set():
                 log.warning(f"[{video_id}] Cancelación detectada después de que el hilo de descarga terminara.")
                 download_success = False # Marcar como fallo si se canceló

            # Verificar que el archivo existe si el hilo reportó éxito
            if download_success and (not actual_temp_filepath or not os.path.exists(actual_temp_filepath)):
                log.error(f"[{video_id}] El hilo reportó éxito pero el archivo final '{actual_temp_filepath}' no existe.")
                download_success = False


        except Exception as e:
            # Captura errores al lanzar el executor o esperar, no los de dentro del hilo
            log.exception(f"[{video_id}] Error en la gestión del hilo de descarga: {e}")
            download_success = False

        # --- Procesamiento Post-Descarga ---

        # Si se canceló o falló la descarga
        if not download_success:
            await edit_message_safe(message, "❌ Descarga fallida o cancelada.")
            # Limpiar archivo temporal si existe y fue identificado
            if actual_temp_filepath and os.path.exists(actual_temp_filepath):
                try:
                    os.remove(actual_temp_filepath)
                    log.info(f"[{video_id}] Archivo temporal '{actual_temp_filepath}' eliminado tras fallo/cancelación.")
                except OSError as e:
                    log.error(f"[{video_id}] Error al eliminar archivo temporal '{actual_temp_filepath}': {e}")
            # Limpiar cualquier otro archivo con el base_filename por si acaso
            for file in os.listdir("downloads"):
                 if file.startswith(base_filename):
                      try:
                          os.remove(os.path.join("downloads", file))
                          log.info(f"[{video_id}] Archivo temporal adicional '{file}' eliminado.")
                      except OSError as e:
                           log.error(f"[{video_id}] Error eliminando '{file}': {e}")

            # Limpiar estado de la tarea
            if chat_id in download_tasks: del download_tasks[chat_id]
            if video_id in user_requests: del user_requests[video_id] # Limpiar solicitud completa
            return # Terminar el handler

        # --- Éxito en la descarga, proceder ---
        log.info(f"[{video_id}] Descarga completada. Archivo: {actual_temp_filepath}")
        final_filepath = actual_temp_filepath # Inicialmente, el archivo descargado es el final

        # --- Re-codificación para iOS si es necesario ---
        recode_success = True # Asumir éxito si no se necesita recodificar
        if device_os == "ios" and quality != "audio":
            # Nombre para el archivo recodificado
            recoded_filename = f"{base_filename}_ios{final_extension}"
            recoded_filepath = os.path.join("downloads", recoded_filename)

            await edit_message_safe(message, f"📱 Preparando recodificación para iOS...")

            # Ejecutar recodificación
            # Ejecutar recodificación
            recode_success = await recode_video_ios(
                input_path=actual_temp_filepath,
                output_path=recoded_filepath,
                message=message,
                video_id=video_id,
                cancel_event=cancel_event, # Reutilizar el mismo evento de cancelación
                yt_dlp_info=info # <--- ¡¡AÑADE ESTA LÍNEA!!
            )

            # Comprobar si se canceló durante la recodificación
            if cancel_event.is_set():
                 log.warning(f"[{video_id}] Cancelación detectada durante o después de la recodificación.")
                 recode_success = False # Marcar como fallo

            if recode_success and os.path.exists(recoded_filepath):
                log.info(f"[{video_id}] Recodificación para iOS exitosa: {recoded_filepath}")
                # Eliminar el archivo original descargado
                try:
                    os.remove(actual_temp_filepath)
                    log.info(f"[{video_id}] Archivo original '{actual_temp_filepath}' eliminado tras recodificación.")
                except OSError as e:
                    log.error(f"[{video_id}] Error eliminando archivo original '{actual_temp_filepath}': {e}")
                final_filepath = recoded_filepath # El archivo final ahora es el recodificado
            else:
                log.error(f"[{video_id}] Falló la recodificación para iOS o el archivo no se encontró/fue cancelado.")
                await edit_message_safe(message, "❌ Falló la recodificación para iOS o fue cancelada.")
                # Limpiar archivos
                if os.path.exists(actual_temp_filepath): os.remove(actual_temp_filepath)
                if os.path.exists(recoded_filepath): os.remove(recoded_filepath)
                 # Limpiar estado
                if chat_id in download_tasks: del download_tasks[chat_id]
                if video_id in user_requests: del user_requests[video_id]
                return # Terminar

        # --- Comprobación final de cancelación antes de subir ---
        if cancel_event.is_set():
            log.warning(f"[{video_id}] Cancelación detectada antes de iniciar la subida.")
            await edit_message_safe(message, "❌ Operación cancelada antes de la subida.")
             # Limpiar archivo final
            if final_filepath and os.path.exists(final_filepath):
                try:
                    os.remove(final_filepath)
                    log.info(f"[{video_id}] Archivo final '{final_filepath}' eliminado tras cancelación.")
                except OSError as e:
                    log.error(f"[{video_id}] Error al eliminar archivo final '{final_filepath}': {e}")
             # Limpiar estado
            if chat_id in download_tasks: del download_tasks[chat_id]
            if video_id in user_requests: del user_requests[video_id]
            return

        # --- Subida a Telegram ---
        if not final_filepath or not os.path.exists(final_filepath):
             log.error(f"[{video_id}] ¡Error crítico! El archivo final '{final_filepath}' no existe antes de la subida.")
             await edit_message_safe(message, "❌ Error interno: el archivo procesado desapareció.")
             if chat_id in download_tasks: del download_tasks[chat_id]
             if video_id in user_requests: del user_requests[video_id]
             return

        file_size = os.path.getsize(final_filepath)
        file_size_mb = file_size / 1024 / 1024
        log.info(f"[{video_id}] Iniciando subida de '{final_filepath}' ({file_size_mb:.2f} MB)")

        # Comprobar límite de tamaño de Telegram (aproximado, puede ser 2GB o 4GB con Premium)
        # Seamos conservadores con 2000 MB
        if file_size > 2000 * 1024 * 1024:
            log.warning(f"[{video_id}] El archivo ({file_size_mb:.2f} MB) excede el límite de ~2GB.")
            await edit_message_safe(message, f"❌ **Archivo demasiado grande ({file_size_mb:.2f} MB).**\nTelegram limita las subidas a unos 2GB. Intenta una calidad inferior.")
             # Limpiar archivo
            os.remove(final_filepath)
            # Limpiar estado
            if chat_id in download_tasks: del download_tasks[chat_id]
            if video_id in user_requests: del user_requests[video_id]
            return

        # Preparar mensaje de subida y callback de progreso
        await edit_message_safe(message, f"⏫ Preparando subida ({file_size_mb:.2f} MB)...")
        upload_start_time = time.time()

        # Necesitamos envolver el callback para pasarle argumentos extra
        async def progress_wrapper(current, total):
           # No hay forma fácil de cancelar la subida de pyrogram una vez iniciada
           # Podríamos intentar borrar el mensaje que la inició, pero es arriesgado.
           # El callback de progreso no puede detener la subida.
           action_str = "Recodificando" if device_os == "ios" and quality != "audio" and recode_success else "Subiendo" # Incorrecto, ya se hizo. Debe ser "Subiendo"
           await upload_progress_callback(current, total, message, upload_start_time, video_id, action="Subiendo")


        sent_message = None
        try:
            # Determinar si es audio o video
            if quality == "audio":
                # Obtener duración y título del audio (si es posible, con ffprobe o mutagen)
                # Por simplicidad, usamos el título del video original
                audio_title = title[:100] # Limitar longitud
                audio_performer = info.get('uploader', 'Desconocido')

                sent_message = await client.send_audio(
                    chat_id=chat_id,
                    audio=final_filepath,
                    caption=f"🎵 **Audio Extraído**\n`{title}`\n\n💾 Tamaño: {file_size_mb:.2f} MB",
                    title=audio_title,
                    performer=audio_performer,
                    # duration=duration_sec, # Necesitaríamos extraerla
                    progress=progress_wrapper,
                    reply_to_message_id=message.reply_to_message_id or message.id # Responder al mensaje original o al de estado
                )
            else: # Es video
                # Obtener dimensiones y duración (con ffprobe o guardar de yt-dlp)
                # Por simplicidad, no las añadimos ahora, pero sería ideal
                # width, height, duration = get_video_metadata(final_filepath)
                 sent_message = await client.send_video(
                    chat_id=chat_id,
                    video=final_filepath,
                    caption=f"🎬 **Video Descargado** ({quality})\n`{title}`\n\n💾 Tamaño: {file_size_mb:.2f} MB",
                    supports_streaming=True, # Asumir que H.264/MP4 lo soporta
                    # width=width,
                    # height=height,
                    # duration=duration,
                    progress=progress_wrapper,
                    reply_to_message_id=message.reply_to_message_id or message.id
                )

            log.info(f"[{video_id}] Subida completada con éxito.")
            # Borrar el mensaje de estado "Subiendo..." final
            await message.delete()

        except Exception as e:
            log.exception(f"[{video_id}] Error durante la subida a Telegram: {e}")
            await edit_message_safe(message, f"❌ Ocurrió un error al subir el archivo a Telegram.\n`{e}`")
            # No borrar el archivo local en caso de error de subida, para posible reintento manual?
            # O sí borrarlo para evitar acumulación? Lo borramos.
            if os.path.exists(final_filepath):
                try:
                    os.remove(final_filepath)
                except OSError as remove_err:
                     log.error(f"[{video_id}] Error eliminando archivo tras fallo de subida: {remove_err}")

        finally:
            log.debug(f"[{video_id}] Entrando al bloque finally de la tarea.")
            # Limpieza final
            was_successful_upload = sent_message is not None # Verificar si hubo mensaje enviado con éxito

            # Limpiar archivo final SI NO hubo subida exitosa O SI se canceló
            if not was_successful_upload or cancel_event.is_set():
                # Identificar qué archivo borrar (puede ser el original o el recodificado)
                # Reutilizamos final_filepath que se actualizó si hubo recodificación exitosa
                file_to_delete_on_failure = final_filepath

                # PERO, si la recodificación falló, final_filepath apunta al archivo recodificado
                # y también necesitamos borrar el original (actual_temp_filepath) si existe.
                # Y si la descarga falló, final_filepath apunta al original (actual_temp_filepath)
                # Esta lógica puede volverse compleja. Simplifiquemos: BORRAR TODO lo relacionado.

                log.warning(f"[{video_id}] Limpiando archivos por fallo, cancelación o no subida exitosa (Cancel set: {cancel_event.is_set()})...")

                files_to_try_removing = []
                # 'actual_temp_filepath' se define dentro del try de descarga/hilo
                # Necesitamos asegurarnos de que sea accesible aquí o buscar de nuevo.
                # Es más seguro buscar por el base_filename.
                if 'base_filename' in locals() or 'base_filename' in globals(): # Comprobar si base_filename se definió
                    log.debug(f"[{video_id}] Buscando archivos con base: {base_filename}")
                    for file in os.listdir("downloads"):
                         if file.startswith(base_filename):
                              files_to_try_removing.append(os.path.join("downloads", file))
                else:
                     # Si no tenemos base_filename, intentar con las variables conocidas si existen
                     if 'actual_temp_filepath' in locals() and actual_temp_filepath: files_to_try_removing.append(actual_temp_filepath)
                     if 'recoded_filepath' in locals() and recoded_filepath: files_to_try_removing.append(recoded_filepath)
                     if 'final_filepath' in locals() and final_filepath not in files_to_try_removing: files_to_try_removing.append(final_filepath)

                log.info(f"[{video_id}] Archivos a intentar eliminar: {files_to_try_removing}")
                for f_path in set(files_to_try_removing): # Usar set para evitar duplicados
                      if f_path and os.path.exists(f_path):
                           try:
                               os.remove(f_path)
                               log.info(f"[{video_id}] Archivo local '{f_path}' eliminado en finally.")
                           except OSError as e:
                               log.error(f"[{video_id}] Error eliminando archivo '{f_path}' en finally: {e}")

            # Si la subida fue exitosa, borrar solo el archivo final (lógica original)
            elif was_successful_upload and final_filepath and os.path.exists(final_filepath):
                 try:
                     os.remove(final_filepath)
                     log.info(f"[{video_id}] Archivo local '{final_filepath}' eliminado tras subida exitosa.")
                 except OSError as e:
                     log.error(f"[{video_id}] Error eliminando archivo local '{final_filepath}' tras subida: {e}")


            # Limpiar estado de la tarea y la solicitud siempre
            log.debug(f"[{video_id}] Limpiando estado de tarea y solicitud en finally.")
            if chat_id in download_tasks: del download_tasks[chat_id]
            if video_id in user_requests: del user_requests[video_id]
            log.info(f"[{video_id}] Tarea finalizada y estado limpiado.")



    # --- Cancelar Selección (antes de descargar) ---
    elif data.startswith("cancel_sel|"):
        parts = data.split("|")
        if len(parts) != 2: return
        _, video_id = parts

        if video_id not in user_requests:
            await callback_query.answer("⚠️ Solicitud no encontrada o expirada.", show_alert=True)
            return

        if user_requests[video_id]["chat_id"] != chat_id:
             await callback_query.answer("No puedes cancelar la solicitud de otro usuario.", show_alert=True)
             return

        log.info(f"[{video_id}] Usuario canceló la selección.")
        await edit_message_safe(message, "✅ Selección cancelada. Puedes enviar otra URL si lo deseas.")
        del user_requests[video_id] # Eliminar la solicitud pendiente
        await callback_query.answer("Selección cancelada.")


    # --- Cancelar Descarga/Recodificación en curso ---
    elif data.startswith("cancel_dl|"):
        parts = data.split("|")
        if len(parts) != 2: return
        _, video_id_to_cancel = parts

        # Buscar la tarea por chat_id (asumiendo una tarea por chat)
        task_info = download_tasks.get(chat_id)

        if task_info and task_info["video_id"] == video_id_to_cancel:
            log.warning(f"[{video_id_to_cancel}] Usuario {user_id} solicitó cancelación para la tarea activa.")
            cancel_event = task_info.get("cancel_event")
            if cancel_event and not cancel_event.is_set():
                cancel_event.set() # Poner el flag de cancelación
                await callback_query.answer("Intentando cancelar la operación...", show_alert=False)
                # El hook de progreso o la función de recodificación detectarán esto
                # No editamos el mensaje aquí, se hará cuando se detecte la cancelación
            elif cancel_event and cancel_event.is_set():
                 await callback_query.answer("La cancelación ya está en proceso.", show_alert=False)
            else:
                 await callback_query.answer("⚠️ No se pudo encontrar el evento de cancelación.", show_alert=True)
        else:
            await callback_query.answer("⚠️ No hay una operación activa para cancelar o la solicitud no coincide.", show_alert=True)

    # --- Callback desconocido o no manejado ---
    else:
        log.warning(f"Callback no manejado recibido de {user_id}: {data}")
        await callback_query.answer("Acción desconocida.", show_alert=False)


# --- Ejecución del Bot ---
if __name__ == "__main__":
    log.info("Iniciando el bot...")
    # Crear carpeta de descargas si no existe
    if not os.path.exists("downloads"):
        try:
            os.makedirs("downloads")
            log.info("Carpeta 'downloads' creada.")
        except OSError as e:
            log.error(f"No se pudo crear la carpeta 'downloads': {e}")
            sys.exit(1)

    # Ejecutar el bot
    try:
        bot.run()
        log.info("Bot detenido.")
    except Exception as e:
        log.exception(f"Error fatal al ejecutar el bot: {e}")