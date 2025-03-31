"""
Gestor de archivos temporales para TTS.

Este módulo proporciona la clase TTSFileManager que se encarga de gestionar
los archivos de audio temporales generados por el sistema TTS, incluyendo
su creación, seguimiento y limpieza automática.
"""

import os
import time
import logging
import shutil
import hashlib
import threading
from typing import Optional, Dict, List, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

class TTSFileManager:
    """
    Gestor para manejar archivos temporales de TTS y su limpieza.
    
    Este componente se encarga de:
    - Llevar registro de archivos creados
    - Realizar limpieza periódica
    - Controlar límites de espacio
    - Proporcionar políticas de caché
    """
    
    def __init__(
        self, 
        temp_dir: Optional[str] = None, 
        max_size_mb: float = 100.0, 
        max_age_hours: float = 24.0, 
        cleanup_interval_minutes: float = 60.0,
        enable_auto_cleanup: bool = True,
        cache_enabled: bool = True
    ):
        """
        Inicializa el gestor de archivos temporales.
        
        Args:
            temp_dir: Directorio para archivos temporales (si es None, usa el directorio por defecto)
            max_size_mb: Tamaño máximo en MB para la carpeta temporal
            max_age_hours: Edad máxima de archivos en horas
            cleanup_interval_minutes: Intervalo entre limpiezas automáticas
            enable_auto_cleanup: Si True, activa la limpieza automática periódica
            cache_enabled: Si True, habilita el caché de archivos
        """
        # Configurar logger
        self.logger = logging.getLogger(__name__)
        
        # Configurar directorio temporal
        if temp_dir is None:
            # Usar el directorio temp dentro del paquete tts
            self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        else:
            self.temp_dir = temp_dir
            
        # Crear el directorio si no existe
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Configurar límites
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convertir MB a bytes
        self.max_age_seconds = max_age_hours * 3600  # Convertir horas a segundos
        self.cleanup_interval_seconds = cleanup_interval_minutes * 60  # Convertir minutos a segundos
        
        # Opciones
        self.enable_auto_cleanup = enable_auto_cleanup
        self.cache_enabled = cache_enabled
        
        # Estado interno
        self.running = True
        self.cleanup_thread = None
        self._file_registry = {}  # id -> {path, hash, created_at, last_used, usage_count}
        self._hash_map = {}  # hash -> id
        
        # Ruta del archivo de registro
        self.registry_file = os.path.join(self.temp_dir, '.tts_file_registry.json')
        
        # Cargar registro existente si está disponible
        self._load_registry()
        
        # Limpieza inicial
        self.cleanup(force=True)
        
        # Iniciar limpieza automática si está habilitada
        if self.enable_auto_cleanup:
            self._start_auto_cleanup()
            
        self.logger.info(f"TTSFileManager inicializado. Dir: {self.temp_dir}, Límite: {max_size_mb}MB")
    
    def _load_registry(self) -> None:
        """Carga el registro de archivos desde disco si existe."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verificar estructura mínima esperada
                if isinstance(data, dict) and "files" in data:
                    self._file_registry = data["files"]
                    
                    # Reconstruir el mapa de hash
                    self._hash_map = {}
                    for file_id, info in self._file_registry.items():
                        if "hash" in info:
                            self._hash_map[info["hash"]] = file_id
                    
                    self.logger.info(f"Registro de archivos cargado: {len(self._file_registry)} archivos")
                else:
                    self.logger.warning("Formato de registro inválido, iniciando con registro vacío")
            except Exception as e:
                self.logger.error(f"Error al cargar registro: {e}")
        else:
            self.logger.info("No se encontró registro existente, iniciando con registro vacío")
    
    def _save_registry(self) -> None:
        """Guarda el registro de archivos en disco."""
        try:
            # Preparar datos para guardar
            data = {
                "last_updated": datetime.now().isoformat(),
                "files": self._file_registry
            }
            
            # Guardar en archivo JSON
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Registro guardado en {self.registry_file}")
        except Exception as e:
            self.logger.error(f"Error al guardar registro: {e}")
    
    def _start_auto_cleanup(self) -> None:
        """Inicia el hilo de limpieza automática."""
        def cleanup_worker():
            while self.running:
                time.sleep(self.cleanup_interval_seconds)
                if not self.running:
                    break
                try:
                    self.cleanup()
                except Exception as e:
                    self.logger.error(f"Error en limpieza automática: {e}")
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        self.logger.info(f"Limpieza automática iniciada (intervalo: {self.cleanup_interval_seconds/60:.1f} minutos)")
    
    def stop(self) -> None:
        """Detiene el hilo de limpieza automática y guarda el registro."""
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=1.0)
        self._save_registry()
        self.logger.info("TTSFileManager detenido")
    
    def register_file(self, 
                      file_path: str, 
                      content_hash: Optional[str] = None, 
                      metadata: Optional[Dict] = None) -> str:
        """
        Registra un archivo en el sistema.
        
        Args:
            file_path: Ruta al archivo
            content_hash: Hash del contenido (opcional)
            metadata: Metadatos adicionales (opcional)
            
        Returns:
            ID único del archivo registrado
        """
        # Generar ID único para el archivo
        file_id = os.path.basename(file_path)
        
        # Si no se proporciona hash, calcular uno basado en el archivo
        if not content_hash and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read(8192)  # Leer primeros 8KB para el hash
                content_hash = hashlib.md5(content).hexdigest()
            except Exception as e:
                self.logger.warning(f"No se pudo calcular hash del archivo {file_path}: {e}")
                content_hash = None
        
        # Registrar archivo
        now = datetime.now().isoformat()
        self._file_registry[file_id] = {
            "path": file_path,
            "hash": content_hash,
            "created_at": now,
            "last_used": now,
            "usage_count": 1,
            "metadata": metadata or {}
        }
        
        # Actualizar mapa de hash si está disponible
        if content_hash and self.cache_enabled:
            self._hash_map[content_hash] = file_id
        
        # Guardar registro actualizado
        self._save_registry()
        
        return file_id
    
    def mark_file_used(self, file_id: str) -> bool:
        """
        Marca un archivo como utilizado, actualizando su timestamp.
        
        Args:
            file_id: ID del archivo
            
        Returns:
            True si se actualizó correctamente, False si no se encontró
        """
        if file_id in self._file_registry:
            self._file_registry[file_id]["last_used"] = datetime.now().isoformat()
            self._file_registry[file_id]["usage_count"] += 1
            return True
        return False
    
    def get_from_cache(self, content_hash: str) -> Optional[str]:
        """
        Busca un archivo en el caché usando su hash de contenido.
        
        Args:
            content_hash: Hash del contenido a buscar
            
        Returns:
            Ruta al archivo si existe en caché, None si no se encuentra
        """
        if not self.cache_enabled:
            return None
            
        # Buscar en el mapa de hash
        file_id = self._hash_map.get(content_hash)
        if not file_id:
            return None
            
        # Verificar que el archivo existe
        file_info = self._file_registry.get(file_id)
        if not file_info:
            # Limpiar entrada inválida
            if content_hash in self._hash_map:
                del self._hash_map[content_hash]
            return None
            
        file_path = file_info["path"]
        if not os.path.exists(file_path):
            # Limpiar entrada para archivo que ya no existe
            self._remove_from_registry(file_id)
            return None
            
        # Actualizar uso
        self.mark_file_used(file_id)
        
        return file_path
    
    def _remove_from_registry(self, file_id: str) -> None:
        """
        Elimina un archivo del registro.
        
        Args:
            file_id: ID del archivo a eliminar
        """
        if file_id in self._file_registry:
            # Limpiar hash map si es necesario
            content_hash = self._file_registry[file_id].get("hash")
            if content_hash and content_hash in self._hash_map:
                del self._hash_map[content_hash]
                
            # Eliminar del registro
            del self._file_registry[file_id]
    
    def get_directory_size(self) -> int:
        """
        Calcula el tamaño total del directorio temporal.
        
        Returns:
            Tamaño en bytes
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(self.temp_dir):
            for f in filenames:
                # Ignorar el archivo de registro
                if f == os.path.basename(self.registry_file):
                    continue
                    
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    
    def get_files_by_age(self, max_files: int = 1000) -> List[Tuple[str, datetime]]:
        """
        Obtiene una lista de archivos ordenados por antigüedad.
        
        Args:
            max_files: Número máximo de archivos a devolver
            
        Returns:
            Lista de tuplas (ruta_archivo, fecha_última_modificación)
        """
        files = []
        
        # Recorrer directorio
        for filename in os.listdir(self.temp_dir):
            # Ignorar archivos especiales
            if filename.startswith('.'):
                continue
                
            file_path = os.path.join(self.temp_dir, filename)
            if not os.path.isfile(file_path):
                continue
                
            # Obtener fecha de última modificación
            try:
                mtime = os.path.getmtime(file_path)
                mtime_dt = datetime.fromtimestamp(mtime)
                files.append((file_path, mtime_dt))
            except Exception:
                # Ignorar archivos con error al obtener mtime
                continue
        
        # Ordenar por antigüedad (más antiguos primero)
        files.sort(key=lambda x: x[1])
        
        return files[:max_files]
    
    def cleanup(self, force: bool = False) -> Dict:
        """
        Realiza limpieza de archivos temporales.
        
        Args:
            force: Si True, ignora el intervalo mínimo entre limpiezas
            
        Returns:
            Diccionario con resultados de la limpieza
        """
        results = {
            "deleted_by_age": 0,
            "deleted_by_size": 0,
            "errors": 0,
            "bytes_freed": 0,
            "registry_entries_removed": 0
        }
        
        self.logger.info("Iniciando limpieza de archivos temporales")
        
        # Paso 1: Verificar y eliminar archivos antiguos
        now = time.time()
        for dirpath, _, filenames in os.walk(self.temp_dir):
            for filename in filenames:
                # Ignorar archivos especiales
                if filename.startswith('.'):
                    continue
                    
                file_path = os.path.join(dirpath, filename)
                
                try:
                    # Verificar antigüedad
                    mtime = os.path.getmtime(file_path)
                    age_seconds = now - mtime
                    
                    if age_seconds > self.max_age_seconds:
                        # Guardar tamaño para estadísticas
                        size = os.path.getsize(file_path)
                        
                        # Eliminar archivo
                        os.remove(file_path)
                        
                        # Eliminar del registro si existe
                        self._remove_from_registry(filename)
                        
                        results["deleted_by_age"] += 1
                        results["bytes_freed"] += size
                        
                        self.logger.debug(f"Archivo eliminado por antigüedad: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error al procesar archivo {file_path}: {e}")
                    results["errors"] += 1
        
        # Paso 2: Verificar tamaño total y eliminar archivos por tamaño si es necesario
        dir_size = self.get_directory_size()
        
        if dir_size > self.max_size_bytes:
            # Calcular cuánto espacio debemos liberar (apuntamos a 80% del máximo)
            target_size = int(self.max_size_bytes * 0.8)
            bytes_to_free = dir_size - target_size
            
            self.logger.info(f"Directorio excede tamaño máximo. Actual: {dir_size/1024/1024:.1f}MB, Objetivo: {target_size/1024/1024:.1f}MB")
            
            # Obtener archivos ordenados por antigüedad
            files_by_age = self.get_files_by_age()
            
            # Eliminar archivos hasta alcanzar el tamaño objetivo
            freed_bytes = 0
            for file_path, _ in files_by_age:
                if freed_bytes >= bytes_to_free:
                    break
                    
                try:
                    # Obtener tamaño
                    size = os.path.getsize(file_path)
                    
                    # Eliminar archivo
                    os.remove(file_path)
                    
                    # Actualizar estadísticas
                    freed_bytes += size
                    results["deleted_by_size"] += 1
                    results["bytes_freed"] += size
                    
                    # Eliminar del registro
                    filename = os.path.basename(file_path)
                    self._remove_from_registry(filename)
                    
                    self.logger.debug(f"Archivo eliminado por tamaño: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error al eliminar archivo {file_path}: {e}")
                    results["errors"] += 1
        
        # Paso 3: Limpiar entradas de registro para archivos que ya no existen
        ids_to_remove = []
        for file_id, info in self._file_registry.items():
            path = info.get("path")
            if not path or not os.path.exists(path):
                ids_to_remove.append(file_id)
        
        # Eliminar entradas
        for file_id in ids_to_remove:
            self._remove_from_registry(file_id)
            results["registry_entries_removed"] += 1
        
        # Guardar registro actualizado
        self._save_registry()
        
        # Registrar resultados
        self.logger.info(f"Limpieza completada: {results['deleted_by_age']} por antigüedad, " +
                        f"{results['deleted_by_size']} por tamaño, " +
                        f"{results['bytes_freed']/1024/1024:.1f}MB liberados")
        
        return results
    
    def generate_filename(self, prefix: str = "tts_output", extension: str = "mp3") -> str:
        """
        Genera un nombre de archivo único para un nuevo archivo de audio.
        
        Args:
            prefix: Prefijo para el nombre de archivo
            extension: Extensión del archivo (sin punto)
            
        Returns:
            Ruta completa al nuevo archivo
        """
        # Generar nombre único
        unique_id = str(hash(time.time() + hash(os.urandom(8))))
        filename = f"{prefix}_{unique_id}.{extension}"
        
        # Ruta completa
        path = os.path.join(self.temp_dir, filename)
        
        return path
    
    def get_hash_for_text(self, text: str, voice_id: str, **params) -> str:
        """
        Genera un hash único para una combinación de texto y parámetros TTS.
        
        Args:
            text: Texto a convertir
            voice_id: ID de voz a utilizar
            **params: Parámetros adicionales
            
        Returns:
            String con el hash
        """
        # Normalizar texto (quitar espacios extras, etc)
        normalized_text = " ".join(text.split())
        
        # Crear cadena para hash
        hash_input = f"{normalized_text}|{voice_id}"
        
        # Añadir parámetros relevantes
        if "model_id" in params:
            hash_input += f"|model:{params['model_id']}"
        if "stability" in params:
            hash_input += f"|stab:{params['stability']}"
        if "similarity_boost" in params:
            hash_input += f"|sim:{params['similarity_boost']}"
        
        # Calcular hash
        content_hash = hashlib.md5(hash_input.encode()).hexdigest()
        
        return content_hash 