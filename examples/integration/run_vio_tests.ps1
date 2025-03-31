# Script PowerShell para ejecutar pruebas específicas de V.I.O. (MainAssistant) y manejo de errores

# Colores para mensajes
$RED = [char]27 + "[0;31m"
$GREEN = [char]27 + "[0;32m"
$YELLOW = [char]27 + "[0;33m"
$BLUE = [char]27 + "[0;34m"
$NC = [char]27 + "[0m" # No Color

# Ruta al ejecutable Python
$PYTHON_CMD = "python"

# Ruta del script run_tests.py
$RUN_TESTS_SCRIPT = Join-Path $PSScriptRoot "run_tests.py"

# Mostrar encabezado
Write-Host "${BLUE}=== Script de pruebas de V.I.O. (MainAssistant) ===${NC}"
Write-Host "Este script ejecutará las pruebas para verificar el funcionamiento de V.I.O. y el manejo de errores."

# Verifica que el script run_tests.py exista
if (-Not (Test-Path $RUN_TESTS_SCRIPT)) {
    Write-Host "${RED}Error: No se encontró el script run_tests.py en $PSScriptRoot${NC}"
    exit 1
}

# Función para ejecutar un test y verificar su resultado
function Run-Test {
    param (
        [string]$TestName,
        [string]$Description
    )
    
    Write-Host "`n${YELLOW}Ejecutando test: ${TestName}${NC}"
    Write-Host "${BLUE}Descripción: ${Description}${NC}"
    
    & $PYTHON_CMD $RUN_TESTS_SCRIPT --run $TestName --verbose
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "${GREEN}✓ Test completado exitosamente${NC}"
        return $true
    } else {
        Write-Host "${RED}✗ Test falló${NC}"
        return $false
    }
}

# Función para ejecutar un workflow y verificar su resultado
function Run-Workflow {
    param (
        [string]$WorkflowName,
        [string]$Description
    )
    
    Write-Host "`n${YELLOW}Ejecutando workflow: ${WorkflowName}${NC}"
    Write-Host "${BLUE}Descripción: ${Description}${NC}"
    
    & $PYTHON_CMD $RUN_TESTS_SCRIPT --run-workflow $WorkflowName --verbose
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "${GREEN}✓ Workflow completado exitosamente${NC}"
        return $true
    } else {
        Write-Host "${RED}✗ Workflow falló${NC}"
        return $false
    }
}

# Función para mostrar el menú
function Show-Menu {
    param (
        [string]$Title = 'Selecciona una opción'
    )
    Clear-Host
    Write-Host "================ $Title ================"
    
    Write-Host "1: Probar MainAssistant básico"
    Write-Host "2: Probar TTS básico"
    Write-Host "3: Probar manejo de errores (agente no disponible)"
    Write-Host "4: Probar manejo de errores (solicitud inválida)"
    Write-Host "5: Ejecutar workflow V.I.O. básico"
    Write-Host "6: Ejecutar workflow de manejo de errores"
    Write-Host "7: Ejecutar workflow completo de V.I.O."
    Write-Host "8: Ejecutar todas las pruebas"
    Write-Host "Q: Salir"
}

# Iniciar bucle de menú
do {
    Show-Menu
    $input = Read-Host "Por favor, ingresa una opción"
    
    switch ($input) {
        '1' {
            Run-Test -TestName "main_assistant:basic" -Description "Prueba básica del MainAssistant"
        }
        '2' {
            Run-Test -TestName "tts:basic" -Description "Prueba básica del sistema TTS"
        }
        '3' {
            Run-Test -TestName "error_handling:agent_unavailable" -Description "Prueba de manejo de error cuando un agente no está disponible"
        }
        '4' {
            Run-Test -TestName "error_handling:invalid_request" -Description "Prueba de manejo de solicitudes inválidas"
        }
        '5' {
            Run-Workflow -WorkflowName "vio_basic_workflow" -Description "Flujo de trabajo básico de V.I.O. con TTS"
        }
        '6' {
            Run-Workflow -WorkflowName "error_handling_workflow" -Description "Flujo de trabajo que prueba el manejo de errores"
        }
        '7' {
            Run-Workflow -WorkflowName "vio_full_workflow" -Description "Flujo de trabajo completo de V.I.O."
        }
        '8' {
            Write-Host "`n${BLUE}Ejecutando todas las pruebas en secuencia...${NC}"
            
            $failed = 0
            # Pruebas individuales
            if (-Not (Run-Test -TestName "main_assistant:basic" -Description "Prueba básica del MainAssistant")) { $failed++ }
            if (-Not (Run-Test -TestName "tts:basic" -Description "Prueba básica del sistema TTS")) { $failed++ }
            if (-Not (Run-Test -TestName "error_handling:agent_unavailable" -Description "Prueba de manejo de agente no disponible")) { $failed++ }
            if (-Not (Run-Test -TestName "error_handling:invalid_request" -Description "Prueba de manejo de solicitudes inválidas")) { $failed++ }
            
            # Workflows
            if (-Not (Run-Workflow -WorkflowName "vio_basic_workflow" -Description "Flujo de trabajo básico de V.I.O.")) { $failed++ }
            if (-Not (Run-Workflow -WorkflowName "error_handling_workflow" -Description "Flujo de trabajo de manejo de errores")) { $failed++ }
            
            Write-Host "`n${BLUE}Resumen de pruebas:${NC}"
            if ($failed -eq 0) {
                Write-Host "${GREEN}Todas las pruebas se completaron exitosamente${NC}"
            } else {
                Write-Host "${RED}$failed pruebas fallaron${NC}"
            }
        }
        'q' {
            return
        }
    }
    pause
} until ($input -eq 'q')

Write-Host "`n${BLUE}Fin de las pruebas${NC}" 