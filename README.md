# 🤖 CMDB Tool - Configuration Management Database con IA

Una herramienta avanzada para escanear y analizar repositorios Git con capacidades de inteligencia artificial para identificación de tecnologías y consultas en lenguaje natural.

## 🚀 Características Principales

### ✨ Funcionalidades Core
- **Escaneo de Repositorios**: Soporte para GitHub, GitLab, y repositorios locales
- **Identificación Automática**: Detecta tecnologías basándose en archivos clave
- **Base de Datos PostgreSQL**: Almacenamiento persistente y eficiente
- **Análisis con IA**: Explicaciones detalladas para repositorios no identificados
- **Consultas en Lenguaje Natural**: Pregunta en español sobre tus repositorios

### 🔍 Tecnologías Soportadas
- **Frontend**: React, Angular, Vue.js
- **Backend**: Node.js, Python, Java, PHP, Ruby, Go, Rust, C#
- **Mobile**: Flutter/Dart, Android, iOS
- **DevOps**: Docker, Kubernetes, Terraform
- **Y muchas más...**

## 📁 Estructura del Proyecto

```
cmdb_repo/
├── main.py                 # Script principal
├── requirements.txt        # Dependencias Python
├── .env.example           # Configuración de ejemplo
├── database_module/
│   └── db_setup.sql       # Scripts de base de datos
├── scanner_module/
│   ├── __init__.py
│   ├── scanner.py         # Motor de escaneo
│   └── db_connector.py    # Conector PostgreSQL
├── validator_module/
│   ├── __init__.py
│   └── validator.py       # Validación con IA
└── query_module/
    ├── __init__.py
    └── query_engine.py    # Consultas en lenguaje natural
```

## 🛠️ Instalación y Configuración

### 1. Requisitos Previos
- Python 3.8+
- PostgreSQL 12+
- Git instalado
- Clave API de OpenAI (opcional, para funcionalidades de IA)

### 2. Instalación
```bash
# Clonar el repositorio
git clone <tu-repo-url>
cd cmdb_repo

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones
```

### 3. Configuración de PostgreSQL
```sql
-- Crear base de datos
CREATE DATABASE cmdb_database;

-- Ejecutar el script de configuración
\i database_module/db_setup.sql
```

### 4. Configurar Variables de Entorno
Edita el archivo `.env`:
```env
DB_HOST=localhost
DB_NAME=cmdb_database
DB_USER=postgres
DB_PASSWORD=tu_password
DB_PORT=5432
OPENAI_API_KEY=tu_api_key_openai  # Opcional
```

## 🎯 Uso de la Herramienta

### Configuración Inicial
```bash
# Configurar base de datos
python main.py --setup-db
```

### Escaneo de Repositorios
```bash
# Escanear un repositorio individual
python main.py --scan https://github.com/facebook/react

# Escanear múltiples repositorios desde archivo
echo "https://github.com/microsoft/vscode" > repos.txt
echo "https://github.com/tensorflow/tensorflow" >> repos.txt
python main.py --scan-batch repos.txt
```

### Consultas en Lenguaje Natural
```bash
# Consulta directa
python main.py --query "¿Qué repositorios tiene Microsoft?"

# Modo interactivo
python main.py --interactive
```

### Análisis y Reportes
```bash
# Resumen de repositorio
python main.py --summary https://github.com/facebook/react

# Estadísticas del sistema
python main.py --stats

# Exportar datos
python main.py --export json
python main.py --export csv
```

## 💬 Ejemplos de Consultas

### Consultas Básicas
- "¿Cuántos repositorios hay en total?"
- "¿Qué repositorios tiene el usuario 'microsoft'?"
- "¿Quién es el propietario del repositorio 'react'?"

### Consultas por Tecnología
- "¿Qué repositorios usan Python?"
- "Proyectos que usan Docker"
- "¿Cuántos repositorios tienen JavaScript?"

### Análisis Avanzado
- "Muéstrame los repositorios no identificados"
- "¿Cuáles son los últimos repositorios analizados?"
- "Repositorios de Google que usan Go"

## 🤖 Capacidades de IA

### Para Repositorios No Identificados
La herramienta proporciona:
- **Análisis detallado** de por qué no se identificó
- **Sugerencias específicas** basadas en archivos encontrados
- **Recomendaciones** para mejorar la detectabilidad
- **Identificación de patrones** no estándar

### Ejemplo de Explicación de IA:
```
ANÁLISIS DEL REPOSITORIO NO IDENTIFICADO:

Repositorio: https://github.com/usuario/proyecto-custom
Archivos encontrados: 45
Extensiones detectadas: py, yaml, md

POSIBLES RAZONES:
1. Proyecto Python sin requirements.txt
2. Configuración en ubicaciones no estándar
3. Proyecto experimental o de datos

RECOMENDACIONES:
- Considere añadir requirements.txt
- Verificar si hay archivos de configuración en subdirectorios
- El proyecto podría beneficiarse de una estructura más estándar
```

## 📊 Base de Datos

