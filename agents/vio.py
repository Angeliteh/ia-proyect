from typing import Tuple

class VIO:
    def _determine_agent_for_query(self, query: str) -> Tuple[str, int]:
        """
        Determine which specialized agent should handle a query.
        
        Args:
            query: User query
            
        Returns:
            Tuple containing (agent_id, match_score)
        """
        query = query.lower().strip()
        
        # Scores for each agent type
        scores = {}
        for agent_id, capabilities in self.specialized_agents.items():
            scores[agent_id] = 0
        
        # ===== DETECCIÓN DE PROGRAMACIÓN Y CÓDIGO =====
        code_related = any(term in query for term in [
            "código", "program", "script", "función", "code", "función", "class", 
            "python", "javascript", "java", "c++", "typescript", "go", "rust",
            "algoritmo", "implementa", "desarrolla", "escribe un código", "escribe un programa"
        ])
        
        # Alta prioridad: Si explícitamente pide crear o escribir un programa
        create_program = any(term in query for term in [
            "crea un programa", "escribe un programa", "desarrolla un programa",
            "necesito un programa", "haz un programa", "programa en python",
            "código en python", "script en python", "implementa en python"
        ])
        
        if create_program:
            # Prioridad máxima para CodeAgent cuando se solicita crear un programa
            if "code" in self.specialized_agents:
                scores["code"] = 10
                self.logger.info(f"Consulta sobre creación de programa detectada, asignando a CodeAgent")
        elif code_related:
            if "code" in self.specialized_agents:
                scores["code"] = 5
                self.logger.info(f"Consulta relacionada con código detectada, favoreciendo a CodeAgent")
                
        # ===== DETECCIÓN DE HARDWARE/SISTEMA =====
        system_related = any(term in query for term in [
            "sistema", "hardware", "memoria", "procesador", "disco", "archivo", "directorio",
            "ram", "cpu", "sistema operativo", "windows", "linux", "macos",
            "ejecuta", "comando", "terminal", "shell", "powershell", "cmd"
        ])
        
        if system_related:
            if "system" in self.specialized_agents:
                scores["system"] = 3
                self.logger.info(f"Consulta sobre hardware/sistema detectada, asignando a SystemAgent")
                
                # Aumentar puntuación si es específicamente sobre hardware del sistema
                hardware_specific = any(term in query for term in [
                    "ram", "cpu", "procesador", "disco duro", "sistema operativo",
                    "memoria física", "uso de memoria", "uso de disco"
                ])
                
                if hardware_specific:
                    scores["system"] += 2
                    self.logger.info(f"Consulta específica sobre hardware, aumentando prioridad para SystemAgent")
                
                # Pero si también pide programar algo relacionado con el sistema,
                # CodeAgent debe tener prioridad
                if code_related and "code" in self.specialized_agents:
                    scores["code"] += 5
                    self.logger.info(f"Consulta para programar algo relacionado con sistema, priorizando CodeAgent")
                
        # ===== DETECCIÓN DE MEMORIA Y CONOCIMIENTO =====
        memory_related = any(term in query for term in [
            "recuerdas", "sabes", "conoces", "qué es", "qué son", "definición",
            "explica", "información sobre", "datos sobre", "búsqueda", "encuentra"
        ])
        
        if memory_related:
            if "memory" in self.specialized_agents:
                scores["memory"] = 3
                self.logger.info(f"Consulta sobre conocimiento/memoria detectada, asignando a MemoryAgent")
                
                # Si es una pregunta explícita sobre un concepto
                question = any(term in query for term in [
                    "qué es", "qué significa", "explica qué", "definición de",
                    "cómo funciona", "para qué sirve", "cuál es", "quién es"
                ])
                
                if question:
                    scores["memory"] += 1
                    self.logger.info(f"Pregunta explícita detectada, aumentando prioridad para MemoryAgent")
                    
        # ===== DETECCIÓN DE TAREAS COMPLEJAS Y PLANEACIÓN =====
        task_related = any(term in query for term in [
            "planifica", "organiza", "coordina", "plan", "tarea", "proyecto",
            "paso a paso", "secuencia", "workflow", "flujo de trabajo", "procedimiento"
        ])
        
        if task_related:
            if "planner" in self.specialized_agents:
                scores["planner"] = 3
                self.logger.info(f"Consulta sobre planeación detectada, asignando a PlannerAgent")
            
            # Si es una tarea compleja que requiere orquestación
            complex_task = any(term in query for term in [
                "varios agentes", "multiples pasos", "coordinación", "colaboración",
                "varios componentes", "orquesta", "flujo complejo", "tarea completa"
            ])
            
            if complex_task and "orchestrator" in self.specialized_agents:
                scores["orchestrator"] = 4
                self.logger.info(f"Tarea compleja detectada, asignando a OrchestratorAgent")
        
        # ===== DETECCIÓN DE PRUEBAS DE COMUNICACIÓN =====
        test_related = any(term in query for term in [
            "prueba", "test", "echo", "comunica", "envía mensaje", "mensaje de prueba"
        ])
        
        if test_related:
            if "echo" in self.specialized_agents:
                scores["echo"] = 3
                self.logger.info(f"Solicitud de prueba detectada, asignando a EchoAgent")
            if "sender" in self.specialized_agents:
                scores["sender"] = 3
                self.logger.info(f"Solicitud de prueba de comunicación detectada, asignando a TestSenderAgent")
                
        # Si las puntuaciones son bajas o no hay un claro ganador, intentar usar el orquestador
        max_score = max(scores.values()) if scores else 0
        if max_score < 2 and "orchestrator" in self.specialized_agents:
            scores["orchestrator"] = 2
            self.logger.info("No hay agente claro para esta consulta, delegando al orquestador")
                
        # Seleccionar el agente con mayor puntuación
        selected_agent_id = max(scores.items(), key=lambda x: x[1])[0] if scores else None
        max_score = scores.get(selected_agent_id, 0) if selected_agent_id else 0
        
        # Log de todas las puntuaciones para debugging
        self.logger.info(f"Puntuaciones de agentes para '{query[:50]}...': {scores}")
        
        if max_score > 0:
            self.logger.info(f"Agente seleccionado: {selected_agent_id} con puntuación {max_score}")
            return selected_agent_id, max_score
        else:
            self.logger.warning("No se encontró un agente adecuado para esta consulta")
            # Fallback a V.I.O. mismo
            return self.agent_id, 0 