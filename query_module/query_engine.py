import os
import re
from typing import Dict, List, Optional, Tuple
import logging
from scanner_module.db_connector import DatabaseConnector
import json
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaturalLanguageQueryEngine:

    def __init__(self, api_key: str = None, db_connector: DatabaseConnector = None, model_name: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        self.db_connector = db_connector or DatabaseConnector()

        if self.api_key:
            genai.configure(api_key=self.api_key)
        try:
            self.gemini_model = genai.GenerativeModel(self.model_name) if self.api_key else None
        except Exception as e:
            logger.error(f"Error inicializando modelo Gemini: {e}")
            self.gemini_model = None

        # Patrones comunes de consulta
        self.query_patterns = {
            'owner_repositories': r'(?:repositorios|repos)\s+(?:de|del)\s+([^?]+)',
            'repository_owner': r'(?:quién|quien)\s+(?:es|tiene)\s+(?:el\s+)?(?:dueño|propietario)\s+(?:de|del)\s+(?:repositorio\s+)?["\']?([^"\'?]+)["\']?',
            'technologies_used': r'(?:qué|que)\s+tecnolog[íi]as?\s+(?:usa|utiliza|se\s+usan)\s+(?:en\s+)?(?:el\s+)?(?:repositorio\s+)?["\']?([^"\'?]+)["\']?',
            'projects_with_technology': r'(?:qué|que)\s+(?:repositorios|proyectos)\s+(?:usan|utilizan|tienen)\s+([^?]+)',
            'repository_count': r'(?:cuántos|cuantos)\s+repositorios',
            'statistics': r'(?:estadísticas|estadisticas|stats|resumen)',
            'unidentified_repos': r'(?:repositorios|repos)\s+(?:no\s+)?(?:identificados|sin\s+identificar)'
        }

    def process_natural_language_query(self, query: str) -> Dict:
        query_lower = query.lower().strip()

        # Intentar patrones específicos primero
        sql_result = self._try_pattern_matching(query_lower)
        if sql_result:
            return sql_result

        # Si no hay patrón, usar IA
        if self.api_key:
            return self._process_with_ai(query)
        else:
            return self._process_fallback(query_lower)

    def _try_pattern_matching(self, query: str) -> Optional[Dict]:
        # Buscar owner de repositorio específico
        match = re.search(self.query_patterns['repository_owner'], query, re.IGNORECASE)
        if match:
            repo_name = match.group(1).strip()
            return self._find_repository_owner(repo_name)

        # Buscar repositorios de un owner específico
        match = re.search(self.query_patterns['owner_repositories'], query, re.IGNORECASE)
        if match:
            owner_name = match.group(1).strip()
            return self._find_repositories_by_owner(owner_name)

        # Buscar tecnologías de un repositorio
        match = re.search(self.query_patterns['technologies_used'], query, re.IGNORECASE)
        if match:
            repo_name = match.group(1).strip()
            return self._find_technologies_for_repository(repo_name)

        # Buscar proyectos con tecnología específica
        match = re.search(self.query_patterns['projects_with_technology'], query, re.IGNORECASE)
        if match:
            technology = match.group(1).strip()
            return self._find_projects_with_technology(technology)

        # Estadísticas generales
        if re.search(self.query_patterns['statistics'], query, re.IGNORECASE):
            return self._get_general_statistics()

        # Repositorios no identificados
        if re.search(self.query_patterns['unidentified_repos'], query, re.IGNORECASE):
            return self._get_unidentified_repositories()

        # Contar repositorios
        if re.search(self.query_patterns['repository_count'], query, re.IGNORECASE):
            return self._count_repositories()

        return None

    def _find_repository_owner(self, repo_name: str) -> Dict:
        try:
            # Buscar por nombre exacto o similar
            repos = self.db_connector.execute_custom_query(
                "SELECT owner_name, repo_name, url FROM repositories WHERE LOWER(repo_name) LIKE LOWER(%s)",
                (f'%{repo_name}%',)
            )

            if repos:
                if len(repos) == 1:
                    repo = repos[0]
                    return {
                        'success': True,
                        'explanation': f"El propietario del repositorio '{repo['repo_name']}' es {repo['owner_name']}",
                        'results': [repo],
                        'count': 1
                    }
                else:
                    return {
                        'success': True,
                        'explanation': f"Encontré {len(repos)} repositorios que coinciden con '{repo_name}':",
                        'results': repos,
                        'count': len(repos)
                    }
            else:
                return {
                    'success': False,
                    'explanation': f"No encontré ningún repositorio con el nombre '{repo_name}'"
                }

        except Exception as e:
            logger.error(f"Error buscando propietario: {e}")
            return {'success': False, 'error': str(e)}

    def _find_repositories_by_owner(self, owner_name: str) -> Dict:
        try:
            repos = self.db_connector.get_repositories_by_owner(owner_name)

            if repos:
                return {
                    'success': True,
                    'explanation': f"{owner_name} tiene {len(repos)} repositorio(s):",
                    'results': repos,
                    'count': len(repos)
                }
            else:
                return {
                    'success': False,
                    'explanation': f"No encontré repositorios para el propietario '{owner_name}'"
                }

        except Exception as e:
            logger.error(f"Error buscando repositorios por owner: {e}")
            return {'success': False, 'error': str(e)}

    def _find_technologies_for_repository(self, repo_name: str) -> Dict:
        try:
            repos = self.db_connector.execute_custom_query(
                "SELECT repo_name, owner_name, technologies FROM repositories WHERE LOWER(repo_name) LIKE LOWER(%s)",
                (f'%{repo_name}%',)
            )

            if repos:
                repo = repos[0]
                technologies = repo.get('technologies', [])

                if technologies:
                    tech_list = ', '.join(technologies)
                    return {
                        'success': True,
                        'explanation': f"El repositorio '{repo['repo_name']}' de {repo['owner_name']} usa: {tech_list}",
                        'results': [{'repository': repo['repo_name'], 'technologies': technologies}],
                        'count': len(technologies)
                    }
                else:
                    return {
                        'success': True,
                        'explanation': f"El repositorio '{repo['repo_name']}' no tiene tecnologías identificadas",
                        'results': [],
                        'count': 0
                    }
            else:
                return {
                    'success': False,
                    'explanation': f"No encontré el repositorio '{repo_name}'"
                }

        except Exception as e:
            logger.error(f"Error buscando tecnologías: {e}")
            return {'success': False, 'error': str(e)}

    def _find_projects_with_technology(self, technology: str) -> Dict:
        try:
            repos = self.db_connector.get_repositories_by_technology(technology)

            if repos:
                return {
                    'success': True,
                    'explanation': f"Encontré {len(repos)} repositorio(s) que usan {technology}:",
                    'results': repos,
                    'count': len(repos)
                }
            else:
                return {
                    'success': False,
                    'explanation': f"No encontré repositorios que usen '{technology}'"
                }

        except Exception as e:
            logger.error(f"Error buscando proyectos con tecnología: {e}")
            return {'success': False, 'error': str(e)}

    def _get_general_statistics(self) -> Dict:
        try:
            all_repos = self.db_connector.get_all_repositories()

            if not all_repos:
                return {
                    'success': False,
                    'explanation': "No hay repositorios en la base de datos"
                }

            total = len(all_repos)
            identified = sum(1 for r in all_repos if r.get('is_identified', False))

            # Tecnologías más comunes
            all_techs = []
            for repo in all_repos:
                all_techs.extend(repo.get('technologies', []))

            tech_counts = {}
            for tech in all_techs:
                tech_counts[tech] = tech_counts.get(tech, 0) + 1

            top_techs = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            stats_text = f"""
📊 Estadísticas del CMDB:
• Total de repositorios: {total}
• Repositorios identificados: {identified} ({identified/total*100:.1f}%)
• Repositorios no identificados: {total-identified}

Tecnologías más populares:"""

            for tech, count in top_techs:
                stats_text += f"\n• {tech}: {count} repositorio(s)"

            return {
                'success': True,
                'explanation': stats_text,
                'results': {
                    'total': total,
                    'identified': identified,
                    'technologies': top_techs
                },
                'count': total
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'success': False, 'error': str(e)}

    def _get_unidentified_repositories(self) -> Dict:
        try:
            unidentified = self.db_connector.get_unidentified_repositories()

            if unidentified:
                return {
                    'success': True,
                    'explanation': f"Hay {len(unidentified)} repositorio(s) no identificados:",
                    'results': unidentified,
                    'count': len(unidentified)
                }
            else:
                return {
                    'success': True,
                    'explanation': "Todos los repositorios han sido identificados correctamente",
                    'results': [],
                    'count': 0
                }

        except Exception as e:
            logger.error(f"Error obteniendo repos no identificados: {e}")
            return {'success': False, 'error': str(e)}

    def _count_repositories(self) -> Dict:
        try:
            total = len(self.db_connector.get_all_repositories())
            return {
                'success': True,
                'explanation': f"Hay {total} repositorio(s) en la base de datos",
                'results': [{'total_repositories': total}],
                'count': total
            }

        except Exception as e:
            logger.error(f"Error contando repositorios: {e}")
            return {'success': False, 'error': str(e)}

    def _process_with_ai(self, query: str) -> Dict:
        try:
            if not self.gemini_model:
                return {'success': False, 'explanation': f"El modelo Gemini '{self.model_name}' no está disponible. Verifica tu clave y modelo. Puedes listar modelos con: genai.list_models()"}
            all_repos = self.db_connector.get_all_repositories(limit=50)
            context = f"""
Base de datos CMDB con {len(all_repos)} repositorios.
Campos disponibles: url, owner_name, repo_name, technologies, is_identified, status, ai_explanation.
Repositorios de muestra:
"""
            for repo in all_repos[:3]:
                context += f"- {repo.get('owner_name', 'N/A')}/{repo.get('repo_name', 'N/A')} (Tecnologías: {', '.join(repo.get('technologies', []))})\n"
            prompt = f"""
Consulta del usuario: \"{query}\"
Contexto de la base de datos:
{context}
Traduce esta consulta a una respuesta útil. Si es una pregunta específica sobre repositorios, proporciona una respuesta basada en los datos disponibles.\nResponde en español de forma clara y directa.
"""
            response = self.gemini_model.generate_content(prompt)
            ai_response = response.text.strip()
            self.db_connector.save_ai_query(query, ai_response, 'natural_language')
            return {
                'success': True,
                'explanation': ai_response,
                'results': [],
                'count': 0,
                'ai_processed': True
            }
        except Exception as e:
            logger.error(f"Error procesando con Gemini: {e}")
            return {'success': False, 'explanation': f"Error procesando con Gemini: {e}. Verifica que el modelo '{self.model_name}' esté disponible para tu clave. Puedes listar modelos con: genai.list_models()"}

    def _process_fallback(self, query: str) -> Dict:
        return {
            'success': False,
            'explanation': f"No pude procesar la consulta '{query}'. Intenta con consultas como: '¿Quién es el dueño del repositorio X?', '¿Qué tecnologías usa el proyecto Y?', 'repositorios de usuario Z'",
            'suggestions': self.get_suggested_queries()
        }

    def get_suggested_queries(self) -> List[str]:
        return [
            "¿Quién es el dueño del repositorio 'proyecto-ejemplo'?",
            "¿Qué tecnologías usa el repositorio 'mi-app'?",
            "repositorios de usuario juan",
            "proyectos que usan Python",
            "repositorios no identificados",
            "estadísticas del sistema",
            "¿cuántos repositorios hay?"
        ]

    def ask_open_question(self, question: str, context: str = None) -> str:
        if not self.gemini_model:
            logger.warning(f"No se encontró modelo Gemini '{self.model_name}'.")
            return f"No se puede procesar la pregunta sin modelo Gemini válido. Puedes listar modelos con: genai.list_models()"
        prompt = f"""
Eres un asistente experto en gestión de bases de datos de configuración (CMDB). Responde la siguiente pregunta de forma clara y precisa. Si tienes contexto adicional, úsalo para mejorar la respuesta.\nPregunta: {question}
"""
        if context:
            prompt += f"\nContexto: {context}\n"
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error al consultar Gemini: {e}")
            return f"Ocurrió un error al procesar la pregunta con Gemini: {e}. Verifica que el modelo '{self.model_name}' esté disponible."

    def summarize_results(self, results: List[Dict], question: str = None) -> str:
        if not self.gemini_model:
            logger.warning(f"No se encontró modelo Gemini '{self.model_name}'.")
            return f"No se puede resumir sin modelo Gemini válido. Puedes listar modelos con: genai.list_models()"
        prompt = "Estos son los resultados de una consulta a la CMDB. Resume los puntos clave de forma clara y breve."
        if question:
            prompt += f"\nPregunta original: {question}"
        prompt += f"\nResultados: {json.dumps(results, ensure_ascii=False, indent=2)}"
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error al resumir resultados con Gemini: {e}")
            return f"Ocurrió un error al resumir los resultados con Gemini: {e}. Verifica que el modelo '{self.model_name}' esté disponible."
