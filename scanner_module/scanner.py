import os
import re
import shutil
import tempfile
import subprocess
from typing import List, Dict, Tuple, Optional
import logging
from urllib.parse import urlparse
import json

from .db_connector import DatabaseConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RepositoryScanner:

    def __init__(self, db_connector: DatabaseConnector = None):
        self.db_connector = db_connector or DatabaseConnector()

        # Patrones de archivos por tecnología
        self.technology_patterns = {
            'Node.js': [
                'package.json',
                'package-lock.json',
                'yarn.lock',
                'node_modules'
            ],
            'Python': [
                'requirements.txt',
                'setup.py',
                'pyproject.toml',
                'Pipfile',
                'poetry.lock',
                'conda.yaml',
                'environment.yml'
            ],
            'Java': [
                'pom.xml',
                'build.gradle',
                'build.gradle.kts',
                'gradle.properties',
                'mvnw',
                'gradlew'
            ],
            'PHP': [
                'composer.json',
                'composer.lock',
                'index.php'
            ],
            'Ruby': [
                'Gemfile',
                'Gemfile.lock',
                '.ruby-version'
            ],
            'Go': [
                'go.mod',
                'go.sum',
                'main.go'
            ],
            'Rust': [
                'Cargo.toml',
                'Cargo.lock'
            ],
            'C#': [
                '*.csproj',
                '*.sln',
                'packages.config',
                'project.json'
            ],
            'Flutter/Dart': [
                'pubspec.yaml',
                'pubspec.lock'
            ],
            'React': [
                'package.json'  # Se valida por dependencias
            ],
            'Angular': [
                'angular.json',
                'angular-cli.json'
            ],
            'Vue.js': [
                'vue.config.js',
                'vue.config.ts'
            ],
            'Docker': [
                'Dockerfile',
                'docker-compose.yml',
                'docker-compose.yaml',
                '.dockerignore'
            ],
            'Kubernetes': [
                'deployment.yaml',
                'service.yaml',
                'ingress.yaml',
                'kustomization.yaml'
            ],
            'Terraform': [
                '*.tf',
                'terraform.tfvars',
                '.terraform'
            ],
            'Android': [
                'build.gradle',
                'AndroidManifest.xml'
            ],
            'iOS': [
                '*.xcodeproj',
                '*.xcworkspace',
                'Podfile'
            ]
        }

    def extract_repo_info_from_url(self, url: str) -> Tuple[str, str]:
        try:
            url = url.strip().rstrip('/')

            # Patrones de URLs
            patterns = [
                r'https?://(?:www\.)?(?:github|gitlab)\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
                r'git@(?:github|gitlab)\.com:([^/]+)/([^/]+?)(?:\.git)?/?$',
                r'https?://[^/]+/([^/]+)/([^/]+?)(?:\.git)?/?$',
                r'git@[^:]+:([^/]+)/([^/]+?)(?:\.git)?/?$'
            ]

            for pattern in patterns:
                match = re.match(pattern, url)
                if match:
                    owner = match.group(1)
                    repo = match.group(2)
                    return owner, repo

            # Fallback
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]

            if len(path_parts) >= 2:
                owner = path_parts[-2]
                repo = path_parts[-1].replace('.git', '')
                return owner, repo

            return 'unknown', url.split('/')[-1].replace('.git', '')

        except Exception as e:
            logger.error(f"Error al extraer info del repo {url}: {e}")
            return 'unknown', 'unknown'

    def clone_repository(self, url: str, temp_dir: str) -> bool:
        """
        Clona un repositorio Git en un directorio temporal

        Args:
            url: URL del repositorio
            temp_dir: Directorio temporal donde clonar

        Returns:
            bool: True si el clonado fue exitoso
        """
        try:
            # Comando git clone con opciones para clonar solo la rama principal
            cmd = [
                'git', 'clone',
                '--depth', '1',  # Solo el último commit
                '--single-branch',  # Solo la rama principal
                url,
                temp_dir
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # Timeout de 5 minutos
            )

            if result.returncode == 0:
                logger.info(f"Repositorio clonado exitosamente: {url}")
                return True
            else:
                logger.error(f"Error al clonar repositorio {url}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout al clonar repositorio: {url}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al clonar repositorio {url}: {e}")
            return False

    def scan_directory_for_technologies(self, directory: str) -> List[str]:
        """
        Escanea un directorio para identificar tecnologías basándose en archivos

        Args:
            directory: Directorio a escanear

        Returns:
            List[str]: Lista de tecnologías identificadas
        """
        identified_technologies = []

        try:
            # Obtener todos los archivos del directorio recursivamente
            all_files = []
            for root, dirs, files in os.walk(directory):
                # Ignorar directorios como .git, node_modules, etc.
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'target']]

                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), directory)
                    all_files.append(relative_path)

            # Verificar patrones de tecnologías
            for technology, patterns in self.technology_patterns.items():
                for pattern in patterns:
                    if self._matches_pattern(all_files, pattern):
                        if technology not in identified_technologies:
                            # Validaciones adicionales para tecnologías específicas
                            if self._validate_technology(technology, directory, all_files):
                                identified_technologies.append(technology)
                        break

            logger.info(f"Tecnologías identificadas: {identified_technologies}")
            return identified_technologies

        except Exception as e:
            logger.error(f"Error al escanear directorio para tecnologías: {e}")
            return []

    def _matches_pattern(self, files: List[str], pattern: str) -> bool:
        """
        Verifica si algún archivo coincide con el patrón

        Args:
            files: Lista de archivos
            pattern: Patrón a buscar

        Returns:
            bool: True si encuentra coincidencia
        """
        if '*' in pattern:
            # Patrón con wildcard
            import fnmatch
            return any(fnmatch.fnmatch(f, pattern) for f in files)
        else:
            # Coincidencia exacta
            return pattern in files or any(f.endswith(pattern) for f in files)

    def _validate_technology(self, technology: str, directory: str, files: List[str]) -> bool:
        """
        Validaciones adicionales para tecnologías específicas

        Args:
            technology: Nombre de la tecnología
            directory: Directorio del repositorio
            files: Lista de archivos

        Returns:
            bool: True si la tecnología es válida
        """
        try:
            if technology == 'React':
                # Verificar si package.json contiene React como dependencia
                package_json_path = os.path.join(directory, 'package.json')
                if os.path.exists(package_json_path):
                    with open(package_json_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        dependencies = package_data.get('dependencies', {})
                        dev_dependencies = package_data.get('devDependencies', {})
                        return 'react' in dependencies or 'react' in dev_dependencies
                return False

            elif technology == 'Android':
                # Verificar que tenga AndroidManifest.xml además de build.gradle
                return any('AndroidManifest.xml' in f for f in files)

            elif technology == 'C#':
                # Verificar archivos .cs
                return any(f.endswith('.cs') for f in files)

            # Para otras tecnologías, la presencia del archivo es suficiente
            return True

        except Exception as e:
            logger.error(f"Error al validar tecnología {technology}: {e}")
            return True  # En caso de error, asumir que es válida

    def scan_repository(self, url: str) -> Dict:
        """
        Escanea un repositorio completo y devuelve la información

        Args:
            url: URL del repositorio

        Returns:
            Dict: Información del repositorio escaneado
        """
        # Extraer información del repositorio
        owner, repo_name = self.extract_repo_info_from_url(url)

        # Inicializar resultado
        result = {
            'url': url,
            'owner_name': owner,
            'repo_name': repo_name,
            'technologies': [],
            'is_identified': False,
            'status': 'error',
            'ai_explanation': None
        }

        temp_dir = None
        try:
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix='cmdb_repo_')

            # Clonar repositorio
            if not self.clone_repository(url, temp_dir):
                result['status'] = 'clone_failed'
                result['ai_explanation'] = f"No se pudo clonar el repositorio desde {url}. Verifique que la URL sea correcta y que el repositorio sea público o tenga los permisos necesarios."
                return result

            # Escanear tecnologías
            technologies = self.scan_directory_for_technologies(temp_dir)
            result['technologies'] = technologies
            result['is_identified'] = len(technologies) > 0
            result['status'] = 'analyzed'

            if not result['is_identified']:
                result['ai_explanation'] = self._generate_explanation_for_unidentified(temp_dir, url)

            logger.info(f"Escaneo completo del repositorio {url}: {len(technologies)} tecnologías identificadas")
            return result

        except Exception as e:
            logger.error(f"Error al escanear repositorio {url}: {e}")
            result['status'] = 'error'
            result['ai_explanation'] = f"Error durante el análisis del repositorio: {str(e)}"
            return result

        finally:
            # Limpiar directorio temporal
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar directorio temporal {temp_dir}: {e}")

    def _generate_explanation_for_unidentified(self, directory: str, url: str) -> str:
        """
        Genera una explicación para repositorios no identificados

        Args:
            directory: Directorio del repositorio
            url: URL del repositorio

        Returns:
            str: Explicación detallada
        """
        try:
            # Analizar estructura del directorio
            file_count = 0
            dir_count = 0
            file_extensions = set()

            for root, dirs, files in os.walk(directory):
                # Ignorar directorios ocultos
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                dir_count += len(dirs)

                for file in files:
                    if not file.startswith('.'):
                        file_count += 1
                        if '.' in file:
                            ext = file.split('.')[-1].lower()
                            file_extensions.add(ext)

            explanation = f"""
ANÁLISIS DEL REPOSITORIO NO IDENTIFICADO:

Repositorio: {url}
Archivos encontrados: {file_count}
Directorios encontrados: {dir_count}

EXTENSIONES DE ARCHIVO DETECTADAS:
{', '.join(sorted(file_extensions)) if file_extensions else 'No se encontraron extensiones específicas'}

POSIBLES RAZONES PARA NO IDENTIFICACIÓN:
1. El repositorio podría contener código en un lenguaje no cubierto por nuestros patrones actuales
2. Podría ser un proyecto de configuración, documentación o datos sin archivos de tecnología estándar
3. Los archivos de configuración podrían estar en ubicaciones no estándar
4. Podría ser un repositorio experimental o de pruebas

RECOMENDACIONES PARA EL DESARROLLADOR:
- Verificar si el repositorio contiene archivos como package.json, requirements.txt, pom.xml, etc.
- Revisar si hay archivos de configuración en subdirectorios
- Considerar añadir archivos de configuración estándar para su tecnología
- Si es un tipo de proyecto nuevo, considerar añadir el patrón correspondiente al sistema

EXTENSIONES DETECTADAS QUE PODRÍAN INDICAR TECNOLOGÍAS:
"""

            # Sugerir tecnologías basándose en extensiones
            extension_suggestions = {
                'py': 'Python (considere añadir requirements.txt)',
                'js': 'JavaScript (considere añadir package.json)',
                'java': 'Java (considere añadir pom.xml o build.gradle)',
                'php': 'PHP (considere añadir composer.json)',
                'rb': 'Ruby (considere añadir Gemfile)',
                'go': 'Go (considere añadir go.mod)',
                'rs': 'Rust (considere añadir Cargo.toml)',
                'cs': 'C# (considere añadir .csproj o .sln)',
                'cpp': 'C++ (considere añadir CMakeLists.txt)',
                'c': 'C (considere añadir Makefile)',
                'ts': 'TypeScript (considere añadir package.json)',
                'dart': 'Dart/Flutter (considere añadir pubspec.yaml)',
                'kt': 'Kotlin (considere añadir build.gradle)',
                'swift': 'Swift (considere añadir Package.swift)',
                'scala': 'Scala (considere añadir build.sbt)'
            }

            for ext in file_extensions:
                if ext in extension_suggestions:
                    explanation += f"- {extension_suggestions[ext]}\n"

            return explanation

        except Exception as e:
            return f"No se pudo generar explicación detallada. Error: {str(e)}"

    def scan_and_store_repository(self, url: str) -> bool:
        """
        Escanea un repositorio y almacena los resultados en la base de datos

        Args:
            url: URL del repositorio

        Returns:
            bool: True si el proceso fue exitoso
        """
        try:
            # Escanear repositorio
            scan_result = self.scan_repository(url)

            # Almacenar en base de datos
            repo_id = self.db_connector.insert_repository(
                url=scan_result['url'],
                owner_name=scan_result['owner_name'],
                repo_name=scan_result['repo_name'],
                technologies=scan_result['technologies'],
                is_identified=scan_result['is_identified'],
                status=scan_result['status'],
                ai_explanation=scan_result['ai_explanation']
            )

            if repo_id:
                logger.info(f"Repositorio almacenado exitosamente con ID: {repo_id}")
                return True
            else:
                logger.error("Error al almacenar repositorio en la base de datos")
                return False

        except Exception as e:
            logger.error(f"Error en scan_and_store_repository: {e}")
            return False

    def batch_scan_repositories(self, urls: List[str]) -> Dict[str, Dict]:
        """
        Escanea múltiples repositorios en lote

        Args:
            urls: Lista de URLs de repositorios

        Returns:
            Dict[str, Dict]: Resultados de escaneo por URL
        """
        results = {}

        for i, url in enumerate(urls, 1):
            logger.info(f"Escaneando repositorio {i}/{len(urls)}: {url}")

            try:
                # Escanear y almacenar repositorio
                success = self.scan_and_store_repository(url)
                results[url] = {
                    'success': success,
                    'scanned_at': i,
                    'total': len(urls)
                }

            except Exception as e:
                logger.error(f"Error al procesar repositorio {url}: {e}")
                results[url] = {
                    'success': False,
                    'error': str(e),
                    'scanned_at': i,
                    'total': len(urls)
                }

        logger.info(f"Escaneo en lote completado. {len(results)} repositorios procesados")
        return results
