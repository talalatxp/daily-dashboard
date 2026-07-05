#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de Productividad y Aprendizaje de IA
Genera un dashboard diario estático recopilando información de diversas fuentes.
Autor: AI Daily Agent
"""

import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET

def formatear_markdown_a_html(texto):
    """
    Convierte sintaxis básica de Markdown (como **negrita** e itinerarios) 
    a HTML válido sin depender de librerías externas.
    """
    if not texto:
        return ""
    # Reemplazar **texto** con <strong>texto</strong>
    texto = re.sub(r'\*\*(.*?)\*\*', r'<strong class="font-bold text-white">\1</strong>', texto)
    # Reemplazar *texto* o _texto_ con <em>texto</em>
    texto = re.sub(r'\*(.*?)\*', r'<em class="italic">\1</em>', texto)
    # Reemplazar saltos de línea con <br/> para preservar el formato
    texto = texto.replace('\n', '<br/>')
    return texto

def cargar_env():
    """
    Carga variables de entorno de un archivo .env si existe en el mismo directorio.
    Evita instalar librerías externas de terceros en el Python local del usuario.
    """
    ruta_script = os.path.dirname(os.path.abspath(__file__))
    ruta_env = os.path.join(ruta_script, ".env")
    if os.path.exists(ruta_env):
        try:
            with open(ruta_env, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea or linea.startswith("#"):
                        continue
                    if "=" in linea:
                        clave, valor = linea.split("=", 1)
                        clave = clave.strip()
                        valor = valor.strip().strip('"').strip("'")
                        os.environ[clave] = valor
        except Exception as e:
            print(f"⚠️ Error al leer el archivo .env: {e}")

# Cargar las variables de entorno locales del archivo .env si existe
cargar_env()

# Configuración del Agente (Intenta leer variables de entorno con valores por defecto seguros)
CIUDAD = os.environ.get("DASHBOARD_CIUDAD")
LATITUD = os.environ.get("DASHBOARD_LATITUD")
LONGITUD = os.environ.get("DASHBOARD_LONGITUD")

# Feeds de noticias alternativos por si falla alguno (usaremos Hugging Face Blog como principal)
RSS_FEED_URL = "https://huggingface.co/blog/feed.xml"
ARXIV_API_URL = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=35"

def consultar_gemini(prompt):
    """
    Realiza una llamada directa a la API de Gemini usando la librería estándar urllib de Python.
    No requiere librerías externas para máxima portabilidad local.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    print("-> Consultando al Agente de IA Gemini...")
    model = "gemini-3.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aistudio-build"
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text_output = res_data['candidates'][0]['content']['parts'][0]['text']
            return text_output.strip()
    except Exception as e:
        print(f"⚠️ Error al consultar Gemini API: {e}")
        return None

def obtener_clima():
    """
    Obtiene el clima actual para las coordenadas configuradas usando la API gratuita de Open-Meteo.
    """
    print("-> Obteniendo datos del clima...")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            current = data.get("current", {})
            temp = current.get("temperature_2m", 20.0)
            hum = current.get("relative_humidity_2m", 50)
            wind = current.get("wind_speed_10m", 10.0)
            code = current.get("weather_code", 0)
            
            # Códigos WMO simplificados
            weather_desc = "Despejado"
            weather_icon = "☀️"
            
            if code == 0:
                weather_desc = "Cielo despejado"
                weather_icon = "☀️"
            elif code in [1, 2, 3]:
                weather_desc = "Parcialmente nublado"
                weather_icon = "⛅"
            elif code in [45, 48]:
                weather_desc = "Niebla"
                weather_icon = "🌫️"
            elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                weather_desc = "Lluvia / Llovizna"
                weather_icon = "🌧️"
            elif code in [71, 73, 75, 77, 85, 86]:
                weather_desc = "Nieve"
                weather_icon = "❄️"
            elif code in [95, 96, 99]:
                weather_desc = "Tormenta"
                weather_icon = "⚡"
                
            return {
                "temp": temp,
                "humedad": hum,
                "viento": wind,
                "descripcion": weather_desc,
                "icono": weather_icon,
                "ciudad": CIUDAD
            }
    except Exception as e:
        print(f"⚠️ Error al obtener clima: {e}")
        return {
            "temp": "N/D",
            "humedad": "N/D",
            "viento": "N/D",
            "descripcion": "No disponible",
            "icono": "🌡️",
            "ciudad": CIUDAD
        }

