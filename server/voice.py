"""
Voice Manager - Speech-to-Text y Text-to-Speech
Soporta múltiples backends para máxima compatibilidad
"""
import os
import subprocess
import threading


class VoiceManager:
    """Maneja entrada y salida de voz (PC/Generic)"""
    
    def __init__(self, language: str = 'es'):
        self.language = language
        self.stt_engine = None
        self.tts_engine = None
        
        self._init_stt()
        self._init_tts()
    
    def _init_stt(self):
        """Inicializa Speech-to-Text"""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.stt_engine = 'google'
        except ImportError:
            pass # Silencioso si falla import, se manejará en listen
        except Exception:
            pass
    
    def _init_tts(self):
        """Inicializa Text-to-Speech"""
        try:
            import pyttsx3
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 150)
            self.tts_engine = 'pyttsx3'
        except ImportError:
            pass
        except Exception:
            pass
    
    def listen(self, timeout: int = 5) -> str:
        """Escucha y convierte voz a texto"""
        if not self.stt_engine:
            return input("🎤 (Escribe aquí): ")
        
        import speech_recognition as sr
        try:
            with self.microphone as source:
                print("🎤 Escuchando...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            print("🔄 Procesando...")
            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"📝 Escuché: {text}")
            return text
        except Exception:
            return ""
    
    def speak(self, text: str):
        """Convierte texto a voz"""
        if self.tts_engine:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                print(f"🔊 {text}")
        else:
            print(f"🔊 {text}")


class VoiceManagerTermux(VoiceManager):
    """Versión para Termux usando termux-microphone-record (más estable)"""
    
    def __init__(self, language: str = 'es'):
        self.language = language
        print("📱 Voice Manager: Modo Termux (Whisper API)")
        
        # Verificar dependencias críticas
        import shutil
        missing = []
        
        if not shutil.which('termux-microphone-record'):
            missing.append("termux-api (pkg install termux-api)")
            
        if missing:
            print("❌ FALTAN DEPENDENCIAS CRÍTICAS:")
            for m in missing:
                print(f"   - {m}")
            print("⚠️ El reconocimiento de voz NO funcionará correctamente.")
            self.disabled = True
        else:
            self.disabled = False

    def listen(self, timeout: int = 5) -> str:
        """Graba audio a archivo y luego lo transcribe con Groq Whisper"""
        if getattr(self, 'disabled', False):
            return input("⌨️ (Falta termux-api) Escribe aquí: ")
            
        import time
        
        # Archivo temporal
        filename = "temp_audio.wav"
        
        try:
            # Asegurar que no hay grabación previa corriendo
            subprocess.run(['termux-microphone-record', '-q'], check=False, capture_output=True)
            if os.path.exists(filename):
                os.remove(filename)
                
            print(f"🎤 Escuchando... (habla por {timeout}s)")
            
            # Iniciar grabación
            subprocess.run([
                'termux-microphone-record',
                '-l', str(timeout),
                '-f', filename
            ], check=True)
            
            # Esperar a que el archivo se escriba bien
            time.sleep(0.5)
            
            if not os.path.exists(filename) or os.path.getsize(filename) < 100:
                print("❌ Audio vacío o no generado")
                return ""
            
            print("🔄 Procesando audio con Whisper...")
            
            # Transcribir usando Groq Whisper API
            text = self._transcribe_with_groq(filename)
            
            if text:
                print(f"📝 Escuché: {text}")
                return text
            else:
                print("❓ No entendí")
                return ""
            
        except subprocess.CalledProcessError:
            print("❌ Error grabando (termux-api)")
            return ""
        except Exception as e:
            print(f"❌ Error: {e}")
            return ""
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def _transcribe_with_groq(self, audio_file: str) -> str:
        """Transcribe audio usando Groq Whisper API"""
        import urllib.request
        import urllib.error
        import json
        
        # Leer API key desde variable de entorno o config
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            # Intentar leer del config
            try:
                import json
                with open('../configs/config.json', 'r') as f:
                    config = json.load(f)
                    api_key = config.get('llm', {}).get('api_key')
            except:
                pass
        
        if not api_key:
            raise Exception("No se encontró GROQ_API_KEY")
        
        # Preparar multipart/form-data manualmente
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        # Construir body multipart
        body_parts = []
        
        # Parte 1: file
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="file"; filename="audio.wav"')
        body_parts.append(b'Content-Type: audio/wav')
        body_parts.append(b'')
        body_parts.append(audio_data)
        
        # Parte 2: model
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"')
        body_parts.append(b'')
        body_parts.append(b'whisper-large-v3-turbo')
        
        # Parte 3: language (opcional)
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="language"')
        body_parts.append(b'')
        body_parts.append(self.language.encode())
        
        # Fin
        body_parts.append(f'--{boundary}--'.encode())
        body_parts.append(b'')
        
        body = b'\r\n'.join(body_parts)
        
        # Hacer request
        url = 'https://api.groq.com/openai/v1/audio/transcriptions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Accept': '*/*'
        }
        
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                return result.get('text', '').strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Groq Whisper error: {error_body}")
        except Exception as e:
            raise Exception(f"Error transcribiendo: {e}")

    def speak(self, text: str):
        """Habla usando termux-tts-speak"""
        print(f"🔊 {text}")
        try:
            subprocess.run(['termux-tts-speak', text], check=False)
        except Exception:
            pass
