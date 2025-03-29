"""
Servidor MCP para bases de datos SQLite.

Este módulo implementa un servidor MCP que permite acceder
y manipular bases de datos SQLite a través del protocolo MCP.
"""

import os
import sqlite3
import logging
import json
import time
import re
import threading
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler

# Importar componentes MCP
from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPErrorCode
from mcp.core.server_base import MCPServerBase

# Configurar logging
logger = logging.getLogger("mcp.server.sqlite")

class SQLiteMCPServer(MCPServerBase):
    """
    Servidor MCP para bases de datos SQLite.
    
    Este servidor permite acceder y manipular bases de datos SQLite
    a través del protocolo MCP, exponiendo operaciones como consultas,
    inserciones, actualizaciones y eliminaciones.
    
    Attributes:
        name: Nombre del servidor
        description: Descripción del servidor
        db_path: Ruta al directorio donde se almacenan las bases de datos
        connections: Diccionario de conexiones activas a bases de datos
    """
    
    def __init__(
        self, 
        name: str = "sqlite_server",
        description: str = "Servidor MCP para bases de datos SQLite",
        db_path: Optional[str] = None
    ):
        """
        Inicializa el servidor SQLite MCP.
        
        Args:
            name: Nombre del servidor
            description: Descripción del servidor
            db_path: Ruta al directorio donde se almacenan las bases de datos
                    (por defecto es el directorio 'data' en la raíz del proyecto)
        """
        # Definir acciones soportadas
        supported_actions = [
            MCPAction.PING,
            MCPAction.CAPABILITIES,
            MCPAction.GET,
            MCPAction.SEARCH,
            MCPAction.CREATE,
            MCPAction.UPDATE,
            MCPAction.DELETE,
            MCPAction.LIST
        ]
        
        # Definir recursos soportados
        supported_resources = [
            MCPResource.SYSTEM,
            "database",
            "table",
            "query"
        ]
        
        # Inicializar clase base
        super().__init__(
            name=name,
            description=description,
            supported_actions=supported_actions,
            supported_resources=supported_resources
        )
        
        # Configurar ruta de bases de datos
        if db_path:
            self.db_path = db_path
        else:
            # Por defecto, usar el directorio 'data' en la raíz del proyecto
            self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "data"))
        
        # Crear el directorio si no existe
        os.makedirs(self.db_path, exist_ok=True)
        
        # Diccionario para almacenar conexiones activas
        self.connections = {}
        
        logger.info(f"Servidor SQLite MCP inicializado. Directorio de bases de datos: {self.db_path}")
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una acción del protocolo MCP.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta MCPResponse con el resultado de la acción
        """
        try:
            # Verificar la acción
            if message.action == MCPAction.PING.value:
                return await self.handle_ping(message)
            
            elif message.action == MCPAction.CAPABILITIES.value:
                return await self.handle_capabilities(message)
            
            elif message.action == MCPAction.GET.value:
                return await self._handle_get(message)
            
            elif message.action == MCPAction.SEARCH.value:
                return await self._handle_search(message)
            
            elif message.action == MCPAction.CREATE.value:
                return await self._handle_create(message)
            
            elif message.action == MCPAction.UPDATE.value:
                return await self._handle_update(message)
            
            elif message.action == MCPAction.DELETE.value:
                return await self._handle_delete(message)
            
            elif message.action == MCPAction.LIST.value:
                return await self._handle_list(message)
            
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_ACTION,
                    message=f"Acción no soportada: {message.action}"
                )
        
        except Exception as e:
            logger.error(f"Error manejando mensaje: {e}", exc_info=True)
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error interno del servidor: {str(e)}"
            )
    
    async def _handle_get(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud GET.
        
        Args:
            message: Mensaje MCP con la acción GET
            
        Returns:
            Respuesta MCPResponse con los datos solicitados
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Obtener información sobre una base de datos
        if resource_type == "database":
            return await self._get_database_info(message)
        
        # Obtener información sobre una tabla
        elif resource_type == "table":
            return await self._get_table_info(message)
        
        # Obtener un registro específico
        elif resource_type == "query":
            return await self._execute_query(message, query_type="get")
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para GET: {resource_type}"
            )
    
    async def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud SEARCH.
        
        Args:
            message: Mensaje MCP con la acción SEARCH
            
        Returns:
            Respuesta MCPResponse con los resultados de la búsqueda
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        if resource_type == "database":
            # Buscar bases de datos
            return await self._search_databases(message)
        
        elif resource_type == "table":
            # Buscar tablas o registros en tablas
            return await self._search_tables(message)
        
        elif resource_type == "query":
            # Ejecutar consulta SQL directa
            return await self._execute_query(message, query_type="search")
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para SEARCH: {resource_type}"
            )
    
    async def _handle_create(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud CREATE.
        
        Args:
            message: Mensaje MCP con la acción CREATE
            
        Returns:
            Respuesta MCPResponse con el resultado de la creación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        if resource_type == "database":
            # Crear una base de datos
            return await self._create_database(message)
        
        elif resource_type == "table":
            # Crear una tabla
            return await self._create_table(message)
        
        elif resource_type == "query":
            # Ejecutar consulta de creación
            return await self._execute_query(message, query_type="create")
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para CREATE: {resource_type}"
            )
    
    async def _handle_update(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud UPDATE.
        
        Args:
            message: Mensaje MCP con la acción UPDATE
            
        Returns:
            Respuesta MCPResponse con el resultado de la actualización
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        if resource_type == "table":
            # Actualizar registros en una tabla
            return await self._update_table_data(message)
        
        elif resource_type == "query":
            # Ejecutar consulta de actualización
            return await self._execute_query(message, query_type="update")
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para UPDATE: {resource_type}"
            )
    
    async def _handle_delete(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud DELETE.
        
        Args:
            message: Mensaje MCP con la acción DELETE
            
        Returns:
            Respuesta MCPResponse con el resultado de la eliminación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        if resource_type == "database":
            # Eliminar una base de datos
            return await self._delete_database(message.data.get("db_name"))
        
        elif resource_type == "table":
            # Eliminar una tabla o registros de una tabla
            return await self._delete_table(message.data.get("db_name"), message.data.get("table_name"))
        
        elif resource_type == "query":
            # Ejecutar consulta de eliminación
            return await self._execute_query(message, query_type="delete")
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para DELETE: {resource_type}"
            )
    
    async def _handle_list(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una solicitud LIST.
        
        Args:
            message: Mensaje MCP con la acción LIST
            
        Returns:
            Respuesta MCPResponse con la lista de recursos
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        if resource_type == "database":
            # Listar bases de datos
            return await self._list_databases(message)
        
        elif resource_type == "table":
            # Listar tablas o registros en tablas
            return await self._list_tables(message)
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_RESOURCE,
                message=f"Tipo de recurso no soportado para LIST: {resource_type}"
            )
    
    # -----------------------------------------------------------------
    # Métodos de utilidad para operaciones con la base de datos
    # -----------------------------------------------------------------
    
    def _get_db_path(self, db_name: str) -> str:
        """
        Obtiene la ruta completa a una base de datos.
        
        Args:
            db_name: Nombre de la base de datos
            
        Returns:
            Ruta completa a la base de datos
        """
        # Asegurar que el nombre de la base de datos termine en .db
        if not db_name.endswith(".db"):
            db_name = f"{db_name}.db"
        
        # Construir ruta completa
        return os.path.join(self.db_path, db_name)
    
    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """
        Obtiene una conexión a una base de datos SQLite.
        
        Args:
            db_path: Ruta a la base de datos
            
        Returns:
            Conexión a la base de datos
            
        Raises:
            FileNotFoundError: Si la base de datos no existe
            sqlite3.Error: Si hay un error al conectar con la base de datos
        """
        # Verificar si la base de datos existe
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {db_path}")
        
        # Verificar si ya hay una conexión abierta
        if db_path in self.connections:
            return self.connections[db_path]
        
        # Crear una nueva conexión
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
        
        # Guardar la conexión
        self.connections[db_path] = connection
        
        return connection
    
    def _close_connection(self, db_path: str) -> None:
        """
        Cierra una conexión a una base de datos.
        
        Args:
            db_path: Ruta a la base de datos
        """
        if db_path in self.connections:
            try:
                self.connections[db_path].close()
            except Exception as e:
                logger.warning(f"Error al cerrar conexión a {db_path}: {e}")
            finally:
                del self.connections[db_path]
    
    def _sanitize_sql(self, sql: str) -> str:
        """
        Sanitiza una consulta SQL para prevenir inyecciones.
        
        Args:
            sql: Consulta SQL a sanitizar
            
        Returns:
            Consulta SQL sanitizada
            
        Note:
            Esta función proporciona una sanitización básica. Para una
            prevención completa de inyecciones SQL, se deben usar
            consultas parametrizadas.
        """
        # Eliminar comentarios
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        # Eliminar comandos peligrosos
        dangerous_commands = [
            r'\bDROP\s+DATABASE\b',
            r'\bDROP\s+TABLE\b',
            r'\bALTER\s+DATABASE\b',
            r'\bSYSTEM\b',
            r'\bDELETE\s+FROM\b\s+WITHOUT\s+WHERE',
            r'\bUPDATE\b\s+WITHOUT\s+WHERE'
        ]
        
        for command in dangerous_commands:
            if re.search(command, sql, re.IGNORECASE):
                raise ValueError(f"Comando SQL no permitido detectado: {command}")
        
        return sql
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza un nombre de archivo para prevenir inyecciones de ruta.
        
        Args:
            filename: Nombre de archivo a sanitizar
            
        Returns:
            Nombre de archivo sanitizado
        """
        # Eliminar caracteres no permitidos en nombres de archivo
        sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # Eliminar rutas relativas o absolutas
        sanitized = os.path.basename(sanitized)
        
        # Limitar a 255 caracteres (máximo típico en sistemas de archivos)
        if len(sanitized) > 255:
            # Truncar conservando extensión si existe
            base, ext = os.path.splitext(sanitized)
            max_base_len = 255 - len(ext)
            sanitized = base[:max_base_len] + ext
        
        return sanitized
    
    def _execute_safe_query(
        self, 
        connection: sqlite3.Connection, 
        query: str, 
        params: Optional[tuple] = None,
        fetch_type: str = "all"
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], int]:
        """
        Ejecuta una consulta SQL de forma segura.
        
        Args:
            connection: Conexión a la base de datos
            query: Consulta SQL a ejecutar
            params: Parámetros para la consulta
            fetch_type: Tipo de fetch a realizar (all, one, rowcount)
            
        Returns:
            Resultados de la consulta según el tipo de fetch
            
        Raises:
            sqlite3.Error: Si hay un error al ejecutar la consulta
        """
        cursor = connection.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_type == "all":
                # Convertir los resultados a diccionarios
                columns = [col[0] for col in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            elif fetch_type == "one":
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
                return None
            
            elif fetch_type == "rowcount":
                connection.commit()
                return cursor.rowcount
            
            else:
                raise ValueError(f"Tipo de fetch no válido: {fetch_type}")
        
        except sqlite3.Error as e:
            connection.rollback()
            raise e
        
        finally:
            cursor.close()
    
    # -----------------------------------------------------------------
    # Implementación de operaciones específicas
    # -----------------------------------------------------------------
    
    async def _get_database_info(self, message: MCPMessage) -> MCPResponse:
        """
        Obtiene información sobre una base de datos.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta con información de la base de datos
        """
        # Obtener el nombre de la base de datos de la ruta del recurso
        parts = message.resource_path.strip("/").split("/")
        if not parts or not parts[0]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos"
            )
        
        db_name = parts[0]
        db_path = self._get_db_path(db_name)
        
        try:
            # Verificar si la base de datos existe
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Base de datos no encontrada: {db_name}"
                )
            
            # Obtener conexión
            connection = self._get_connection(db_path)
            
            # Obtener lista de tablas
            tables = self._execute_safe_query(
                connection,
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                fetch_type="all"
            )
            
            # Obtener estadísticas de la base de datos
            file_size = os.path.getsize(db_path)
            
            # Construir respuesta
            db_info = {
                "name": db_name,
                "path": db_path,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "tables": [table["name"] for table in tables],
                "tables_count": len(tables),
                "last_modified": time.ctime(os.path.getmtime(db_path))
            }
            
            return MCPResponse.success_response(
                message_id=message.id,
                data=db_info
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo información de la base de datos {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error obteniendo información de la base de datos: {str(e)}"
            )
    
    async def _get_table_info(self, message: MCPMessage) -> MCPResponse:
        """
        Obtiene información sobre una tabla.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta con información de la tabla
        """
        # Analizar la ruta del recurso
        parts = message.resource_path.strip("/").split("/")
        if len(parts) < 2:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos y la tabla"
            )
        
        db_name = parts[0]
        table_name = parts[1]
        db_path = self._get_db_path(db_name)
        
        try:
            # Verificar si la base de datos existe
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Base de datos no encontrada: {db_name}"
                )
            
            # Obtener conexión
            connection = self._get_connection(db_path)
            
            # Verificar si la tabla existe
            table_exists = self._execute_safe_query(
                connection,
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
                fetch_type="one"
            )
            
            if not table_exists:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Tabla no encontrada: {table_name}"
                )
            
            # Obtener información de columnas
            columns = self._execute_safe_query(
                connection,
                f"PRAGMA table_info({table_name})",
                fetch_type="all"
            )
            
            # Obtener conteo de registros
            row_count = self._execute_safe_query(
                connection,
                f"SELECT COUNT(*) as count FROM {table_name}",
                fetch_type="one"
            )
            
            # Construir información de la tabla
            table_info = {
                "name": table_name,
                "columns": columns,
                "row_count": row_count["count"],
                "database": db_name
            }
            
            return MCPResponse.success_response(
                message_id=message.id,
                data=table_info
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo información de la tabla {table_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error obteniendo información de la tabla: {str(e)}"
            )
    
    async def _execute_query(self, message: MCPMessage, query_type: str) -> MCPResponse:
        """
        Ejecuta una consulta SQL.
        
        Args:
            message: Mensaje MCP con la solicitud
            query_type: Tipo de consulta (get, search, create, update, delete)
            
        Returns:
            Respuesta con los resultados de la consulta
        """
        data = message.data or {}
        
        # Obtener parámetros
        db_name = data.get("db_name")
        sql = data.get("query")
        params = data.get("params", [])
        
        # Validar parámetros
        if not db_name:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos"
            )
        
        if not sql:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere la consulta SQL"
            )
        
        db_path = self._get_db_path(db_name)
        
        try:
            # Verificar si la base de datos existe
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Base de datos no encontrada: {db_name}"
                )
            
            # Sanitizar la consulta SQL
            try:
                sql = self._sanitize_sql(sql)
            except ValueError as e:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message=str(e)
                )
            
            # Obtener conexión
            connection = self._get_connection(db_path)
            
            # Ejecutar la consulta según el tipo
            if query_type in ["get", "search"]:
                results = self._execute_safe_query(
                    connection,
                    sql,
                    tuple(params) if params else None,
                    fetch_type="all"
                )
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "results": results,
                        "count": len(results)
                    }
                )
                
            elif query_type in ["create", "update", "delete"]:
                affected_rows = self._execute_safe_query(
                    connection,
                    sql,
                    tuple(params) if params else None,
                    fetch_type="rowcount"
                )
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "affected_rows": affected_rows,
                        "success": True
                    }
                )
            
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message=f"Tipo de consulta no válido: {query_type}"
                )
            
        except sqlite3.Error as e:
            logger.error(f"Error SQL en {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.DB_ERROR,
                message=f"Error en la consulta SQL: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando consulta en {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error al ejecutar la consulta: {str(e)}"
            )
    
    async def _list_databases(self, message: MCPMessage) -> MCPResponse:
        """
        Lista las bases de datos disponibles.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta con la lista de bases de datos
        """
        try:
            # Obtener todas las bases de datos del directorio
            db_files = [f for f in os.listdir(self.db_path) if f.endswith(".db")]
            
            # Construir información de cada base de datos
            databases = []
            
            for db_file in db_files:
                db_path = os.path.join(self.db_path, db_file)
                
                try:
                    # Obtener información básica del archivo
                    file_size = os.path.getsize(db_path)
                    mod_time = os.path.getmtime(db_path)
                    
                    # Intentar obtener el número de tablas
                    try:
                        connection = self._get_connection(db_path)
                        tables = self._execute_safe_query(
                            connection,
                            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                            fetch_type="all"
                        )
                        tables_count = len(tables)
                    except Exception:
                        tables_count = None
                    
                    # Agregar información de la base de datos
                    databases.append({
                        "name": db_file,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "last_modified": time.ctime(mod_time),
                        "tables_count": tables_count
                    })
                    
                except Exception as e:
                    logger.warning(f"Error obteniendo información de {db_file}: {e}")
                    # Incluir información mínima
                    databases.append({
                        "name": db_file,
                        "error": str(e)
                    })
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "databases": databases,
                    "count": len(databases),
                    "db_path": self.db_path
                }
            )
            
        except Exception as e:
            logger.error(f"Error listando bases de datos: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error al listar bases de datos: {str(e)}"
            )
    
    async def _list_tables(self, message: MCPMessage) -> MCPResponse:
        """
        Lista las tablas de una base de datos.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta con la lista de tablas
        """
        # Analizar la ruta del recurso
        parts = message.resource_path.strip("/").split("/")
        if not parts or not parts[0]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos"
            )
        
        db_name = parts[0]
        db_path = self._get_db_path(db_name)
        
        try:
            # Verificar si la base de datos existe
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Base de datos no encontrada: {db_name}"
                )
            
            # Obtener conexión
            connection = self._get_connection(db_path)
            
            # Obtener lista de tablas
            tables = self._execute_safe_query(
                connection,
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                fetch_type="all"
            )
            
            # Construir información detallada de cada tabla
            table_details = []
            
            for table in tables:
                table_name = table["name"]
                
                # Obtener conteo de registros
                try:
                    row_count = self._execute_safe_query(
                        connection,
                        f"SELECT COUNT(*) as count FROM {table_name}",
                        fetch_type="one"
                    )
                    count = row_count["count"]
                except:
                    count = None
                
                # Obtener información de columnas
                try:
                    columns = self._execute_safe_query(
                        connection,
                        f"PRAGMA table_info({table_name})",
                        fetch_type="all"
                    )
                    columns_info = [
                        {
                            "name": col["name"],
                            "type": col["type"],
                            "is_primary_key": bool(col["pk"]),
                            "not_null": bool(col["notnull"])
                        }
                        for col in columns
                    ]
                except:
                    columns_info = []
                
                # Agregar información de la tabla
                table_details.append({
                    "name": table_name,
                    "row_count": count,
                    "columns_count": len(columns_info),
                    "columns": columns_info
                })
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "database": db_name,
                    "tables": table_details,
                    "count": len(table_details)
                }
            )
            
        except Exception as e:
            logger.error(f"Error listando tablas de {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error al listar tablas: {str(e)}"
            )
    
    async def _create_database(self, message: MCPMessage) -> MCPResponse:
        """
        Crea una nueva base de datos SQLite.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta indicando el resultado de la operación
        """
        data = message.data or {}
        db_name = data.get("db_name")
        
        if not db_name:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos"
            )
        
        # Sanitizar nombre
        db_name = self._sanitize_filename(db_name)
        db_path = self._get_db_path(db_name)
        
        try:
            # Verificar si la base de datos ya existe
            if os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message=f"La base de datos ya existe: {db_name}"
                )
            
            # Crear la base de datos (crear una conexión creará el archivo)
            connection = sqlite3.connect(db_path)
            connection.close()
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "success": True,
                    "database": db_name,
                    "path": db_path,
                    "message": f"Base de datos {db_name} creada correctamente"
                }
            )
            
        except Exception as e:
            logger.error(f"Error creando base de datos {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error al crear la base de datos: {str(e)}"
            )
    
    async def _create_table(self, message: MCPMessage) -> MCPResponse:
        """
        Crea una nueva tabla en una base de datos.
        
        Args:
            message: Mensaje MCP con la solicitud
            
        Returns:
            Respuesta con el resultado de la creación
        """
        # Analizar la ruta del recurso
        parts = message.resource_path.strip("/").split("/")
        if len(parts) < 2:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el nombre de la base de datos y la tabla"
            )
        
        db_name = parts[0]
        table_name = parts[1]
        db_path = self._get_db_path(db_name)
        
        # Obtener la definición de columnas
        data = message.data or {}
        columns = data.get("columns", [])
        
        if not columns:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere la definición de columnas"
            )
        
        try:
            # Verificar si la base de datos existe
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"Base de datos no encontrada: {db_name}"
                )
            
            # Obtener conexión
            connection = self._get_connection(db_path)
            
            # Verificar si la tabla ya existe
            table_exists = self._execute_safe_query(
                connection,
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
                fetch_type="one"
            )
            
            if table_exists:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_CONFLICT,
                    message=f"La tabla ya existe: {table_name}"
                )
            
            # Construir la sentencia SQL para crear la tabla
            column_defs = []
            
            for column in columns:
                name = column.get("name")
                col_type = column.get("type", "TEXT")
                primary_key = column.get("primary_key", False)
                not_null = column.get("not_null", False)
                
                if not name:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.INVALID_REQUEST,
                        message=f"Falta el nombre de la columna en la definición: {column}"
                    )
                
                # Construir definición de columna
                col_def = f"{name} {col_type}"
                
                if primary_key:
                    col_def += " PRIMARY KEY"
                
                if not_null:
                    col_def += " NOT NULL"
                
                column_defs.append(col_def)
            
            # Crear la tabla
            create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
            
            self._execute_safe_query(
                connection,
                create_sql,
                fetch_type="rowcount"
            )
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "success": True,
                    "database": db_name,
                    "table": table_name,
                    "message": f"Tabla {table_name} creada correctamente"
                }
            )
            
        except Exception as e:
            logger.error(f"Error creando tabla {table_name} en {db_name}: {e}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error al crear la tabla: {str(e)}"
            )

    async def _delete_database(self, db_name):
        """Elimina una base de datos."""
        if not db_name:
            return MCPResponse.error_response(
                message_id="",
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere nombre de base de datos"
            )
            
        db_path = self._get_db_path(db_name)
        
        try:
            if not os.path.exists(db_path):
                return MCPResponse.error_response(
                    message_id="",
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"La base de datos '{db_name}' no existe"
                )
                
            # Cerrar cualquier conexión abierta a la base de datos
            if db_path in self.connections:
                try:
                    self.connections[db_path].close()
                    del self.connections[db_path]
                except Exception:
                    pass
                    
            # Eliminar el archivo
            os.remove(db_path)
            
            return MCPResponse.success_response(
                message_id="",
                data={
                    "deleted": True,
                    "database": db_name
                }
            )
        except Exception as e:
            return MCPResponse.error_response(
                message_id="",
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error eliminando base de datos: {str(e)}"
            )

    async def _delete_table(self, db_name, table_name):
        """Elimina una tabla de una base de datos."""
        if not db_name or not table_name:
            return MCPResponse.error_response(
                message_id="",
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requieren nombre de base de datos y tabla"
            )
            
        # Verificar si la base de datos existe
        db_path = self._get_db_path(db_name)
        if not os.path.exists(db_path):
            return MCPResponse.error_response(
                message_id="",
                code=MCPErrorCode.NOT_FOUND,
                message=f"La base de datos '{db_name}' no existe"
            )
            
        try:
            # Verificar si la tabla existe
            conn = self._get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                return MCPResponse.error_response(
                    message_id="",
                    code=MCPErrorCode.NOT_FOUND,
                    message=f"La tabla '{table_name}' no existe en la base de datos '{db_name}'"
                )
                
            # Eliminar la tabla
            cursor.execute(f"DROP TABLE {table_name}")
            conn.commit()
            
            return MCPResponse.success_response(
                message_id="",
                data={
                    "deleted": True,
                    "database": db_name,
                    "table": table_name
                }
            )
        except Exception as e:
            return MCPResponse.error_response(
                message_id="",
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error eliminando tabla: {str(e)}"
            )