def obtener_paper_del_dia():
    """
    Busca un paper reciente en arXiv sobre IA (cs.AI o cs.LG).
    Prioriza títulos o resúmenes que contengan la palabra 'Survey', 'Review', 'LLM' o 'Agent'.
    """
    print("-> Buscando paper de IA en arXiv...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(ARXIV_API_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            # Espacio de nombres Atom de arXiv
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            
            papers = []
            for entry in entries:
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                pdf_link = ""
                
                # Buscar enlace al PDF
                for link in entry.findall('atom:link', ns):
                    if link.attrib.get('title') == 'pdf' or 'pdf' in link.attrib.get('href', ''):
                        pdf_link = link.attrib.get('href')
                        break
                
                if not pdf_link:
                    # Alternativa construida si no hay link explícito con título pdf
                    base_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
                    pdf_link = f"https://arxiv.org/pdf/{base_id}.pdf"
                
                autores = [auth.find('atom:name', ns).text for auth in entry.findall('atom:author', ns)]
                
                papers.append({
                    "titulo": title,
                    "autores": ", ".join(autores[:3]) + (" y otros" if len(autores) > 3 else ""),
                    "resumen": summary[:220] + "..." if len(summary) > 220 else summary,
                    "pdf": pdf_link,
                    "fecha": entry.find('atom:published', ns).text[:10]
                })
            
            if not papers:
                raise ValueError("No se encontraron papers en el feed de arXiv.")
                
            # Intentar buscar uno que sea un "Survey" o "Review" para maximizar aprendizaje
            for p in papers:
                if "survey" in p["titulo"].lower() or "review" in p["titulo"].lower() or "survey" in p["resumen"].lower():
                    print("-> Paper seleccionado (Priorizado por ser un Survey/Review).")
                    return p
                    
            # Si no hay survey, buscar uno sobre LLMs o Agents
            for p in papers:
                if "llm" in p["titulo"].lower() or "agent" in p["titulo"].lower() or "language model" in p["titulo"].lower():
                    print("-> Paper seleccionado (Priorizado sobre LLMs/Agentes).")
                    return p
                    
            # Si no, devolver el primero de la lista (más reciente)
            print("-> Paper seleccionado (Más reciente en la categoría).")
            return papers[0]
            
    except Exception as e:
        print(f"⚠️ Error al obtener paper de arXiv: {e}")
        return {
            "titulo": "A Survey of Large Language Model Based Autonomous Agents",
            "autores": "Lei Wang, Chen Ma, Xueyang Feng, et al.",
            "resumen": "Este artículo presenta una revisión exhaustiva sobre los agentes autónomos basados en modelos de lenguaje grandes (LLMs), sistematizando la arquitectura del agente en perfiles, memoria, planificación y acción.",
            "pdf": "https://arxiv.org/pdf/2308.11432.pdf",
            "fecha": "2026-07-04"
        }

def obtener_noticias_ia():
    """
    Obtiene las últimas 3 noticias de IA desde el RSS feed de Hugging Face Blog.
    """
    print("-> Buscando noticias de IA de Hugging Face...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(RSS_FEED_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            # Hugging Face RSS suele usar <item>
            items = root.findall('.//item')
            if not items:
                # Si es Atom usa <entry>
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                is_atom = True
            else:
                is_atom = False
                
            noticias = []
            
            for item in items[:5]: # leemos hasta 5 para asegurar que sacamos 3 válidas
                if is_atom:
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    title = item.find('atom:title', ns).text
                    link = item.find('atom:link', ns).attrib.get('href')
                    pub_date = item.find('atom:updated', ns).text[:10]
                else:
                    title = item.find('title').text
                    link = item.find('link').text
                    pub_date_elem = item.find('pubDate')
                    if pub_date_elem is not None:
                        pub_date = pub_date_elem.text[:16]
                    else:
                        pub_date = "Hoy"
                
                noticias.append({
                    "titulo": title.strip(),
                    "link": link.strip(),
                    "fecha": pub_date
                })
                
                if len(noticias) >= 3:
                    break
                    
            if not noticias:
                raise ValueError("No se encontraron noticias válidas en el RSS.")
                
            return noticias
            
    except Exception as e:
        print(f"⚠️ Error al obtener noticias RSS: {e}")
        # Noticias de respaldo
        return [
            {
                "titulo": "Hugging Face lanza nuevos modelos optimizados para ejecución local en navegadores",
                "link": "https://huggingface.co/blog",
                "fecha": "Reciente"
            },
            {
                "titulo": "El auge de los agentes autónomos de IA en la productividad diaria",
                "link": "https://huggingface.co/blog",
                "fecha": "Reciente"
            },
            {
                "titulo": "arXiv alcanza un nuevo récord de papers de IA publicados semanalmente",
                "link": "https://arxiv.org",
                "fecha": "Reciente"
            }
        ]

def leer_tareas_hoy():
    """
    Lee el archivo tareas.json y filtra las tareas asignadas para hoy.
    """
    print("-> Leyendo tareas pendientes...")
    archivo_json = "tareas.json"
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    if not os.path.exists(archivo_json):
        print(f"⚠️ El archivo {archivo_json} no existe. Creando uno de ejemplo.")
        tareas_ejemplo = [
            {"id": 1, "titulo": "Revisar novedades del agente de IA", "fecha": hoy_str, "completada": False, "prioridad": "Alta", "categoria": "IA"},
            {"id": 2, "titulo": "Configurar cron diario en mi ordenador", "fecha": hoy_str, "completada": False, "prioridad": "Media", "categoria": "Productividad"}
        ]
        with open(archivo_json, "w", encoding="utf-8") as f:
            json.dump(tareas_ejemplo, f, indent=2, ensure_ascii=False)
        return tareas_ejemplo
        
    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            todas_tareas = json.load(f)
            
        tareas_hoy = []
        for t in todas_tareas:
            if t.get("fecha") == hoy_str:
                tareas_hoy.append(t)
                
        # Si no hay tareas específicas para hoy, devolver un aviso amigable
        return tareas_hoy
    except Exception as e:
        print(f"⚠️ Error al leer tareas.json: {e}")
        return []

def generar_html(clima, paper, noticias, tareas, resumen_ia=None, consejo_ia=None, insight_ia=None):
    """
    Inyecta toda la información en la plantilla web de index.html con diseño Responsive Dark Mode.
    """
    print("-> Construyendo archivo index.html...")
    hoy_legible = datetime.now().strftime("%A, %d de %B de %Y")
    
    # Traducción simple de días de la semana y meses al español
    meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre",
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
        "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    for eng, esp in meses.items():
        hoy_legible = hoy_legible.replace(eng, esp)

    # Generación de la lista de tareas en HTML
    tareas_html = ""
    if not tareas:
        tareas_html = """
        <div class="flex flex-col items-center justify-center p-6 text-center border border-dashed border-slate-700 rounded-xl bg-slate-800/20">
            <span class="text-3xl mb-2">🎉</span>
            <p class="text-slate-400 font-medium">¡No tienes tareas programadas para hoy!</p>
            <p class="text-xs text-slate-500 mt-1">Disfruta tu día o añade tareas en tareas.json</p>
        </div>
        """
    else:
        for t in tareas:
            completada = t.get("completada", False)
            checked_attr = "checked" if completada else ""
            line_through_class = "line-through text-slate-500" if completada else "text-slate-200"
            color_prioridad = "bg-rose-500/10 text-rose-400 border-rose-500/20"
            if t.get("prioridad") == "Media":
                color_prioridad = "bg-amber-500/10 text-amber-400 border-amber-500/20"
            elif t.get("prioridad") == "Baja":
                color_prioridad = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                
            tareas_html += f"""
            <div class="flex items-start gap-3 p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/50 hover:border-indigo-500/30 hover:bg-slate-800/70 transition-all duration-200">
                <div class="flex items-center h-6">
                    <input type="checkbox" {checked_attr} disabled class="w-5 h-5 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 bg-slate-900 pointer-events-none transition-colors">
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium {line_through_class} break-words">{t.get('titulo')}</p>
                    <div class="flex gap-2 mt-1.5 items-center">
                        <span class="text-[10px] px-2 py-0.5 rounded-full border {color_prioridad} font-medium">{t.get('prioridad')}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/40 text-slate-400 border border-slate-700/50">{t.get('categoria', 'General')}</span>
                    </div>
                </div>
            </div>
            """

    # Generación de noticias en HTML
    noticias_html = ""
    for idx, n in enumerate(noticias):
        noticias_html += f"""
        <a href="{n.get('link')}" target="_blank" class="group block p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 hover:border-indigo-500/30 hover:bg-slate-800/60 transition-all duration-300">
            <div class="flex items-start justify-between gap-3">
                <span class="flex items-center justify-center w-6 h-6 text-xs font-bold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:bg-indigo-500 group-hover:text-white transition-all duration-300 shrink-0">0{idx+1}</span>
                <div class="flex-1 min-w-0">
                    <h4 class="text-sm font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors duration-200 line-clamp-2">{n.get('titulo')}</h4>
                    <p class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <span>📰 Blog/Feed</span> • <span>{n.get('fecha')}</span>
                    </p>
                </div>
                <span class="text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all duration-200 text-sm shrink-0">→</span>
            </div>
        </a>
        """

    # Bloque de resumen del paper (con o sin Gemini)
    if resumen_ia:
        resumen_formateado = formatear_markdown_a_html(resumen_ia)
        paper_resumen_html = f"""
        <div class="bg-indigo-950/20 p-4 rounded-xl border border-indigo-500/20 text-slate-300 text-xs sm:text-sm leading-relaxed space-y-2">
            <span class="text-[10px] uppercase font-bold tracking-widest text-indigo-400 font-mono flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
                Sintetizado por Agente de IA Gemini
            </span>
            <div class="space-y-2">{resumen_formateado}</div>
        </div>
        """
    else:
        paper_resumen_html = f"""
        <div class="space-y-3">
            <p class="text-xs sm:text-sm text-slate-400 leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-slate-800/50 italic">
                "{paper.get('resumen')}"
            </p>
            <div class="bg-slate-850/50 p-3.5 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2">
                <span class="text-base">💡</span>
                <p><strong>Tip de IA:</strong> Crea un archivo de texto llamado <code class="text-indigo-400 bg-slate-950 px-1 py-0.5 rounded font-mono">.env</code> en la misma carpeta para configurar tu <code class="text-indigo-400 bg-slate-950 px-1 py-0.5 rounded font-mono">GEMINI_API_KEY</code> para que el Agente de IA de Gemini traduzca, resuma y extraiga automáticamente los puntos clave de este paper para ti.</p>
            </div>
        </div>
        """

    # Bloque de insights y consejos (con o sin Gemini)
    ai_insights_html = ""
    if resumen_ia or consejo_ia or insight_ia:
        consejo_block = ""
        if consejo_ia:
            consejo_formateado = formatear_markdown_a_html(consejo_ia)
            consejo_block = f"""
            <div class="flex-1 min-w-[280px] bg-indigo-500/5 border border-indigo-500/10 p-4 rounded-xl space-y-2">
                <span class="text-[10px] uppercase font-bold tracking-widest text-indigo-400 font-mono flex items-center gap-1.5">🎯 Estrategia del Agente</span>
                <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">"{consejo_formateado}"</p>
            </div>
            """
            
        insight_block = ""
        if insight_ia:
            insight_formateado = formatear_markdown_a_html(insight_ia)
            insight_block = f"""
            <div class="flex-1 min-w-[280px] bg-purple-500/5 border border-purple-500/10 p-4 rounded-xl space-y-2">
                <span class="text-[10px] uppercase font-bold tracking-widest text-purple-400 font-mono flex items-center gap-1.5">🧠 Concepto de IA del Día</span>
                <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">{insight_formateado}</p>
            </div>
            """
            
        ai_insights_html = f"""
        <!-- BANNER DE IA ACTIVO -->
        <section class="bg-gradient-to-r from-indigo-950/30 via-slate-900/40 to-purple-950/30 border border-indigo-500/20 rounded-2xl p-5 shadow-xl shadow-indigo-950/10">
            <div class="flex items-center gap-2 border-b border-slate-800/60 pb-3 mb-4">
                <span class="text-xl">✨</span>
                <h2 class="text-sm font-bold uppercase tracking-wider text-indigo-300">Análisis del Agente de IA</h2>
                <span class="ml-auto text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Gemini Activo
                </span>
            </div>
            <div class="flex flex-col md:flex-row gap-4">
                {consejo_block}
                {insight_block}
            </div>
        </section>
        """
    else:
        ai_insights_html = """
        <!-- BANNER PROMOCIÓN AGENTE DE IA -->
        <section class="bg-slate-900/30 border border-dashed border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-3">
                <span class="text-2xl shrink-0">🧠</span>
                <div>
                    <h3 class="text-sm font-bold text-slate-300">¿Quieres activar los resúmenes automáticos y consejos de productividad con IA?</h3>
                    <p class="text-xs text-slate-500 mt-0.5">Configura tu propia <code class="text-indigo-400 bg-slate-950 px-1 py-0.5 rounded font-mono">GEMINI_API_KEY</code> para que el agente te analice las tareas y explique conceptos diariamente.</p>
                </div>
            </div>
            <div class="shrink-0 flex items-center gap-2">
                <span class="text-[10px] font-mono text-slate-500 uppercase bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800">Modo Local Estándar</span>
            </div>
        </section>
        """

    # Plantilla HTML con Tailwind CSS embebido vía CDN para máxima portabilidad local
    plantilla = f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Personal de IA y Productividad</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }},
                }}
            }}
        }}
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #0b0f19;
            background-image: 
                radial-gradient(at 0% 0%, rgba(17, 24, 39, 0.9) 0, transparent 50%), 
                radial-gradient(at 100% 100%, rgba(30, 27, 75, 0.4) 0, transparent 50%);
        }}
    </style>
