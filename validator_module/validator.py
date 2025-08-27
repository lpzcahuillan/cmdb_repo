import os
import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime

from scanner_module.db_connector import DatabaseConnector

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIValidator:
    """Clase para validación y análisis con IA de repositorios"""

    def __init__(self, api_key: str = None, db_connector: DatabaseConnector = None):
        """
        Inicializa el validador de IA

        Args:
            api_key: Clave API de OpenAI (opcional, puede usar variable de entorno)
            db_connector: Conector de base de datos
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("No se proporcionó clave API de Gemini. Funcionalidad de IA limitada.")

        # Configurar cliente OpenAI
        if self.api_key:
            genai.configure(api_key=self.api_key)

        self.gemini_model = genai.GenerativeModel('gemini-pro') if self.api_key else None
        self.db_connector = db_connector or DatabaseConnector()

        # Prompts para análisis
        self.prompts = {
            'unidentified_analysis': """
Eres un experto en análisis de repositorios de código y arquitectura de software. 
Analiza la siguiente información de un repositorio que no pudo ser identificado automáticamente:

Repositorio: {url}
Propietario: {owner}
Nombre: {repo_name}
Archivos encontrados: {file_count}
Extensiones detectadas: {extensions}
Estructura de directorios: {directory_structure}

Por favor proporciona:
1. Una explicación detallada de por qué el repositorio no fue identificado
2. Posibles tecnologías que podrían estar en uso basándose en las extensiones
3. Recomendaciones específicas para mejorar la identificación
4. Sugerencias de archivos de configuración que podrían añadirse
5. Análisis del tipo de proyecto que podría ser

Responde en español de manera técnica pero comprensible.
""",

            'technology_suggestion': """
Basándose en las siguientes extensiones de archivo encontradas en un repositorio:
{extensions}

Y la siguiente estructura de directorios:
{structure}

Sugiere las tecnologías más probables que se están utilizando y explica el razonamiento.
Proporciona también recomendaciones para mejorar la detectabilidad del proyecto.
""",

            'repository_summary': """
Genera un resumen técnico del siguiente repositorio:

URL: {url}
Tecnologías identificadas: {technologies}
Estado: {status}
Propietario: {owner}

Proporciona un análisis de:
1. Stack tecnológico utilizado
2. Posible propósito del proyecto
3. Nivel de madurez del proyecto
4. Recomendaciones de mejores prácticas
"""
        }

    def generate_enhanced_explanation(self, repo_data: Dict, file_analysis: Dict = None) -> str:
        """
        Genera una explicación mejorada con IA para un repositorio

        Args:
            repo_data: Datos del repositorio
            file_analysis: Análisis adicional de archivos (opcional)

        Returns:
            str: Explicación detallada generada por IA
        """
        try:
            if not self.gemini_model:
                return self._generate_fallback_explanation(repo_data, file_analysis)

            # Preparar datos para el prompt
            extensions = file_analysis.get('extensions', []) if file_analysis else []
            directory_structure = file_analysis.get('structure', 'No disponible') if file_analysis else 'No disponible'
            file_count = file_analysis.get('file_count', 0) if file_analysis else 0

            prompt = self.prompts['unidentified_analysis'].format(
                url=repo_data.get('url', 'No especificada'),
                owner=repo_data.get('owner_name', 'No especificado'),
                repo_name=repo_data.get('repo_name', 'No especificado'),
                file_count=file_count,
                extensions=', '.join(extensions) if extensions else 'Ninguna específica',
                directory_structure=directory_structure
            )

            # Llamada a OpenAI API
            response = self.gemini_model.generate_content(prompt)
            ai_explanation = response.text.strip()

            # Guardar consulta en base de datos
            self.db_connector.save_ai_query(
                query_text=f"Análisis de repositorio no identificado: {repo_data.get('url')}",
                response_text=ai_explanation,
                query_type='unidentified_analysis'
            )

            return ai_explanation

        except Exception as e:
            logger.error(f"Error al generar explicación con Gemini: {e}")
            return self._generate_fallback_explanation(repo_data, file_analysis)

    def _generate_fallback_explanation(self, repo_data: Dict, file_analysis: Dict = None) -> str:
        """
        Genera explicación de respaldo sin IA

        Args:
            repo_data: Datos del repositorio
            file_analysis: Análisis de archivos

        Returns:
            str: Explicación básica
        """
        extensions = file_analysis.get('extensions', []) if file_analysis else []

        explanation = f"""
