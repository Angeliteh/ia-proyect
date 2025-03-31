#!/bin/bash
# Script para ejecutar pruebas específicas de V.I.O. (MainAssistant) y manejo de errores

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ruta al ejecutable Python
PYTHON_CMD=python

# Ruta del script run_tests.py 
RUN_TESTS_SCRIPT="$(dirname "$0")/run_tests.py"

echo -e "${BLUE}=== Script de pruebas de V.I.O. (MainAssistant) ===${NC}"
echo "Este script ejecutará las pruebas para verificar el funcionamiento de V.I.O. y el manejo de errores."

# Verifica que el script run_tests.py exista
if [ ! -f "$RUN_TESTS_SCRIPT" ]; then
    echo -e "${RED}Error: No se encontró el script run_tests.py en $(dirname "$0")${NC}"
    exit 1
fi

# Función para ejecutar un test y verificar su resultado
run_test() {
    local test_name=$1
    local description=$2
    
    echo -e "\n${YELLOW}Ejecutando test: ${test_name}${NC}"
    echo -e "${BLUE}Descripción: ${description}${NC}"
    
    $PYTHON_CMD "$RUN_TESTS_SCRIPT" --run "$test_name" --verbose
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Test completado exitosamente${NC}"
        return 0
    else
        echo -e "${RED}✗ Test falló${NC}"
        return 1
    fi
}

# Función para ejecutar un workflow y verificar su resultado
run_workflow() {
    local workflow_name=$1
    local description=$2
    
    echo -e "\n${YELLOW}Ejecutando workflow: ${workflow_name}${NC}"
    echo -e "${BLUE}Descripción: ${description}${NC}"
    
    $PYTHON_CMD "$RUN_TESTS_SCRIPT" --run-workflow "$workflow_name" --verbose
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Workflow completado exitosamente${NC}"
        return 0
    else
        echo -e "${RED}✗ Workflow falló${NC}"
        return 1
    fi
}

# Menú de opciones
PS3="Selecciona una opción: "
options=(
    "Probar MainAssistant básico" 
    "Probar TTS básico" 
    "Probar manejo de errores (agente no disponible)" 
    "Probar manejo de errores (solicitud inválida)" 
    "Ejecutar workflow V.I.O. básico" 
    "Ejecutar workflow de manejo de errores"
    "Ejecutar workflow completo de V.I.O." 
    "Ejecutar todas las pruebas"
    "Salir"
)

select opt in "${options[@]}"
do
    case $opt in
        "Probar MainAssistant básico")
            run_test "main_assistant:basic" "Prueba básica del MainAssistant"
            ;;
        "Probar TTS básico")
            run_test "tts:basic" "Prueba básica del sistema TTS"
            ;;
        "Probar manejo de errores (agente no disponible)")
            run_test "error_handling:agent_unavailable" "Prueba de manejo de error cuando un agente no está disponible"
            ;;
        "Probar manejo de errores (solicitud inválida)")
            run_test "error_handling:invalid_request" "Prueba de manejo de solicitudes inválidas"
            ;;
        "Ejecutar workflow V.I.O. básico")
            run_workflow "vio_basic_workflow" "Flujo de trabajo básico de V.I.O. con TTS"
            ;;
        "Ejecutar workflow de manejo de errores")
            run_workflow "error_handling_workflow" "Flujo de trabajo que prueba el manejo de errores"
            ;;
        "Ejecutar workflow completo de V.I.O.")
            run_workflow "vio_full_workflow" "Flujo de trabajo completo de V.I.O."
            ;;
        "Ejecutar todas las pruebas")
            echo -e "\n${BLUE}Ejecutando todas las pruebas en secuencia...${NC}"
            
            failed=0
            # Pruebas individuales
            run_test "main_assistant:basic" "Prueba básica del MainAssistant" || ((failed++))
            run_test "tts:basic" "Prueba básica del sistema TTS" || ((failed++))
            run_test "error_handling:agent_unavailable" "Prueba de manejo de agente no disponible" || ((failed++))
            run_test "error_handling:invalid_request" "Prueba de manejo de solicitudes inválidas" || ((failed++))
            
            # Workflows
            run_workflow "vio_basic_workflow" "Flujo de trabajo básico de V.I.O." || ((failed++))
            run_workflow "error_handling_workflow" "Flujo de trabajo de manejo de errores" || ((failed++))
            
            echo -e "\n${BLUE}Resumen de pruebas:${NC}"
            if [ $failed -eq 0 ]; then
                echo -e "${GREEN}Todas las pruebas se completaron exitosamente${NC}"
            else
                echo -e "${RED}$failed pruebas fallaron${NC}"
            fi
            ;;
        "Salir")
            break
            ;;
        *) 
            echo -e "${RED}Opción inválida${NC}"
            ;;
    esac
done

echo -e "\n${BLUE}Fin de las pruebas${NC}" 