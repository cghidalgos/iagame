# Usa la imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY . .

#descomentar estas lineas si se esta en ambiente de producción y se hacen cambios en el repo -- SI.Se debe comemtar la linea 8
# Instala Git y dependencias necesarias
#RUN apt-get update && apt-get install -y git && apt-get clean

# Clona el repositorio directamente en el contenedor
#RUN git clone https://github.com/cghidalgos/TallerCartas.git /app

# Instala las dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Configura variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expone el puerto en el que se ejecutará la aplicación
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn (multi-workers para concurrencia)
# Ajusta los workers/threads con variables env si lo deseas: GUNICORN_WORKERS, GUNICORN_THREADS
ENV GUNICORN_WORKERS=3
ENV GUNICORN_THREADS=2
# Usamos la forma shell para permitir expansión de variables de entorno
CMD gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-3} --threads ${GUNICORN_THREADS:-2} --timeout 60 --access-logfile - app:app