ANÁLISIS BÁSICO DEL REPOSITORIO NO IDENTIFICADO

Repositorio: {repo_data.get('url', 'No especificada')}
Propietario: {repo_data.get('owner_name', 'No especificado')}
Nombre: {repo_data.get('repo_name', 'No especificado')}

MOTIVOS POSIBLES DE NO IDENTIFICACIÓN:
• No se encontraron archivos de configuración estándar
• El proyecto podría usar tecnologías no cubiertas por los patrones actuales
• Los archivos de configuración podrían estar en ubicaciones no estándar

EXTENSIONES DETECTADAS: {', '.join(extensions) if extensions else 'Ninguna específica'}

RECOMENDACIONES:
• Verificar la presencia de archivos como package.json, requirements.txt, pom.xml
• Considerar añadir archivos de configuración apropiados para la tecnología utilizada
• Revisar si el repositorio contiene principalmente documentación o datos
"""

        # Sugerencias basadas en extensiones
        if extensions:
            extension_suggestions = {
                'py': 'Python - Considere añadir requirements.txt o setup.py',
                'js': 'JavaScript - Considere añadir package.json',
                'java': 'Java - Considere añadir pom.xml o build.gradle',
                'php': 'PHP - Considere añadir composer.json',
                'rb': 'Ruby - Considere añadir Gemfile',
                'go': 'Go - Considere añadir go.mod',
                'rs': 'Rust - Considere añadir Cargo.toml'
            }

            explanation += "\n\nSUGERENCIAS BASADAS EN EXTENSIONES:\n"
            for ext in extensions:
                if ext in extension_suggestions:
                    explanation += f"• {extension_suggestions[ext]}\n"

        return explanation

    def suggest_technologies_for_extensions(self, extensions: List[str]) -> Dict[str, str]:
        """
        Sugiere tecnologías basándose en extensiones de archivo

        Args:
            extensions: Lista de extensiones de archivo

        Returns:
            Dict[str, str]: Mapeo de extensión a tecnología sugerida
        """
        try:
            if not self.gemini_model or not extensions:
                return self._get_basic_technology_suggestions(extensions)

            prompt = self.prompts['technology_suggestion'].format(
                extensions=', '.join(extensions),
                structure="Estructura básica de directorios"
            )

            response = self.gemini_model.generate_content(prompt)
            suggestions_text = response.text.strip()

            # Guardar consulta
            self.db_connector.save_ai_query(
                query_text=f"Sugerencia de tecnologías para extensiones: {', '.join(extensions)}",
                response_text=suggestions_text,
                query_type='technology_suggestion'
            )

            return {'ai_analysis': suggestions_text}

        except Exception as e:
            logger.error(f"Error al sugerir tecnologías con Gemini: {e}")
            return self._get_basic_technology_suggestions(extensions)

    def _get_basic_technology_suggestions(self, extensions: List[str]) -> Dict[str, str]:
        """
        Sugerencias básicas de tecnología sin IA

        Args:
            extensions: Lista de extensiones

        Returns:
            Dict[str, str]: Sugerencias básicas
        """
        basic_mapping = {
            'py': 'Python',
            'js': 'JavaScript/Node.js',
            'ts': 'TypeScript',
            'java': 'Java',
            'php': 'PHP',
            'rb': 'Ruby',
            'go': 'Go',
            'rs': 'Rust',
            'cs': 'C#',
            'cpp': 'C++',
            'c': 'C',
            'dart': 'Dart/Flutter',
            'kt': 'Kotlin',
            'swift': 'Swift',
            'scala': 'Scala'
        }

        suggestions = {}
        for ext in extensions:
            if ext in basic_mapping:
                suggestions[ext] = basic_mapping[ext]

        return suggestions

    def generate_repository_summary(self, repo_data: Dict) -> str:
        """
        Genera un resumen técnico del repositorio

        Args:
            repo_data: Datos del repositorio

        Returns:
            str: Resumen técnico
        """
        try:
            if not self.gemini_model:
                return self._generate_basic_summary(repo_data)

            prompt = self.prompts['repository_summary'].format(
                url=repo_data.get('url', 'No especificada'),
                technologies=', '.join(repo_data.get('technologies', [])) or 'No identificadas',
                status=repo_data.get('status', 'Desconocido'),
                owner=repo_data.get('owner_name', 'No especificado')
            )

            response = self.gemini_model.generate_content(prompt)
            summary = response.text.strip()

            # Guardar consulta
            self.db_connector.save_ai_query(
                query_text=f"Resumen de repositorio: {repo_data.get('url')}",
                response_text=summary,
                query_type='repository_summary'
            )

            return summary

        except Exception as e:
            logger.error(f"Error al generar resumen con Gemini: {e}")
            return self._generate_basic_summary(repo_data)

    def _generate_basic_summary(self, repo_data: Dict) -> str:
        """
        Genera resumen básico sin IA

        Args:
            repo_data: Datos del repositorio

        Returns:
            str: Resumen básico
        """
        technologies = repo_data.get('technologies', [])

        summary = f"""
