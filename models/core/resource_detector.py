"""
Detector de recursos del sistema.

Este módulo proporciona clases para detectar los recursos de hardware disponibles
en el sistema, como CPU, RAM, GPU y VRAM.
"""

import os
import logging
import platform
import psutil
from typing import Dict, Any, List, Optional

class ResourceDetector:
    """
    Detector de recursos del sistema.
    
    Esta clase proporciona métodos para detectar los recursos disponibles
    en el sistema, como CPU, RAM, GPU y VRAM.
    
    Attributes:
        logger: Logger para esta clase
    """
    
    def __init__(self):
        """Inicializa el detector de recursos."""
        self.logger = logging.getLogger("models.resource_detector")
        self._resources_cache = None
    
    def detect_resources(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Detecta los recursos disponibles en el sistema.
        
        Args:
            force_refresh: Si es True, fuerza una nueva detección de recursos
                           ignorando la caché
                           
        Returns:
            Diccionario con información sobre los recursos disponibles
        """
        if self._resources_cache is None or force_refresh:
            self.logger.info("Detectando recursos del sistema...")
            
            resources = {
                "system": self._detect_system_info(),
                "cpu": self._detect_cpu_info(),
                "memory": self._detect_memory_info(),
                "gpu": self._detect_gpu_info()
            }
            
            self._resources_cache = resources
            self.logger.info("Detección de recursos completada")
            
        return self._resources_cache
    
    def _detect_system_info(self) -> Dict[str, str]:
        """
        Detecta información básica del sistema.
        
        Returns:
            Diccionario con información del sistema
        """
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        }
    
    def _detect_cpu_info(self) -> Dict[str, Any]:
        """
        Detecta información sobre la CPU.
        
        Returns:
            Diccionario con información de la CPU
        """
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_frequency": psutil.cpu_freq(),
            "cpu_percent": psutil.cpu_percent(interval=1)
        }
        
        # Intentar obtener información adicional en sistemas Linux
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpu_info_text = f.read()
                    
                # Extraer modelo de CPU en Linux
                for line in cpu_info_text.split("\n"):
                    if "model name" in line:
                        cpu_info["model_name"] = line.split(":")[1].strip()
                        break
            except Exception as e:
                self.logger.warning(f"No se pudo obtener información adicional de CPU: {e}")
                
        return cpu_info
    
    def _detect_memory_info(self) -> Dict[str, Any]:
        """
        Detecta información sobre la memoria del sistema.
        
        Returns:
            Diccionario con información de la memoria
        """
        memory = psutil.virtual_memory()
        
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent_used": memory.percent
        }
    
    def _detect_gpu_info(self) -> Dict[str, Any]:
        """
        Detecta información sobre las GPUs disponibles.
        
        Returns:
            Diccionario con información de las GPUs
        """
        gpu_info = {
            "available": False,
            "devices": []
        }
        
        # Intentar detectar GPUs NVIDIA
        try:
            import pynvml
            pynvml.nvmlInit()
            
            gpu_info["available"] = True
            gpu_info["count"] = pynvml.nvmlDeviceGetCount()
            
            for i in range(gpu_info["count"]):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                device_name = pynvml.nvmlDeviceGetName(handle)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                device_info = {
                    "index": i,
                    "name": device_name,
                    "total_memory_gb": round(memory_info.total / (1024**3), 2),
                    "free_memory_gb": round(memory_info.free / (1024**3), 2),
                    "used_memory_gb": round(memory_info.used / (1024**3), 2),
                    "memory_percent_used": round((memory_info.used / memory_info.total) * 100, 2)
                }
                
                gpu_info["devices"].append(device_info)
                
            pynvml.nvmlShutdown()
            
        except ImportError:
            self.logger.info("PyNVML no está instalado. No se puede detectar GPUs NVIDIA.")
        except Exception as e:
            self.logger.warning(f"Error detectando GPUs NVIDIA: {e}")
            
        # Intento alternativo con PyTorch
        if not gpu_info["available"]:
            try:
                import torch
                
                if torch.cuda.is_available():
                    gpu_info["available"] = True
                    gpu_info["count"] = torch.cuda.device_count()
                    
                    for i in range(gpu_info["count"]):
                        props = torch.cuda.get_device_properties(i)
                        device_info = {
                            "index": i,
                            "name": props.name,
                            "total_memory_gb": round(props.total_memory / (1024**3), 2),
                            # PyTorch no proporciona memoria libre/usada directamente
                            "compute_capability": f"{props.major}.{props.minor}"
                        }
                        
                        gpu_info["devices"].append(device_info)
                        
            except ImportError:
                self.logger.info("PyTorch no está instalado. No se puede detectar GPUs con PyTorch.")
            except Exception as e:
                self.logger.warning(f"Error detectando GPUs con PyTorch: {e}")
                
        return gpu_info
    
    def estimate_optimal_device(
        self,
        model_size_gb: float,
        context_length: int = 2048
    ) -> Dict[str, Any]:
        """
        Estima el dispositivo óptimo para ejecutar un modelo.
        
        Args:
            model_size_gb: Tamaño estimado del modelo en GB
            context_length: Longitud del contexto
            
        Returns:
            Diccionario con información sobre el dispositivo recomendado
        """
        resources = self.detect_resources()
        
        # Memoria requerida aproximada (modelo + contexto + overhead)
        # Fórmula simplificada: tamaño_modelo + (contexto * factor_overhead)
        context_overhead_gb = (context_length / 2048) * 0.5  # ~0.5GB por 2048 tokens de contexto
        total_required_gb = model_size_gb + context_overhead_gb
        
        # Verificar si hay GPU disponible con memoria suficiente
        if resources["gpu"]["available"]:
            for device in resources["gpu"]["devices"]:
                if device.get("free_memory_gb", 0) > total_required_gb * 1.2:  # 20% de margen
                    return {
                        "device": "gpu",
                        "index": device["index"],
                        "name": device["name"],
                        "available_memory": device.get("free_memory_gb", device.get("total_memory_gb")),
                        "required_memory": total_required_gb
                    }
        
        # Si no hay GPU adecuada, verificar CPU
        if resources["memory"]["available_gb"] > total_required_gb * 1.5:  # 50% de margen para CPU
            return {
                "device": "cpu",
                "cores": resources["cpu"]["logical_cores"],
                "available_memory": resources["memory"]["available_gb"],
                "required_memory": total_required_gb
            }
        
        # Si ningún dispositivo tiene recursos suficientes, recomendar el que tenga más
        if resources["gpu"]["available"]:
            max_memory_device = max(
                resources["gpu"]["devices"], 
                key=lambda d: d.get("free_memory_gb", d.get("total_memory_gb", 0))
            )
            
            return {
                "device": "gpu",
                "index": max_memory_device["index"],
                "name": max_memory_device["name"],
                "available_memory": max_memory_device.get("free_memory_gb", max_memory_device.get("total_memory_gb")),
                "required_memory": total_required_gb,
                "warning": "Recursos insuficientes. El modelo puede funcionar lentamente o fallar."
            }
        
        # Si no hay GPU, recomendar CPU con advertencia
        return {
            "device": "cpu",
            "cores": resources["cpu"]["logical_cores"],
            "available_memory": resources["memory"]["available_gb"],
            "required_memory": total_required_gb,
            "warning": "Recursos insuficientes. El modelo puede funcionar lentamente o fallar."
        } 