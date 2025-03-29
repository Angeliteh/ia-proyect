#!/usr/bin/env python
"""
Script para probar directamente la API de Brave Search sin usar MCP.
Este script nos ayudará a diagnosticar problemas con la API.
"""

import os
import sys
import requests
import json
import argparse
import logging
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('brave_api_test.log'),
        logging.StreamHandler()
    ]
)

# Configuración básica
BASE_URL = "https://api.search.brave.com/res/v1/web"
USER_AGENT = "BraveSearchTest/1.0"

def test_search_api(api_key, query="inteligencia artificial", count=5, offset=0):
    """Prueba directa de la API de búsqueda web de Brave Search."""
    logging.info(f"Probando API de búsqueda web con query: '{query}'")
    
    # Configurar headers
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
        "User-Agent": USER_AGENT
    }
    
    # Configurar parámetros
    params = {
        "q": query,
        "count": count,
        "offset": offset,
        "country": "US",
        "search_lang": "es"
    }
    
    # Realizar solicitud
    logging.info(f"URL: {BASE_URL}/search")
    logging.info(f"Parámetros: {params}")
    logging.info(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'X-Subscription-Token'})}")
    logging.info(f"API Key (primeros 4 caracteres): {api_key[:4]}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=30
        )
        
        logging.info(f"Código de estado: {response.status_code}")
        logging.info(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logging.info("Respuesta JSON válida recibida")
                
                # Verificar si hay resultados web
                if "web" in result and "results" in result["web"]:
                    web_results = result["web"]["results"]
                    logging.info(f"Resultados web encontrados: {len(web_results)}")
                    
                    # Mostrar los primeros resultados
                    for i, item in enumerate(web_results[:3], 1):
                        logging.info(f"\nResultado {i}:")
                        logging.info(f"  Título: {item.get('title', 'N/A')}")
                        logging.info(f"  URL: {item.get('url', 'N/A')}")
                        logging.info(f"  Descripción: {item.get('description', 'N/A')[:100]}...")
                else:
                    logging.info("No se encontraron resultados web en la respuesta")
                    logging.info(f"Estructura de respuesta: {json.dumps(result, indent=2)[:500]}...")
            except json.JSONDecodeError as e:
                logging.error(f"Error al decodificar JSON: {e}")
                logging.error(f"Contenido de la respuesta: {response.text[:500]}...")
        else:
            logging.error(f"Error HTTP: {response.status_code}")
            logging.error(f"Contenido de la respuesta: {response.text[:500]}...")
            
    except Exception as e:
        logging.error(f"Error al realizar la solicitud: {e}")

def test_places_api(api_key, query="restaurantes en Madrid", count=5):
    """Prueba directa de la API de búsqueda local de Brave Search."""
    logging.info(f"\nProbando API de búsqueda local con query: '{query}'")
    
    # Configurar headers
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
        "User-Agent": USER_AGENT
    }
    
    # Configurar parámetros
    params = {
        "q": query,
        "count": count,
        "country": "ES",  # España para una búsqueda en Madrid
        "search_lang": "es"
    }
    
    # Realizar solicitud
    logging.info(f"URL: {BASE_URL}/search")
    logging.info(f"Parámetros: {params}")
    logging.info(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'X-Subscription-Token'})}")
    logging.info(f"API Key (primeros 4 caracteres): {api_key[:4]}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=30
        )
        
        logging.info(f"Código de estado: {response.status_code}")
        logging.info(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logging.info("Respuesta JSON válida recibida")
                
                # Verificar si hay resultados de lugares
                if "places" in result and "results" in result["places"]:
                    places_results = result["places"]["results"]
                    logging.info(f"Resultados locales encontrados: {len(places_results)}")
                    
                    # Mostrar los primeros resultados
                    for i, item in enumerate(places_results[:3], 1):
                        logging.info(f"\nResultado {i}:")
                        logging.info(f"  Nombre: {item.get('name', 'N/A')}")
                        logging.info(f"  Dirección: {item.get('addr', 'N/A')}")
                        logging.info(f"  Tipo: {item.get('type', 'N/A')}")
                        if "rating" in item:
                            logging.info(f"  Valoración: {item['rating']}")
                        if "distance" in item:
                            logging.info(f"  Distancia: {item['distance']} km")
                else:
                    logging.info("No se encontraron resultados locales en la respuesta")
                    logging.info(f"Estructura de respuesta: {json.dumps(result, indent=2)[:500]}...")
            except json.JSONDecodeError as e:
                logging.error(f"Error al decodificar JSON: {e}")
                logging.error(f"Contenido de la respuesta: {response.text[:500]}...")
        else:
            logging.error(f"Error HTTP: {response.status_code}")
            logging.error(f"Contenido de la respuesta: {response.text[:500]}...")
            
    except Exception as e:
        logging.error(f"Error al realizar la solicitud: {e}")

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Prueba directa de la API de Brave Search")
    parser.add_argument("--api-key", help="API key para Brave Search")
    parser.add_argument("--test", choices=["web", "local", "both"], default="both",
                      help="Tipo de prueba a realizar (web, local o ambas)")
    parser.add_argument("--query-web", default="inteligencia artificial",
                      help="Consulta para búsqueda web")
    parser.add_argument("--query-local", default="restaurantes en Madrid",
                      help="Consulta para búsqueda local")
    args = parser.parse_args()
    
    # Cargar variables de entorno para API keys
    load_dotenv()
    
    # Obtener API key de argumentos o variables de entorno
    api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    
    if not api_key:
        logging.error("No se ha proporcionado una API key para Brave Search. Use --api-key o defina BRAVE_API_KEY")
        sys.exit(1)
    
    logging.info("=== PRUEBA DIRECTA DE BRAVE SEARCH API ===")
    
    # Ejecutar pruebas según lo solicitado
    if args.test in ["web", "both"]:
        test_search_api(api_key, args.query_web)
    
    if args.test in ["local", "both"]:
        test_places_api(api_key, args.query_local)
    
    logging.info("\n=== PRUEBA FINALIZADA ===")

if __name__ == "__main__":
    main() 