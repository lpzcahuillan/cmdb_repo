-- Script para crear la base de datos CMDB y las tablas necesarias
-- Ejecutar como superusuario de PostgreSQL

CREATE DATABASE cmdb_database;

\c cmdb_database;

-- Tabla principal para almacenar información de repositorios
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL UNIQUE,
    owner_name VARCHAR(255) NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    technologies TEXT[], -- Array de tecnologías identificadas
    is_identified BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, analyzed, error
    ai_explanation TEXT, -- Explicación de IA para repositorios no identificados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para mejorar el rendimiento de consultas
CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner_name);
CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(repo_name);
CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(status);
CREATE INDEX IF NOT EXISTS idx_repositories_identified ON repositories(is_identified);

-- Tabla para almacenar patrones de tecnologías
CREATE TABLE IF NOT EXISTS technology_patterns (
    id SERIAL PRIMARY KEY,
    technology_name VARCHAR(100) NOT NULL,
    file_pattern VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar patrones de tecnologías comunes
INSERT INTO technology_patterns (technology_name, file_pattern, description) VALUES
    ('Node.js', 'package.json', 'Proyecto de Node.js con gestión de dependencias npm'),
    ('Python', 'requirements.txt', 'Proyecto Python con dependencias pip'),
    ('Python', 'setup.py', 'Proyecto Python con configuración de instalación'),
    ('Python', 'pyproject.toml', 'Proyecto Python moderno con configuración PEP 518'),
    ('Java', 'pom.xml', 'Proyecto Java con Maven'),
    ('Java', 'build.gradle', 'Proyecto Java con Gradle'),
    ('Java', 'build.gradle.kts', 'Proyecto Java con Gradle Kotlin DSL'),
    ('PHP', 'composer.json', 'Proyecto PHP con Composer'),
    ('Ruby', 'Gemfile', 'Proyecto Ruby con Bundler'),
    ('Go', 'go.mod', 'Proyecto Go con módulos'),
    ('Rust', 'Cargo.toml', 'Proyecto Rust con Cargo'),
    ('C#', '*.csproj', 'Proyecto C# .NET'),
    ('C#', '*.sln', 'Solución de Visual Studio'),
    ('Flutter', 'pubspec.yaml', 'Proyecto Flutter/Dart'),
    ('React', 'package.json', 'Proyecto React (detectado por dependencias)'),
    ('Angular', 'angular.json', 'Proyecto Angular'),
    ('Vue.js', 'vue.config.js', 'Proyecto Vue.js'),
    ('Docker', 'Dockerfile', 'Proyecto con contenedores Docker'),
    ('Docker', 'docker-compose.yml', 'Proyecto con Docker Compose'),
    ('Kubernetes', '*.yaml', 'Configuración de Kubernetes')
ON CONFLICT DO NOTHING;

-- Tabla para almacenar consultas de IA y sus respuestas (cache)
CREATE TABLE IF NOT EXISTS ai_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'natural_language',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Función para actualizar timestamp de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar automáticamente updated_at
CREATE TRIGGER update_repositories_updated_at
    BEFORE UPDATE ON repositories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
