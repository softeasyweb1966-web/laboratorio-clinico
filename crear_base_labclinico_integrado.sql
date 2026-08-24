-- Crea una base nueva y exclusiva para este proyecto.
-- Ejecutar conectado a PostgreSQL como superusuario o un usuario con permiso para crear bases.

SELECT 'CREATE DATABASE labclinico_integrado WITH OWNER postgres ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'labclinico_integrado'
)\gexec
