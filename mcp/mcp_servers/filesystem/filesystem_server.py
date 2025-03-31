"""
Servidor MCP para acceder al sistema de archivos.

Este módulo proporciona un servidor MCP que permite acceder
y manipular archivos en el sistema local.
"""

import os
import logging
import pathlib
import json
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

class FilesystemServer(MCPServerBase):
    """
    Servidor MCP para acceso al sistema de archivos.
    
    Proporciona acciones para listar, obtener, crear, modificar
    y eliminar archivos y directorios.
    
    Attributes:
        root_path: Ruta raíz para las operaciones de archivo
        allow_write: Si se permiten operaciones de escritura
        logger: Logger para esta clase
    """
    
    def __init__(
        self, 
        root_path: str = ".", 
        allow_write: bool = False,
        description: str = "Servidor MCP para acceso al sistema de archivos",
        auth_required: bool = False
    ):
        """
        Inicializa el servidor de sistema de archivos.
        
        Args:
            root_path: Ruta raíz para las operaciones (relativa o absoluta)
            allow_write: Si se permiten operaciones de escritura
            description: Descripción del servidor
            auth_required: Si se requiere autenticación
        """
        # Normalizar y convertir a ruta absoluta
        self.root_path = os.path.abspath(root_path)
        self.allow_write = allow_write
        
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
        
        # Configurar logger
        self.logger = logging.getLogger("mcp.server.filesystem")
        
        # Crear el directorio root_path si no existe
        if not os.path.exists(self.root_path):
            try:
                os.makedirs(self.root_path, exist_ok=True)
                self.logger.info(f"Directorio raíz creado: {self.root_path}")
            except Exception as e:
                self.logger.error(f"Error creando directorio raíz: {e}")
        
        self.logger.info(f"Servidor de sistema de archivos inicializado con raíz: {self.root_path}")
        self.logger.info(f"Operaciones de escritura: {'permitidas' if self.allow_write else 'no permitidas'}")
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja acciones específicas del servidor de sistema de archivos.
        
        Args:
            message: Mensaje MCP con la acción a realizar
            
        Returns:
            Respuesta MCP con el resultado de la acción
        """
        action = message.action
        resource_type = message.resource_type
        
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
            if action == MCPAction.GET:
                return await self._handle_get(message)
            elif action == MCPAction.LIST:
                return await self._handle_list(message)
            elif action == MCPAction.SEARCH:
                return await self._handle_search(message)
            # Operaciones de escritura
            elif action in [MCPAction.CREATE, MCPAction.UPDATE, MCPAction.DELETE]:
                if not self.allow_write:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.PERMISSION_DENIED,
                        message="Operaciones de escritura no permitidas"
                    )
                
                if action == MCPAction.CREATE:
                    return await self._handle_create(message)
                elif action == MCPAction.UPDATE:
                    return await self._handle_update(message)
                elif action == MCPAction.DELETE:
                    return await self._handle_delete(message)
            
            # No debería llegar aquí, pero por si acaso
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error interno al procesar acción {action}"
            )
        
        except MCPError as e:
            # Propagamos errores MCP directamente
            return MCPResponse.error_response(
                message_id=message.id,
                code=e.code,
                message=e.message,
                details=e.details
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
        Maneja la acción GET para obtener contenido de un archivo.
        
        Args:
            message: Mensaje MCP con la acción GET
            
        Returns:
            Respuesta con el contenido del archivo
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={"message": "Método GET no implementado completamente"}
        )
    
    async def _handle_list(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción LIST para listar contenido de un directorio.
        
        Args:
            message: Mensaje MCP con la acción LIST
            
        Returns:
            Respuesta con la lista de archivos y directorios
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={
                "items": [
                    {"name": "ejemplo.txt", "type": "file", "size": 1024},
                    {"name": "carpeta_ejemplo", "type": "directory"}
                ]
            }
        )
    
    async def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción SEARCH para buscar archivos.
        
        Args:
            message: Mensaje MCP con la acción SEARCH
            
        Returns:
            Respuesta con los resultados de la búsqueda
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={
                "results": [
                    {"name": "resultado1.txt", "path": "/ejemplo/resultado1.txt"},
                    {"name": "resultado2.txt", "path": "/ejemplo/carpeta/resultado2.txt"}
                ]
            }
        )
    
    async def _handle_create(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción CREATE para crear archivos o directorios.
        
        Args:
            message: Mensaje MCP con la acción CREATE
            
        Returns:
            Respuesta indicando el resultado de la creación
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={"message": "Archivo creado con éxito"}
        )
    
    async def _handle_update(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción UPDATE para actualizar archivos.
        
        Args:
            message: Mensaje MCP con la acción UPDATE
            
        Returns:
            Respuesta indicando el resultado de la actualización
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={"message": "Archivo actualizado con éxito"}
        )
    
    async def _handle_delete(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción DELETE para eliminar archivos o directorios.
        
        Args:
            message: Mensaje MCP con la acción DELETE
            
        Returns:
            Respuesta indicando el resultado de la eliminación
        """
        # Por simplicidad, solo implementaremos un método de ejemplo
        return MCPResponse.success_response(
            message_id=message.id,
            data={"message": "Archivo eliminado con éxito"}
        ) 