"""
Resource Monitor module for MCP.

This module provides functionality to monitor system resources like CPU, memory, and GPU usage.
"""

import os
import time
import logging
import threading
import psutil
from typing import Dict, List, Optional, Callable

class ResourceMonitor:
    """
    Monitors system resources and provides usage statistics.
    
    The ResourceMonitor runs in a separate thread and periodically checks
    system resource usage, triggering callbacks when thresholds are exceeded.
    
    Attributes:
        logger: Logger instance for this class
        thresholds: Dictionary of resource thresholds
        check_interval: Interval in seconds between resource checks
        callbacks: List of callbacks to call when thresholds are exceeded
        _stop_event: Threading event to signal the monitor to stop
        _thread: Background thread running the monitoring
    """
    
    def __init__(self, thresholds: Dict[str, float], check_interval: int = 5):
        """
        Initialize the ResourceMonitor.
        
        Args:
            thresholds: Dictionary mapping resource names to threshold values (0-100%)
            check_interval: Seconds between resource checks
        """
        self.logger = logging.getLogger("mcp.resource_monitor")
        self.thresholds = thresholds
        self.check_interval = check_interval
        self.callbacks = []
        self._stop_event = threading.Event()
        self._thread = None
        
        # Check if GPU monitoring is available
        self.gpu_available = self._check_gpu_available()
        
        self.logger.info("ResourceMonitor initialized")
        
    def _check_gpu_available(self) -> bool:
        """
        Check if GPU monitoring is available.
        
        Returns:
            Boolean indicating if GPU monitoring is available
        """
        try:
            # Try to import GPU monitoring libraries
            # For NVIDIA GPUs
            import pynvml
            return True
        except ImportError:
            self.logger.warning("GPU monitoring not available (pynvml not installed)")
            return False
    
    def start(self):
        """Start the resource monitoring thread."""
        if self._thread is not None and self._thread.is_alive():
            self.logger.warning("Resource monitor is already running")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop(self):
        """Stop the resource monitoring thread."""
        if self._thread is None or not self._thread.is_alive():
            self.logger.warning("Resource monitor is not running")
            return
            
        self._stop_event.set()
        self._thread.join(timeout=self.check_interval * 2)
        self.logger.info("Resource monitoring stopped")
    
    def add_callback(self, callback: Callable[[str, float], None]):
        """
        Add a callback to be called when a threshold is exceeded.
        
        The callback will be called with the resource name and current value.
        
        Args:
            callback: Function to call with (resource_name, current_value) when threshold exceeded
        """
        self.callbacks.append(callback)
    
    def get_current_usage(self) -> Dict[str, float]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary mapping resource names to usage percentages
        """
        usage = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        }
        
        # Add GPU stats if available
        if self.gpu_available:
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # First GPU
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                usage["gpu_memory_percent"] = (mem_info.used / mem_info.total) * 100
                pynvml.nvmlShutdown()
            except Exception as e:
                self.logger.warning(f"Failed to get GPU stats: {e}")
        
        return usage
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in background thread."""
        while not self._stop_event.is_set():
            try:
                # Get current usage
                usage = self.get_current_usage()
                
                # Check thresholds
                for resource, value in usage.items():
                    threshold = self.thresholds.get(resource)
                    if threshold is not None and value > threshold:
                        self.logger.warning(f"{resource} usage ({value:.1f}%) exceeds threshold ({threshold:.1f}%)")
                        for callback in self.callbacks:
                            try:
                                callback(resource, value)
                            except Exception as e:
                                self.logger.error(f"Error in resource callback: {e}")
            
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
            
            # Wait for next check or until stopped
            self._stop_event.wait(self.check_interval) 