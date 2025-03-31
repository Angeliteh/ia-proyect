"""
Cliente local MCP para conexiones directas.

Este módulo proporciona un cliente MCP para conexiones directas en memoria
con servidores MCP locales.
"""

import logging
from typing import Optional, Dict, Any

from mcp.core.client_base import MCPClientBase
from mcp.core.server_base import MCPServerBase
from mcp.core.protocol import MCPMessage, MCPResponse, MCPError, MCPErrorCode

class LocalClient(MCPClientBase):
    """
    Cliente MCP para conexiones directas a servidores locales.
    
    Este cliente permite una comunicación directa (en memoria) con
    servidores MCP que se ejecutan en el mismo proceso, sin necesidad
    de transporte de red.
    
    Attributes:
        server: Servidor MCP al que está conectado
        logger: Logger para este cliente
    """
    
    def __init__(
        self, 
        server: Optional[MCPServerBase] = None,
        timeout: int = 5,
        retry_attempts: int = 2
    ):
        """
        Inicializa un cliente local MCP.
        
        Args:
            server: Servidor MCP al que conectarse (opcional)
            timeout: Tiempo de espera en segundos para operaciones
            retry_attempts: Número de intentos de reintento para operaciones
        """
        super().__init__(
            server_url="direct://local", 
            timeout=timeout,
            retry_attempts=retry_attempts
        )
        self.server = server
        self.logger = logging.getLogger("mcp.clients.local")
        self.logger.info("Cliente local MCP inicializado")
    
    async def connect(self, server: MCPServerBase = None) -> bool:
        """
        Conecta con un servidor MCP local.
        
        Args:
            server: Servidor MCP al que conectarse (opcional, si no se especificó en el constructor)
            
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        if server is not None:
            self.server = server
            
        if self.server is None:
            self.logger.error("No se especificó un servidor al que conectarse")
            return False
            
        self.logger.info(f"Cliente conectado al servidor: {self.server.name}")
        return True
    
    async def disconnect(self) -> bool:
        """
        Desconecta del servidor.
        
        Returns:
            True si la desconexión fue exitosa, False en caso contrario
        """
        if self.server is None:
            self.logger.warning("Cliente no conectado a ningún servidor")
            return False
            
        previous_server = self.server
        self.server = None
        self.logger.info(f"Cliente desconectado del servidor: {previous_server.name}")
        return True
    
    async def _send_request(self, request: MCPMessage) -> MCPResponse:
        """
        Envía una solicitud al servidor MCP conectado.
        
        Args:
            request: Solicitud MCP a enviar
            
        Returns:
            Respuesta del servidor
            
        Raises:
            ConnectionError: Si el cliente no está conectado a ningún servidor
        """
        if self.server is None:
            self.logger.error("Cliente no conectado a ningún servidor")
            return MCPResponse.error_response(
                message_id=request.id,
                code=MCPErrorCode.CONNECTION_ERROR,
                message="Cliente no conectado a ningún servidor"
            )
        
        try:
            # Enviar directamente al servidor local
            response = await self.server.process_message(request)
            return response
        except Exception as e:
            self.logger.error(f"Error procesando solicitud: {e}")
            return MCPResponse.error_response(
                message_id=request.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error procesando solicitud: {str(e)}"
            ) 