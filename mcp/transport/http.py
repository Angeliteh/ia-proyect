"""
Implementación de transporte HTTP para MCP.

Este módulo proporciona clases para la comunicación MCP sobre HTTP,
permitiendo la comunicación entre clientes y servidores a través de la web.
"""

import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional

from mcp.core.protocol import MCPMessage, MCPResponse, MCPError, MCPErrorCode

class HttpTransport:
    """
    Transporte HTTP para comunicación MCP.
    
    Esta clase proporciona métodos para enviar y recibir mensajes MCP
    a través del protocolo HTTP.
    
    Attributes:
        base_url: URL base del servidor MCP
        session: Sesión HTTP para reutilizar conexiones
        timeout: Tiempo de espera en segundos para operaciones HTTP
        logger: Logger para esta clase
    """
    
    def __init__(
        self, 
        base_url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Inicializa un transporte HTTP.
        
        Args:
            base_url: URL base del servidor MCP (ej: 'http://localhost:8080/api/mcp')
            timeout: Tiempo de espera en segundos para operaciones HTTP
            headers: Cabeceras HTTP adicionales a incluir en cada solicitud
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {}
        self.session = None
        self.logger = logging.getLogger("mcp.transport.http")
        
    async def connect(self) -> bool:
        """
        Inicializa la sesión HTTP.
        
        Returns:
            True si la conexión se estableció correctamente
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    **self.headers
                }
            )
        return True
        
    async def disconnect(self) -> bool:
        """
        Cierra la sesión HTTP.
        
        Returns:
            True si la desconexión fue exitosa
        """
        if self.session is not None:
            await self.session.close()
            self.session = None
        return True
        
    async def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje MCP al servidor a través de HTTP.
        
        Args:
            message: Mensaje MCP a enviar. Los atributos necesarios son:
                   - id: Identificador único del mensaje
                   - action: Acción a realizar (valor de MCPAction o cadena personalizada)
                   - resource_type: Tipo de recurso (valor de MCPResource o cadena personalizada)
                   - resource_path: Ruta del recurso
                   - data: Datos adicionales para la acción (opcional)
                   - auth_token: Token de autenticación (opcional)
            
        Returns:
            Respuesta MCP del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
            
        Note:
            El mensaje puede contener acciones o tipos de recursos personalizados.
            Si action o resource_type tienen un atributo 'value', se usará ese valor.
            Caso contrario, se usará el valor tal cual.
        """
        if self.session is None:
            await self.connect()
            
        try:
            # Convertir mensaje a JSON
            message_data = {
                'id': message.id,
                'action': message.action.value if hasattr(message.action, 'value') else message.action,
                'resource_type': message.resource_type.value if hasattr(message.resource_type, 'value') else message.resource_type,
                'resource_path': message.resource_path,
                'data': message.data
            }
            
            if message.auth_token:
                message_data['auth_token'] = message.auth_token
                
            # Enviar la solicitud HTTP
            async with self.session.post(
                self.base_url,
                json=message_data,
                timeout=self.timeout
            ) as response:
                # Verificar el estado de la respuesta
                if response.status != 200:
                    self.logger.error(f"Error HTTP: {response.status}")
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.CONNECTION_ERROR,
                        message=f"Error HTTP: {response.status}",
                        details={"http_status": response.status}
                    )
                    
                # Analizar la respuesta JSON
                try:
                    response_data = await response.json()
                    
                    # Crear objeto MCPResponse
                    if response_data.get('success', False):
                        return MCPResponse.success_response(
                            message_id=response_data.get('message_id', message.id),
                            data=response_data.get('data', {})
                        )
                    else:
                        error_data = response_data.get('error', {})
                        return MCPResponse.error_response(
                            message_id=response_data.get('message_id', message.id),
                            code=error_data.get('code', MCPErrorCode.SERVER_ERROR.value),
                            message=error_data.get('message', 'Error desconocido'),
                            details=error_data.get('details', {})
                        )
                        
                except json.JSONDecodeError:
                    self.logger.error("Error decodificando respuesta JSON")
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.INVALID_RESPONSE,
                        message="Error decodificando respuesta JSON"
                    )
                    
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout en solicitud HTTP (>{self.timeout}s)")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.TIMEOUT,
                message=f"Timeout en solicitud HTTP (>{self.timeout}s)"
            )
            
        except Exception as e:
            self.logger.error(f"Error en transporte HTTP: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.CONNECTION_ERROR,
                message=f"Error en transporte HTTP: {str(e)}"
            ) 