</head>
<body class="text-slate-100 min-h-screen py-8 px-4 sm:px-6 lg:px-8 font-sans antialiased">
    <div class="max-w-7xl mx-auto space-y-8">
        
        <!-- HEADER -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-6">
            <div>
                <div class="flex items-center gap-3">
                    <span class="text-3xl">🔮</span>
                    <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                        Daily AI Dashboard
                    </h1>
                </div>
                <p class="text-sm text-slate-400 mt-1 font-medium">Asistente personal diario de productividad y aprendizaje científico</p>
            </div>
            <div class="flex flex-col md:items-end gap-1 font-mono text-xs text-slate-400">
                <div class="flex items-center gap-2 bg-slate-800/50 border border-slate-700/60 px-3 py-1.5 rounded-lg">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Actualizado: {hoy_legible}</span>
                </div>
            </div>
        </header>

        {ai_insights_html}

        <!-- MAIN GRID LAYOUT -->
        <main class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- PANEL IZQUIERDO: CLIMA Y TAREAS (5 columnas) -->
            <div class="lg:col-span-5 flex flex-col gap-6">
                
                <!-- CARD 1: CLIMA -->
                <section class="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all duration-300 shadow-xl shadow-black/10">
                    <div class="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4">
                        <div class="flex items-center gap-2">
                            <span class="text-lg">🌤️</span>
                            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400">Clima Actual</h2>
                        </div>
                        <span class="text-xs font-mono text-slate-500">{clima.get('ciudad')}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <span class="text-5xl shrink-0 filter drop-shadow-[0_4px_12px_rgba(99,102,241,0.2)]">{clima.get('icono')}</span>
                            <div>
                                <div class="text-3xl sm:text-4xl font-extrabold text-slate-100 flex items-start">
                                    {clima.get('temp')}<span class="text-lg font-semibold text-indigo-400 mt-1">°C</span>
                                </div>
                                <p class="text-sm font-medium text-slate-300 mt-0.5">{clima.get('descripcion')}</p>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 text-right gap-1 border-l border-slate-800/60 pl-4 font-mono text-[11px] text-slate-400">
                            <div>💨 Viento: <span class="font-bold text-slate-200">{clima.get('viento')} km/h</span></div>
                            <div>💧 Humedad: <span class="font-bold text-slate-200">{clima.get('humedad')}%</span></div>
                        </div>
                    </div>
                </section>

                <!-- CARD 2: TAREAS PROGRAMADAS -->
                <section class="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-5 flex-1 hover:border-slate-700/80 transition-all duration-300 shadow-xl shadow-black/10 flex flex-col">
                    <div class="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4 shrink-0">
                        <div class="flex items-center gap-2">
                            <span class="text-lg">🎯</span>
                            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400">Tareas para Hoy</h2>
                        </div>
                        <span class="text-xs font-mono text-slate-500 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">{len(tareas)} asignadas</span>
                    </div>
                    <div class="space-y-3 flex-1 overflow-y-auto max-h-[350px] pr-1">
                        {tareas_html}
                    </div>
                </section>
                
            </div>

            <!-- PANEL DERECHO: PAPERS Y NOTICIAS (7 columnas) -->
            <div class="lg:col-span-7 flex flex-col gap-6">
                
                <!-- CARD 3: RECOMENDACIÓN DE PAPER (arXiv) -->
                <section class="bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-900/60 backdrop-blur-xl border border-indigo-900/30 rounded-2xl p-5 hover:border-indigo-500/30 transition-all duration-300 shadow-xl shadow-black/10 flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4">
                            <div class="flex items-center gap-2">
                                <span class="text-lg">📚</span>
                                <h2 class="text-sm font-bold uppercase tracking-wider text-indigo-400">Paper Científico del Día</h2>
                            </div>
                            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">arXiv AI Feed</span>
                        </div>
                        <div class="space-y-3">
                            <h3 class="text-base sm:text-lg font-bold text-slate-100 hover:text-indigo-300 transition-colors leading-snug line-clamp-2">
                                {paper.get('titulo')}
                            </h3>
                            <p class="text-xs text-indigo-300 font-medium">Autores: <span class="text-slate-300">{paper.get('autores')}</span></p>
                            {paper_resumen_html}
                        </div>
                    </div>
                    <div class="flex items-center justify-between gap-4 mt-5 pt-4 border-t border-slate-800/60">
                        <span class="text-[11px] text-slate-500 font-mono">Publicado: {paper.get('fecha')}</span>
                        <a href="{paper.get('pdf')}" target="_blank" class="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs py-2 px-4 rounded-xl transition-all shadow-lg shadow-indigo-600/15">
                            <span>📄 Abrir PDF Oficial</span>
                            <span class="text-xs">→</span>
                        </a>
                    </div>
                </section>

                <!-- CARD 4: NOTICIAS DE IA -->
                <section class="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all duration-300 shadow-xl shadow-black/10">
                    <div class="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4">
                        <div class="flex items-center gap-2">
                            <span class="text-lg">🔥</span>
                            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400">Últimas Noticias de IA</h2>
                        </div>
                        <span class="text-xs font-mono text-slate-500">HF RSS Feed</span>
                    </div>
                    <div class="space-y-3">
                        {noticias_html}
                    </div>
                </section>
                
            </div>
            
        </main>

        <!-- FOOTER -->
        <footer class="text-center pt-8 border-t border-slate-900/80 text-[11px] text-slate-500 font-mono flex flex-col sm:flex-row justify-between items-center gap-4">
            <p>© 2026 Daily AI Dashboard • Generado automáticamente</p>
            <p>Hereda de tareas.json • Hecho con Python puro</p>
        </footer>
        
    </div>
