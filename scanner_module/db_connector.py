import psycopg2
import psycopg2.extras
import os
from typing import List, Dict, Optional, Tuple
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnector:

    def __init__(self, host: str = None, database: str = None, user: str = None,
                 password: str = None, port: int = 5432):
        # Variables de entorno por defecto
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.database = database or os.getenv('DB_NAME', 'cmdb_database')
        self.user = user or os.getenv('DB_USER', 'postgres')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.port = port or int(os.getenv('DB_PORT', '5432'))

        self.connection_string = (
            f"host={self.host} "
            f"dbname={self.database} "
            f"user={self.user} "
            f"password={self.password} "
            f"port={self.port}"
        )

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Error de conexión a la base de datos: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Error al probar la conexión: {e}")
            return False

    def create_tables_if_not_exist(self) -> bool:
        create_repositories_table = """
        CREATE TABLE IF NOT EXISTS repositories (
            id SERIAL PRIMARY KEY,
            url VARCHAR(500) NOT NULL UNIQUE,
            owner_name VARCHAR(255) NOT NULL,
            repo_name VARCHAR(255) NOT NULL,
            technologies TEXT[],
            is_identified BOOLEAN DEFAULT FALSE,
            status VARCHAR(50) DEFAULT 'pending',
            ai_explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_technology_patterns_table = """
        CREATE TABLE IF NOT EXISTS technology_patterns (
            id SERIAL PRIMARY KEY,
            technology_name VARCHAR(100) NOT NULL,
            file_pattern VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_ai_queries_table = """
        CREATE TABLE IF NOT EXISTS ai_queries (
            id SERIAL PRIMARY KEY,
            query_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            query_type VARCHAR(50) DEFAULT 'natural_language',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Crear tablas
                    cursor.execute(create_repositories_table)
                    cursor.execute(create_technology_patterns_table)
                    cursor.execute(create_ai_queries_table)

                    # Crear índices
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner_name);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(repo_name);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(status);")

                    conn.commit()
                    logger.info("Tablas creadas exitosamente")
                    return True
        except Exception as e:
            logger.error(f"Error al crear las tablas: {e}")
            return False

    def insert_repository(self, url: str, owner_name: str, repo_name: str,
                         technologies: List[str] = None, is_identified: bool = False,
                         status: str = 'pending', ai_explanation: str = None) -> Optional[int]:
        """
        Inserta o actualiza un repositorio en la base de datos

        Args:
            url: URL del repositorio
            owner_name: Nombre del propietario
            repo_name: Nombre del repositorio
            technologies: Lista de tecnologías identificadas
            is_identified: Si el repositorio fue identificado
            status: Estado del análisis
            ai_explanation: Explicación de IA para repositorios no identificados

        Returns:
            int: ID del repositorio insertado/actualizado o None si hay error
        """
        technologies = technologies or []

        insert_query = """
        INSERT INTO repositories (url, owner_name, repo_name, technologies, is_identified, status, ai_explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE SET
            owner_name = EXCLUDED.owner_name,
            repo_name = EXCLUDED.repo_name,
            technologies = EXCLUDED.technologies,
            is_identified = EXCLUDED.is_identified,
            status = EXCLUDED.status,
            ai_explanation = EXCLUDED.ai_explanation,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_query, (url, owner_name, repo_name,
                                                technologies, is_identified, status, ai_explanation))
                    repo_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Repositorio insertado/actualizado con ID: {repo_id}")
                    return repo_id
        except Exception as e:
            logger.error(f"Error al insertar repositorio: {e}")
            return None

    def get_repository_by_url(self, url: str) -> Optional[Dict]:
        """
        Obtiene un repositorio por su URL

        Args:
            url: URL del repositorio

        Returns:
            Dict: Datos del repositorio o None si no existe
        """
        query = "SELECT * FROM repositories WHERE url = %s;"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (url,))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error al obtener repositorio por URL: {e}")
            return None

    def get_repositories_by_owner(self, owner_name: str) -> List[Dict]:
        """
        Obtiene todos los repositorios de un propietario

        Args:
            owner_name: Nombre del propietario

        Returns:
            List[Dict]: Lista de repositorios del propietario
        """
        query = "SELECT * FROM repositories WHERE owner_name = %s ORDER BY repo_name;"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (owner_name,))
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al obtener repositorios por propietario: {e}")
            return []

    def get_repositories_by_technology(self, technology: str) -> List[Dict]:
        """
        Obtiene repositorios que usan una tecnología específica

        Args:
            technology: Nombre de la tecnología

        Returns:
            List[Dict]: Lista de repositorios que usan la tecnología
        """
        query = "SELECT * FROM repositories WHERE %s = ANY(technologies) ORDER BY owner_name, repo_name;"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (technology,))
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al obtener repositorios por tecnología: {e}")
            return []

    def get_all_repositories(self, limit: int = None) -> List[Dict]:
        """
        Obtiene todos los repositorios de la base de datos

        Args:
            limit: Límite de resultados (opcional)

        Returns:
            List[Dict]: Lista de todos los repositorios
        """
        query = "SELECT * FROM repositories ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al obtener todos los repositorios: {e}")
            return []

    def get_unidentified_repositories(self) -> List[Dict]:
        """
        Obtiene repositorios no identificados

        Returns:
            List[Dict]: Lista de repositorios no identificados
        """
        query = "SELECT * FROM repositories WHERE is_identified = FALSE ORDER BY created_at DESC;"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al obtener repositorios no identificados: {e}")
            return []

    def execute_custom_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Ejecuta una consulta personalizada

        Args:
            query: Consulta SQL
            params: Parámetros para la consulta

        Returns:
            List[Dict]: Resultados de la consulta
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params or ())
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al ejecutar consulta personalizada: {e}")
            return []

    def save_ai_query(self, query_text: str, response_text: str, query_type: str = 'natural_language') -> bool:
        """
        Guarda una consulta de IA y su respuesta

        Args:
            query_text: Texto de la consulta
            response_text: Respuesta generada
            query_type: Tipo de consulta

        Returns:
            bool: True si se guardó exitosamente
        """
        insert_query = """
        INSERT INTO ai_queries (query_text, response_text, query_type)
        VALUES (%s, %s, %s);
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_query, (query_text, response_text, query_type))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error al guardar consulta de IA: {e}")
            return False
