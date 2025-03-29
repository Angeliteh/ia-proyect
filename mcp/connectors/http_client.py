"""
Cliente HTTP para el Model Context Protocol (MCP).

Este módulo proporciona una implementación de cliente MCP que se comunica
con servidores MCP a través del protocolo HTTP/REST.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, Union

from mcp.core.client_base import MCPClientBase
from mcp.core.protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPError, 
    MCPErrorCode
)

logger = logging.getLogger(__name__)

class MCPHttpClient(MCPClientBase):
    """Cliente MCP genérico para servidores que utilizan HTTP/REST.
    
    Este cliente permite conectarse a servidores MCP externos que exponen
    una API HTTP/REST, simplificando la integración con servicios MCP de terceros.
    
    Attributes:
        base_url: URL base del servidor MCP.
        api_key: Clave API para autenticación (opcional).
        headers: Cabeceras HTTP adicionales para las solicitudes.
        session: Sesión HTTP para mantener conexiones.
        is_connected: Estado de la conexión con el servidor.
    """
    
    def __init__(self, 
                 base_url: str, 
                 api_key: Optional[str] = None, 
                 headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30):
        """Inicializa el cliente HTTP para MCP.
        
        Args:
            base_url: URL base del servidor MCP (ej: "https://api.example.com/mcp").
            api_key: Clave API para autenticación (opcional).
            headers: Cabeceras HTTP adicionales para incluir en las solicitudes.
            timeout: Tiempo máximo de espera para solicitudes en segundos.
        """
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.headers = headers or {}
        self.session = None
        self.is_connected = False
        
        # Configurar cabecera de autenticación si se proporciona API key
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def connect(self) -> bool:
        """Establece la conexión con el servidor MCP.
        
        Verifica que el servidor esté disponible e inicializa una sesión HTTP.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario.
        """
        try:
            logger.info(f"Conectando con servidor MCP en {self.base_url}")
            self.session = requests.Session()
            self.session.headers.update(self.headers)
            
            # Intentar hacer un ping al servidor para verificar disponibilidad
            response = self.session.get(
                f"{self.base_url}/ping", 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.is_connected = True
                logger.info("Conexión exitosa con el servidor MCP")
                return True
            else:
                logger.error(f"Error al conectar: Código HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error al conectar con el servidor MCP: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Cierra la conexión con el servidor MCP.
        
        Libera los recursos asociados con la sesión HTTP.
        
        Returns:
            bool: True si la desconexión fue exitosa.
        """
        if self.session:
            self.session.close()
            self.session = None
        self.is_connected = False
        logger.info("Desconexión del servidor MCP completada")
        return True
    
    def send_message(self, message: MCPMessage) -> MCPResponse:
        """Envía un mensaje MCP al servidor a través de HTTP.
        
        Args:
            message: Mensaje MCP a enviar.
            
        Returns:
            MCPResponse: Respuesta del servidor o error si la comunicación falla.
        """
        if not self.is_connected or not self.session:
            error_msg = "Cliente no conectado al servidor MCP"
            logger.error(error_msg)
            return MCPResponse(
                success=False,
                error=MCPError(
                    code=MCPErrorCode.CONNECTION_ERROR,
                    message=error_msg
                )
            )
        
        try:
            # Convertir el mensaje a formato JSON
            message_dict = message.to_dict()
            logger.debug(f"Enviando mensaje al servidor MCP: {message_dict}")
            
            # Enviar solicitud HTTP POST
            response = self.session.post(
                f"{self.base_url}/api",
                json=message_dict,
                timeout=self.timeout
            )
            
            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                # Parsear la respuesta JSON
                try:
                    response_data = response.json()
                    logger.debug(f"Respuesta recibida: {response_data}")
                    return MCPResponse.from_dict(response_data)
                except json.JSONDecodeError:
                    error_msg = "Error al decodificar la respuesta JSON"
                    logger.error(f"{error_msg}: {response.text}")
                    return MCPResponse(
                        success=False,
                        error=MCPError(
                            code=MCPErrorCode.INVALID_RESPONSE,
                            message=error_msg
                        )
                    )
            else:
                error_msg = f"Error HTTP {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                return MCPResponse(
                    success=False,
                    error=MCPError(
                        code=MCPErrorCode.SERVER_ERROR,
                        message=error_msg
                    )
                )
        except requests.Timeout:
            error_msg = f"Tiempo de espera agotado (timeout: {self.timeout}s)"
            logger.error(error_msg)
            return MCPResponse(
                success=False,
                error=MCPError(
                    code=MCPErrorCode.TIMEOUT,
                    message=error_msg
                )
            )
        except Exception as e:
            error_msg = f"Error de comunicación: {str(e)}"
            logger.error(error_msg)
            return MCPResponse(
                success=False,
                error=MCPError(
                    code=MCPErrorCode.UNKNOWN_ERROR,
                    message=error_msg
                )
            )
            
    def ping(self) -> MCPResponse:
        """Envía un ping al servidor para verificar su disponibilidad.
        
        Returns:
            MCPResponse: Respuesta del servidor.
        """
        message = MCPMessage.create_ping()
        return self.send_message(message)
    
    def get_capabilities(self) -> MCPResponse:
        """Solicita las capacidades del servidor MCP.
        
        Returns:
            MCPResponse: Respuesta con las capacidades del servidor.
        """
        message = MCPMessage.create_capabilities_request()
        return self.send_message(message) 