# MCP Clients

Este directorio contiene definiciones base e implementaciones específicas de clientes MCP (Model Context Protocol). 

## Descripción

Los clientes MCP permiten a las aplicaciones y modelos de IA conectarse con servidores MCP para acceder a datos y recursos. La mayoría de la funcionalidad de conexión se encuentra en los conectores genéricos (`mcp/connectors/`), mientras que este directorio está pensado para las implementaciones específicas a ciertos servicios.

## Relación con los conectores

Es importante entender la diferencia entre los **conectores genéricos** y los **clientes específicos**:

- **Conectores genéricos** (`mcp/connectors/`): Implementan la mecánica de comunicación (HTTP, WebSockets, etc.) de forma genérica. Son suficientes para la mayoría de casos de uso.

- **Clientes específicos** (`mcp_clients/`): Extienden los conectores genéricos añadiendo lógica específica para ciertos servidores o servicios, como:
  - Autenticación especializada
  - Transformación de datos específica para el servicio
  - Abstracción de operaciones complejas
  - Implementación de flujos de trabajo específicos

## Cuándo usar conectores vs. clientes específicos

**Usa los conectores genéricos cuando**:
- Necesites interactuar con un servidor MCP de forma directa
- Las operaciones sean simples o estándar
- No requieras lógica especializada para el servicio

**Crea un cliente específico cuando**:
- Necesites abstraer operaciones complejas o frecuentes
- Requieras manejar autenticación especializada
- Desees proporcionar una API más amigable para un servicio específico
- Debas implementar reconexión, reintentos o lógica de error específica

## Estructura del directorio

```
mcp_clients/
├── base.py             # Definiciones base para clientes específicos
├── __init__.py         # Inicializaciones y exportaciones
└── README.md           # Esta documentación
```

## Ejemplo de uso

### Uso de un conector genérico

```python
from mcp.connectors.http_client import MCPHttpClient
from mcp.core.protocol import MCPMessage, MCPAction, MCPResource

# Crear cliente HTTP genérico
client = MCPHttpClient(base_url="http://localhost:8080")
client.connect()

# Crear manualmente un mensaje MCP
message = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type=MCPResource.WEB_SEARCH,
    resource_path="/search",
    data={"query": "inteligencia artificial"}
)

# Enviar mensaje y procesar respuesta
response = client.send_message(message)
```

### Implementación de un cliente específico

Si necesitaras crear un cliente específico, podría verse así:

```python
from mcp.connectors.http_client import MCPHttpClient
from mcp.core.protocol import MCPMessage, MCPAction, MCPResource

class SearchClient:
    """Cliente específico para servicios de búsqueda."""
    
    def __init__(self, base_url, api_key=None):
        """Inicializa el cliente de búsqueda."""
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        self.client = MCPHttpClient(base_url=base_url, headers=headers)
    
    def connect(self):
        """Conecta con el servidor de búsqueda."""
        return self.client.connect()
        
    def search_web(self, query, count=10):
        """
        Realiza una búsqueda web.
        
        Args:
            query: Consulta de búsqueda
            count: Número de resultados a devolver
            
        Returns:
            Lista de resultados de búsqueda
        """
        message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=MCPResource.WEB_SEARCH,
            resource_path="/search",
            data={"query": query, "count": count}
        )
        
        response = self.client.send_message(message)
        
        if response.success:
            return response.data.get("results", [])
        else:
            # Manejar el error específicamente
            error_msg = response.error.message if response.error else "Error desconocido"
            raise Exception(f"Error en búsqueda: {error_msg}")
```

## Mejores prácticas

1. **Mantenlo simple**: Usa los conectores genéricos siempre que sea posible.

2. **Clientela específica**: Crea clientes específicos solo cuando agreguen valor real o abstraigan complejidad significativa.

3. **Reutilización**: Un cliente específico debería poder ser reutilizado en múltiples contextos.

4. **Pruebas**: Escribe pruebas unitarias para clientes específicos, especialmente si contienen lógica de negocio. 