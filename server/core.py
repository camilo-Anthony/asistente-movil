"""
Core del Asistente - Lógica principal y conexión con LLM
Compatible con Termux (sin dependencias que necesitan Rust)
"""
from typing import Optional
import os
import json
import urllib.request
import urllib.error

# Importar MCPs
from mcps.mobile_mcp import MobileMCP
from mcps.spotify_mcp import SpotifyMCP


class Assistant:
    """Asistente principal que procesa comandos y coordina MCPs"""
    
    def __init__(self, config: dict):
        self.config = config
        self.wake_word = config['assistant'].get('wake_word', 'asistente')
        self.language = config['assistant'].get('language', 'es')
        
        # Configurar LLM según provider
        self.provider = config['llm'].get('provider', 'groq')
        self.api_key = config['llm'].get('api_key', '')
        self.model_name = config['llm'].get('model', 'llama-3.3-70b-versatile')
        
        print(f"✅ LLM: {self.provider} ({self.model_name})")
        
        # Inicializar MCPs habilitados
        self.mcps = {}
        self._init_mcps()
        
        # Contexto del sistema
        self.system_prompt = self._build_system_prompt()
    
    def _init_mcps(self):
        """Inicializa los MCPs habilitados en la configuración"""
        mcp_config = self.config.get('mcps', {})
        
        if mcp_config.get('mobile', {}).get('enabled', True):
            self.mcps['mobile'] = MobileMCP()
        
        # Spotify MCP (deshabilitado por defecto en Termux)
        if mcp_config.get('spotify', {}).get('enabled', False):
            try:
                self.mcps['spotify'] = SpotifyMCP(mcp_config.get('spotify', {}))
            except Exception as e:
                print(f"⚠️ Spotify MCP no disponible: {e}")
        
        # YouTube MCP (nuevo)
        if mcp_config.get('youtube', {}).get('enabled', False):
            try:
                from mcps.youtube_mcp import YouTubeMCP
                self.mcps['youtube'] = YouTubeMCP()
            except ImportError as e:
                print(f"❌ Falta yt-dlp para YouTube: {e}")
            except Exception as e:
                print(f"⚠️ YouTube MCP error: {e}")
    
    def _build_system_prompt(self) -> str:
        """Construye el prompt del sistema con las capacidades disponibles"""
        mcp_descriptions = []
        for name, mcp in self.mcps.items():
            mcp_descriptions.append(f"- {name}: {mcp.description}")
        
        mcps_text = "\n".join(mcp_descriptions) if mcp_descriptions else "- Ninguno habilitado"
        
        return f"""Eres un asistente personal llamado "{self.wake_word}".
Tu objetivo es ayudar al usuario con tareas en su dispositivo móvil.

CAPACIDADES DISPONIBLES (MCPs):
{mcps_text}

REGLAS:
1. Responde siempre en español de forma concisa y amigable
2. Si no puedes hacer algo, explica por qué
3. Para acciones en apps, usa los MCPs disponibles
4. Sé proactivo pero no invasivo

IMPORTANTE PARA YOUTUBE:
- Si el usuario dice "pon", "reproduce", "abre" o "play" → Pasa {{"auto_play": true}} en params
- Si el usuario dice "busca", "encuentra", "search" → NO pases auto_play (o false)
- Ejemplo: "pon Despacito en youtube" → {{"mcp": "youtube", "action": "search_video", "params": {{"query": "Despacito", "auto_play": true}}}}
- Ejemplo: "busca Despacito en youtube" → {{"mcp": "youtube", "action": "search_video", "params": {{"query": "Despacito"}}}}

Responde de forma natural y útil."""
    
    async def process_command(self, command: str) -> str:
        """Procesa un comando del usuario"""
        # Remover wake word si está presente
        command_lower = command.lower()
        for trigger in [f"hey {self.wake_word}", f"oye {self.wake_word}", self.wake_word]:
            if command_lower.startswith(trigger):
                command = command[len(trigger):].strip()
                if command.startswith(','):
                    command = command[1:].strip()
                break
        
        if not command:
            return "¿En qué puedo ayudarte?"
        
        try:
            # Analizar si el comando requiere un MCP
            mcp_action = await self._analyze_for_mcp(command)
            
            if mcp_action:
                # Ejecutar acción de MCP
                result = await self._execute_mcp_action(mcp_action)
                return result
            else:
                # Respuesta general con LLM
                response = self._generate_response(command)
                return response
                
        except Exception as e:
            return f"Lo siento, hubo un error: {str(e)}"
    
    def _call_groq_api(self, messages: list) -> str:
        """Llama a la API de Groq directamente con urllib (sin dependencias)"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Error API: {e.code} - {error_body}")
    
    def _generate_response(self, prompt: str) -> str:
        """Genera respuesta usando el LLM configurado"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        if self.provider == 'groq':
            return self._call_groq_api(messages)
        else:
            raise ValueError(f"Provider '{self.provider}' no soportado")
    
    async def _analyze_for_mcp(self, command: str) -> Optional[dict]:
        """Analiza si el comando requiere una acción de MCP"""
        mcp_tools = self._get_mcp_tools_description()
        
        if not mcp_tools or mcp_tools == "Ninguna herramienta disponible":
            return None
        
        analysis_prompt = f"""Analiza este comando y determina si requiere una acción de MCP.

MCPs disponibles:
{mcp_tools}

Comando: "{command}"

Responde SOLO en formato JSON:
{{"requires_mcp": true/false, "mcp": "nombre", "action": "accion", "params": {{}}}}

Si no requiere MCP, responde: {{"requires_mcp": false}}"""
        
        try:
            response = self._generate_response(analysis_prompt)
            text = response.strip()
            
            # Extraer JSON
            import re
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if data.get('requires_mcp', False):
                    return data
        except:
            pass
        
        return None
    
    def _get_mcp_tools_description(self) -> str:
        """Obtiene descripción de herramientas de MCPs"""
        descriptions = []
        for name, mcp in self.mcps.items():
            tools = mcp.get_tools()
            for tool in tools:
                descriptions.append(f"- {name}.{tool['name']}: {tool['description']}")
        
        return "\n".join(descriptions) if descriptions else "Ninguna herramienta disponible"
    
    async def _execute_mcp_action(self, action: dict) -> str:
        """Ejecuta una acción de MCP"""
        mcp_name = action.get('mcp', '')
        action_name = action.get('action', '')
        params = action.get('params', {})
        
        # Si el mcp_name tiene formato "mcp.action", separarlo
        if '.' in mcp_name:
            parts = mcp_name.split('.', 1)
            mcp_name = parts[0]
            if not action_name:
                action_name = parts[1]
        
        if mcp_name not in self.mcps:
            return f"MCP '{mcp_name}' no está disponible"
        
        mcp = self.mcps[mcp_name]
        result = await mcp.execute(action_name, params)
        
        return result
