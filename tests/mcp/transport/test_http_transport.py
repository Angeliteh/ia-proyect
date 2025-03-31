"""
Pruebas para el transporte HTTP de MCP.

Este módulo contiene pruebas unitarias para verificar el funcionamiento
del transporte HTTP para MCP.
"""

import asyncio
import json
import unittest
import functools
from unittest.mock import patch, MagicMock, AsyncMock

from mcp.transport.http import HttpTransport
from mcp.core.protocol import MCPMessage, MCPResponse, MCPErrorCode

def async_test(func):
    """Decorador para ejecutar tests asíncronos en unittest."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

class TestHttpTransport(unittest.TestCase):
    """Pruebas para HttpTransport."""
    
    def setUp(self):
        """Configurar entorno de prueba."""
        self.base_url = "http://localhost:8080/api/mcp/echo_server"
        self.transport = HttpTransport(
            base_url=self.base_url,
            timeout=5,
            headers={"X-Test": "test-value"}
        )
    
    def test_init(self):
        """Probar inicialización del transporte."""
        self.assertEqual(self.transport.base_url, self.base_url)
        self.assertEqual(self.transport.timeout, 5)
        self.assertEqual(self.transport.headers["X-Test"], "test-value")
        self.assertIsNone(self.transport.session)
        
    @async_test
    async def test_connect_disconnect(self):
        """Probar conexión y desconexión."""
        # Patchar ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Conectar
            result = await self.transport.connect()
            self.assertTrue(result)
            self.assertIsNotNone(self.transport.session)
            
            # Verificar que se creó la sesión con las cabeceras correctas
            mock_session_class.assert_called_once()
            headers_arg = mock_session_class.call_args[1]["headers"]
            self.assertEqual(headers_arg["Content-Type"], "application/json")
            self.assertEqual(headers_arg["X-Test"], "test-value")
            
            # Desconectar
            result = await self.transport.disconnect()
            self.assertTrue(result)
            self.assertIsNone(self.transport.session)
            
            # Verificar que se cerró la sesión
            mock_session.close.assert_called_once()
            
    @async_test
    async def test_send_message_success(self):
        """Probar envío de mensaje exitoso."""
        # Crear mock de respuesta
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "message_id": "test-id",
            "data": {"result": "ok"}
        })
        
        # Configurar session mock para que funcione con async with
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        
        # Configurar context manager simulado
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = cm
        
        # Patchear ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Conectar
            await self.transport.connect()
            
            # Crear mensaje de prueba
            message = MCPMessage(
                message_id="test-id",
                action="get",
                resource_type="file",
                resource_path="/test.txt",
                data={"param": "value"}
            )
            
            # Enviar mensaje
            response = await self.transport.send_message(message)
            
            # Verificar respuesta
            self.assertTrue(response.success)
            self.assertEqual(response.message_id, "test-id")
            self.assertEqual(response.data["result"], "ok")
            
            # Verificar que se llamó a la API correctamente
            mock_session.post.assert_called_once_with(
                self.base_url,
                json={
                    'id': 'test-id',
                    'action': 'get',
                    'resource_type': 'file',
                    'resource_path': '/test.txt',
                    'data': {'param': 'value'}
                },
                timeout=5
            )
            
            # Desconectar
            await self.transport.disconnect()
            
    @async_test
    async def test_send_message_error_response(self):
        """Probar envío de mensaje con respuesta de error."""
        # Crear mock de respuesta con error
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "message_id": "test-id",
            "error": {
                "code": MCPErrorCode.RESOURCE_NOT_FOUND.value,
                "message": "Recurso no encontrado",
                "details": {"path": "/test.txt"}
            }
        })
        
        # Configurar session mock para que funcione con async with
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        
        # Configurar context manager simulado
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = cm
        
        # Patchear ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Conectar
            await self.transport.connect()
            
            # Crear mensaje de prueba
            message = MCPMessage(
                message_id="test-id",
                action="get",
                resource_type="file",
                resource_path="/test.txt"
            )
            
            # Enviar mensaje
            response = await self.transport.send_message(message)
            
            # Verificar respuesta
            self.assertFalse(response.success)
            self.assertEqual(response.message_id, "test-id")
            self.assertEqual(response.error.code, MCPErrorCode.RESOURCE_NOT_FOUND.value)
            self.assertEqual(response.error.message, "Recurso no encontrado")
            self.assertEqual(response.error.details["path"], "/test.txt")
            
            # Desconectar
            await self.transport.disconnect()
            
    @async_test
    async def test_send_message_http_error(self):
        """Probar envío de mensaje con error HTTP."""
        # Crear mock de respuesta con error HTTP
        mock_response = MagicMock()
        mock_response.status = 404
        
        # Configurar session mock para que funcione con async with
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        
        # Configurar context manager simulado
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = cm
        
        # Patchear ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Conectar
            await self.transport.connect()
            
            # Crear mensaje de prueba
            message = MCPMessage(
                message_id="test-id",
                action="get",
                resource_type="file",
                resource_path="/test.txt"
            )
            
            # Enviar mensaje
            response = await self.transport.send_message(message)
            
            # Verificar respuesta
            self.assertFalse(response.success)
            self.assertEqual(response.message_id, "test-id")
            self.assertEqual(response.error.code, MCPErrorCode.CONNECTION_ERROR.value)
            self.assertIn("http_status", response.error.details)
            self.assertEqual(response.error.details["http_status"], 404)
            
            # Desconectar
            await self.transport.disconnect()
            
    @async_test
    async def test_send_message_timeout(self):
        """Probar envío de mensaje con timeout."""
        # Configurar session mock que lanza timeout
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=asyncio.TimeoutError())
        
        # Patchear ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Conectar
            await self.transport.connect()
            
            # Crear mensaje de prueba
            message = MCPMessage(
                message_id="test-id",
                action="get",
                resource_type="file",
                resource_path="/test.txt"
            )
            
            # Enviar mensaje
            response = await self.transport.send_message(message)
            
            # Verificar respuesta
            self.assertFalse(response.success)
            self.assertEqual(response.message_id, "test-id")
            self.assertEqual(response.error.code, MCPErrorCode.TIMEOUT.value)
            
            # Desconectar
            await self.transport.disconnect()
            
    @async_test
    async def test_send_message_json_error(self):
        """Probar envío de mensaje con error de JSON."""
        # Crear mock de respuesta que lanza error JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        # Configurar session mock para que funcione con async with
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        
        # Configurar context manager simulado
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = cm
        
        # Patchear ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Conectar
            await self.transport.connect()
            
            # Crear mensaje de prueba
            message = MCPMessage(
                message_id="test-id",
                action="get",
                resource_type="file",
                resource_path="/test.txt"
            )
            
            # Enviar mensaje
            response = await self.transport.send_message(message)
            
            # Verificar respuesta
            self.assertFalse(response.success)
            self.assertEqual(response.message_id, "test-id")
            self.assertEqual(response.error.code, MCPErrorCode.INVALID_RESPONSE.value)
            
            # Desconectar
            await self.transport.disconnect()

if __name__ == "__main__":
    unittest.main() 