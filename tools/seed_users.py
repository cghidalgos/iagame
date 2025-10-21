import json
import random
import os
from statistics import mean

# This script generates 30 simulated IA-game users consistent with the app schema
# It preserves any existing users and appends new ones.

N = 30

# Reasonable ranges & distributions
EDAD_RANGE = (14, 30)
PROMEDIO_RANGE = (2.5, 5.0)  # 1-5 scale with decimals
HAB_RANGE = (1, 10)         # integer 1..10 for skills

# Typical gravity scores (points) and mapping to dificultad & normalized score similar to app
# We'll loosely simulate: hard yields higher points on average
DIFICULTADES = ["easy", "medium", "hard"]

IA_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Casey", "Drew", "Riley", "Morgan",
    "Robin", "Cruz", "Kai", "Ari", "Noa", "Ren", "Quin", "Sky", "Sasha",
    "Nico", "Reese", "Jules", "Mika", "Zion", "Avery", "Rowan", "Emery",
    "Parker", "Ellis", "Hayden", "Jamie", "Cameron", "Adrian", "Logan",
]
LAST_NAMES = [
    "García", "Rodríguez", "Martínez", "Hernández", "López", "González",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Vargas", "Castro", "Morales", "Ortega", "Rojas", "Navarro"
]

PERFILES = [
    "Científico de datos", "Ingeniero de aprendizaje automático", "Analista de datos",
    "Ingeniero de datos", "Analista de negocio", "Arquitecto de datos",
    "Estadístico", "Administrador de base de datos"
]

MEJORAS_BASE = [
    {"area": "Programación", "detalle": "Practica con Python, R o lenguajes orientados a datos y ML."},
    {"area": "Matemáticas y estadística", "detalle": "Refuerza álgebra lineal, cálculo y estadística para IA."},
    {"area": "Análisis de datos", "detalle": "Aprende técnicas de exploración, visualización y limpieza de datos."},
    {"area": "Comunicación", "detalle": "Mejora tu capacidad de presentar insights y trabajar con stakeholders."},
    {"area": "Inglés técnico", "detalle": "Domina el inglés para documentación, papers y herramientas de IA."},
]

# Derived helpers that approximate app logic

def laberinto_score_to_percentage(t):
    # app seems to use 100% around ~10s and falls off; we'll clamp 0..100
    # We'll map 10s -> 100, 60s -> 0 linearly
    perc = 100 * max(0.0, min(1.0, (60.0 - (t - 10.0)) / 60.0))
    return round(perc, 2)


def gravedad_points_for(dificultad):
    if dificultad == "easy":
        base = random.randint(80, 200)
    elif dificultad == "medium":
        base = random.randint(150, 320)
    else:  # hard
        base = random.randint(250, 500)
    return base


def gravedad_points_to_score(points, dificultad):
    # Rough normalization similar to app ranges used earlier (observed examples ~376->0.94, 416->1.0)
    # We'll scale by dificultad cap
    cap = {"easy": 250, "medium": 350, "hard": 420}.get(dificultad, 350)
    score = min(1.0, max(0.0, points / cap))
    return round(score, 2)


def habilidades_score_from(skills):
    vals = [
        skills["programacion"], skills["matematicas"], skills["analisis_datos"], skills["ingles"],
        skills["resolucion_problemas"], skills["trabajo_equipo"], skills["comunicacion"], skills["creatividad"]
    ]
    return round(mean(vals) / 10.0, 4)


def porcentajes(trivia_pct, laberinto_pct, hab_score, gravedad_pct):
    return {
        "trivia": round(trivia_pct, 2),
        "laberinto": round(laberinto_pct, 2),
        "habilidades": round(hab_score * 100, 2),
        "gravedad": round(gravedad_pct, 2),
    }


