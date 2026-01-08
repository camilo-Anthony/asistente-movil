"""
YouTube MCP - Búsqueda y reproducción inteligente
Usa yt-dlp para buscar sin API Key
"""
import asyncio
import json
import subprocess

class YouTubeMCP:
    """MCP para YouTube usando yt-dlp"""
    
    description = "Búsqueda avanzada de videos en YouTube"
    
    def __init__(self, config: dict = None):
        self._check_ytdlp()
        
    def _check_ytdlp(self):
        """Verifica/Instala yt-dlp"""
        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
            print("✅ YouTube: yt-dlp activo")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠️ YouTube: Instalando yt-dlp...")
            try:
                subprocess.run(['pip', 'install', 'yt-dlp'], check=True)
                print("✅ YouTube: yt-dlp instalado")
            except:
                print("❌ Error instalando yt-dlp")

    def get_tools(self) -> list:
        return [
            {
                "name": "search_video",
                "description": "Busca videos en YouTube con detalles",
                "params": {"query": "string", "limit": "int (default 5)"}
            },
            {
                "name": "play_video",
                "description": "Abre un video específico",
                "params": {"url": "string"}
            }
        ]

    async def execute(self, action: str, params: dict) -> str:
        action_lower = action.lower().strip()
        
        # Detección flexible por keywords
        # Si dice "pon", "reproduce", "play" → buscar y abrir automáticamente
        if any(kw in action_lower for kw in ['pon', 'reproduce', 'play', 'abre']):
            params['auto_play'] = True
            return await self._search(params)
        elif any(kw in action_lower for kw in ['buscar', 'search', 'busca', 'encuentra']):
            return await self._search(params)
        
        # Fallback: intentar igualdad exacta
        if action == "search_video":
            return await self._search(params)
        elif action == "play_video":
            return await self._play(params)
            
        return f"❌ Acción '{action}' desconocida para YouTube MCP"

    async def _search(self, params: dict) -> str:
        query = params.get('query')
        limit = params.get('limit', 5)
        auto_play = params.get('auto_play', False)
        
        print(f"🔍 Buscando '{query}' en YouTube...")
        
        cmd = [
            'yt-dlp',
            f'ytsearch{limit}:{query}',
            '--dump-json',
            '--no-playlist',
            '--flat-playlist'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return f"❌ Error buscando: {stderr.decode()}"
            
        results = []
        output = stdout.decode()
        first_url = None
        
        # yt-dlp devuelve un JSON por línea
        for line in output.strip().split('\n'):
            if line:
                try:
                    video = json.loads(line)
                    url = video.get('url')
                    title = video.get('title')
                    duration = video.get('duration_string', '??:??')
                    
                    if not first_url:
                        first_url = url
                    
                    results.append(f"- {title} ({duration})\n  URL: {url}")
                except:
                    pass
                    
        if not results:
            return f"❌ No encontré videos para '{query}'"
        
        # Si auto_play está activado, abrir el primero
        if auto_play and first_url:
            subprocess.run(['termux-open-url', first_url], check=False)
            return f"▶️ Reproduciendo: {results[0].split('URL:')[0].strip()}"
        
        return f"📺 Videos encontrados:\n" + "\n".join(results)

    async def _play(self, params: dict) -> str:
        url = params.get('url')
        # Usar termux-open-url
        subprocess.run(['termux-open-url', url])
        return f"▶️ Abriendo video..."
