"""
Detector de Wake Word personalizable
Permite que cada usuario configure su propio trigger
"""


class WakeWordDetector:
    """Detecta el wake word personalizado del usuario"""
    
    def __init__(self, wake_word: str, language: str = 'es'):
        self.wake_word = wake_word.lower()
        self.language = language
        self.triggers = self._build_triggers()
    
    def _build_triggers(self) -> list:
        """Construye las variantes del wake word"""
        ww = self.wake_word
        return [
            f"hey {ww}",
            f"oye {ww}",
            f"hola {ww}",
            f"ok {ww}",
            ww
        ]
    
    def detect(self, text: str) -> bool:
        """Detecta si el texto contiene el wake word"""
        text_lower = text.lower().strip()
        
        for trigger in self.triggers:
            if text_lower.startswith(trigger):
                return True
        
        return False
    
    def extract_command(self, text: str) -> str:
        """Extrae el comando después del wake word"""
        text_lower = text.lower().strip()
        
        for trigger in self.triggers:
            if text_lower.startswith(trigger):
                command = text[len(trigger):].strip()
                # Remover puntuación inicial
                if command and command[0] in ',.:':
                    command = command[1:].strip()
                return command
        
        return text
    
    def update_wake_word(self, new_wake_word: str):
        """Actualiza el wake word (para configuración en runtime)"""
        self.wake_word = new_wake_word.lower()
        self.triggers = self._build_triggers()
