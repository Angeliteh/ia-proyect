"""
Servidor MCP para SQLite.

Este servidor proporciona acceso a bases de datos SQLite a través del protocolo MCP,
permitiendo ejecutar consultas SQL y administrar tablas.
"""

import asyncio
import aiosqlite
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
import sqlite3

from mcp.core import (
    MCPServerBase, 
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPErrorCode
)

class SQLiteServer(MCPServerBase):
    """
    Servidor MCP para acceder a bases de datos SQLite.
    
    Este servidor permite ejecutar consultas SQL, listar tablas,
    obtener estructura de tablas y realizar otras operaciones con SQLite.
    """
    
    def __init__(
        self, 
        name: str = "sqlite_server", 
        db_path: str = ":memory:",
        description: str = "Servidor MCP para acceso a bases de datos SQLite"
    ):
        """
        Inicializa el servidor SQLite.
        
        Args:
            name: Nombre del servidor (por defecto: "sqlite_server")
            db_path: Ruta al archivo de base de datos SQLite (por defecto: ":memory:")
            description: Descripción del servidor
        """
        super().__init__(
            name=name,
            description=description,
            auth_required=False,
            supported_actions=[
                MCPAction.PING,
                MCPAction.CAPABILITIES,
                MCPAction.GET,     # Obtener una tabla o registro
                MCPAction.LIST,    # Listar tablas o registros
                MCPAction.SEARCH,  # Buscar registros
                MCPAction.CREATE,  # Crear tablas o registros
                MCPAction.UPDATE,  # Actualizar registros
                MCPAction.DELETE,  # Eliminar tablas o registros
                MCPAction.QUERY,   # Ejecutar consulta SQL personalizada
                MCPAction.SCHEMA   # Obtener el esquema de una tabla
            ],
            supported_resources=[
                MCPResource.SYSTEM,    # Recurso necesario para PING y CAPABILITIES
                MCPResource.DATABASE,
                "table",
                "record"
            ]
        )
        
        self.db_path = db_path
        self.connection = None
        self.db_info = {
            "path": db_path,
            "type": "sqlite",
            "in_memory": db_path == ":memory:"
        }
        
        # Diccionario para cachear esquemas de tablas
        self.table_schemas = {}
        
    async def _ensure_connection(self):
        """
        Asegura que exista una conexión a la base de datos.
        
        Returns:
            Conexión a la base de datos
        """
        if not self.connection:
            try:
                self.connection = await aiosqlite.connect(self.db_path)
                self.connection.row_factory = aiosqlite.Row
                self.logger.info(f"Conexión establecida con SQLite: {self.db_path}")
            except Exception as e:
                self.logger.error(f"Error conectando a la base de datos: {str(e)}")
                raise
                
        return self.connection
    
    async def close(self):
        """Cierra la conexión a la base de datos."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.logger.info("Conexión a SQLite cerrada")
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja las acciones recibidas por el servidor.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta al mensaje
        """
        try:
            # Asegurar conexión a la base de datos
            await self._ensure_connection()
            
            self.logger.info(f"SQLiteServer recibió: {message.action} - {message.resource_path}")
            
            # Manejar acciones según el tipo
            if message.action == MCPAction.PING.value:
                # Responder al ping directamente
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={"status": "ok", "server": self.name, "type": "sqlite"}
                )
            elif message.action == MCPAction.CAPABILITIES.value:
                # Responder a solicitud de capacidades directamente
                return MCPResponse.success_response(
                    message_id=message.id,
                    data=self.capabilities
                )
            elif message.action == MCPAction.GET.value:
                return await self._handle_get(message)
            elif message.action == MCPAction.LIST.value:
                return await self._handle_list(message)
            elif message.action == MCPAction.SEARCH.value:
                return await self._handle_search(message)
            elif message.action == MCPAction.CREATE.value:
                return await self._handle_create(message)
            elif message.action == MCPAction.UPDATE.value:
                return await self._handle_update(message)
            elif message.action == MCPAction.DELETE.value:
                return await self._handle_delete(message)
            elif message.action == MCPAction.QUERY.value:
                return await self._handle_query(message)
            elif message.action == MCPAction.SCHEMA.value:
                return await self._handle_schema(message)
            else:
                # Acción no implementada
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message=f"Acción no implementada: {message.action}"
                )
        except Exception as e:
            self.logger.error(f"Error procesando acción {message.action}: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error del servidor: {str(e)}"
            )
    
    async def _handle_get(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción GET para obtener registros o información de tablas.
        
        Args:
            message: Mensaje MCP con acción GET
            
        Returns:
            Respuesta con los datos solicitados
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        # Para solicitudes de sistema, manejamos diferente
        if resource_type == MCPResource.SYSTEM.value:
            # Solicitudes del sistema
            if resource_path == "/info":
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "server": self.name,
                        "description": self.description,
                        "type": "sqlite",
                        "db_path": self.db_path,
                        "in_memory": self.db_path == ":memory:"
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Recurso de sistema no encontrado: {resource_path}"
                )
        elif resource_type == "table":
            # Obtener un registro específico de una tabla
            table_name = resource_path.strip('/')
            record_id = message.data.get("id")
            id_field = message.data.get("id_field", "id")
            
            if not record_id:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un ID para obtener un registro específico"
                )
            
            query = f"SELECT * FROM {table_name} WHERE {id_field} = ?"
            async with self.connection.execute(query, (record_id,)) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return MCPResponse.success_response(
                        message_id=message.id,
                        data=dict(row)
                    )
                else:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Registro con ID {record_id} no encontrado en tabla {table_name}"
                    )
        
        elif resource_type == MCPResource.DATABASE.value:
            # Obtener información de la base de datos
            return MCPResponse.success_response(
                message_id=message.id,
                data=self.db_info
            )
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para GET: {resource_type}"
            )
    
    async def _handle_list(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción LIST para listar tablas o registros.
        
        Args:
            message: Mensaje MCP con acción LIST
            
        Returns:
            Respuesta con la lista solicitada
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        if resource_type == MCPResource.DATABASE.value:
            # Listar tablas en la base de datos
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            async with self.connection.execute(query) as cursor:
                tables = [row['name'] for row in await cursor.fetchall()]
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={"tables": tables}
                )
        
        elif resource_type == "table":
            # Listar registros de una tabla
            table_name = resource_path.strip('/')
            limit = message.data.get("limit", 100)
            offset = message.data.get("offset", 0)
            
            # Verificar si la tabla existe
            async with self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                (table_name,)
            ) as cursor:
                if not await cursor.fetchone():
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Tabla no encontrada: {table_name}"
                    )
            
            # Obtener registros con paginación
            query = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
            async with self.connection.execute(query, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                result = [dict(row) for row in rows]
                
                # Obtener el número total de registros
                async with self.connection.execute(f"SELECT COUNT(*) as total FROM {table_name}") as count_cursor:
                    count_row = await count_cursor.fetchone()
                    total = count_row['total'] if count_row else 0
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "items": result,
                        "total": total,
                        "limit": limit,
                        "offset": offset
                    }
                )
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para LIST: {resource_type}"
            )
    
    async def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción SEARCH para buscar registros en tablas.
        
        Args:
            message: Mensaje MCP con acción SEARCH
            
        Returns:
            Respuesta con los resultados de la búsqueda
        """
        resource_type = message.resource_type
        
        if resource_type != "table":
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para SEARCH: {resource_type}"
            )
        
        table_name = message.resource_path.strip('/')
        query = message.data.get("query", "")
        fields = message.data.get("fields", [])
        limit = message.data.get("limit", 100)
        offset = message.data.get("offset", 0)
        
        # Obtener el esquema de la tabla para conocer sus campos
        async with self.connection.execute(f"PRAGMA table_info({table_name})") as cursor:
            columns = await cursor.fetchall()
            if not columns:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Tabla no encontrada: {table_name}"
                )
            
            column_names = [col['name'] for col in columns]
        
        # Si no se especifican campos, buscar en todos
        search_fields = fields if fields else column_names
        
        # Construir la consulta de búsqueda
        conditions = []
        params = []
        
        for field in search_fields:
            if field in column_names:
                conditions.append(f"{field} LIKE ?")
                params.append(f"%{query}%")
        
        if not conditions:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"No hay campos válidos para buscar"
            )
        
        sql_query = f"SELECT * FROM {table_name} WHERE {' OR '.join(conditions)} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Ejecutar la búsqueda
        async with self.connection.execute(sql_query, params) as cursor:
            rows = await cursor.fetchall()
            result = [dict(row) for row in rows]
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "results": result,
                    "count": len(result),
                    "query": query
                }
            )
    
    async def _handle_create(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción CREATE para crear tablas o registros.
        
        Args:
            message: Mensaje MCP con acción CREATE
            
        Returns:
            Respuesta con el resultado de la creación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        if resource_type == "table":
            # Crear una tabla
            table_name = resource_path.strip('/')
            schema = message.data.get("schema", {})
            
            if not schema:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un esquema para crear una tabla"
                )
            
            # Construir la definición de la tabla
            columns = []
            for name, definition in schema.items():
                columns.append(f"{name} {definition}")
            
            column_defs = ", ".join(columns)
            create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
            
            try:
                await self.connection.execute(create_query)
                await self.connection.commit()
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "table": table_name,
                        "message": f"Tabla {table_name} creada exitosamente"
                    }
                )
            except sqlite3.Error as e:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.SERVER_ERROR,
                    message=f"Error creando tabla: {str(e)}"
                )
        
        elif resource_type == "record":
            # Crear un registro en una tabla
            table_name = resource_path.strip('/')
            record_data = message.data.get("data", {})
            
            if not record_data:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requieren datos para crear un registro"
                )
            
            columns = record_data.keys()
            placeholders = ", ".join(["?" for _ in columns])
            values = [record_data[col] for col in columns]
            
            insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            try:
                cursor = await self.connection.execute(insert_query, values)
                await self.connection.commit()
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "id": cursor.lastrowid,
                        "message": f"Registro creado exitosamente en tabla {table_name}"
                    }
                )
            except sqlite3.Error as e:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.SERVER_ERROR,
                    message=f"Error creando registro: {str(e)}"
                )
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para CREATE: {resource_type}"
            )
    
    async def _handle_update(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción UPDATE para actualizar registros.
        
        Args:
            message: Mensaje MCP con acción UPDATE
            
        Returns:
            Respuesta con el resultado de la actualización
        """
        resource_type = message.resource_type
        
        if resource_type != "record":
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para UPDATE: {resource_type}"
            )
        
        table_name = message.resource_path.strip('/')
        record_id = message.data.get("id")
        id_field = message.data.get("id_field", "id")
        update_data = message.data.get("data", {})
        
        if not record_id:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere un ID para actualizar un registro"
            )
        
        if not update_data:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requieren datos para actualizar un registro"
            )
        
        # Construir la consulta de actualización
        set_clauses = []
        values = []
        
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(record_id)
        update_query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_field} = ?"
        
        try:
            cursor = await self.connection.execute(update_query, values)
            await self.connection.commit()
            
            if cursor.rowcount > 0:
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "message": f"Registro actualizado exitosamente",
                        "rows_affected": cursor.rowcount
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"No se encontró el registro con ID {record_id}"
                )
        except sqlite3.Error as e:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error actualizando registro: {str(e)}"
            )
    
    async def _handle_delete(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción DELETE para eliminar tablas o registros.
        
        Args:
            message: Mensaje MCP con acción DELETE
            
        Returns:
            Respuesta con el resultado de la eliminación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path.strip('/')
        
        if resource_type == "table":
            # Eliminar una tabla
            table_name = resource_path
            
            try:
                await self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                await self.connection.commit()
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "message": f"Tabla {table_name} eliminada exitosamente"
                    }
                )
            except sqlite3.Error as e:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.SERVER_ERROR,
                    message=f"Error eliminando tabla: {str(e)}"
                )
        
        elif resource_type == "record":
            # Eliminar un registro de una tabla
            table_name = resource_path
            record_id = message.data.get("id")
            id_field = message.data.get("id_field", "id")
            
            if not record_id:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un ID para eliminar un registro"
                )
            
            try:
                delete_query = f"DELETE FROM {table_name} WHERE {id_field} = ?"
                cursor = await self.connection.execute(delete_query, (record_id,))
                await self.connection.commit()
                
                if cursor.rowcount > 0:
                    return MCPResponse.success_response(
                        message_id=message.id,
                        data={
                            "message": f"Registro eliminado exitosamente",
                            "rows_affected": cursor.rowcount
                        }
                    )
                else:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"No se encontró el registro con ID {record_id}"
                    )
            except sqlite3.Error as e:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.SERVER_ERROR,
                    message=f"Error eliminando registro: {str(e)}"
                )
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para DELETE: {resource_type}"
            )
    
    async def _handle_query(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción personalizada QUERY para ejecutar consultas SQL.
        
        Args:
            message: Mensaje MCP con acción QUERY
            
        Returns:
            Respuesta con los resultados de la consulta
        """
        query = message.data.get("query", "")
        params = message.data.get("params", [])
        query_type = message.data.get("type", "select")
        
        if not query:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere una consulta SQL"
            )
        
        try:
            if query_type.lower() == "select":
                # Consulta de selección (retorna resultados)
                async with self.connection.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    result = [dict(row) for row in rows]
                    
                    return MCPResponse.success_response(
                        message_id=message.id,
                        data={
                            "rows": result,
                            "count": len(result)
                        }
                    )
            else:
                # Consulta de modificación (no retorna resultados)
                cursor = await self.connection.execute(query, params)
                await self.connection.commit()
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "rows_affected": cursor.rowcount,
                        "last_row_id": cursor.lastrowid
                    }
                )
        except sqlite3.Error as e:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error ejecutando consulta: {str(e)}"
            )
    
    async def _handle_schema(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción personalizada SCHEMA para obtener el esquema de una tabla.
        
        Args:
            message: Mensaje MCP con acción SCHEMA
            
        Returns:
            Respuesta con el esquema de la tabla
        """
        resource_type = message.resource_type
        
        if resource_type != "table":
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado para SCHEMA: {resource_type}"
            )
        
        table_name = message.resource_path.strip('/')
        
        try:
            # Obtener información de la tabla
            async with self.connection.execute(f"PRAGMA table_info({table_name})") as cursor:
                columns = await cursor.fetchall()
                
                if not columns:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Tabla no encontrada: {table_name}"
                    )
                
                schema = {
                    "name": table_name,
                    "columns": []
                }
                
                for col in columns:
                    schema["columns"].append({
                        "name": col["name"],
                        "type": col["type"],
                        "notnull": bool(col["notnull"]),
                        "default_value": col["dflt_value"],
                        "pk": bool(col["pk"])
                    })
                
                # Obtener índices
                async with self.connection.execute(
                    f"SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?", 
                    (table_name,)
                ) as cursor:
                    indices = await cursor.fetchall()
                    schema["indices"] = [{"name": idx["name"], "sql": idx["sql"]} for idx in indices]
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data=schema
                )
                
        except sqlite3.Error as e:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error obteniendo esquema: {str(e)}"
            )
