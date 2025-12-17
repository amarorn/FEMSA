#!/bin/bash
# ============================================================================
# Script para ver logs do Cloud Scheduler e Cloud Run
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ID="${GCP_PROJECT_ID:-}"
JOB_NAME="${1:-}"
SERVICE_NAME="${2:-}"
REGION="${GCP_REGION:-us-central1}"

echo "=========================================================================="
echo -e "${BLUE}Ver Logs - Cloud Scheduler e Cloud Run${NC}"
echo "=========================================================================="
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERRO] Google Cloud SDK não encontrado!${NC}"
    exit 1
fi

# Verificar PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}[INFO] Variável GCP_PROJECT_ID não definida.${NC}"
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ ! -z "$CURRENT_PROJECT" ]; then
        PROJECT_ID="$CURRENT_PROJECT"
        echo -e "${GREEN}Usando projeto atual: $PROJECT_ID${NC}"
    else
        echo -e "${BLUE}Digite o Project ID do Google Cloud:${NC}"
        read -r PROJECT_ID
    fi
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}[ERRO] Project ID é obrigatório!${NC}"
    exit 1
fi

gcloud config set project "$PROJECT_ID"

echo ""
echo "=========================================================================="
echo -e "${BLUE}1. Listando Jobs do Cloud Scheduler${NC}"
echo "=========================================================================="
echo ""

if [ -z "$JOB_NAME" ]; then
    echo -e "${YELLOW}Jobs disponíveis:${NC}"
    gcloud scheduler jobs list --location="$REGION" 2>/dev/null || {
        echo -e "${RED}Erro ao listar jobs. Verifique se a região está correta.${NC}"
        echo "Regiões comuns: us-central1, us-east1, europe-west1"
        exit 1
    }
    echo ""
    echo -e "${BLUE}Para ver logs de um job específico, use:${NC}"
    echo "  ./ver_logs.sh JOB_NAME [SERVICE_NAME]"
    exit 0
fi

echo ""
echo "=========================================================================="
echo -e "${BLUE}2. Logs do Cloud Scheduler: $JOB_NAME${NC}"
echo "=========================================================================="
echo ""

# Ver detalhes do job
echo -e "${YELLOW}Detalhes do Job:${NC}"
gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" 2>/dev/null || {
    echo -e "${RED}Job não encontrado: $JOB_NAME${NC}"
    exit 1
}

echo ""
echo -e "${YELLOW}Últimas execuções (logs):${NC}"
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=$JOB_NAME" \
    --limit 20 \
    --format="table(timestamp,severity,textPayload,jsonPayload.message)" 2>/dev/null || {
    echo -e "${RED}Erro ao ler logs. Verifique permissões.${NC}"
}

if [ ! -z "$SERVICE_NAME" ]; then
    echo ""
    echo "=========================================================================="
    echo -e "${BLUE}3. Logs do Cloud Run: $SERVICE_NAME${NC}"
    echo "=========================================================================="
    echo ""
    
    gcloud run services logs read "$SERVICE_NAME" --region="$REGION" --limit 20 2>/dev/null || {
        echo -e "${RED}Erro ao ler logs do Cloud Run.${NC}"
        echo "Verifique se o serviço existe:"
        gcloud run services list --region="$REGION"
    }
fi

echo ""
echo "=========================================================================="
echo -e "${GREEN}✓ Logs exibidos${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}Dicas:${NC}"
echo "  • Para ver logs em tempo real: gcloud logging tail"
echo "  • Para exportar logs: gcloud logging read ... --format json > logs.json"
echo "  • Console Web: https://console.cloud.google.com/logs"



