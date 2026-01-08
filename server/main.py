"""
Asistente Móvil - Punto de entrada principal
Ejecutar: python main.py [--voice]
"""
import asyncio
import json
import os
import sys

from core import Assistant
from wake_word import WakeWordDetector


def load_config():
    """Carga la configuración del usuario"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'config.json')
    
    if not os.path.exists(config_path):
        print("❌ No se encontró config.json")
        print("📝 Copia configs/config.example.json a configs/config.json")
        print("   y agrega tu API key")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def run_text_mode(assistant, wake_word):
    """Modo texto (entrada por teclado)"""
    print(f"\n✅ ¡Listo! Di 'Hey {wake_word}' seguido de tu comando")
    print("   Escribe 'salir' para terminar\n")
    
    while True:
        try:
            user_input = input("Tú: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("👋 ¡Hasta luego!")
                break
            
            if not user_input:
                continue
            
            response = await assistant.process_command(user_input)
            print(f"🤖: {response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def run_voice_mode(assistant, wake_word, voice_manager):
    """Modo voz (entrada y salida por audio)"""
    print(f"\n✅ ¡Modo voz activo!")
    print(f"   Di 'Hey {wake_word}' seguido de tu comando")
    print("   Presiona Ctrl+C para salir\n")
    
    voice_manager.speak(f"Hola, soy {wake_word}. ¿En qué puedo ayudarte?")
    
    while True:
        try:
            # Escuchar
            user_input = voice_manager.listen(timeout=10)
            
            if not user_input:
                continue
            
            print(f"Tú: {user_input}")
            
            # Procesar
            response = await assistant.process_command(user_input)
            print(f"🤖: {response}")
            
            # Responder con voz
            voice_manager.speak(response)
            
        except KeyboardInterrupt:
            voice_manager.speak("¡Hasta luego!")
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Función principal"""
    print("🤖 Iniciando Asistente Móvil...")
    print("=" * 50)
    
    # Detectar modo
    voice_mode = '--voice' in sys.argv or '-v' in sys.argv
    
    # Cargar configuración
    config = load_config()
    if not config:
        return
    
    wake_word = config['assistant'].get('wake_word', 'asistente')
    print(f"🎤 Wake word: 'Hey {wake_word}'")
    print(f"🌐 Idioma: {config['assistant'].get('language', 'es')}")
    print(f"🔊 Modo: {'Voz' if voice_mode else 'Texto'}")
    print("=" * 50)
    
    # Verificar API key
    api_key = config['llm'].get('api_key', '')
    if not api_key or 'TU_' in api_key:
        print("❌ Configura tu API key en configs/config.json")
        return
    
    # Inicializar asistente
    assistant = Assistant(config)
    
    if voice_mode:
        # Importar voice manager
        try:
            from voice import VoiceManager, VoiceManagerTermux
            
            # Usar versión Termux si está disponible
            if os.path.exists('/data/data/com.termux'):
                voice_manager = VoiceManagerTermux(config['assistant'].get('language', 'es'))
            else:
                voice_manager = VoiceManager(config['assistant'].get('language', 'es'))
            
            await run_voice_mode(assistant, wake_word, voice_manager)
        except ImportError as e:
            print(f"❌ Error importando módulo de voz: {e}")
            print("   Instala: pip install SpeechRecognition pyttsx3 pyaudio")
            print("   Ejecutando en modo texto...")
            await run_text_mode(assistant, wake_word)
    else:
        await run_text_mode(assistant, wake_word)


if __name__ == "__main__":
    asyncio.run(main())
