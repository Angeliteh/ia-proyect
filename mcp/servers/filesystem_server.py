"""
Servidor MCP para acceder al sistema de archivos.

Este módulo proporciona un servidor MCP que permite acceder
y manipular archivos en el sistema local.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union

from mcp.core.server_base import MCPServerBase
from mcp.core.protocol import (
    MCPMessage,
    MCPResponse,
    MCPAction,
    MCPResource,
    MCPError,
    MCPErrorCode
)
from mcp.connectors.filesystem import FilesystemConnector

class FilesystemServer(MCPServerBase):
    """
    Servidor MCP para acceso al sistema de archivos.

    Proporciona acciones para listar, obtener, crear, modificar
    y eliminar archivos y directorios.

    Attributes:
        root_path: Ruta raíz para las operaciones de archivo
        allow_write: Si se permiten operaciones de escritura
        connector: Conector de sistema de archivos
        logger: Logger para esta clase
    """

    def __init__(
        self,
        root_path: str = ".",
        allow_write: bool = False,
        description: str = "Servidor MCP para acceso al sistema de archivos",
        auth_required: bool = False,
        max_file_size: int = 10 * 1024 * 1024  # 10 MB por defecto
    ):
        """
        Inicializa el servidor de sistema de archivos.

        Args:
            root_path: Ruta raíz para las operaciones (relativa o absoluta)
            allow_write: Si se permiten operaciones de escritura
            description: Descripción del servidor
            auth_required: Si se requiere autenticación
            max_file_size: Tamaño máximo permitido para archivos (en bytes)
        """
        # Configurar el conector de sistema de archivos
        self.connector = FilesystemConnector(
            root_path=root_path,
            allow_write=allow_write,
            max_file_size=max_file_size
        )
        
        # Llamar al constructor de la clase base
        super().__init__(
            name="FilesystemServer",
            description=description,
            auth_required=auth_required,
            supported_actions=[
                MCPAction.GET,
                MCPAction.LIST,
                MCPAction.SEARCH,
                MCPAction.CREATE,
                MCPAction.UPDATE,
                MCPAction.DELETE
            ],
            supported_resources=[
                MCPResource.FILE,
                MCPResource.DIRECTORY
            ]
        )
        
        self.logger.info(f"Servidor de sistema de archivos inicializado con raíz: {root_path}")
        self.logger.info(f"Operaciones de escritura: {'permitidas' if allow_write else 'no permitidas'}")

    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja las acciones recibidas por el servidor.
        
        Args:
            message: Mensaje MCP con la acción a realizar
            
        Returns:
            Respuesta MCP con el resultado de la acción
        """
        action = message.action
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        # Verificar si la acción está soportada
        if action not in self.supported_actions:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Acción no soportada: {action}"
            )
                
        # Verificar el tipo de recurso
        if resource_type not in self.supported_resources:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Tipo de recurso no soportado: {resource_type}"
            )

        # Derivar a manejadores específicos según la acción
        try:
            if action == MCPAction.GET.value:
                return await self._handle_get(message)
            elif action == MCPAction.LIST.value:
                return await self._handle_list(message)
            elif action == MCPAction.SEARCH.value:
                return await self._handle_search(message)
            # Operaciones de escritura
            elif action in [MCPAction.CREATE.value, MCPAction.UPDATE.value, MCPAction.DELETE.value]:
                if not self.connector.allow_write:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.PERMISSION_DENIED,
                        message="Operaciones de escritura no permitidas"
                    )

                if action == MCPAction.CREATE.value:
                    return await self._handle_create(message)
                elif action == MCPAction.UPDATE.value:
                    return await self._handle_update(message)
                elif action == MCPAction.DELETE.value:
                    return await self._handle_delete(message)

            # No debería llegar aquí, pero por si acaso
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error interno al procesar acción {action}"
            )

        except FileNotFoundError as e:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.RESOURCE_NOT_FOUND,
                message=str(e)
            )
        except (PermissionError, ValueError) as e:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.PERMISSION_DENIED,
                message=str(e)
            )
        except Exception as e:
            # Convertimos otros errores a errores MCP
            self.logger.exception(f"Error no esperado procesando acción {action}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error procesando acción {action}: {str(e)}"
            )

    async def _handle_get(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción GET para obtener un archivo o información de directorio.
        
        Args:
            message: Mensaje MCP con la acción GET
            
        Returns:
            Respuesta con el contenido o información
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        try:
            if resource_type == MCPResource.FILE.value:
                # Obtener contenido e información del archivo
                content, info = self.connector.read_file(resource_path)
                
                # Convertir contenido binario a texto si es posible
                try:
                    text_content = content.decode('utf-8')
                    is_text = True
                except UnicodeDecodeError:
                    text_content = None
                    is_text = False
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "info": info,
                        "content": text_content if is_text else None,
                        "is_text": is_text,
                        "size": len(content)
                    }
                )
                
            elif resource_type == MCPResource.DIRECTORY.value:
                # Obtener información del directorio
                info = self.connector.get_file_info(resource_path)
                
                if not info["is_dir"]:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.INVALID_REQUEST,
                        message=f"La ruta no es un directorio: {resource_path}"
                    )
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={"info": info}
                )
                
        except Exception as e:
            self.logger.error(f"Error en acción GET: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción GET"
        )

    async def _handle_list(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción LIST para listar contenido de un directorio.
        
        Args:
            message: Mensaje MCP con la acción LIST
            
        Returns:
            Respuesta con la lista de archivos y directorios
        """
        resource_path = message.resource_path
        
        try:
            items = self.connector.list_directory(resource_path)
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={"items": items}
            )
                
        except Exception as e:
            self.logger.error(f"Error en acción LIST: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción LIST"
        )

    async def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción SEARCH para buscar archivos.
        
        Args:
            message: Mensaje MCP con la acción SEARCH
            
        Returns:
            Respuesta con los resultados de la búsqueda
        """
        resource_path = message.resource_path
        search_data = message.data or {}
        
        pattern = search_data.get("pattern", "*")
        recursive = search_data.get("recursive", True)
        max_results = search_data.get("max_results", 100)
        
        try:
            results = self.connector.search_files(
                path=resource_path,
                pattern=pattern,
                recursive=recursive,
                max_results=max_results
            )
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "results": results,
                    "count": len(results),
                    "pattern": pattern,
                    "path": resource_path
                }
            )
                
        except Exception as e:
            self.logger.error(f"Error en acción SEARCH: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción SEARCH"
        )

    async def _handle_create(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción CREATE para crear archivos o directorios.
        
        Args:
            message: Mensaje MCP con la acción CREATE
            
        Returns:
            Respuesta indicando el resultado de la creación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        try:
            if resource_type == MCPResource.FILE.value:
                # Crear un archivo
                content = data.get("content", "")
                file_info = self.connector.write_file(resource_path, content)
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "message": "Archivo creado con éxito",
                        "info": file_info
                    }
                )
                
            elif resource_type == MCPResource.DIRECTORY.value:
                # Crear un directorio
                resolved_path = self.connector._resolve_path(resource_path)
                os.makedirs(resolved_path, exist_ok=True)
                
                dir_info = self.connector.get_file_info(resource_path)
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "message": "Directorio creado con éxito",
                        "info": dir_info
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error en acción CREATE: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción CREATE"
        )

    async def _handle_update(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción UPDATE para actualizar archivos.
        
        Args:
            message: Mensaje MCP con la acción UPDATE
            
        Returns:
            Respuesta indicando el resultado de la actualización
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        try:
            if resource_type == MCPResource.FILE.value:
                # Actualizar un archivo
                content = data.get("content", "")
                file_info = self.connector.write_file(resource_path, content)
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "message": "Archivo actualizado con éxito",
                        "info": file_info
                    }
                )
                
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message="Solo se puede actualizar archivos, no directorios"
                )
                
        except Exception as e:
            self.logger.error(f"Error en acción UPDATE: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción UPDATE"
        )

    async def _handle_delete(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción DELETE para eliminar archivos o directorios.
        
        Args:
            message: Mensaje MCP con la acción DELETE
            
        Returns:
            Respuesta indicando el resultado de la eliminación
        """
        resource_path = message.resource_path
        data = message.data or {}
        
        recursive = data.get("recursive", False)
        
        try:
            self.connector.delete_item(resource_path, recursive=recursive)
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "message": "Elemento eliminado con éxito",
                    "path": resource_path
                }
            )
                
        except Exception as e:
            self.logger.error(f"Error en acción DELETE: {str(e)}")
            raise
            
        return MCPResponse.error_response(
            message_id=message.id,
            code=MCPErrorCode.SERVER_ERROR,
            message="Error al procesar acción DELETE"
        ) 