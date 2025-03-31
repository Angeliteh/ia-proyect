#!/usr/bin/env python
"""
CLI para iniciar el servidor SQLite MCP.

Este script permite iniciar el servidor SQLite MCP desde la línea de comandos
con diferentes opciones de configuración.
"""

import os
import sys
import argparse
import asyncio
import logging
import signal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("sqlite_mcp_cli")

# Añadir el directorio padre al path
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from mcp.core.init import initialize_mcp, shutdown_mcp
from mcp_servers.sqlite.sqlite_server import SQLiteMCPServer, run_http_server

def signal_handler(sig, frame):
    """Manejador de señales para detener el servidor correctamente."""
    logger.info("Señal de interrupción recibida. Deteniendo servidor...")
    asyncio.create_task(shutdown_mcp())
    sys.exit(0)

async def run_server(args):
    """Iniciar el servidor con los argumentos proporcionados."""
    # Inicializar MCP
    initialize_mcp()
    
    # Crear directorio de BD si no existe
    if not os.path.exists(args.db_path):
        os.makedirs(args.db_path, exist_ok=True)
        logger.info(f"Directorio de bases de datos creado: {args.db_path}")
    else:
        logger.info(f"Usando directorio de bases de datos: {args.db_path}")
        
    # Iniciar servidor HTTP
    logger.info(f"Iniciando servidor SQLite MCP en {args.host}:{args.port}...")
    
    try:
        http_server, port = run_http_server(
            host=args.host,
            port=args.port,
            db_path=args.db_path
        )
        
        # Configurar manejador de señales
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info(f"Servidor SQLite MCP iniciado en http://{args.host}:{port}")
        logger.info("Presiona Ctrl+C para detener el servidor")
        
        # Mantener el servidor en ejecución
        while True:
            await asyncio.sleep(3600)  # Esperar indefinidamente
            
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
    finally:
        # Asegurarse de cerrar MCP correctamente
        await shutdown_mcp()
        logger.info("Servidor SQLite MCP detenido")

def main():
    """Función principal del CLI."""
    parser = argparse.ArgumentParser(description="Servidor MCP para SQLite")
    
    # Opciones del servidor
    parser.add_argument('--host', default='localhost',
                      help='Dirección IP para el servidor (por defecto: localhost)')
    parser.add_argument('--port', type=int, default=8080,
                      help='Puerto para el servidor (por defecto: 8080)')
    parser.add_argument('--db-path', dest='db_path', default='./sqlite_dbs',
                      help='Ruta al directorio de bases de datos SQLite (por defecto: ./sqlite_dbs)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO', help='Nivel de logging (por defecto: INFO)')
    
    # Analizar argumentos
    args = parser.parse_args()
    
    # Configurar nivel de log
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Normalizar ruta de bases de datos
    args.db_path = os.path.abspath(args.db_path)
    
    # Iniciar servidor
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en la aplicación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 