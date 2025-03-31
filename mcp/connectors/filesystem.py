"""
Conector de sistema de archivos para MCP.

Este módulo proporciona un conector que permite a los servidores MCP
interactuar con el sistema de archivos local.
"""

import os
import pathlib
import logging
import shutil
from typing import Dict, Any, List, Optional, Union, Tuple

class FilesystemConnector:
    """
    Conector para acceso al sistema de archivos local.
    
    Esta clase proporciona métodos para interactuar con el sistema de archivos,
    incluyendo operaciones de lectura, escritura, búsqueda y manipulación.
    
    Attributes:
        root_path: Ruta raíz desde la que se realizan todas las operaciones
        allow_write: Si se permiten operaciones de escritura
        logger: Logger para esta clase
    """
    
    def __init__(
        self, 
        root_path: str = ".",
        allow_write: bool = False,
        max_file_size: int = 10 * 1024 * 1024  # 10 MB por defecto
    ):
        """
        Inicializa el conector del sistema de archivos.
        
        Args:
            root_path: Ruta raíz para las operaciones (relativa o absoluta)
            allow_write: Si se permiten operaciones de escritura
            max_file_size: Tamaño máximo permitido para archivos (en bytes)
        """
        # Normalizar y convertir a ruta absoluta
        self.root_path = os.path.abspath(root_path)
        self.allow_write = allow_write
        self.max_file_size = max_file_size
        self.logger = logging.getLogger("mcp.connectors.filesystem")
        
        self.logger.info(f"Conector de sistema de archivos inicializado con raíz: {self.root_path}")
        self.logger.info(f"Operaciones de escritura: {'permitidas' if self.allow_write else 'no permitidas'}")
        
    def _resolve_path(self, path: str) -> str:
        """
        Resuelve una ruta relativa a la ruta raíz.
        
        Args:
            path: Ruta relativa a resolver
            
        Returns:
            Ruta absoluta resuelta
            
        Raises:
            ValueError: Si la ruta intenta acceder a una ubicación fuera de la raíz
        """
        # Normalizar la ruta y quitar separadores iniciales
        norm_path = os.path.normpath(path.lstrip('/\\'))
        
        # Construir la ruta absoluta
        abs_path = os.path.abspath(os.path.join(self.root_path, norm_path))
        
        # Verificar que la ruta esté dentro de la ruta raíz
        if not abs_path.startswith(self.root_path):
            self.logger.warning(f"Intento de acceso fuera de la raíz: {path} -> {abs_path}")
            raise ValueError(f"La ruta {path} intenta acceder fuera del directorio raíz")
            
        return abs_path
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Obtiene información de un archivo o directorio.
        
        Args:
            path: Ruta al archivo o directorio
            
        Returns:
            Diccionario con información del archivo/directorio
            
        Raises:
            FileNotFoundError: Si el archivo o directorio no existe
        """
        resolved_path = self._resolve_path(path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Archivo o directorio no encontrado: {path}")
            
        stat_result = os.stat(resolved_path)
        is_dir = os.path.isdir(resolved_path)
        
        result = {
            "name": os.path.basename(resolved_path),
            "path": path,  # Devolvemos la ruta original, no la resuelta
            "type": "directory" if is_dir else "file",
            "size": stat_result.st_size if not is_dir else None,
            "created": stat_result.st_ctime,
            "modified": stat_result.st_mtime,
            "accessed": stat_result.st_atime,
            "is_dir": is_dir,
            "is_file": os.path.isfile(resolved_path),
            "permissions": stat_result.st_mode & 0o777
        }
        
        # Agregar extensión y tipo MIME para archivos
        if not is_dir:
            result["extension"] = os.path.splitext(resolved_path)[1].lstrip('.').lower()
            
        return result
        
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """
        Lista el contenido de un directorio.
        
        Args:
            path: Ruta al directorio
            
        Returns:
            Lista de diccionarios con información de cada elemento
            
        Raises:
            FileNotFoundError: Si el directorio no existe
            NotADirectoryError: Si la ruta no es un directorio
        """
        resolved_path = self._resolve_path(path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Directorio no encontrado: {path}")
            
        if not os.path.isdir(resolved_path):
            raise NotADirectoryError(f"La ruta no es un directorio: {path}")
            
        result = []
        
        for item in os.listdir(resolved_path):
            item_path = os.path.join(path, item).replace('\\', '/')
            try:
                item_info = self.get_file_info(item_path)
                result.append(item_info)
            except Exception as e:
                self.logger.warning(f"Error obteniendo información de {item_path}: {str(e)}")
                
        return result
        
    def read_file(self, path: str, max_size: Optional[int] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Lee el contenido de un archivo.
        
        Args:
            path: Ruta al archivo
            max_size: Tamaño máximo a leer (None para usar el valor por defecto)
            
        Returns:
            Tupla con (contenido_bytes, info_archivo)
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            IsADirectoryError: Si la ruta es un directorio
            ValueError: Si el archivo es demasiado grande
        """
        resolved_path = self._resolve_path(path)
        max_size = max_size or self.max_file_size
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
            
        if os.path.isdir(resolved_path):
            raise IsADirectoryError(f"La ruta es un directorio, no un archivo: {path}")
            
        file_size = os.path.getsize(resolved_path)
        if file_size > max_size:
            raise ValueError(f"Archivo demasiado grande ({file_size} bytes, máximo {max_size})")
            
        with open(resolved_path, 'rb') as f:
            content = f.read()
            
        info = self.get_file_info(path)
        
        return content, info
        
    def write_file(self, path: str, content: Union[str, bytes]) -> Dict[str, Any]:
        """
        Escribe contenido en un archivo.
        
        Args:
            path: Ruta al archivo
            content: Contenido a escribir (str o bytes)
            
        Returns:
            Diccionario con información del archivo escrito
            
        Raises:
            PermissionError: Si no se permiten operaciones de escritura
            ValueError: Si el contenido es demasiado grande
        """
        if not self.allow_write:
            raise PermissionError("Operaciones de escritura no permitidas")
            
        resolved_path = self._resolve_path(path)
        
        # Asegurar que el directorio padre exista
        parent_dir = os.path.dirname(resolved_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Convertir a bytes si es necesario
        if isinstance(content, str):
            content = content.encode('utf-8')
            
        # Verificar tamaño
        if len(content) > self.max_file_size:
            raise ValueError(f"Contenido demasiado grande ({len(content)} bytes, máximo {self.max_file_size})")
            
        # Escribir archivo
        with open(resolved_path, 'wb') as f:
            f.write(content)
            
        return self.get_file_info(path)
        
    def delete_item(self, path: str, recursive: bool = False) -> bool:
        """
        Elimina un archivo o directorio.
        
        Args:
            path: Ruta al archivo o directorio
            recursive: Si se permite borrado recursivo para directorios
            
        Returns:
            True si se eliminó correctamente
            
        Raises:
            PermissionError: Si no se permiten operaciones de escritura
            FileNotFoundError: Si el archivo o directorio no existe
            IsADirectoryError: Si es un directorio no vacío y recursive=False
        """
        if not self.allow_write:
            raise PermissionError("Operaciones de escritura no permitidas")
            
        resolved_path = self._resolve_path(path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Archivo o directorio no encontrado: {path}")
            
        if os.path.isdir(resolved_path):
            if recursive:
                shutil.rmtree(resolved_path)
            else:
                # Verificar si está vacío
                if os.listdir(resolved_path):
                    raise IsADirectoryError(f"El directorio no está vacío: {path}")
                os.rmdir(resolved_path)
        else:
            os.unlink(resolved_path)
            
        return True
        
    def search_files(
        self, 
        path: str, 
        pattern: str, 
        recursive: bool = True, 
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Busca archivos que coincidan con un patrón.
        
        Args:
            path: Ruta base para la búsqueda
            pattern: Patrón glob para buscar (ej: '*.txt')
            recursive: Si la búsqueda debe ser recursiva
            max_results: Número máximo de resultados
            
        Returns:
            Lista de diccionarios con información de archivos encontrados
        """
        resolved_path = self._resolve_path(path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Directorio de búsqueda no encontrado: {path}")
            
        if not os.path.isdir(resolved_path):
            raise NotADirectoryError(f"La ruta no es un directorio: {path}")
            
        results = []
        p = pathlib.Path(resolved_path)
        
        # Realizar búsqueda
        glob_pattern = '**/'+pattern if recursive else pattern
        matches = list(p.glob(glob_pattern))
        
        # Limitar resultados
        for match in matches[:max_results]:
            rel_path = os.path.relpath(match, self.root_path)
            norm_path = rel_path.replace('\\', '/')
            try:
                info = self.get_file_info(norm_path)
                results.append(info)
            except Exception as e:
                self.logger.warning(f"Error obteniendo información de {norm_path}: {str(e)}")
                
        return results 