# 🤖 Flask IA Career Profiler App

Esta aplicación Flask simula un proceso de evaluación para identificar perfiles profesionales en Inteligencia Artificial. Los usuarios completan un formulario de habilidades, responden una trivia sobre la historia de la IA, resuelven un laberinto interactivo con un robot y capturan imágenes de Alan Turing, recibiendo un puntaje final ponderado y su perfil profesional recomendado.

## Características
- Formulario de habilidades en IA (programación, matemáticas, análisis de datos, etc.)
- Trivia sobre la historia de la Inteligencia Artificial (10 preguntas)
- Laberinto interactivo con robot buscando la salida
- Mini-juego "Alan Turing Challenge" - captura imágenes de Alan Turing
- Puntaje final ponderado: 25% trivia, 25% laberinto, 25% formulario, 25% Alan Turing
- 8 perfiles profesionales: Científico de datos, Ingeniero ML, Analista de datos, Ingeniero de datos, Analista de negocio, Arquitecto de datos, Estadístico, Administrador de BD
- Ranking Top usuarios con gráficas dinámicas
- Diseño responsive con Bootstrap
- Fácil personalización de preguntas y lógica de puntaje

## Perfiles identificados
1. **Científico de datos** - Experto en matemáticas, programación y creatividad
2. **Ingeniero de aprendizaje automático** - Especialista en programación, matemáticas y resolución de problemas
3. **Analista de datos** - Fuerte en análisis, comunicación y matemáticas
4. **Ingeniero de datos** - Programación, análisis y trabajo en equipo
5. **Analista de negocio** - Comunicación, análisis y trabajo en equipo
6. **Arquitecto de datos** - Resolución de problemas, programación y análisis
7. **Estadístico** - Matemáticas avanzadas y análisis
8. **Administrador de base de datos** - Programación, resolución de problemas y análisis

## Instalación
1. Clona el repositorio:
```bash
git clone https://github.com/cghidalgos/iagame.git
cd iagame
```

2. Crea un entorno virtual y actívalo:
```bash
python -m venv venv
source venv/bin/activate # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecuta la aplicación:
```bash
python app.py
```

5. Abre tu navegador en [http://localhost:5004](http://localhost:5004)

## Docker
```bash
docker-compose up --build
```
Acceder en: `http://localhost:5013`

## Estructura del Proyecto
```
iagame/
│
├── app.py
├── usuarios.json
├── requirements.txt
├── docker-compose.yml
├── dockerfile
├── templates/
│   ├── index.html
│   ├── form.html
│   ├── trivia.html
│   ├── juego.html (laberinto del robot)
│   ├── gravedad_cero.html (Alan Turing challenge)
│   ├── resultados.html
│   └── ranking.html
└── static/
    └── js/
        └── laberinto.js
```

## Personalización
- Edita las preguntas de trivia en `app.py` (`trivia_preguntas`)
- Modifica la fórmula de puntaje en la ruta `/procesar`
- Ajusta los pesos de los perfiles profesionales según necesites
- Cambia colores y gráficas en los templates

## Créditos
by GHS - Transformado a temática de Inteligencia Artificial 

