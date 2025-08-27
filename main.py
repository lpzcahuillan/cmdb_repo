import os
import sys
import argparse
import json
from typing import List, Dict
import logging
from dotenv import load_dotenv

# Importar módulos del proyecto
from scanner_module import RepositoryScanner, DatabaseConnector
from validator_module import AIValidator
from query_module import NaturalLanguageQueryEngine

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cmdb.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CMDBTool:
    """Clase principal que coordina toda la funcionalidad de CMDB"""

    def __init__(self):
        """Inicializa la herramienta CMDB"""
        try:
            # Inicializar componentes
            self.db_connector = DatabaseConnector()
            self.scanner = RepositoryScanner(self.db_connector)
            self.ai_validator = AIValidator(db_connector=self.db_connector)
            self.query_engine = NaturalLanguageQueryEngine(db_connector=self.db_connector)

            logger.info("CMDB Tool inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar CMDB Tool: {e}")
            sys.exit(1)

    def setup_database(self) -> bool:
        """
        Configura la base de datos y crea las tablas necesarias

        Returns:
            bool: True si la configuración fue exitosa
        """
        logger.info("Configurando base de datos...")

        # Probar conexión
        if not self.db_connector.test_connection():
            logger.error("No se pudo conectar a la base de datos PostgreSQL")
            logger.error("Verifique las variables de entorno: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT")
            return False

        # Crear tablas
        if not self.db_connector.create_tables_if_not_exist():
            logger.error("No se pudieron crear las tablas de la base de datos")
            return False

        logger.info("Base de datos configurada correctamente")
        return True

    def scan_single_repository(self, url: str) -> Dict:
        """
        Escanea un único repositorio

        Args:
            url: URL del repositorio

        Returns:
            Dict: Resultado del escaneo
        """
        logger.info(f"Escaneando repositorio: {url}")

        try:
            # Escanear y almacenar repositorio
            success = self.scanner.scan_and_store_repository(url)

            if success:
                # Obtener datos del repositorio
                repo_data = self.db_connector.get_repository_by_url(url)

                if repo_data and not repo_data['is_identified']:
                    # Generar explicación mejorada con IA para repositorios no identificados
                    enhanced_explanation = self.ai_validator.generate_enhanced_explanation(repo_data)

                    # Actualizar explicación en la base de datos
                    self.db_connector.insert_repository(
                        url=repo_data['url'],
                        owner_name=repo_data['owner_name'],
                        repo_name=repo_data['repo_name'],
                        technologies=repo_data['technologies'],
                        is_identified=repo_data['is_identified'],
                        status=repo_data['status'],
                        ai_explanation=enhanced_explanation
                    )

                    repo_data['ai_explanation'] = enhanced_explanation

                return {
                    'success': True,
                    'repository': repo_data,
                    'message': 'Repositorio escaneado y almacenado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'Error al escanear o almacenar el repositorio'
                }

        except Exception as e:
            logger.error(f"Error al escanear repositorio {url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def scan_multiple_repositories(self, urls: List[str]) -> Dict:
        """
        Escanea múltiples repositorios en lote

        Args:
            urls: Lista de URLs de repositorios

        Returns:
            Dict: Resultados del escaneo en lote
        """
        logger.info(f"Iniciando escaneo en lote de {len(urls)} repositorios")

        try:
            results = self.scanner.batch_scan_repositories(urls)

            # Procesar repositorios no identificados con IA
            unidentified_repos = self.db_connector.get_unidentified_repositories()

            for repo in unidentified_repos:
                if repo['url'] in urls:  # Solo procesar los que acabamos de escanear
                    enhanced_explanation = self.ai_validator.generate_enhanced_explanation(repo)

                    # Actualizar explicación
                    self.db_connector.insert_repository(
                        url=repo['url'],
                        owner_name=repo['owner_name'],
                        repo_name=repo['repo_name'],
                        technologies=repo['technologies'],
                        is_identified=repo['is_identified'],
                        status=repo['status'],
                        ai_explanation=enhanced_explanation
                    )

            return {
                'success': True,
                'results': results,
                'total_processed': len(urls),
                'successful': sum(1 for r in results.values() if r.get('success', False)),
                'failed': sum(1 for r in results.values() if not r.get('success', False))
            }

        except Exception as e:
            logger.error(f"Error en escaneo en lote: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def query_database(self, query: str) -> Dict:
        """
        Realiza una consulta en lenguaje natural a la base de datos

        Args:
            query: Consulta en lenguaje natural

        Returns:
            Dict: Resultado de la consulta
        """
        logger.info(f"Procesando consulta: {query}")

        try:
            result = self.query_engine.process_natural_language_query(query)
            return result
        except Exception as e:
            logger.error(f"Error al procesar consulta: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_repository_summary(self, url: str) -> Dict:
        """
        Obtiene un resumen detallado de un repositorio

        Args:
            url: URL del repositorio

        Returns:
            Dict: Resumen del repositorio
        """
        try:
            repo_data = self.db_connector.get_repository_by_url(url)

            if not repo_data:
                return {
                    'success': False,
                    'error': 'Repositorio no encontrado en la base de datos'
                }

            # Generar resumen con IA
            summary = self.ai_validator.generate_repository_summary(repo_data)

            # Validar completitud
            validation = self.ai_validator.validate_repository_completeness(repo_data)

            return {
                'success': True,
                'repository': repo_data,
                'summary': summary,
                'validation': validation
            }

        except Exception as e:
            logger.error(f"Error al obtener resumen del repositorio: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas generales de la base de datos

        Returns:
            Dict: Estadísticas del sistema
        """
        try:
            all_repos = self.db_connector.get_all_repositories()
            analysis = self.ai_validator.analyze_repository_patterns(all_repos)

            return {
                'success': True,
                'statistics': analysis,
                'sample_repositories': all_repos[:5]  # Muestra de 5 repositorios
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def export_data(self, format: str = 'json', filename: str = None) -> Dict:
        """
        Exporta los datos de la base de datos

        Args:
            format: Formato de exportación ('json' o 'csv')
            filename: Nombre del archivo de salida

        Returns:
            Dict: Resultado de la exportación
        """
        try:
            all_repos = self.db_connector.get_all_repositories()

            if not filename:
                filename = f"cmdb_export.{format}"

            if format.lower() == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(all_repos, f, indent=2, ensure_ascii=False, default=str)

            elif format.lower() == 'csv':
                import csv

                if all_repos:
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=all_repos[0].keys())
                        writer.writeheader()
                        for repo in all_repos:
                            # Convertir listas a strings para CSV
                            row = repo.copy()
                            if 'technologies' in row and isinstance(row['technologies'], list):
                                row['technologies'] = ', '.join(row['technologies'])
                            writer.writerow(row)

            return {
                'success': True,
                'filename': filename,
                'format': format,
                'records_exported': len(all_repos)
            }

        except Exception as e:
            logger.error(f"Error al exportar datos: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def ask_open_question(self, question: str, context: str = None) -> str:
        """
        Permite hacer preguntas abiertas sobre la CMDB usando LLM.
        Args:
            question (str): Pregunta en lenguaje natural.
            context (str, optional): Contexto adicional.
        Returns:
            str: Respuesta generada por IA.
        """
        return self.query_engine.ask_open_question(question, context)

    def summarize_results(self, results_json: str, question: str = None) -> str:
        """
        Resume resultados de una consulta usando LLM.
        Args:
            results_json (str): Resultados en formato JSON.
            question (str, optional): Pregunta original.
        Returns:
            str: Resumen generado por IA.
        """
        try:
            import json
            results = json.loads(results_json)
        except Exception as e:
            logger.error(f"Error al parsear resultados: {e}")
            return "Formato de resultados inválido. Debe ser JSON."
        return self.query_engine.summarize_results(results, question)

def main():
    """Función principal del programa"""
    parser = argparse.ArgumentParser(
        description='Herramienta CMDB con capacidades de IA para análisis de repositorios Git'
    )

    parser.add_argument('--setup-db', action='store_true',
                       help='Configurar base de datos y crear tablas')

    parser.add_argument('--scan', type=str,
                       help='Escanear un repositorio individual (URL)')

    parser.add_argument('--scan-batch', type=str,
                       help='Escanear múltiples repositorios desde archivo (una URL por línea)')

    parser.add_argument('--query', type=str,
                       help='Realizar consulta en lenguaje natural')

    parser.add_argument('--summary', type=str,
                       help='Obtener resumen de repositorio (URL)')

    parser.add_argument('--stats', action='store_true',
                       help='Mostrar estadísticas del sistema')

    parser.add_argument('--export', type=str, choices=['json', 'csv'],
                       help='Exportar datos en formato especificado')

    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para consultas')

    args = parser.parse_args()

    # Inicializar herramienta CMDB
    cmdb = CMDBTool()

    # Configurar base de datos si se solicita
    if args.setup_db:
        if cmdb.setup_database():
            print("✅ Base de datos configurada correctamente")
        else:
            print("❌ Error al configurar la base de datos")
            sys.exit(1)
        return

    # Escanear repositorio individual
    if args.scan:
        result = cmdb.scan_single_repository(args.scan)
        if result['success']:
            print(f"✅ Repositorio escaneado: {args.scan}")
            repo = result['repository']
            print(f"   Propietario: {repo['owner_name']}")
            print(f"   Tecnologías: {', '.join(repo['technologies']) if repo['technologies'] else 'No identificadas'}")
            print(f"   Estado: {repo['status']}")
        else:
            print(f"❌ Error al escanear repositorio: {result.get('error', 'Error desconocido')}")
        return

    # Escanear múltiples repositorios
    if args.scan_batch:
        try:
            with open(args.scan_batch, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]

            result = cmdb.scan_multiple_repositories(urls)
            if result['success']:
                print(f"✅ Escaneo en lote completado:")
                print(f"   Total procesados: {result['total_processed']}")
                print(f"   Exitosos: {result['successful']}")
                print(f"   Fallidos: {result['failed']}")
            else:
                print(f"❌ Error en escaneo en lote: {result.get('error', 'Error desconocido')}")
        except FileNotFoundError:
            print(f"❌ Archivo no encontrado: {args.scan_batch}")
        return

    # Realizar consulta
    if args.query:
        result = cmdb.query_database(args.query)
        if result['success']:
            print(f"✅ Consulta: {args.query}")
            print(f"   {result.get('explanation', 'Sin explicación')}")

            if result.get('results'):
                print(f"\nResultados ({result.get('count', 0)}):")
                for i, item in enumerate(result['results'][:10], 1):  # Mostrar hasta 10 resultados
                    if isinstance(item, dict):
                        if 'repo_name' in item:
                            print(f"   {i}. {item.get('owner_name', 'N/A')}/{item.get('repo_name', 'N/A')}")
                        else:
                            print(f"   {i}. {item}")
                    else:
                        print(f"   {i}. {item}")
        else:
            print(f"❌ Error en consulta: {result.get('error', 'Error desconocido')}")
        return

    # Obtener resumen
    if args.summary:
        result = cmdb.get_repository_summary(args.summary)
        if result['success']:
            print(f"✅ Resumen del repositorio: {args.summary}")
            print(f"\n{result['summary']}")

            validation = result.get('validation', {})
            print(f"\nValidación de completitud: {validation.get('percentage', 0):.1f}%")
        else:
            print(f"❌ Error al obtener resumen: {result.get('error', 'Error desconocido')}")
        return

    # Mostrar estadísticas
    if args.stats:
        result = cmdb.get_statistics()
        if result['success']:
            stats = result['statistics']
            print("📊 Estadísticas del sistema CMDB:")
            print(f"   Total de repositorios: {stats['total_repositories']}")
            print(f"   Repositorios identificados: {stats['identified_repositories']}")
            print(f"   Tasa de identificación: {stats['identification_rate']:.1f}%")

            if stats['most_common_technologies']:
                print(f"\nTecnologías más comunes:")
                for tech, count in stats['most_common_technologies'][:5]:
                    print(f"   {tech}: {count}")
        else:
            print(f"❌ Error al obtener estadísticas: {result.get('error', 'Error desconocido')}")
        return

    # Exportar datos
    if args.export:
        result = cmdb.export_data(args.export)
        if result['success']:
            print(f"✅ Datos exportados a: {result['filename']}")
            print(f"   Formato: {result['format']}")
            print(f"   Registros: {result['records_exported']}")
        else:
            print(f"❌ Error al exportar: {result.get('error', 'Error desconocido')}")
        return

    # Modo interactivo
    if args.interactive:
        print("🤖 Modo interactivo CMDB - Escribe 'quit' para salir")
        print("Ejemplos de consultas:")
        for example in cmdb.query_engine.get_suggested_queries()[:3]:
            print(f"   • {example}")
        print()

        while True:
            try:
                query = input("CMDB> ").strip()
                if query.lower() in ['quit', 'exit', 'salir']:
                    break

                if query:
                    result = cmdb.query_database(query)
                    if result['success']:
                        print(f"✅ {result.get('explanation', 'Consulta procesada')}")

                        if result.get('results'):
                            for i, item in enumerate(result['results'][:5], 1):
                                if isinstance(item, dict):
                                    if 'repo_name' in item:
                                        print(f"   {i}. {item.get('owner_name')}/{item.get('repo_name')}")
                                    else:
                                        print(f"   {i}. {list(item.values())}")
                    else:
                        print(f"❌ {result.get('error', 'Error en consulta')}")
                    print()

            except KeyboardInterrupt:
                print("\n¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        return

    # Si no se especifica ninguna acción, mostrar ayuda
    parser.print_help()

if __name__ == "__main__":
    main()
