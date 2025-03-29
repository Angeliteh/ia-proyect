"""
Registro central de servidores y clientes MCP.

Este módulo proporciona un registro centralizado para gestionar
los servidores y clientes MCP disponibles en el sistema.
"""

import logging
from typing import Dict, Any, Optional, Type, List, Union, Callable
import importlib
import inspect
import os
import yaml

from .server_base import MCPServerBase
from .client_base import MCPClientBase
from .protocol import MCPError, MCPErrorCode

class MCPRegistry:
    """
    Registro central de servidores y clientes MCP.
    
    Proporciona métodos para registrar, crear y gestionar
    servidores y clientes MCP.
    
    Attributes:
        servers: Diccionario de clases de servidores registrados
        clients: Diccionario de clases de clientes registrados
        instances: Diccionario de instancias de servidores activas
        logger: Logger para esta clase
    """
    
    _instance = None
    
    def __new__(cls):
        """
        Implementación de patrón Singleton para el registro.
        
        Returns:
            Instancia única del registro
        """
        if cls._instance is None:
            cls._instance = super(MCPRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Inicializa el registro MCP.
        """
        if self._initialized:
            return
            
        self._servers = {}  # {nombre: {class, config}}
        self._clients = {}  # {nombre: {class, config}}
        self._instances = {}  # {nombre: instancia_servidor}
        self.logger = logging.getLogger("mcp.registry")
        self._initialized = True
    
    def register_server(
        self, 
        name: str, 
        server_class: Type[MCPServerBase], 
        **kwargs
    ) -> None:
        """
        Registra una clase de servidor MCP.
        
        Args:
            name: Nombre único para el servidor
            server_class: Clase del servidor (debe heredar de MCPServerBase)
            **kwargs: Configuración por defecto para instancias de este servidor
        
        Raises:
            ValueError: Si el nombre ya está registrado o la clase no es válida
        """
        if name in self._servers:
            raise ValueError(f"Ya existe un servidor registrado con el nombre '{name}'")
            
        if not inspect.isclass(server_class) or not issubclass(server_class, MCPServerBase):
            raise ValueError(f"La clase proporcionada debe heredar de MCPServerBase")
            
        self._servers[name] = {
            "class": server_class,
            "config": kwargs
        }
        self.logger.info(f"Servidor MCP registrado: {name}")
    
    def register_client(
        self, 
        name: str, 
        client_class: Type[MCPClientBase], 
        **kwargs
    ) -> None:
        """
        Registra una clase de cliente MCP.
        
        Args:
            name: Nombre único para el cliente
            client_class: Clase del cliente (debe heredar de MCPClientBase)
            **kwargs: Configuración por defecto para instancias de este cliente
        
        Raises:
            ValueError: Si el nombre ya está registrado o la clase no es válida
        """
        if name in self._clients:
            raise ValueError(f"Ya existe un cliente registrado con el nombre '{name}'")
            
        if not inspect.isclass(client_class) or not issubclass(client_class, MCPClientBase):
            raise ValueError(f"La clase proporcionada debe heredar de MCPClientBase")
            
        self._clients[name] = {
            "class": client_class,
            "config": kwargs
        }
        self.logger.info(f"Cliente MCP registrado: {name}")
    
    def create_server(self, name: str, **kwargs) -> MCPServerBase:
        """
        Crea una instancia de un servidor MCP registrado.
        
        Args:
            name: Nombre del servidor registrado
            **kwargs: Configuración específica para esta instancia
                      (sobrescribe la configuración por defecto)
        
        Returns:
            Instancia del servidor MCP
            
        Raises:
            ValueError: Si el servidor no está registrado
        """
        if name not in self._servers:
            raise ValueError(f"No hay un servidor registrado con el nombre '{name}'")
            
        server_info = self._servers[name]
        server_class = server_info["class"]
        
        # Combinar configuración por defecto con específica
        config = {**server_info["config"], **kwargs}
        
        return server_class(**config)
    
    def create_client(self, name: str, **kwargs) -> MCPClientBase:
        """
        Crea una instancia de un cliente MCP registrado.
        
        Args:
            name: Nombre del cliente registrado
            **kwargs: Configuración específica para esta instancia
                      (sobrescribe la configuración por defecto)
        
        Returns:
            Instancia del cliente MCP
            
        Raises:
            ValueError: Si el cliente no está registrado
        """
        if name not in self._clients:
            raise ValueError(f"No hay un cliente registrado con el nombre '{name}'")
            
        client_info = self._clients[name]
        client_class = client_info["class"]
        
        # Combinar configuración por defecto con específica
        config = {**client_info["config"], **kwargs}
        
        return client_class(**config)
    
    def get_server_instance(self, name: str, **kwargs) -> MCPServerBase:
        """
        Obtiene una instancia activa del servidor o crea una nueva.
        
        Args:
            name: Nombre del servidor
            **kwargs: Configuración para una nueva instancia
            
        Returns:
            Instancia activa del servidor
            
        Raises:
            ValueError: Si el servidor no está registrado
        """
        if name in self._instances:
            return self._instances[name]
            
        instance = self.create_server(name, **kwargs)
        self._instances[name] = instance
        return instance
    
    def list_server_types(self) -> List[str]:
        """
        Lista los tipos de servidores registrados.
        
        Returns:
            Lista de nombres de servidores registrados
        """
        return list(self._servers.keys())
    
    def list_client_types(self) -> List[str]:
        """
        Lista los tipos de clientes registrados.
        
        Returns:
            Lista de nombres de clientes registrados
        """
        return list(self._clients.keys())
    
    def list_server_instances(self) -> List[str]:
        """
        Lista las instancias activas de servidores.
        
        Returns:
            Lista de nombres de instancias activas
        """
        return list(self._instances.keys())
    
    def shutdown_all_servers(self) -> None:
        """
        Cierra todas las instancias activas de servidores.
        """
        for name, instance in list(self._instances.items()):
            self.logger.info(f"Cerrando servidor: {name}")
            try:
                # Si el servidor tiene un método de cierre, llamarlo
                if hasattr(instance, "shutdown") and callable(getattr(instance, "shutdown")):
                    instance.shutdown()
                
                del self._instances[name]
            except Exception as e:
                self.logger.error(f"Error al cerrar el servidor {name}: {e}")
    
    def load_config_from_file(self, config_path: str) -> None:
        """
        Carga la configuración de servidores y clientes desde un archivo.
        
        Args:
            config_path: Ruta al archivo de configuración YAML
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si la configuración tiene formato inválido
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No se encontró el archivo de configuración: {config_path}")
            
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if not isinstance(config, dict):
                raise ValueError("El archivo de configuración debe contener un diccionario")
                
            # Cargar servidores
            for server_name, server_config in config.get("servers", {}).items():
                if "class" not in server_config:
                    self.logger.warning(f"Falta la clase para el servidor {server_name}")
                    continue
                    
                try:
                    # Importar la clase del servidor
                    module_path, class_name = server_config["class"].rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    server_class = getattr(module, class_name)
                    
                    # Registrar el servidor
                    self.register_server(
                        name=server_name,
                        server_class=server_class,
                        **server_config.get("config", {})
                    )
                except Exception as e:
                    self.logger.error(f"Error registrando servidor {server_name}: {e}")
            
            # Cargar clientes
            for client_name, client_config in config.get("clients", {}).items():
                if "class" not in client_config:
                    self.logger.warning(f"Falta la clase para el cliente {client_name}")
                    continue
                    
                try:
                    # Importar la clase del cliente
                    module_path, class_name = client_config["class"].rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    client_class = getattr(module, class_name)
                    
                    # Registrar el cliente
                    self.register_client(
                        name=client_name,
                        client_class=client_class,
                        **client_config.get("config", {})
                    )
                except Exception as e:
                    self.logger.error(f"Error registrando cliente {client_name}: {e}")
            
            self.logger.info(f"Configuración cargada desde {config_path}")
            
        except Exception as e:
            self.logger.exception(f"Error cargando configuración: {e}")
            raise 