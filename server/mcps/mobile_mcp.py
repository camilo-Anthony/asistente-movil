"""
Mobile MCP - Control del dispositivo móvil Android
Usa Termux:API en Termux, o ADB en PC
"""
import subprocess
import asyncio
import os
from typing import Optional


class MobileMCP:
    """MCP para control del dispositivo móvil Android"""
    
    description = "Control del dispositivo móvil: abrir apps, enviar notificaciones"
    
    def __init__(self):
        self.is_termux = os.path.exists('/data/data/com.termux')
        
        if self.is_termux:
            print("📱 Mobile MCP: Modo Termux")
        else:
            self.adb_available = self._check_adb()
            if self.adb_available:
                print("📱 Mobile MCP: Modo ADB")
            else:
                print("⚠️ Mobile MCP: Sin ADB disponible")
    
    def _check_adb(self) -> bool:
        """Verifica si ADB está disponible"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_tools(self) -> list:
        """Retorna las herramientas disponibles de este MCP"""
        return [
            {
                "name": "open_app",
                "description": "Abre una aplicación por nombre",
                "params": {"app_name": "string"}
            },
            {
                "name": "notify",
                "description": "Envía una notificación",
                "params": {"title": "string", "message": "string"}
            },
            {
                "name": "vibrate",
                "description": "Hace vibrar el dispositivo",
                "params": {"duration": "int (ms)"}
            },
            {
                "name": "toast",
                "description": "Muestra un toast en pantalla",
                "params": {"message": "string"}
            },
            {
                "name": "clipboard",
                "description": "Copia texto al portapapeles",
                "params": {"text": "string"}
            },
            {
                "name": "tts",
                "description": "Habla un texto en voz alta",
                "params": {"text": "string"}
            }
        ]
    
    async def execute(self, action: str, params: dict) -> str:
        """Ejecuta una acción del MCP"""
        action_lower = action.lower().strip()
        
        # Detectar acción por keywords (más flexible)
        if any(kw in action_lower for kw in ['abrir', 'open', 'launch', 'iniciar', 'ejecutar', 'app']):
            return await self._open_app(params)
        elif any(kw in action_lower for kw in ['notif', 'aviso', 'alerta']):
            return await self._notify(params)
        elif any(kw in action_lower for kw in ['vibr']):
            return await self._vibrate(params)
        elif any(kw in action_lower for kw in ['toast', 'mensaje']):
            return await self._toast(params)
        elif any(kw in action_lower for kw in ['copi', 'clipboard', 'portapapeles']):
            return await self._clipboard(params)
        elif any(kw in action_lower for kw in ['habla', 'deci', 'speak', 'tts', 'voz']):
            return await self._tts(params)
        
        # Fallback: intentar como open_app si no matchea nada
        if params.get('app_name'):
            return await self._open_app(params)
        
        return f"❌ Acción '{action}' no reconocida"
    
    async def _run_termux_cmd(self, *args) -> tuple:
        """Ejecuta un comando de Termux:API"""
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode(), stderr.decode(), process.returncode
    
    async def _open_app(self, params: dict) -> str:
        """Abre una aplicación"""
        app_name = params.get('app_name', '').lower()
        query = params.get('query', '')
        
        # Mapeo a deep links y paquetes
        # 'search_url': URL/URI para búsquedas (usa {query})
        # 'pkg': Paquete de Android
        app_data = {
            'whatsapp': {
                'url': 'https://wa.me', 
                'pkg': 'com.whatsapp',
                'search_url': 'https://wa.me/?text={query}' 
            },
            'telegram': {'url': 'https://t.me', 'pkg': 'org.telegram.messenger'},
            'instagram': {'url': 'https://instagram.com', 'pkg': 'com.instagram.android'},
            'spotify': {
                'url': 'spotify://', 
                'pkg': 'com.spotify.music',
                'search_url': 'spotify:search:{query}' 
            },
            'youtube': {
                'url': 'https://youtube.com', 
                'pkg': 'com.google.android.youtube',
                'search_url': 'https://www.youtube.com/results?search_query={query}'
            },
            'gmail': {'url': 'https://mail.google.com', 'pkg': 'com.google.android.gm'},
            'chrome': {
                'url': 'https://google.com', 
                'pkg': 'com.android.chrome', 
                'search_url': 'https://www.google.com/search?q={query}'
            },
            'twitter': {
                'url': 'https://twitter.com', 
                'pkg': 'com.twitter.android',
                'search_url': 'https://twitter.com/search?q={query}'
            },
            'x': {
                'url': 'https://x.com', 
                'pkg': 'com.twitter.android',
                'search_url': 'https://x.com/search?q={query}'
            },
            'tiktok': {
                'url': 'https://tiktok.com', 
                'pkg': 'com.zhiliaoapp.musically',
                'search_url': 'https://www.tiktok.com/search?q={query}'
            },
            'facebook': {'url': 'https://facebook.com', 'pkg': 'com.facebook.katana'},
            'maps': {
                'url': 'https://maps.google.com', 
                'pkg': 'com.google.android.apps.maps',
                'search_url': 'geo:0,0?q={query}'
            },
            'netflix': {
                'url': 'https://netflix.com', 
                'pkg': 'com.netflix.mediaclient',
                'search_url': 'http://www.netflix.com/search/{query}'
            },
        }
        
        app_info = app_data.get(app_name)
        
        if self.is_termux:
            if not app_info:
                return f"❌ App '{app_name}' no configurada"

            pkg = app_info['pkg']
            
            # Si hay query y la app soporta búsqueda, usar el deep link de búsqueda
            if query and app_info.get('search_url'):
                search_url = app_info['search_url'].format(query=query)
                await self._run_termux_cmd('termux-open-url', search_url)
                return f"✅ Buscando '{query}' en {app_name}"

            # Si no, flujo normal de abrir app
            
            # Método 1: Usar monkey (más confiable)
            process = await asyncio.create_subprocess_shell(
                f'monkey -p {pkg} -c android.intent.category.LAUNCHER 1 2>/dev/null',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                return f"✅ Abriendo {app_name}"
            
            # Método 2: am start directo
            process = await asyncio.create_subprocess_shell(
                f'am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg} 2>/dev/null',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                return f"✅ Abriendo {app_name}"
            
            # Método 3: URL como último recurso
            if app_info.get('url'):
                await self._run_termux_cmd('termux-open-url', app_info['url'])
                return f"✅ Abriendo {app_name} (via web)"
            
            return f"❌ No se pudo abrir {app_name}"
        else:
            # Modo ADB
            if not self.adb_available:
                return "❌ ADB no está disponible"
            
            # ADB también podría soportar OPEN URL con intents, por ahora simple launch
            pkg = app_info['pkg'] if app_info else app_name
            process = await asyncio.create_subprocess_exec(
                'adb', 'shell', 'monkey', '-p', pkg, '-c',
                'android.intent.category.LAUNCHER', '1',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return f"✅ Abriendo {app_name}"




    
    async def _notify(self, params: dict) -> str:
        """Envía una notificación"""
        title = params.get('title', 'Asistente')
        message = params.get('message', '')
        
        if self.is_termux:
            await self._run_termux_cmd(
                'termux-notification',
                '-t', title,
                '-c', message
            )
            return f"🔔 Notificación enviada: {title}"
        else:
            return "❌ Notificaciones solo disponibles en Termux"
    
    async def _vibrate(self, params: dict) -> str:
        """Hace vibrar el dispositivo"""
        duration = params.get('duration', 500)
        
        if self.is_termux:
            await self._run_termux_cmd(
                'termux-vibrate', '-d', str(duration)
            )
            return f"📳 Vibrando por {duration}ms"
        else:
            return "❌ Vibración solo disponible en Termux"
    
    async def _toast(self, params: dict) -> str:
        """Muestra un toast"""
        message = params.get('message', '')
        
        if self.is_termux:
            await self._run_termux_cmd(
                'termux-toast', message
            )
            return f"💬 Toast mostrado"
        else:
            return "❌ Toast solo disponible en Termux"
    
    async def _clipboard(self, params: dict) -> str:
        """Copia al portapapeles"""
        text = params.get('text', '')
        
        if self.is_termux:
            process = await asyncio.create_subprocess_exec(
                'termux-clipboard-set',
                stdin=asyncio.subprocess.PIPE
            )
            await process.communicate(input=text.encode())
            return f"📋 Copiado al portapapeles"
        else:
            return "❌ Portapapeles solo disponible en Termux"
    
    async def _tts(self, params: dict) -> str:
        """Text-to-speech"""
        text = params.get('text', '')
        
        if self.is_termux:
            await self._run_termux_cmd(
                'termux-tts-speak', text
            )
            return f"🔊 Hablando: {text}"
        else:
            return "❌ TTS solo disponible en Termux"
