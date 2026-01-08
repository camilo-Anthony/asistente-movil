"""
Spotify MCP - Control de Spotify con API oficial
Requiere: Spotify Premium + Credenciales de Developer
"""
import asyncio
import webbrowser
from typing import Optional
import os


class SpotifyMCP:
    """MCP para control de Spotify usando la API oficial"""
    
    description = "Control de Spotify: reproducir, pausar, buscar, playlists"
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.sp = None
        self.authenticated = False
        self._init_spotify()
    
    def _init_spotify(self):
        """Inicializa conexión con Spotify"""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            
            client_id = self.config.get('client_id', os.getenv('SPOTIFY_CLIENT_ID'))
            client_secret = self.config.get('client_secret', os.getenv('SPOTIFY_CLIENT_SECRET'))
            redirect_uri = self.config.get('redirect_uri', 'http://localhost:8888/callback')
            
            if not client_id or not client_secret:
                print("⚠️ Spotify: Configura client_id y client_secret")
                return
            
            # Scopes necesarios para control completo
            scope = " ".join([
                "user-read-playback-state",
                "user-modify-playback-state",
                "user-read-currently-playing",
                "playlist-read-private",
                "playlist-read-collaborative",
                "user-library-read"
            ])
            
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                cache_path=".spotify_cache",
                open_browser=False  # Crucial para Termux
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            self.authenticated = True
            print("✅ Spotify: Conectado")
            
        except ImportError:
            print("⚠️ Spotify: Instala spotipy con 'pip install spotipy'")
        except Exception as e:
            print(f"⚠️ Spotify: Error de autenticación - {e}")
    
    def get_tools(self) -> list:
        """Retorna las herramientas disponibles"""
        return [
            {
                "name": "play",
                "description": "Reproduce música (actual o busca una canción)",
                "params": {"query": "string (opcional)"}
            },
            {
                "name": "pause",
                "description": "Pausa la reproducción actual",
                "params": {}
            },
            {
                "name": "next",
                "description": "Salta a la siguiente canción",
                "params": {}
            },
            {
                "name": "previous",
                "description": "Vuelve a la canción anterior",
                "params": {}
            },
            {
                "name": "search",
                "description": "Busca canciones, artistas o álbumes",
                "params": {"query": "string", "type": "track|artist|album"}
            },
            {
                "name": "current",
                "description": "Muestra la canción actual",
                "params": {}
            },
            {
                "name": "volume",
                "description": "Ajusta el volumen (0-100)",
                "params": {"level": "int"}
            },
            {
                "name": "playlists",
                "description": "Lista tus playlists",
                "params": {}
            },
            {
                "name": "play_playlist",
                "description": "Reproduce una playlist por nombre",
                "params": {"name": "string"}
            }
        ]
    
    async def execute(self, action: str, params: dict) -> str:
        """Ejecuta una acción del MCP"""
        if not self.authenticated:
            return "❌ Spotify no está autenticado. Configura tus credenciales."
        
        actions = {
            "play": self._play,
            "pause": self._pause,
            "next": self._next,
            "previous": self._previous,
            "search": self._search,
            "current": self._current,
            "volume": self._volume,
            "playlists": self._playlists,
            "play_playlist": self._play_playlist
        }
        
        if action not in actions:
            return f"❌ Acción '{action}' no reconocida"
        
        try:
            result = await actions[action](params)
            return result
        except Exception as e:
            return f"❌ Error en Spotify: {str(e)}"
    
    async def _play(self, params: dict) -> str:
        """Reproduce música"""
        query = params.get('query', '')
        
        if query:
            # Buscar y reproducir
            results = self.sp.search(q=query, type='track', limit=1)
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                return f"❌ No encontré '{query}'"
            
            track = tracks[0]
            track_uri = track['uri']
            track_name = track['name']
            artist = track['artists'][0]['name']
            
            self.sp.start_playback(uris=[track_uri])
            return f"🎵 Reproduciendo: {track_name} - {artist}"
        else:
            # Continuar reproducción
            self.sp.start_playback()
            return "▶️ Reproducción reanudada"
    
    async def _pause(self, params: dict) -> str:
        """Pausa la reproducción"""
        self.sp.pause_playback()
        return "⏸️ Pausado"
    
    async def _next(self, params: dict) -> str:
        """Siguiente canción"""
        self.sp.next_track()
        await asyncio.sleep(0.5)  # Esperar a que cambie
        return await self._current({})
    
    async def _previous(self, params: dict) -> str:
        """Canción anterior"""
        self.sp.previous_track()
        await asyncio.sleep(0.5)
        return await self._current({})
    
    async def _search(self, params: dict) -> str:
        """Busca contenido"""
        query = params.get('query', '')
        search_type = params.get('type', 'track')
        
        if not query:
            return "❌ Especifica qué buscar"
        
        results = self.sp.search(q=query, type=search_type, limit=5)
        items = results.get(f'{search_type}s', {}).get('items', [])
        
        if not items:
            return f"❌ No encontré resultados para '{query}'"
        
        response = f"🔍 Resultados para '{query}':\n"
        for i, item in enumerate(items, 1):
            if search_type == 'track':
                artist = item['artists'][0]['name']
                response += f"{i}. {item['name']} - {artist}\n"
            else:
                response += f"{i}. {item['name']}\n"
        
        return response
    
    async def _current(self, params: dict) -> str:
        """Canción actual"""
        current = self.sp.current_playback()
        
        if not current or not current.get('item'):
            return "🔇 No hay nada reproduciéndose"
        
        track = current['item']
        name = track['name']
        artist = track['artists'][0]['name']
        is_playing = current.get('is_playing', False)
        
        status = "▶️" if is_playing else "⏸️"
        return f"{status} {name} - {artist}"
    
    async def _volume(self, params: dict) -> str:
        """Ajusta volumen"""
        level = params.get('level', 50)
        level = max(0, min(100, int(level)))
        
        self.sp.volume(level)
        return f"🔊 Volumen: {level}%"
    
    async def _playlists(self, params: dict) -> str:
        """Lista playlists"""
        playlists = self.sp.current_user_playlists(limit=10)
        items = playlists.get('items', [])
        
        if not items:
            return "📝 No tienes playlists"
        
        response = "📝 Tus playlists:\n"
        for i, pl in enumerate(items, 1):
            response += f"{i}. {pl['name']} ({pl['tracks']['total']} canciones)\n"
        
        return response
    
    async def _play_playlist(self, params: dict) -> str:
        """Reproduce una playlist por nombre"""
        name = params.get('name', '').lower()
        
        if not name:
            return "❌ Especifica el nombre de la playlist"
        
        playlists = self.sp.current_user_playlists(limit=50)
        items = playlists.get('items', [])
        
        for pl in items:
            if name in pl['name'].lower():
                self.sp.start_playback(context_uri=pl['uri'])
                return f"🎵 Reproduciendo playlist: {pl['name']}"
        
        return f"❌ No encontré playlist '{name}'"
