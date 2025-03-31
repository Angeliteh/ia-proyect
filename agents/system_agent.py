"""
System Agent module.

This agent specializes in system-related tasks, including:
- File operations (read/write/list)
- Process management
- Application execution
- System information retrieval
- Basic system monitoring
"""

import os
import sys
import platform
import subprocess
import logging
import shutil
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

from .base import BaseAgent, AgentResponse


class SystemAgent(BaseAgent):
    """
    Agent specialized in system-related tasks.
    
    This agent can interact with the operating system to perform
    various tasks such as file operations, process management,
    and application execution.
    
    Attributes:
        working_dir: Current working directory for file operations
        os_type: Type of operating system (Windows, Linux, macOS)
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the system agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary containing:
                - working_dir: Initial working directory (optional)
                - allowed_executables: List of allowed executables (optional)
                - restricted_dirs: List of restricted directories (optional)
        """
        super().__init__(agent_id, config)
        
        # Set up working directory
        self.working_dir = config.get("working_dir", os.getcwd())
        self.logger.info(f"Working directory: {self.working_dir}")
        
        # Determine OS type
        self.os_type = platform.system()
        self.logger.info(f"Operating system: {self.os_type}")
        
        # Security settings
        self.allowed_executables = config.get("allowed_executables", [])
        self.restricted_dirs = config.get("restricted_dirs", [])
        
        # Add standard directories to restricted list if not specified
        if not self.restricted_dirs:
            if self.os_type == "Windows":
                self.restricted_dirs = [
                    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"
                ]
            else:  # Linux/macOS
                self.restricted_dirs = [
                    "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/etc", "/var"
                ]
        
        self.logger.info(f"Restricted directories: {self.restricted_dirs}")
        self.logger.info(f"System agent initialized on {self.os_type}")
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a system-related query.
        
        Args:
            query: The system-related query or command
            context: Optional context with:
                - action: Specific action to perform (execute, read_file, etc.)
                - parameters: Parameters for the action
                
        Returns:
            AgentResponse with the processed result
        """
        self.set_state("processing")
        context = context or {}
        
        # Extract action and parameters
        action = context.get("action", self._detect_action(query))
        parameters = context.get("parameters", {})
        
        self.logger.info(f"Processing system task: {action}")
        
        try:
            return await self._process_with_memory(action, query, parameters, context)
        except Exception as e:
            self.logger.error(f"Error processing system task: {str(e)}")
            self.set_state("error")
            return AgentResponse(
                content=f"Error processing your system request: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "action": action,
                    "os_type": self.os_type
                }
            )
    
    async def _process_with_memory(self, action: str, query: str, parameters: Dict, context: Dict) -> AgentResponse:
        """
        Procesa una tarea del sistema utilizando memoria.
        
        Args:
            action: Acción a realizar
            query: Consulta original
            parameters: Parámetros para la acción
            context: Contexto adicional
            
        Returns:
            AgentResponse con el resultado
        """
        # Configuración de memoria
        memory_context = {
            "memory_used": False,
            "operations_found": 0
        }
        
        # Verificar explícitamente si se solicitó usar memoria
        use_memory = context.get("use_memory", True)  # Por defecto usamos memoria
        used_memory_for_params = False
        
        if self.has_memory() and use_memory:
            # Construir consulta de memoria más precisa
            memory_query = f"{action} {query}"
            self.logger.info(f"Buscando operaciones similares con consulta: {memory_query}")
            
            # Intentar buscar operaciones del mismo tipo primero
            similar_operations = self.recall(
                query=memory_query, 
                memory_type="system_operation",
                limit=3
            )
            
            # Si no encontramos, o si hay referencias explícitas al pasado, 
            # buscar de forma más amplia
            contains_past_reference = any(ref in query.lower() for ref in [
                "antes", "anterior", "previo", "último", "consulté", 
                "hace un momento", "recuerdas", "mostré", "dijiste"
            ])
            
            if (not similar_operations and (context.get("use_memory", False) or contains_past_reference)):
                self.logger.info("Búsqueda ampliada de operaciones similares por referencia al pasado")
                similar_operations = self.recall(query=query, limit=5)
            
            # Procesar las operaciones encontradas
            if similar_operations:
                memory_context["memory_used"] = True
                memory_context["operations_found"] = len(similar_operations)
                self.logger.info(f"Encontradas {len(similar_operations)} operaciones similares")
                
                # Para operaciones de archivos, necesitamos la ruta
                if action in ["list_files", "read_file", "write_file"]:
                    self.logger.info(f"Intentando inferir path para {action}")
                    inferred_path = None
                    
                    # Buscar la ruta más relevante
                    for op in similar_operations:
                        if isinstance(op.content, dict):
                            # Priorizar operaciones del mismo tipo
                            if op.content.get("action") == action and "path" in op.content:
                                inferred_path = op.content["path"]
                                self.logger.info(f"Inferido path de operación similar: {inferred_path}")
                                break
                    
                    # Si no encontramos path específico, buscar cualquier path
                    if not inferred_path:
                        for op in similar_operations:
                            if isinstance(op.content, dict) and "path" in op.content:
                                inferred_path = op.content["path"]
                                self.logger.info(f"Inferido path de cualquier operación: {inferred_path}")
                                break
                    
                    # Si encontramos path, usarlo
                    if inferred_path:
                        parameters["path"] = inferred_path
                        used_memory_for_params = True
                        self.logger.info(f"Usando path inferido: {inferred_path}")
            else:
                self.logger.info("No se encontraron operaciones similares en memoria")
        
        # Ejecutar la acción solicitada con los parámetros (posiblemente inferidos)
        result = ""
        if action == "execute_command":
            result = await self._execute_command(parameters.get("command", query))
        elif action == "read_file":
            result = await self._read_file(parameters.get("path", ""))
        elif action == "write_file":
            result = await self._write_file(
                parameters.get("path", ""), 
                parameters.get("content", "")
            )
        elif action == "list_files":
            result = await self._list_files(parameters.get("path", "."))
        elif action == "system_info":
            result = await self._get_system_info()
        elif action == "process_info":
            result = await self._get_process_info(parameters.get("pid"))
        elif action == "launch_app":
            result = await self._launch_application(
                parameters.get("app_name", ""),
                parameters.get("args", [])
            )
        else:
            result = f"Unknown action: {action}. Please use one of the supported actions."
            self.set_state("error")
            return AgentResponse(
                content=result,
                status="error",
                metadata={
                    "error": f"Unknown action: {action}",
                    "memory_used": memory_context.get("memory_used", False),
                    "used_memory_for_params": used_memory_for_params
                }
            )
        
        # Guardar la operación en memoria para futuras referencias
        if self.has_memory():
            # Preparar contenido de memoria con detalles de operación
            memory_content = {
                "action": action,
                "query": query,
                "path": parameters.get("path"),
                "result": result[:500]  # Guardar un resultado truncado para ahorrar espacio
            }
            
            # Determinar importancia según tipo de acción
            if action in ["write_file", "execute_command"]:
                importance = 0.7  # Mayor importancia para operaciones de escritura
            else:
                importance = 0.5  # Importancia estándar para operaciones de lectura
            
            # Recordar esta operación
            memory_id = self.remember(
                content=memory_content,
                importance=importance,
                memory_type="system_operation",
                metadata={
                    "os_type": self.os_type,
                    "working_dir": self.working_dir,
                    "action_type": action
                }
            )
            self.logger.debug(f"Operación de sistema almacenada en memoria: {memory_id}")
        
        self.set_state("idle")
        return AgentResponse(
            content=result,
            metadata={
                "action": action,
                "os_type": self.os_type,
                "memory_used": memory_context.get("memory_used", False),
                "used_memory_for_params": used_memory_for_params,
                **memory_context
            }
        )
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        return [
            "execute_command",
            "read_file",
            "write_file",
            "list_files",
            "system_info",
            "process_info",
            "launch_app"
        ]
    
    def _detect_action(self, query: str) -> str:
        """
        Detect the type of system action from the query.
        
        Args:
            query: The user query
            
        Returns:
            Action type string
        """
        query = query.lower()
        
        if any(x in query for x in ["execute", "run", "command", "terminal", "cmd", "shell"]):
            return "execute_command"
        elif any(x in query for x in ["read", "cat", "show contents", "display file"]):
            return "read_file"
        elif any(x in query for x in ["write", "save", "create file", "update file"]):
            return "write_file"
        elif any(x in query for x in ["list", "ls", "dir", "directory", "files in"]):
            return "list_files"
        elif any(x in query for x in ["system info", "system information", "about system", "hardware"]):
            return "system_info"
        elif any(x in query for x in ["process", "running", "task", "memory usage"]):
            return "process_info"
        elif any(x in query for x in ["launch", "start", "open", "application", "program", "app"]):
            return "launch_app"
        else:
            # Default action
            return "system_info"
    
    async def _execute_command(self, command: str) -> str:
        """
        Executes a system command.
        
        Args:
            command: The command to execute
            
        Returns:
            Command output or error message
        
        Raises:
            ValueError: If the command is not allowed
        """
        # Basic security check - this should be expanded based on requirements
        if self._is_dangerous_command(command):
            raise ValueError(f"Command '{command}' is not allowed for security reasons")
        
        try:
            # Execute the command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=30)
            
            if process.returncode != 0:
                if stderr:
                    return f"Command failed with error: {stderr}"
                else:
                    return f"Command failed with return code: {process.returncode}"
            
            return stdout if stdout else "Command executed successfully with no output"
        except subprocess.TimeoutExpired:
            return "Command execution timed out after 30 seconds"
        except Exception as e:
            raise ValueError(f"Error executing command: {str(e)}")
    
    def _is_dangerous_command(self, command: str) -> bool:
        """
        Check if a command is potentially dangerous.
        
        Args:
            command: The command to check
            
        Returns:
            True if the command is potentially dangerous
        """
        # Basic dangerous command detection
        dangerous_keywords = [
            "rm -rf", "format", "del /f", "deltree", 
            "shutdown", "reboot", "mkfs", ":(){:|:&};:",
            "> /dev/sda", "dd if=/dev/zero", "mv /* /dev/null"
        ]
        
        command_lower = command.lower()
        return any(keyword.lower() in command_lower for keyword in dangerous_keywords)
    
    async def _read_file(self, path: str) -> str:
        """
        Read the contents of a file.
        
        Args:
            path: Path to the file to read
            
        Returns:
            File contents as string
            
        Raises:
            ValueError: If the file doesn't exist or can't be read
        """
        # Resolve path
        if not os.path.isabs(path):
            path = os.path.join(self.working_dir, path)
        
        # Security check
        if self._is_path_restricted(path):
            raise ValueError(f"Access to path '{path}' is restricted")
        
        try:
            if not os.path.exists(path):
                raise ValueError(f"File '{path}' does not exist")
            
            if not os.path.isfile(path):
                raise ValueError(f"'{path}' is not a file")
            
            with open(path, 'r') as file:
                return file.read()
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
    
    async def _write_file(self, path: str, content: str) -> str:
        """
        Write content to a file.
        
        Args:
            path: Path where to write the file
            content: Content to write
            
        Returns:
            Success message
            
        Raises:
            ValueError: If the file can't be written
        """
        # Resolve path
        if not os.path.isabs(path):
            path = os.path.join(self.working_dir, path)
        
        # Security check
        if self._is_path_restricted(path):
            raise ValueError(f"Access to path '{path}' is restricted")
        
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(path, 'w') as file:
                file.write(content)
            
            return f"File written successfully to '{path}'"
        except Exception as e:
            raise ValueError(f"Error writing file: {str(e)}")
    
    async def _list_files(self, path: str) -> str:
        """
        List files in a directory.
        
        Args:
            path: Path to the directory
            
        Returns:
            Formatted string with directory contents
            
        Raises:
            ValueError: If the directory doesn't exist
        """
        # Resolve path
        if not os.path.isabs(path):
            path = os.path.join(self.working_dir, path)
        
        # Security check
        if self._is_path_restricted(path):
            raise ValueError(f"Access to path '{path}' is restricted")
        
        try:
            if not os.path.exists(path):
                raise ValueError(f"Path '{path}' does not exist")
            
            if not os.path.isdir(path):
                raise ValueError(f"'{path}' is not a directory")
            
            # Get directory contents
            items = os.listdir(path)
            
            # Format output
            result = f"Contents of {path}:\n\n"
            
            directories = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    directories.append((item, "Directory"))
                else:
                    size = os.path.getsize(item_path)
                    size_str = self._format_size(size)
                    files.append((item, f"File ({size_str})"))
            
            # Add directories
            if directories:
                result += "Directories:\n"
                for name, type_info in sorted(directories):
                    result += f"  {name}/\n"
                result += "\n"
            
            # Add files
            if files:
                result += "Files:\n"
                for name, type_info in sorted(files):
                    result += f"  {name} - {type_info}\n"
            
            if not directories and not files:
                result += "The directory is empty."
            
            return result
        except Exception as e:
            raise ValueError(f"Error listing files: {str(e)}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024 or unit == 'TB':
                return f"{size_bytes:.2f} {unit}".rstrip('0').rstrip('.') + ' ' + unit
            size_bytes /= 1024
    
    def _is_path_restricted(self, path: str) -> bool:
        """
        Check if a path is in a restricted directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is restricted
        """
        path = os.path.abspath(path)
        
        for restricted_dir in self.restricted_dirs:
            restricted_path = os.path.abspath(restricted_dir)
            if path == restricted_path or path.startswith(restricted_path + os.sep):
                return True
        
        return False
    
    async def _get_system_info(self) -> str:
        """
        Get system information.
        
        Returns:
            Formatted string with system information
        """
        try:
            # Collect system information
            info = {
                "System": platform.system(),
                "Node": platform.node(),
                "Release": platform.release(),
                "Version": platform.version(),
                "Machine": platform.machine(),
                "Processor": platform.processor()
            }
            
            # Get more detailed information using psutil
            memory = psutil.virtual_memory()
            info["Memory Total"] = self._format_size(memory.total)
            info["Memory Available"] = self._format_size(memory.available)
            info["Memory Used"] = f"{memory.percent}%"
            
            disk = psutil.disk_usage('/')
            info["Disk Total"] = self._format_size(disk.total)
            info["Disk Free"] = self._format_size(disk.free)
            info["Disk Used"] = f"{disk.percent}%"
            
            cpu_info = {
                "Physical Cores": psutil.cpu_count(logical=False),
                "Logical Cores": psutil.cpu_count(logical=True),
                "CPU Usage": f"{psutil.cpu_percent(interval=1.0)}%"
            }
            
            # Format output
            result = "System Information:\n\n"
            
            for key, value in info.items():
                result += f"{key}: {value}\n"
            
            result += "\nCPU Information:\n\n"
            for key, value in cpu_info.items():
                result += f"{key}: {value}\n"
            
            return result
        except Exception as e:
            return f"Error getting system information: {str(e)}"
    
    async def _get_process_info(self, pid: Optional[int] = None) -> str:
        """
        Get information about running processes.
        
        Args:
            pid: Process ID to get info for (None for summary of all processes)
            
        Returns:
            Formatted string with process information
        """
        try:
            if pid is not None:
                # Get info for specific process
                try:
                    process = psutil.Process(pid)
                    
                    info = {
                        "PID": process.pid,
                        "Name": process.name(),
                        "Status": process.status(),
                        "Created": process.create_time(),
                        "CPU Usage": f"{process.cpu_percent()}%",
                        "Memory Usage": self._format_size(process.memory_info().rss),
                        "Command": " ".join(process.cmdline())
                    }
                    
                    result = f"Process Information (PID: {pid}):\n\n"
                    for key, value in info.items():
                        result += f"{key}: {value}\n"
                    
                    return result
                except psutil.NoSuchProcess:
                    return f"No process with PID {pid} found"
            else:
                # Get summary of all processes
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                    try:
                        mem = self._format_size(proc.info['memory_info'].rss) if proc.info['memory_info'] else "N/A"
                        processes.append({
                            "PID": proc.info['pid'],
                            "Name": proc.info['name'],
                            "CPU": f"{proc.info['cpu_percent']}%",
                            "Memory": mem
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Sort by memory usage (if available)
                processes.sort(key=lambda x: x["Name"])
                
                # Show top 10 processes
                result = "Top 10 Processes by Name:\n\n"
                result += f"{'PID':<7} {'Name':<20} {'CPU':<7} {'Memory':<10}\n"
                result += "-" * 50 + "\n"
                
                for proc in processes[:10]:
                    result += f"{proc['PID']:<7} {proc['Name'][:20]:<20} {proc['CPU']:<7} {proc['Memory']:<10}\n"
                
                result += f"\nTotal Processes: {len(processes)}"
                return result
        except Exception as e:
            return f"Error getting process information: {str(e)}"
    
    async def _launch_application(self, app_name: str, args: List[str] = None) -> str:
        """
        Launch an application.
        
        Args:
            app_name: Name or path of the application to launch
            args: Command line arguments for the application
            
        Returns:
            Success message or error
            
        Raises:
            ValueError: If the application is not allowed or can't be launched
        """
        if not app_name:
            raise ValueError("Application name is required")
        
        args = args or []
        
        # Security check
        if self.allowed_executables and app_name not in self.allowed_executables:
            raise ValueError(f"Application '{app_name}' is not in the allowed list")
        
        try:
            if self.os_type == "Windows":
                # On Windows, use start command to launch application
                cmd = ["start", app_name] + args
                subprocess.Popen(cmd, shell=True)
                return f"Application '{app_name}' launched successfully"
            else:
                # On Linux/macOS
                subprocess.Popen([app_name] + args, start_new_session=True)
                return f"Application '{app_name}' launched successfully"
        except Exception as e:
            raise ValueError(f"Error launching application: {str(e)}") 