def pick_profile(skills):
    # Approximate the weights: programacion/matematicas/analisis are key
    weights = {
        "Científico de datos": 0.2 * skills["programacion"] + 0.25 * skills["matematicas"] + 0.25 * skills["analisis_datos"] + 0.15 * skills["resolucion_problemas"] + 0.15 * skills["comunicacion"],
        "Ingeniero de aprendizaje automático": 0.3 * skills["programacion"] + 0.25 * skills["matematicas"] + 0.2 * skills["analisis_datos"] + 0.15 * skills["resolucion_problemas"] + 0.1 * skills["ingles"],
        "Analista de datos": 0.15 * skills["programacion"] + 0.2 * skills["matematicas"] + 0.3 * skills["analisis_datos"] + 0.15 * skills["comunicacion"] + 0.2 * skills["ingles"],
        "Ingeniero de datos": 0.3 * skills["programacion"] + 0.2 * skills["matematicas"] + 0.15 * skills["analisis_datos"] + 0.2 * skills["resolucion_problemas"] + 0.15 * skills["trabajo_equipo"],
        "Analista de negocio": 0.1 * skills["programacion"] + 0.15 * skills["matematicas"] + 0.25 * skills["analisis_datos"] + 0.25 * skills["comunicacion"] + 0.25 * skills["trabajo_equipo"],
        "Arquitecto de datos": 0.2 * skills["programacion"] + 0.2 * skills["matematicas"] + 0.2 * skills["analisis_datos"] + 0.2 * skills["resolucion_problemas"] + 0.2 * skills["trabajo_equipo"],
        "Estadístico": 0.1 * skills["programacion"] + 0.4 * skills["matematicas"] + 0.2 * skills["analisis_datos"] + 0.15 * skills["comunicacion"] + 0.15 * skills["ingles"],
        "Administrador de base de datos": 0.25 * skills["programacion"] + 0.15 * skills["matematicas"] + 0.15 * skills["analisis_datos"] + 0.2 * skills["resolucion_problemas"] + 0.25 * skills["trabajo_equipo"],
    }
    return max(weights.items(), key=lambda kv: kv[1])[0]


def mejor_habilidad(skills):
    key = max(skills, key=lambda k: skills[k])
    return key.capitalize().replace('_', '')


def evaluaciones(skills):
    eva = {}
    for k, v in skills.items():
        if v >= 8:
            desc = "🟢 Alto - excelente"
        elif v >= 5:
            desc = "🟡 Medio - aceptable, pero mejorable"
        else:
            desc = "🔴 Bajo - necesita mejorar"
        eva[k] = [v, desc]
    return eva


def simulate_user():
    edad = random.randint(*EDAD_RANGE)
    promedio = round(random.uniform(*PROMEDIO_RANGE), 1)

    skills = {
        "programacion": random.randint(*HAB_RANGE),
        "matematicas": random.randint(*HAB_RANGE),
        "analisis_datos": random.randint(*HAB_RANGE),
        "ingles": random.randint(*HAB_RANGE),
        "resolucion_problemas": random.randint(*HAB_RANGE),
        "trabajo_equipo": random.randint(*HAB_RANGE),
        "comunicacion": random.randint(*HAB_RANGE),
        "creatividad": random.randint(*HAB_RANGE),
    }

    # Trivia: simulate 6-10 correct out of 10 with slight bias toward mid-high
    trivia_total = 10
    trivia_puntaje = random.randint(4, 10)

    # Laberinto time: simulate 9s to 70s
    laberinto_tiempo = round(random.uniform(9.0, 70.0), 1)
    laberinto_pct = laberinto_score_to_percentage(laberinto_tiempo)

    dificultad = random.choices(DIFICULTADES, weights=[0.25, 0.4, 0.35], k=1)[0]
    gravedad_puntos = gravedad_points_for(dificultad)
    gravedad_score = gravedad_points_to_score(gravedad_puntos, dificultad)
    gravedad_pct = round(gravedad_score * 100, 2)

    hab_score = habilidades_score_from(skills)

    # Final score: equal weights similar to app: trivia, laberinto, habilidades, gravedad
    trivia_pct = (trivia_puntaje / trivia_total) * 100
    puntaje_final = round(((trivia_pct + laberinto_pct + (hab_score * 100) + gravedad_pct) / 4) / 100, 6)

    perfil = pick_profile(skills)

    record = {
        "edad": edad,
        "promedio": promedio,
        **skills,
        "puntaje_final": puntaje_final,
        "nombre": f"{random.choice(IA_NAMES)} {random.choice(LAST_NAMES)}",
        "trivia_puntaje": trivia_puntaje,
        "trivia_total": trivia_total,
        "laberinto_tiempo": laberinto_tiempo,
        "habilidades_score": hab_score,
        "gravedad_puntos": gravedad_puntos,
        "gravedad_combo": 0,
        "gravedad_dificultad": dificultad,
        "gravedad_score": gravedad_score,
        "tipo_ingeniero": perfil,
        "mejoras": random.sample(MEJORAS_BASE, k=random.randint(2, 5)),
        "porcentajes": porcentajes(trivia_pct, laberinto_pct, hab_score, gravedad_pct),
        "evaluaciones": evaluaciones(skills),
        "mejor_habilidad": mejor_habilidad(skills),
    }
    return record


def main():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usuarios.json"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except FileNotFoundError:
        data = []

    initial_len = len(data)

    for _ in range(N):
        data.append(simulate_user())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Seeded {N} users. Total now: {len(data)} (was {initial_len}). File: {path}")


if __name__ == "__main__":
    random.seed()
    main()
