from flask import Flask, render_template, request, session, redirect
import csv
import pandas as pd
import joblib
from datetime import datetime, timezone
from collections import Counter
import json
import os
import tempfile
import fcntl
import time
import errno
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Carga del modelo (opcional). Si no existe, se calcula puntaje de habilidades con normalización simple
try:
    modelo = joblib.load('modelo.pkl')
    scaler = joblib.load('escalador.pkl')
except Exception:
    modelo = None
    scaler = None



##############################
# Persistencia segura en disco
##############################

USUARIOS_PATH = 'usuarios.json'
USUARIOS_LOCK_PATH = USUARIOS_PATH + '.lock'
CSV_PATH = 'datos.csv'
CSV_LOCK_PATH = CSV_PATH + '.lock'

def _ensure_usuarios_file() -> None:
    """Crea el archivo de usuarios si no existe."""
    if not os.path.exists(USUARIOS_PATH):
        # Garantiza que el directorio exista (por si cambia la ruta en el futuro)
        dir_name = os.path.dirname(USUARIOS_PATH)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(USUARIOS_PATH, 'w', encoding='utf-8') as f:
            f.write('[]')

def leer_usuarios() -> list:
    """Lee usuarios desde disco de forma robusta.
    Usa reemplazo atómico en escritura, por lo que aquí basta con leer y tolerar JSON corrupto transitorio.
    """
    _ensure_usuarios_file()
    try:
        with open(USUARIOS_PATH, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
        if contenido:
            return json.loads(contenido)
        return []
    except Exception:
        # Si por alguna razón el archivo está incompleto/transitorio, devolvemos lista vacía en vez de romper la vista
        return []

def agregar_usuario(entrada: dict) -> None:
    """Anexa un usuario al archivo con escritura atómica y lock exclusivo.
    - Bloquea el archivo mientras arma la nueva lista
    - Escribe a un archivo temporal y luego hace os.replace, que es atómico
    """
    _ensure_usuarios_file()
    # Usamos un lockfile separado para evitar EBUSY al reemplazar un archivo bind-mount abierto
    lock_fd = os.open(USUARIOS_LOCK_PATH, os.O_CREAT | os.O_RDWR)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        # Leer el contenido actual (fuera de un descriptor bloqueado del propio archivo)
        try:
            with open(USUARIOS_PATH, 'r', encoding='utf-8') as rf:
                contenido = rf.read().strip()
            datos = json.loads(contenido) if contenido else []
            if not isinstance(datos, list):
                datos = []
        except Exception:
            datos = []

        datos.append(entrada)

        # Escritura a temporal y replace con reintentos
        dir_ = os.path.dirname(USUARIOS_PATH) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix='usuarios_', suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                json.dump(datos, tf, ensure_ascii=False, indent=4)
                tf.flush()
                os.fsync(tf.fileno())

            # Intentar reemplazar varias veces para esquivar EBUSY en sistemas de archivos montados
            replaced = False
            for attempt in range(6):
                try:
                    os.replace(tmp_path, USUARIOS_PATH)
                    replaced = True
                    break
                except OSError as e:
                    if e.errno in (errno.EBUSY, errno.EPERM):
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            if not replaced:
                # Último recurso: escribir directamente (no atómico, pero bajo lock de escritura)
                with open(USUARIOS_PATH, 'w', encoding='utf-8') as wf:
                    json.dump(datos, wf, ensure_ascii=False, indent=4)
                    wf.flush()
                    os.fsync(wf.fileno())
        finally:
            # Limpieza del temporal si quedó
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def limpiar_usuarios() -> None:
    """Limpia el archivo de usuarios de forma segura (lista vacía).
    Usa el mismo mecanismo de lock y reemplazo atómico con reintentos.
    """
    _ensure_usuarios_file()
    lock_fd = os.open(USUARIOS_LOCK_PATH, os.O_CREAT | os.O_RDWR)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        dir_ = os.path.dirname(USUARIOS_PATH) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix='usuarios_', suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                tf.write('[]')
                tf.flush()
                os.fsync(tf.fileno())

            replaced = False
            for attempt in range(6):
                try:
                    os.replace(tmp_path, USUARIOS_PATH)
                    replaced = True
                    break
                except OSError as e:
                    if e.errno in (errno.EBUSY, errno.EPERM):
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            if not replaced:
                with open(USUARIOS_PATH, 'w', encoding='utf-8') as wf:
                    wf.write('[]')
                    wf.flush()
                    os.fsync(wf.fileno())
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def actualizar_usuarios(nueva_lista: list) -> None:
    """Sobrescribe el archivo de usuarios con la lista dada (atómico + lock)."""
    _ensure_usuarios_file()
    lock_fd = os.open(USUARIOS_LOCK_PATH, os.O_CREAT | os.O_RDWR)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        dir_ = os.path.dirname(USUARIOS_PATH) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix='usuarios_', suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                json.dump(nueva_lista, tf, ensure_ascii=False, indent=4)
                tf.flush()
                os.fsync(tf.fileno())
            replaced = False
            for attempt in range(6):
                try:
                    os.replace(tmp_path, USUARIOS_PATH)
                    replaced = True
                    break
                except OSError as e:
                    if e.errno in (errno.EBUSY, errno.EPERM):
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            if not replaced:
                with open(USUARIOS_PATH, 'w', encoding='utf-8') as wf:
                    json.dump(nueva_lista, wf, ensure_ascii=False, indent=4)
                    wf.flush()
                    os.fsync(wf.fileno())
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


##############################
# Utilidades CSV (datos.csv)
##############################

def _ensure_csv_header() -> None:
    """Crea datos.csv con encabezado si no existe."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            f.write('timestamp,nombre,correo,telefono\n')


def leer_interes_csv() -> list:
    """Lee datos.csv y devuelve lista de dicts (sin incluir encabezado)."""
    if not os.path.exists(CSV_PATH):
        return []
    filas = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filas.append({
                    'timestamp': row.get('timestamp', ''),
                    'nombre': row.get('nombre', ''),
                    'correo': row.get('correo', ''),
                    'telefono': row.get('telefono', ''),
                })
    except Exception:
        # Si hay problema de formato, devolvemos vacío para no romper la vista
        return []
    return filas


def escribir_interes_csv(filas: list) -> None:
    """Escribe las filas a datos.csv (manteniendo encabezado) de forma atómica con lock."""
    # Normalizar a lista de dicts con keys esperadas
    keys = ['timestamp', 'nombre', 'correo', 'telefono']
    filas_norm = []
    for r in filas:
        filas_norm.append({k: (r.get(k, '') if isinstance(r, dict) else '') for k in keys})

    # Lockfile para CSV
    lock_fd = os.open(CSV_LOCK_PATH, os.O_CREAT | os.O_RDWR)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        dir_ = os.path.dirname(CSV_PATH) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix='datos_', suffix='.csv.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as tf:
                writer = csv.DictWriter(tf, fieldnames=keys)
                writer.writeheader()
                for row in filas_norm:
                    writer.writerow(row)
                tf.flush()
                os.fsync(tf.fileno())
            replaced = False
            for attempt in range(6):
                try:
                    os.replace(tmp_path, CSV_PATH)
                    replaced = True
                    break
                except OSError as e:
                    if e.errno in (errno.EBUSY, errno.EPERM):
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            if not replaced:
                with open(CSV_PATH, 'w', encoding='utf-8', newline='') as wf:
                    writer = csv.DictWriter(wf, fieldnames=keys)
                    writer.writeheader()
                    for row in filas_norm:
                        writer.writerow(row)
                    wf.flush()
                    os.fsync(wf.fileno())
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

# Preguntas de trivia sobre la historia de la Inteligencia Artificial
trivia_preguntas = [
    {
        'id': 1,
        'pregunta': '¿Quién es considerado el padre de la Inteligencia Artificial?',
        'opciones': ['Alan Turing', 'John McCarthy', 'Marvin Minsky', 'Claude Shannon'],
        'respuesta': 'Alan Turing'
    },
    {
        'id': 2,
        'pregunta': '¿En qué año se acuñó el término "Inteligencia Artificial"?',
        'opciones': ['1950', '1956', '1960', '1965'],
        'respuesta': '1956'
    },
    {
        'id': 3,
        'pregunta': '¿Qué prueba propuso Alan Turing para determinar si una máquina puede pensar?',
        'opciones': ['Test de Binet', 'Test de Turing', 'Test de Minsky', 'Test de McCarthy'],
        'respuesta': 'Test de Turing'
    },
    {
        'id': 4,
        'pregunta': '¿Cuál fue el primer programa de ajedrez que venció al campeón mundial?',
        'opciones': ['AlphaGo', 'Deep Blue', 'Watson', 'Stockfish'],
        'respuesta': 'Deep Blue'
    },
    {
        'id': 5,
        'pregunta': '¿En qué conferencia se fundó oficialmente la IA como campo de estudio?',
        'opciones': ['Conferencia de Dartmouth', 'Conferencia de MIT', 'Conferencia de Stanford', 'Conferencia de Princeton'],
        'respuesta': 'Conferencia de Dartmouth'
    },
    {
        'id': 6,
        'pregunta': '¿Qué sistema de IA de Google venció al campeón mundial de Go en 2016?',
        'opciones': ['Deep Blue', 'Watson', 'AlphaGo', 'Stockfish'],
        'respuesta': 'AlphaGo'
    },
    {
        'id': 7,
        'pregunta': '¿Cuál es el nombre del asistente virtual de Amazon?',
        'opciones': ['Siri', 'Cortana', 'Alexa', 'Google Assistant'],
        'respuesta': 'Alexa'
    },
    {
        'id': 8,
        'pregunta': '¿Qué red neuronal revolucionó el procesamiento de imágenes en 2012?',
        'opciones': ['AlexNet', 'VGG', 'ResNet', 'GoogLeNet'],
        'respuesta': 'AlexNet'
    },
    {
        'id': 9,
        'pregunta': '¿Quién desarrolló el concepto de "perceptrón" en 1958?',
        'opciones': ['Alan Turing', 'Frank Rosenblatt', 'John McCarthy', 'Geoffrey Hinton'],
        'respuesta': 'Frank Rosenblatt'
    },
    {
        'id': 10,
        'pregunta': '¿Qué modelo de lenguaje desarrolló OpenAI que revolucionó el NLP en 2018?',
        'opciones': ['BERT', 'GPT', 'ELMo', 'Transformer'],
        'respuesta': 'GPT'
    }
]

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/healthz')
def healthz():
    return {'status': 'ok'}, 200

@app.route('/trivia', methods=['GET', 'POST'])
def trivia():
    if request.method == 'POST':
        respuestas_usuario = {str(p['id']): request.form.get(str(p['id'])) for p in trivia_preguntas}
        puntaje = sum(1 for p in trivia_preguntas if respuestas_usuario.get(str(p['id'])) == p['respuesta'])
        
        # Guardar detalles de respuestas para mostrar después
        detalles_trivia = []
        for p in trivia_preguntas:
            respuesta_usr = respuestas_usuario.get(str(p['id']))
            es_correcta = respuesta_usr == p['respuesta']
            detalles_trivia.append({
                'pregunta': p['pregunta'],
                'respuesta_usuario': respuesta_usr,
                'respuesta_correcta': p['respuesta'],
                'correcta': es_correcta
            })
        
        session['trivia_puntaje'] = puntaje
        session['trivia_total'] = len(trivia_preguntas)
        session['trivia_detalles'] = detalles_trivia
        session['trivia_inicio'] = datetime.now(timezone.utc)
        return redirect('/juego')
    return render_template('trivia.html', preguntas=trivia_preguntas)

@app.route('/juego', methods=['GET', 'POST'])
def juego():
    if request.method == 'POST':
        session['laberinto_tiempo'] = float(request.form['tiempo'])
        # Ir al juego de gravedad cero antes del formulario
        return redirect('/gravedad-cero')
    return render_template('juego.html')

@app.route('/formulario')
def formulario():
    if 'laberinto_tiempo' not in session:
        return redirect('/trivia')
    return render_template('form.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    nombre = request.form['nombre']
    entrada = {
        'edad': int(request.form['edad']),
        'promedio': float(request.form['promedio']),
        'programacion': int(request.form['programacion']),
        'matematicas': int(request.form['matematicas']),
        'analisis_datos': int(request.form['analisis_datos']),
        'ingles': int(request.form['ingles']),
        'resolucion_problemas': int(request.form['resolucion_problemas']),
        'trabajo_equipo': int(request.form['trabajo_equipo']),
        'comunicacion': int(request.form['comunicacion']),
        'creatividad': int(request.form['creatividad'])
    }

    # Probabilidad por ML (si hay modelo). No afecta el 33/33/33, se mantiene como dato informativo opcional
    probabilidad = None
    if scaler is not None and modelo is not None:
        try:
            entrada_df = pd.DataFrame([entrada])
            entrada_esc = scaler.transform(entrada_df)
            probabilidad = float(modelo.predict_proba(entrada_esc)[0][1])
        except Exception:
            probabilidad = None

    # Calcular puntajes combinados (33.3% cada componente)
    # 1) Trivia: correctas / total
    trivia_correctas = session.get('trivia_puntaje', 0)
    trivia_total = session.get('trivia_total', 5)
    trivia_total = trivia_total if trivia_total else 5
    trivia_score = (trivia_correctas / trivia_total) if trivia_total > 0 else 0.0

    # 2) Laberinto: eficiencia = 1 - tiempo/120 (cap entre 0 y 1)
    tiempo_laberinto = float(session.get('laberinto_tiempo', 0))
    laberinto_score = max(0.0, min(1.0, 1.0 - (tiempo_laberinto / 120.0)))

    # 2.5) Gravedad cero: normalización según dificultad
    gravedad_score_raw = int(session.get('gravedad_score', 0))
    gravedad_combo = int(session.get('gravedad_combo', 0))
    gravedad_dificultad = session.get('gravedad_dificultad', 'medium')
    caps = {'easy': 200.0, 'medium': 300.0, 'hard': 400.0}
    cap = caps.get(gravedad_dificultad, 300.0)
    gravedad_score = max(0.0, min(1.0, gravedad_score_raw / cap))

    # 3) Habilidades del formulario: normalización simple de campos clave
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    norm_promedio = clamp01(entrada['promedio'] / 5.0)
    norm_programacion = clamp01(entrada['programacion'] / 10.0)
    norm_matematicas = clamp01(entrada['matematicas'] / 10.0)
    norm_analisis = clamp01(entrada['analisis_datos'] / 10.0)
    norm_ingles = clamp01(entrada['ingles'] / 10.0)
    norm_resolucion = clamp01(entrada['resolucion_problemas'] / 10.0)
    norm_equipo = clamp01(entrada['trabajo_equipo'] / 10.0)
    norm_comunicacion = clamp01(entrada['comunicacion'] / 10.0)
    norm_creatividad = clamp01(entrada['creatividad'] / 10.0)

    skills_norm_list = [
        norm_promedio, norm_programacion, norm_matematicas, norm_analisis,
        norm_ingles, norm_resolucion, norm_equipo, norm_comunicacion, norm_creatividad
    ]
    habilidades_score = sum(skills_norm_list) / len(skills_norm_list)

    # Puntaje final (0..1) con 4 componentes (25% cada uno)
    entrada['puntaje_final'] = (trivia_score + laberinto_score + habilidades_score + gravedad_score) / 4.0
    entrada['nombre'] = nombre
    if probabilidad is not None:
        entrada['probabilidad'] = probabilidad
    entrada.update({
        'trivia_puntaje': trivia_correctas,
        'trivia_total': trivia_total,
        'laberinto_tiempo': tiempo_laberinto,
        'habilidades_score': habilidades_score,
        'gravedad_puntos': gravedad_score_raw,
        'gravedad_combo': gravedad_combo,
        'gravedad_dificultad': gravedad_dificultad,
        'gravedad_score': gravedad_score
    })

    habilidades = {
        'programacion': entrada['programacion'],
        'matematicas': entrada['matematicas'],
        'analisis_datos': entrada['analisis_datos'],
        'ingles': entrada['ingles'],
        'resolucion_problemas': entrada['resolucion_problemas'],
        'trabajo_equipo': entrada['trabajo_equipo'],
        'comunicacion': entrada['comunicacion'],
        'creatividad': entrada['creatividad']
    }

    def evaluar(valor, clave=None):
        if valor >= 8:
            return "🟢 Alto - excelente"
        elif valor >= 5:
            return "🟡 Medio - aceptable, pero mejorable"
        else:
            return "🔴 Bajo - necesita mejorar"

    evaluaciones = {k: (v, evaluar(v, k)) for k, v in habilidades.items()}

    def valor_para_comparar(x):
        return x[1] if x[1] > 1 else (10 if x[1] == 1 else 0)

    mejor_habilidad = max(habilidades.items(), key=valor_para_comparar)[0].replace('_', ' ').capitalize()

    # Clasificación de perfiles profesionales en IA
    # Calculamos scores ponderados para cada perfil
    score_cientifico_datos = (
        norm_matematicas * 0.3 +
        norm_programacion * 0.25 +
        norm_analisis * 0.25 +
        norm_creatividad * 0.2
    )
    
    score_ingeniero_ml = (
        norm_programacion * 0.35 +
        norm_matematicas * 0.25 +
        norm_resolucion * 0.25 +
        norm_analisis * 0.15
    )
    
    score_analista_datos = (
        norm_analisis * 0.35 +
        norm_comunicacion * 0.25 +
        norm_matematicas * 0.2 +
        norm_promedio * 0.2
    )
    
    score_ingeniero_datos = (
        norm_programacion * 0.3 +
        norm_analisis * 0.25 +
        norm_resolucion * 0.25 +
        norm_equipo * 0.2
    )
    
    score_analista_negocio = (
        norm_comunicacion * 0.35 +
        norm_analisis * 0.25 +
        norm_equipo * 0.2 +
        norm_creatividad * 0.2
    )
    
    score_arquitecto_datos = (
        norm_resolucion * 0.3 +
        norm_programacion * 0.25 +
        norm_analisis * 0.25 +
        norm_promedio * 0.2
    )
    
    score_estadistico = (
        norm_matematicas * 0.4 +
        norm_analisis * 0.3 +
        norm_promedio * 0.2 +
        norm_resolucion * 0.1
    )
    
    score_admin_bd = (
        norm_programacion * 0.3 +
        norm_resolucion * 0.3 +
        norm_analisis * 0.2 +
        norm_equipo * 0.2
    )

    # Encontrar el perfil con mayor score
    perfiles_scores = {
        'Científico de datos': score_cientifico_datos,
        'Ingeniero de aprendizaje automático': score_ingeniero_ml,
        'Analista de datos': score_analista_datos,
        'Ingeniero de datos': score_ingeniero_datos,
        'Analista de negocio': score_analista_negocio,
        'Arquitecto de datos': score_arquitecto_datos,
        'Estadístico': score_estadistico,
        'Administrador de base de datos': score_admin_bd
    }

    # Asignar el perfil con mayor score (siempre habrá uno)
    tipo_ingeniero = max(perfiles_scores.items(), key=lambda x: x[1])[0]

    entrada['tipo_ingeniero'] = tipo_ingeniero

    # Áreas de mejora sugeridas
    mejoras = []
    if norm_programacion < 0.7:
        mejoras.append({'area': 'Programación', 'detalle': 'Practica con Python, R o lenguajes orientados a datos y ML.'})
    if norm_matematicas < 0.7:
        mejoras.append({'area': 'Matemáticas y estadística', 'detalle': 'Refuerza álgebra lineal, cálculo y estadística para IA.'})
    if norm_analisis < 0.7:
        mejoras.append({'area': 'Análisis de datos', 'detalle': 'Aprende técnicas de exploración, visualización y limpieza de datos.'})
    if norm_comunicacion < 0.7:
        mejoras.append({'area': 'Comunicación', 'detalle': 'Mejora tu capacidad de presentar insights y trabajar con stakeholders.'})
    if norm_ingles < 0.7:
        mejoras.append({'area': 'Inglés técnico', 'detalle': 'Domina el inglés para documentación, papers y herramientas de IA.'})
    entrada['mejoras'] = mejoras

    # Porcentajes para UI
    porcentajes = {
        'trivia': trivia_score * 100.0,
        'laberinto': laberinto_score * 100.0,
        'habilidades': habilidades_score * 100.0,
        'gravedad': gravedad_score * 100.0
    }
    entrada['porcentajes'] = porcentajes

    entrada['evaluaciones'] = evaluaciones
    entrada['mejor_habilidad'] = mejor_habilidad
    
    # Guardar detalles de trivia
    trivia_detalles = session.get('trivia_detalles', [])
    entrada['trivia_detalles'] = trivia_detalles

    # Persistir de manera segura (atómica) para evitar corrupción con múltiples usuarios concurrentes
    agregar_usuario(entrada)

    return render_template(
        'resultados.html',
        datos=entrada,
        probabilidad=probabilidad,
        evaluaciones=evaluaciones,
        mejor_habilidad=mejor_habilidad,
        porcentajes=porcentajes,
        trivia_detalles=trivia_detalles
    )

@app.route('/gravedad-cero')
def gravedad_cero():
    return render_template('gravedad_cero.html')

@app.route('/gravedad-cero/fin', methods=['POST'])
def gravedad_cero_fin():
    # Guardar resultados del mini-juego en sesión y continuar al formulario
    try:
        session['gravedad_score'] = int(request.form.get('score', 0))
        session['gravedad_combo'] = int(request.form.get('combo', 0))
        session['gravedad_dificultad'] = request.form.get('dificultad', 'medium')
    except Exception:
        session['gravedad_score'] = 0
        session['gravedad_combo'] = 0
        session['gravedad_dificultad'] = 'medium'
    return redirect('/formulario')

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    """Resetea todos los usuarios si la clave es correcta."""
    clave = request.form.get('clave', '')
    if clave != 'holamundo123':
        # 403 si la clave es incorrecta (respuesta simple para evitar dependencias de plantilla)
        return ("Clave incorrecta. No se realizó el reinicio.", 403, {"Content-Type": "text/plain; charset=utf-8"})
    limpiar_usuarios()
    # Limpiar sesión actual también
    session.clear()
    return redirect('/')

@app.route('/ranking')
def ranking():
    # Leer usuarios desde disco (robusto ante concurrencia)
    usuarios_actual = leer_usuarios()

    # Adjuntar un UID estable basado en el índice actual para poder enlazar a detalle
    for idx, u in enumerate(usuarios_actual):
        if isinstance(u, dict):
            u.setdefault('uid', idx)

    top_usuarios = sorted(
        usuarios_actual,
        key=lambda x: x.get('puntaje_final', 0),
        reverse=True
    )

    # Asegurar campos para compatibilidad
    for u in top_usuarios:
        u.setdefault('puntaje_final', 0)
        u.setdefault('trivia_puntaje', 0)
        u.setdefault('trivia_total', 10)
        u.setdefault('laberinto_tiempo', 0)
        u.setdefault('mejor_habilidad', 'No disponible')
        u.setdefault('evaluaciones', {})
        u.setdefault('tipo_ingeniero', 'No definido')
        u.setdefault('edad', 0)

    promedio = sum(u.get('puntaje_final', 0) for u in top_usuarios) / len(top_usuarios) if top_usuarios else 0
    mejor = max(u.get('puntaje_final', 0) for u in top_usuarios) if top_usuarios else 0
    peor = min(u.get('puntaje_final', 0) for u in top_usuarios) if top_usuarios else 0

    mejores_habilidades = [u.get('mejor_habilidad', 'No disponible') for u in top_usuarios]
    conteo_habilidades = Counter(mejores_habilidades)
    labels_habilidades = list(conteo_habilidades.keys())
    valores_habilidades = list(conteo_habilidades.values())

    # Estadísticas adicionales para dashboard (Funcionalidad #5)
    perfiles = [u.get('tipo_ingeniero', 'No definido') for u in top_usuarios]
    conteo_perfiles = Counter(perfiles)
    
    # Promedio de habilidades para comparativa de radar
    if top_usuarios:
        habilidades_keys = ['programacion', 'matematicas', 'analisis_datos', 'resolucion_problemas', 
                           'comunicacion', 'creatividad', 'trabajo_equipo', 'ingles']
        promedios_habilidades = {}
        for key in habilidades_keys:
            valores = [u.get(key, 0) for u in top_usuarios if key in u]
            promedios_habilidades[key] = sum(valores) / len(valores) if valores else 0
    else:
        promedios_habilidades = {}
    
    # Estadísticas de trivia
    total_preguntas = len(trivia_preguntas)
    aciertos_por_pregunta = {i: 0 for i in range(1, total_preguntas + 1)}
    for u in top_usuarios:
        # Aquí no tenemos respuestas individuales guardadas, solo el total
        pass
    
    # Distribución por edades
    edades = [u.get('edad', 0) for u in top_usuarios if u.get('edad', 0) > 0]
    promedio_edad = sum(edades) / len(edades) if edades else 0
    
    # Tiempo promedio laberinto
    tiempos = [u.get('laberinto_tiempo', 0) for u in top_usuarios]
    promedio_laberinto = sum(tiempos) / len(tiempos) if tiempos else 0

    # Solo los 10 primeros para gráficos de podio/tablas extensas
    usuarios_top10 = top_usuarios[:10]

    return render_template(
        'ranking.html',
        usuarios=usuarios_top10,
        usuarios_top=top_usuarios,
        promedio=promedio,
        mejor=mejor,
        peor=peor,
        labels_habilidades=labels_habilidades,
        valores_habilidades=valores_habilidades,
        conteo_perfiles=conteo_perfiles,
        promedios_habilidades=promedios_habilidades,
        promedio_edad=promedio_edad,
        promedio_laberinto=promedio_laberinto,
        total_usuarios=len(top_usuarios)
    )


@app.route('/usuario/<int:uid>')
def usuario_detalle(uid: int):
    """Vista de detalle que reusa resultados.html para un usuario persistido.
    Permite volver a ver la información detallada desde el ranking.
    """
    usuarios = leer_usuarios()
    if 0 <= uid < len(usuarios) and isinstance(usuarios[uid], dict):
        datos = usuarios[uid]
        # Asegurar campos mínimos esperados por la plantilla
        evaluaciones = datos.get('evaluaciones', {})
        mejor_habilidad = datos.get('mejor_habilidad', 'No disponible')
        porcentajes = datos.get('porcentajes', {
            'trivia': (datos.get('trivia_puntaje', 0) / max(datos.get('trivia_total', 10), 1)) * 100.0,
            'laberinto': max(0.0, min(1.0, 1.0 - (float(datos.get('laberinto_tiempo', 0)) / 120.0))) * 100.0,
            'habilidades': float(datos.get('habilidades_score', 0.0)) * 100.0,
            'gravedad': float(datos.get('gravedad_score', 0.0)) * 100.0
        })
        trivia_detalles = datos.get('trivia_detalles', [])
        return render_template('resultados.html', datos=datos, evaluaciones=evaluaciones, mejor_habilidad=mejor_habilidad, porcentajes=porcentajes, probabilidad=datos.get('probabilidad'), trivia_detalles=trivia_detalles)
    # Si no se encuentra, redirigir al ranking
    return redirect('/ranking')

@app.post('/interes-material')
def interes_material():
    data = request.get_json(silent=True) or request.form
    nombre = (data.get('nombre') or '').strip()
    correo = (data.get('correo') or '').strip()
    telefono = (data.get('telefono') or '').strip()
    if not nombre or not correo or not telefono:
        return jsonify({ 'ok': False, 'error': 'Faltan campos requeridos' }), 400
    # Validación simple de correo
    import re
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", correo):
        return jsonify({ 'ok': False, 'error': 'Correo inválido' }), 400

    # Guardar en archivo CSV datos.csv (UTF-8)
    try:
        ruta = 'datos.csv'
        header_needed = not os.path.exists(ruta)
        # Escapar comillas dobles
        def esc(x: str) -> str:
            return '"' + x.replace('"', '""') + '"'
        with open(ruta, 'a', encoding='utf-8') as f:
            if header_needed:
                f.write('timestamp,nombre,correo,telefono\n')
            timestamp = datetime.now().isoformat()
            fila = f"{esc(timestamp)},{esc(nombre)},{esc(correo)},{esc(telefono)}\n"
            f.write(fila)
        return jsonify({ 'ok': True })
    except Exception:
        return jsonify({ 'ok': False, 'error': 'No se pudo guardar el interés' }), 500


##############################
# Vistas y endpoints de ADMIN
##############################

def _admin_autorizado() -> bool:
    """Protección opcional. Si existe ADMIN_KEY en entorno, exigir cabecera X-Admin-Key o parámetro/campo 'k'."""
    admin_key = os.environ.get('ADMIN_KEY')
    if not admin_key:
        return True
    provided = request.headers.get('X-Admin-Key') or request.args.get('k') or request.form.get('k')
    return provided == admin_key


@app.route('/admin', methods=['GET'])
def admin_view():
    if not _admin_autorizado():
        return ("No autorizado", 401)

    usuarios = leer_usuarios()
    for idx, u in enumerate(usuarios):
        if isinstance(u, dict):
            u.setdefault('uid', idx)
            u.setdefault('nombre', 'Sin nombre')
            u.setdefault('puntaje_final', 0)
            u.setdefault('trivia_puntaje', 0)
            u.setdefault('trivia_total', 10)
            u.setdefault('laberinto_tiempo', 0)

    interes = leer_interes_csv()
    # Indexar filas para poder borrar por índice
    for i, r in enumerate(interes):
        r['idx'] = i

    # Pasar querystring de clave si aplica para que los formularios lo conserven
    admin_key = os.environ.get('ADMIN_KEY')
    k = request.args.get('k', '')
    admin_qs = f"?k={k}" if admin_key and k else ''
    return render_template('admin.html', usuarios=usuarios, interes=interes, admin_qs=admin_qs, k_value=k)


@app.post('/admin/delete-user/<int:uid>')
def admin_delete_user(uid: int):
    if not _admin_autorizado():
        return ("No autorizado", 401)
    usuarios = leer_usuarios()
    if 0 <= uid < len(usuarios):
        usuarios.pop(uid)
        actualizar_usuarios(usuarios)
        k = request.args.get('k') or request.form.get('k') or ''
        return redirect(f"/admin?k={k}" if k else '/admin')
    return ("Usuario no encontrado", 404)


@app.post('/admin/delete-users')
def admin_delete_all_users():
    if not _admin_autorizado():
        return ("No autorizado", 401)
    limpiar_usuarios()
    k = request.args.get('k') or request.form.get('k') or ''
    return redirect(f"/admin?k={k}" if k else '/admin')


@app.post('/admin/delete-csv/<int:idx>')
def admin_delete_csv_row(idx: int):
    if not _admin_autorizado():
        return ("No autorizado", 401)
    filas = leer_interes_csv()
    if 0 <= idx < len(filas):
        filas.pop(idx)
        escribir_interes_csv(filas)
        k = request.args.get('k') or request.form.get('k') or ''
        return redirect(f"/admin?k={k}" if k else '/admin')
    return ("Fila no encontrada", 404)


@app.post('/admin/delete-csv')
def admin_delete_csv_all():
    if not _admin_autorizado():
        return ("No autorizado", 401)
    escribir_interes_csv([])
    k = request.args.get('k') or request.form.get('k') or ''
    return redirect(f"/admin?k={k}" if k else '/admin')

if __name__ == '__main__':
    # Solo para desarrollo local. En contenedor se usa Gunicorn (ver Dockerfile)
    app.run(debug=False, host='0.0.0.0', port=5004)
