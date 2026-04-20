import yt_dlp
import uuid
import os
import re

# Dicionário em memória para armazenar o status dos downloads
# Em um sistema em nuvem escalável, isso seria substituído por Redis
PROGRESS_STORE = {}
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def analyze_media(url: str) -> dict:
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Filtra resoluções reais e descarta formatos de lixo
        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                # Formato com vídeo e áudio juntos
                resolution = f.get('format_note') or f"{f.get('height', 'Unknown')}p"
                ext = f.get('ext', 'mp4')
                formats.append({
                    "quality": f"{resolution} ({ext}) - Completo",
                    "format_id": f.get('format_id'),
                    "ext": ext,
                    "type": "video"
                })
        
        # Opções genéricas caso a plataforma separe áudio/vídeo (ex: YouTube DASH)
        formats.insert(0, {"quality": "Qualidade Máxima (Vídeo + Áudio)", "format_id": "bestvideo+bestaudio/best", "ext": "mp4", "type": "video"})
        formats.append({"quality": "Apenas Áudio (Melhor)", "format_id": "bestaudio/best", "ext": "mp3", "type": "audio"})

        # Formatação de tempo
        duration_sec = info.get('duration', 0)
        mins, secs = divmod(duration_sec, 60)
        
        return {
            "title": info.get('title', 'Mídia Desconhecida'),
            "thumbnail": info.get('thumbnail', ''),
            "duration": f"{int(mins):02d}:{int(secs):02d}",
            "platform": info.get('extractor_key', 'Desconhecido'),
            "formats": formats
        }

def clean_ansi(text):
    """Remove códigos de cores do terminal retornados pelo yt-dlp"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def download_task(task_id: str, url: str, format_id: str):
    output_template = f"{DOWNLOAD_DIR}/{task_id}_%(title)s.%(ext)s"
    
    def my_hook(d):
        if d['status'] == 'downloading':
            try:
                percent_str = clean_ansi(d.get('_percent_str', '0%')).replace('%', '').strip()
                PROGRESS_STORE[task_id].update({
                    "percent": float(percent_str) if percent_str != 'N/A' else 0,
                    "speed": clean_ansi(d.get('_speed_str', '0KiB/s')).strip(),
                    "eta": clean_ansi(d.get('_eta_str', '00:00')).strip()
                })
            except Exception:
                pass
        elif d['status'] == 'finished':
            PROGRESS_STORE[task_id]['percent'] = 100
            PROGRESS_STORE[task_id]['status'] = 'processing' # Aguardando merge do ffmpeg se necessário

    ydl_opts = {
        'format': format_id,
        'cookiefile': 'backend/youtube.com_cookies.txt',
        'outtmpl': output_template,
        'progress_hooks': [my_hook],
        'quiet': True,
        'noplaylist': True,
        'merge_output_format': 'mp4' if 'video' in format_id else None,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if 'audio' in format_id else []
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # O nome final do arquivo após merges/conversões
            final_filename = ydl.prepare_filename(info)
            if 'audio' in format_id:
                final_filename = final_filename.rsplit('.', 1)[0] + '.mp3'
                
            PROGRESS_STORE[task_id]['status'] = 'completed'
            PROGRESS_STORE[task_id]['filepath'] = final_filename
    except Exception as e:
        PROGRESS_STORE[task_id]['status'] = 'error'
        PROGRESS_STORE[task_id]['error_msg'] = str(e)