### Tabla Principal: `repositories`
- `url`: URL del repositorio
- `owner_name`: Propietario del repositorio
- `repo_name`: Nombre del repositorio
- `technologies`: Array de tecnologías identificadas
- `is_identified`: Boolean de identificación
- `status`: Estado del análisis
- `ai_explanation`: Explicación de IA
- `created_at/updated_at`: Timestamps

### Funcionalidades de BD
- **Inserción/Actualización** automática
- **Índices optimizados** para consultas rápidas
- **Triggers** para timestamps automáticos
- **Consultas complejas** con PostgreSQL

## 🔧 Arquitectura Modular

### 1. Scanner Module (`scanner_module/`)
- **scanner.py**: Motor principal de escaneo
- **db_connector.py**: Gestión de base de datos con psycopg2
- Soporte para múltiples plataformas Git
- Detección basada en patrones de archivos

### 2. Validator Module (`validator_module/`)
- **validator.py**: Validación y análisis con IA
- Integración con OpenAI GPT
- Explicaciones contextualizadas
- Análisis de patrones de repositorios

### 3. Query Module (`query_module/`)
- **query_engine.py**: Motor de consultas en lenguaje natural
- Conversión automática a SQL
- Patrones predefinidos y IA avanzada
- Cache de consultas frecuentes

## 🚨 Manejo de Errores

### Errores Comunes y Soluciones

#### Error de Conexión a BD
```bash
# Verificar PostgreSQL esté ejecutándose
sudo service postgresql start

# Verificar credenciales en .env
```

#### Error de Clonado de Repositorio
- Verificar conectividad a internet
- Confirmar que el repositorio sea público
- Revisar configuración de Git

#### Error de API de OpenAI
- Verificar clave API válida
- Confirmar créditos disponibles
- La herramienta funciona sin IA con funcionalidad limitada

## 📈 Rendimiento y Escalabilidad

### Optimizaciones Implementadas
- **Clonado superficial** (--depth 1) para velocidad
- **Índices de BD** para consultas rápidas
- **Procesamiento en lote** para múltiples repositorios
- **Cache de consultas IA** para evitar llamadas repetitivas

### Límites Recomendados
- Máximo 50 repositorios por lote
- Timeout de 5 minutos por clonado
- Máximo 50 resultados por consulta

## 🤝 Trabajo en Equipo

### Para Equipos de 2-4 Personas

#### División de Tareas Sugerida:
1. **Desarrollador 1**: Scanner module y base de datos
2. **Desarrollador 2**: Validator module y IA
3. **Desarrollador 3**: Query module y interfaz
4. **Desarrollador 4**: Testing y documentación

#### Flujo de Desarrollo:
1. Configurar entorno compartido
2. Definir estándares de código
3. Usar branches por funcionalidad
4. Testing continuo con repositorios reales

## 🧪 Testing

### Casos de Prueba Recomendados
```bash
# Repositorios públicos conocidos
python main.py --scan https://github.com/facebook/react
python main.py --scan https://github.com/microsoft/vscode
python main.py --scan https://github.com/tensorflow/tensorflow

# Consultas de prueba
python main.py --query "repositorios de facebook"
python main.py --query "proyectos que usan Python"
```

## 📋 Requisitos del Proyecto

### ✅ Requisitos Funcionales Implementados
- [x] Escaneo de repositorios Git desde cualquier plataforma
- [x] Análisis de tecnologías basado en archivos clave
- [x] Identificación de metadatos (propietario, nombre)
- [x] Distinción entre repositorios identificados/no identificados
- [x] Almacenamiento en PostgreSQL

### ✅ Arquitectura y Tecnología
- [x] Desarrollo en Python
- [x] Diseño modular con estructura clara
- [x] Conexión PostgreSQL con psycopg2
- [x] Comandos Git estándar agnósticos a plataforma
- [x] Tablas con actualización automática

### ✅ Inteligencia Artificial
- [x] Explicaciones detalladas para repositorios no identificados
- [x] Consultas en lenguaje natural a la base de datos
- [x] Análisis contextualizado y sugerencias

## 🆘 Soporte y Troubleshooting

### Logs del Sistema
Los logs se guardan en `cmdb.log` con información detallada de:
- Operaciones de escaneo
- Consultas a base de datos
- Errores y excepciones
- Llamadas a API de IA

### Comandos de Diagnóstico
```bash
# Verificar conexión a BD
python -c "from scanner_module import DatabaseConnector; print(DatabaseConnector().test_connection())"

# Verificar configuración
python main.py --stats
```

## 📄 Licencia

Este proyecto está desarrollado como herramienta educativa para equipos de desarrollo.

## 🤖 Próximas Funcionalidades

- [ ] Interfaz web con Flask/FastAPI
- [ ] Integración con APIs de GitHub/GitLab
- [ ] Análisis de dependencias de seguridad
- [ ] Dashboard de métricas en tiempo real
- [ ] Exportación a formatos adicionales (XML, YAML)

---

**¡Desarrollado con ❤️ para facilitar la gestión de configuraciones en equipos de desarrollo!**
