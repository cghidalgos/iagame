# 🚀 Flask Astronaut Ranking App

Esta aplicación Flask simula un proceso de postulación espacial: los usuarios completan un formulario de habilidades, responden una trivia sobre astronautas, resuelven un laberinto interactivo y reciben un puntaje final ponderado. El ranking muestra el Top 10 de postulantes y gráficas comparativas.

## Características
- Formulario de habilidades (liderazgo, idiomas, creatividad, etc.)
- Trivia de astronautas (5 preguntas de opción múltiple)
- Laberinto interactivo (juego con medición de tiempo)
- Puntaje final ponderado: 50% formulario, 30% trivia, 20% laberinto
- Ranking Top 10 con detalles y gráficas (puntaje, trivia, laberinto, mejor habilidad)
- Gráficas dinámicas con Chart.js
- Diseño responsive con Bootstrap
- Fácil personalización de preguntas y lógica de puntaje

## Instalación
1. Clona el repositorio:
git clone https://github.com/tuusuario/flask-astronaut-ranking.git
cd flask-astronaut-ranking

text
2. Crea un entorno virtual y actívalo:
python -m venv venv
source venv/bin/activate # En Windows: venv\Scripts\activate

text
3. Instala las dependencias:
pip install flask pandas scikit-learn joblib

text
4. Asegúrate de tener los archivos del modelo (`modelo.pkl` y `escalador.pkl`) en la raíz del proyecto.
5. Ejecuta la aplicación:
python app.py

text
6. Abre tu navegador en [http://localhost:5004](http://localhost:5004)

## Estructura del Proyecto
flask-astronaut-ranking/
│
├── app.py
├── modelo.pkl
├── escalador.pkl
├── usuarios.json (opcional, si usas persistencia)
├── templates/
│ ├── index.html
│ ├── form.html
│ ├── trivia.html
│ ├── juego.html
│ ├── resultados.html
│ └── ranking.html
└── static/
└── (opcional: imágenes, css, js)

text

## Personalización
- Edita las preguntas de trivia en `app.py` (`trivia_preguntas`)
- Modifica la fórmula de puntaje en la ruta `/procesar`
- Ajusta colores y tipos de gráficas en los scripts Chart.js de los templates
- Puedes adaptar el guardado en JSON para persistencia de registros

## Créditos
by GHS 

