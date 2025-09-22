# MCP BI Connector

Este proyecto implementa un MCP (Model Context Protocol) server como API REST usando Azure Functions para crear un custom connector.

## Descripción

Este connector permite integrar funcionalidades de BI (Business Intelligence) a través de un endpoint HTTP deployed en Azure Functions.

## Estructura del proyecto

```
mcp_bi/
├── function_app.py          # Azure Functions wrapper
├── requirements.txt         # Dependencias de Python
├── host.json               # Configuración de Azure Functions
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── deploy.yml      # GitHub Actions para deployment
```

## Instalación local

1. Clona el repositorio:
```bash
git clone https://github.com/tu-usuario/mcp-bi-connector.git
cd mcp-bi-connector
```

2. Instala dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecuta localmente:
```bash
func start
```

## Deployment en Azure

El proyecto está configurado para deployment automático usando GitHub Actions cuando se hace push a la rama `main`.

### Configuración requerida:

1. Crear Azure Function App
2. Configurar GitHub secrets:
   - `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`

## Uso del API

### Listar herramientas disponibles:
```bash
curl -X POST https://tu-function-app.azurewebsites.net/api/mcp-endpoint \
  -H "Content-Type: application/json" \
  -d '{"method": "list_tools"}'
```

### Ejecutar herramienta:
```bash
curl -X POST https://tu-function-app.azurewebsites.net/api/mcp-endpoint \
  -H "Content-Type: application/json" \
  -d '{"method": "call_tool", "params": {"name": "tool_name", "arguments": {}}}'
```

## Contribuir

1. Fork el proyecto
2. Crea una feature branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la branch (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.