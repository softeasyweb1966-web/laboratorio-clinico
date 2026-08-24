# LabClinico Integrado

Proyecto unificado creado a partir de:

- `laboratorio/` como base operativa principal
- `resultados/` como modulo de resultados integrado

## Estructura actual

- `app/`: aplicacion principal integrada
- `laboratorio/`: referencia historica, no debe usarse como proyecto activo
- `resultados/`: referencia historica, no debe usarse como proyecto activo
- `inicializar_bd.py`: crea tablas y carga datos iniciales
- `run.py`: arranque de Flask

## Base de datos oficial

Este proyecto trabajara solo con PostgreSQL.

La aplicacion exige la variable:

- `LABCLINICO_DATABASE_URL`

Ejemplo:

`postgresql+psycopg2://postgres:CAMBIA_ESTA_CLAVE@127.0.0.1:5432/labclinico_integrado`

No hay fallback a SQLite.
Si la variable no existe o no apunta a PostgreSQL, la app falla de inmediato para evitar usar una base equivocada.

## Configuracion recomendada

1. Crear una base PostgreSQL nueva solo para este proyecto.
2. Crear un entorno virtual nuevo en esta carpeta raiz.
3. Instalar `requirements.txt`.
4. Crear `.env` a partir de `.env.example`.
5. Ejecutar `python inicializar_bd.py`.
6. Ejecutar `python run.py`.

## Limpieza final

Las carpetas `laboratorio/` y `resultados/` siguen sirviendo como respaldo de consulta.
Ya no son necesarias para ejecutar el proyecto nuevo, pero es mejor borrarlas solo despues de validar que el sistema arranca contra la nueva base PostgreSQL dedicada.