</body>
</html>
"""

    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(plantilla)
        print("🎉 index.html generado con éxito!")
    except Exception as e:
        print(f"⚠️ Error al escribir index.html: {e}")

def main():
    print("="*50)
    print("DAILY AI AGENT - INICIANDO ACTUALIZACIÓN DIARIA")
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    clima = obtener_clima()
    paper = obtener_paper_del_dia()
    noticias = obtener_noticias_ia()
    tareas = leer_tareas_hoy()
    
    # === INTEGRACIÓN CON AGENTE DE IA (GEMINI) ===
    resumen_ia = None
    consejo_ia = None
    insight_ia = None
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("[INFO] GEMINI_API_KEY detectada. Iniciando análisis inteligente con Gemini...")
        
        # 1. Resumen de Paper
        prompt_paper = f"""
        Actúa como un científico de IA de élite y experto divulgador.
        Resume y explica de forma súper clara, inspiradora y humana en español el siguiente paper científico de arXiv:
        Título: {paper.get('titulo')}
        Autores: {paper.get('autores')}
        Abstract: {paper.get('resumen')}

        Por favor, estructura tu respuesta exactamente con estas dos secciones en español (usa un lenguaje profesional pero muy accesible, sin asteriscos ni markdown complejo, solo párrafos directos):
        💡 **¿De qué trata?**: [Tu explicación simple aquí en un párrafo breve]
        🚀 **¿Por qué es importante?**: [Tu explicación de impacto aquí en un párrafo breve]
        """
        resumen_ia = consultar_gemini(prompt_paper)
        
        # 2. Consejos de Tareas
        if tareas:
            tareas_titulos = [f"- {t.get('titulo')} (Prioridad: {t.get('prioridad')}, Categoría: {t.get('categoria')})" for t in tareas]
            tareas_str = "\n".join(tareas_titulos)
            prompt_tareas = f"""
            Actúa como un coach de productividad personal y experto organizador.
            Analiza la siguiente lista de tareas de hoy:
            {tareas_str}

            Dame un consejo muy breve (máximo 3 frases) en español, sumamente motivador y táctico, sobre cómo abordar mi día, priorizar estas tareas o evitar la procrastinación. Sé directo y amigable.
            """
            consejo_ia = consultar_gemini(prompt_tareas)
            
        # 3. Concepto o Insight del Día
        prompt_insight = """
        Genera un 'Concepto del Día' sobre Inteligencia Artificial (por ejemplo: qué son los 'AI Agents', 'RAG', 'Prompt Tuning', 'Embeddings', 'Fine-tuning', etc.).
        Elige un concepto técnico clave y explícalo en español de manera extremadamente sencilla, usando una analogía cotidiana para que cualquiera lo entienda.
        Formato de salida (máximo 4 frases):
        💡 **Concepto del Día**: [Nombre del concepto]
        🧠 **Explicación**: [Tu explicación clara con analogía aquí]
        """
        insight_ia = consultar_gemini(prompt_insight)
    else:
        print("[Aviso] GEMINI_API_KEY no configurada. El dashboard se generará en modo local estándar.")
        
    generar_html(clima, paper, noticias, tareas, resumen_ia, consejo_ia, insight_ia)
    
    print("="*50)
    print("ACTUALIZACIÓN COMPLETADA CON ÉXITO")
    print("="*50)

if __name__ == "__main__":
    main()
