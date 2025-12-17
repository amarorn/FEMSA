#!/bin/bash
# ============================================================================
# Script para build e deploy automático no Google Cloud Run
# ============================================================================

set -e  # Parar em caso de erro

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Mudar para o diretório raiz do projeto (onde está o cloudbuild.yaml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}[INFO] Executando de: $PROJECT_ROOT${NC}"
echo ""

# Configurações (ajustar conforme necessário)
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"

# Verificar se PROJECT_ID está definido
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}[INFO] Variável GCP_PROJECT_ID não definida.${NC}"
    echo -e "${BLUE}Digite o Project ID do Google Cloud:${NC}"
    read -r PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}[ERRO] Project ID é obrigatório!${NC}"
    exit 1
fi

echo "=========================================================================="
echo -e "${BLUE}FEMSA - Deploy para Google Cloud Run${NC}"
echo "=========================================================================="
echo ""
echo -e "${GREEN}Project ID:${NC} $PROJECT_ID"
echo -e "${GREEN}Region:${NC} $REGION"
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERRO] Google Cloud SDK não encontrado!${NC}"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verificar se docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERRO] Docker não encontrado!${NC}"
    exit 1
fi

# Configurar projeto
echo -e "${YELLOW}[INFO] Configurando projeto GCP...${NC}"
gcloud config set project "$PROJECT_ID"

# Habilitar APIs (se necessário)
echo -e "${YELLOW}[INFO] Habilitando APIs necessárias...${NC}"
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

# Autenticar Docker
echo -e "${YELLOW}[INFO] Autenticando Docker no GCR...${NC}"
gcloud auth configure-docker --quiet

# Build e Deploy App 1
echo ""
echo "=========================================================================="
echo -e "${BLUE}Build e Deploy: App Cenário 1 Corporativo${NC}"
echo "=========================================================================="
echo ""

echo -e "${YELLOW}[INFO] Building Docker image...${NC}"
docker build -f ml-prot/Dockerfile.cenario1 -t "gcr.io/$PROJECT_ID/femsa-cenario1:latest" .

echo -e "${YELLOW}[INFO] Pushing to Container Registry...${NC}"
docker push "gcr.io/$PROJECT_ID/femsa-cenario1:latest"

echo -e "${YELLOW}[INFO] Deploying to Cloud Run...${NC}"
gcloud run deploy femsa-cenario1 \
  --image "gcr.io/$PROJECT_ID/femsa-cenario1:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8050 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --quiet

# Obter URL do App 1
URL1=$(gcloud run services describe femsa-cenario1 --region "$REGION" --format 'value(status.url)')
echo -e "${GREEN}✓ App 1 deployado:${NC} $URL1"

# Build e Deploy App 2
echo ""
echo "=========================================================================="
echo -e "${BLUE}Build e Deploy: App Mix Optimization${NC}"
echo "=========================================================================="
echo ""

echo -e "${YELLOW}[INFO] Building Docker image...${NC}"
docker build -f ml-prot/Dockerfile.mix -t "gcr.io/$PROJECT_ID/femsa-mix-optimization:latest" .

echo -e "${YELLOW}[INFO] Pushing to Container Registry...${NC}"
docker push "gcr.io/$PROJECT_ID/femsa-mix-optimization:latest"

echo -e "${YELLOW}[INFO] Deploying to Cloud Run...${NC}"
gcloud run deploy femsa-mix-optimization \
  --image "gcr.io/$PROJECT_ID/femsa-mix-optimization:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8051 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --quiet

# Obter URL do App 2
URL2=$(gcloud run services describe femsa-mix-optimization --region "$REGION" --format 'value(status.url)')
echo -e "${GREEN}✓ App 2 deployado:${NC} $URL2"

# Resumo
echo ""
echo "=========================================================================="
echo -e "${GREEN}✓ Deploy concluído com sucesso!${NC}"
echo "=========================================================================="
echo ""
echo "📍 URLs disponíveis:"
echo -e "   ${BLUE}App Cenário 1:${NC} $URL1"
echo -e "   ${BLUE}App Mix Optimization:${NC} $URL2"
echo ""
echo "=========================================================================="

