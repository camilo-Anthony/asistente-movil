# Asistente Móvil - MCP Personalizable

Un asistente de IA para Android/Termux con wake word personalizable.

## Instalación en Termux

```bash
# Instalar dependencias
pkg install python
pip install -r requirements.txt

# Configurar
cp configs/config.example.json configs/config.json
# Editar config.json con tu API key de Gemini

# Ejecutar
python server/main.py
```

## Estructura

```
asistente-movil/
├── server/
│   ├── main.py           # Punto de entrada
│   ├── core.py           # Lógica principal
│   ├── wake_word.py      # Detección de wake word
│   └── mcps/             # MCPs propios
│       ├── mobile_mcp.py
│       ├── gmail_mcp.py
│       └── ...
└── configs/
    └── config.json       # Tu configuración
```

## Uso

```
Tú: "Hey [TuNombre], pon música en Spotify"
IA: "Reproduciendo tu playlist..."
```