# Servidor HTTP para exponer el servidor MCP
class SQLiteHTTPHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para el servidor MCP de SQLite."""
    
    server_instance = None  # Instancia del servidor SQLite
    
    def _serialize_response(self, response):
        """Serializa una respuesta MCP a JSON."""
        return json.dumps(response.to_dict()).encode('utf-8')
    
    def _parse_request(self):
        """Parsea una solicitud HTTP a un mensaje MCP."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        if not body:
            return None
            
        try:
            data = json.loads(body)
            return MCPMessage.from_dict(data)
        except Exception as e:
            logger.error(f"Error al parsear solicitud: {e}")
            return None
    
    def _return_json(self, status_code, data):
        """Envía una respuesta JSON."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = json.dumps(data).encode('utf-8')
        self.wfile.write(response)
    
    def _return_error(self, status_code, message):
        """Envía una respuesta de error."""
        error_data = {
            "error": {
                "code": status_code,
                "message": message
            }
        }
        self._return_json(status_code, error_data)
    
    def do_POST(self):
        """Maneja solicitudes POST."""
        # Verificar si hay una instancia de servidor
        if not self.server_instance:
            self._return_error(500, "Servidor MCP no inicializado")
            return
            
        # Parsear la solicitud
        message = self._parse_request()
        if not message:
            self._return_error(400, "Solicitud inválida o mal formada")
            return
            
        try:
            # Procesar el mensaje con el servidor MCP
            import asyncio  # Importación necesaria aquí
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process():
                return await self.server_instance.process_message(message)
                
            response = loop.run_until_complete(process())
            loop.close()
            
            # Enviar la respuesta
            self._return_json(200, response.to_dict())
            
        except Exception as e:
            logger.error(f"Error procesando solicitud: {e}", exc_info=True)
            self._return_error(500, f"Error interno del servidor: {str(e)}")
    
    def do_GET(self):
        """Maneja solicitudes GET."""
        # Ruta para verificar estado del servidor
        if self.path == '/ping':
            self._return_json(200, {"status": "ok", "message": "Servidor SQLite MCP activo"})
        else:
            self._return_error(404, "Ruta no encontrada")
            
async def run_mcp_http_server(host="localhost", port=8080, db_path=None):
    """
    Ejecuta el servidor MCP para SQLite como un servidor HTTP.
    
    Args:
        host (str): Dirección de host para el servidor HTTP.
        port (int): Puerto para el servidor HTTP.
        db_path (str): Ruta al directorio de bases de datos SQLite.
        
    Returns:
        Objeto servidor HTTP.
    """
    from mcp.transport.http_server import start_http_server
    
    # Inicializar MCP si no se ha hecho
    from mcp.core.init import is_mcp_initialized, initialize_mcp, async_initialize_mcp
    if not is_mcp_initialized():
        await async_initialize_mcp()
    
    # Crear el servidor SQLite
    sqlite_server = SQLiteMCPServer(db_path=db_path)
    
    # Iniciar servidor HTTP con el servidor SQLite
    http_server, port = start_http_server(host=host, port=port, mcp_server=sqlite_server)
    
    logger.info(f"Servidor SQLite MCP ejecutándose en http://{host}:{port}")
    return http_server, port

def run_http_server(host="localhost", port=8080, db_path=None):
    """
    Versión sincrónica para iniciar el servidor HTTP.
    
    Args:
        host (str): Dirección de host para el servidor HTTP.
        port (int): Puerto para el servidor HTTP.
        db_path (str): Ruta al directorio de bases de datos SQLite.
        
    Returns:
        Objeto servidor HTTP.
    """
    import asyncio
    
    # Crear el servidor SQLite
    if db_path is None:
        db_path = os.path.join(os.getcwd(), "sqlite_dbs")
    
    # Inicializar MCP si no se ha hecho
    from mcp.core.init import is_mcp_initialized, initialize_mcp
    if not is_mcp_initialized():
        initialize_mcp()
    
    # Crear el servidor SQLite
    sqlite_server = SQLiteMCPServer(db_path=db_path)
    
    # Usar el event loop existente si está disponible
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Si el loop ya está corriendo, usar create_task
    if loop.is_running():
        from mcp.transport.http_server import start_http_server
        
        # Crear una versión no asíncrona para este caso
        http_server = HTTPServer((host, port), SQLiteHTTPHandler)
        SQLiteHTTPHandler.server_instance = sqlite_server
        
        # Iniciar servidor en un thread separado
        import threading
        server_thread = threading.Thread(target=http_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        logger.info(f"Servidor SQLite MCP ejecutándose en http://{host}:{port}")
        return http_server, port
    else:
        # Si el loop no está corriendo, usar el método asíncrono normal
        return loop.run_until_complete(run_mcp_http_server(host, port, db_path)) 