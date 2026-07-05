# 🧠 Agente Daily AI Dashboard

Este es tu panel inteligente de productividad y aprendizaje diario de Inteligencia Artificial. Recopila automáticamente el clima local, las noticias de última hora, las tareas de tu día y resume el paper científico más reciente de arXiv sobre Inteligencia Artificial.

Si tienes configurada tu clave de Gemini, el Agente traducirá, resumirá y extraerá los puntos clave del paper del día, te dará un consejo de enfoque personalizado para tus tareas y te explicará un nuevo concepto técnico con analogías cotidianas.

---

## 📂 Archivos del Proyecto

Coloca estos archivos en la misma carpeta en tu ordenador local con Windows:
1. `actualizar.bat` - El script ejecutable para Windows que inicia el proceso de actualización del Dashboard y levanta tu servidor web local.
2. `generar_dashboard.py` - El cerebro del Agente de Inteligencia Artificial que procesa las API, se conecta opcionalmente con Gemini y crea el archivo `index.html`.
3. `tareas.json` - El listado editable con las tareas que quieres cumplir durante tu jornada.
4. `.env` - **(Recomendado)** Tu archivo privado de configuración donde guardas tus claves e información de ubicación para que nadie más la vea.

---

## 🔒 Configuración Segura con `.env`

Para proteger tus claves y que no queden visibles dentro de los archivos de ejecución como `.bat`, el script de Python incluye un cargador nativo y seguro de variables de entorno.

### Paso 1: Crear el archivo `.env`
Crea un archivo de texto llamado sencillamente `.env` (asegúrate de que no termine en `.txt`) en la misma carpeta donde tienes los scripts y agrega tus datos de la siguiente manera:

```env
# Clave API de Google AI Studio (Gemini) para habilitar el análisis inteligente
GEMINI_API_KEY="tu_clave_de_gemini_aqui"

# Configuración de tu ubicación para el pronóstico del clima diario
DASHBOARD_CIUDAD="tu ciudad"
DASHBOARD_LATITUD="tu latitud"
DASHBOARD_LONGITUD="tu longitud"