RESUMEN DEL REPOSITORIO

URL: {repo_data.get('url', 'No especificada')}
Propietario: {repo_data.get('owner_name', 'No especificado')}
Nombre: {repo_data.get('repo_name', 'No especificado')}
Estado: {repo_data.get('status', 'Desconocido')}

TECNOLOGÍAS IDENTIFICADAS:
{', '.join(technologies) if technologies else 'No se identificaron tecnologías'}

ANÁLISIS BÁSICO:
• Repositorio {'identificado' if repo_data.get('is_identified') else 'no identificado'}
• {len(technologies)} tecnologías detectadas
• Estado del análisis: {repo_data.get('status', 'Desconocido')}
"""

        if not technologies:
            summary += "\n• Se recomienda revisar la estructura del proyecto y añadir archivos de configuración apropiados"

        return summary

    def analyze_repository_patterns(self, repositories: List[Dict]) -> Dict:
        """
        Analiza patrones en múltiples repositorios

        Args:
            repositories: Lista de repositorios

        Returns:
            Dict: Análisis de patrones
        """
        if not repositories:
            return {'error': 'No hay repositorios para analizar'}

        # Estadísticas básicas
        total_repos = len(repositories)
        identified_repos = sum(1 for r in repositories if r.get('is_identified', False))

        # Tecnologías más comunes
        all_technologies = []
        for repo in repositories:
            all_technologies.extend(repo.get('technologies', []))

        tech_counts = {}
        for tech in all_technologies:
            tech_counts[tech] = tech_counts.get(tech, 0) + 1

        # Propietarios más activos
        owner_counts = {}
        for repo in repositories:
            owner = repo.get('owner_name', 'unknown')
            owner_counts[owner] = owner_counts.get(owner, 0) + 1

        analysis = {
            'total_repositories': total_repos,
            'identified_repositories': identified_repos,
            'identification_rate': (identified_repos / total_repos * 100) if total_repos > 0 else 0,
            'most_common_technologies': sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'most_active_owners': sorted(owner_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'unidentified_count': total_repos - identified_repos
        }

        return analysis

    def validate_repository_completeness(self, repo_data: Dict) -> Dict:
        """
        Valida la completitud de un repositorio

        Args:
            repo_data: Datos del repositorio

        Returns:
            Dict: Resultado de validación
        """
        validation = {
            'score': 0,
            'max_score': 100,
            'issues': [],
            'recommendations': []
        }

        # Verificar URL válida
        if repo_data.get('url'):
            validation['score'] += 20
        else:
            validation['issues'].append('URL no especificada')

        # Verificar propietario
        if repo_data.get('owner_name') and repo_data['owner_name'] != 'unknown':
            validation['score'] += 15
        else:
            validation['issues'].append('Propietario no identificado')
            validation['recommendations'].append('Verificar que la URL del repositorio sea válida')

        # Verificar nombre del repositorio
        if repo_data.get('repo_name') and repo_data['repo_name'] != 'unknown':
            validation['score'] += 15
        else:
            validation['issues'].append('Nombre del repositorio no identificado')

        # Verificar tecnologías identificadas
        technologies = repo_data.get('technologies', [])
        if technologies:
            validation['score'] += 30
        else:
            validation['issues'].append('No se identificaron tecnologías')
            validation['recommendations'].append('Añadir archivos de configuración estándar (package.json, requirements.txt, etc.)')

        # Verificar estado del análisis
        if repo_data.get('status') == 'analyzed':
            validation['score'] += 20
        else:
            validation['issues'].append(f"Estado del análisis: {repo_data.get('status', 'Desconocido')}")

        # Calcular porcentaje
        validation['percentage'] = (validation['score'] / validation['max_score']) * 100

        return validation
