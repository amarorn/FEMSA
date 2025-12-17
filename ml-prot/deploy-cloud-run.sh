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
    echo -e "${BLUE}Digite o Project ID do Google Cloud (nome do projeto, não o número):${NC}"
    echo -e "${YELLOW}Exemplo: meu-projeto-femsa (não 426244243362)${NC}"
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
# Verificar se é project number e converter para project ID
if [[ "$PROJECT_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${YELLOW}[INFO] Project number detectado, obtendo Project ID...${NC}"
    # Tentar obter project ID usando o project number
    ACTUAL_PROJECT_ID=$(gcloud projects list --filter="projectNumber=$PROJECT_ID" --format="value(projectId)" 2>/dev/null | head -1)
    if [ ! -z "$ACTUAL_PROJECT_ID" ] && [ "$ACTUAL_PROJECT_ID" != "$PROJECT_ID" ]; then
        PROJECT_ID="$ACTUAL_PROJECT_ID"
        echo -e "${GREEN}Project ID convertido: $PROJECT_ID${NC}"
    else
        echo -e "${YELLOW}[AVISO] Não foi possível converter project number. Usando como está.${NC}"
        echo -e "${YELLOW}[AVISO] Certifique-se de usar Project ID (nome) ao invés de Project Number.${NC}"
    fi
fi
gcloud config set project "$PROJECT_ID"

# Habilitar APIs (se necessário)
echo -e "${YELLOW}[INFO] Habilitando APIs necessárias...${NC}"
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable artifactregistry.googleapis.com --quiet

# Criar Artifact Registry repository (se não existir)
REPO_NAME="femsa-apps"
REPO_LOCATION="$REGION"
echo -e "${YELLOW}[INFO] Verificando Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REPO_LOCATION" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}[INFO] Criando Artifact Registry repository...${NC}"
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REPO_LOCATION" \
        --description="FEMSA Applications" \
        --project="$PROJECT_ID" \
        --quiet
fi

# Autenticar Docker no Artifact Registry
echo -e "${YELLOW}[INFO] Autenticando Docker no Artifact Registry...${NC}"
gcloud auth configure-docker "$REPO_LOCATION-docker.pkg.dev" --quiet

# Build e Deploy App 1
echo ""
echo "=========================================================================="
echo -e "${BLUE}Build e Deploy: App Cenário 1 Corporativo${NC}"
echo "=========================================================================="
echo ""

# Definir imagem no Artifact Registry
IMAGE_CENARIO1="$REPO_LOCATION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/femsa-cenario1:latest"

echo -e "${YELLOW}[INFO] Building Docker image...${NC}"
docker build -f ml-prot/Dockerfile.cenario1 -t "$IMAGE_CENARIO1" .

echo -e "${YELLOW}[INFO] Pushing to Artifact Registry...${NC}"
docker push "$IMAGE_CENARIO1"

echo -e "${YELLOW}[INFO] Deploying to Cloud Run...${NC}"
gcloud run deploy femsa-cenario1 \
  --image "$IMAGE_CENARIO1" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
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

# Definir imagem no Artifact Registry
IMAGE_MIX="$REPO_LOCATION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/femsa-mix-optimization:latest"

echo -e "${YELLOW}[INFO] Building Docker image...${NC}"
docker build -f ml-prot/Dockerfile.mix -t "$IMAGE_MIX" .

echo -e "${YELLOW}[INFO] Pushing to Artifact Registry...${NC}"
docker push "$IMAGE_MIX"

echo -e "${YELLOW}[INFO] Deploying to Cloud Run...${NC}"
gcloud run deploy femsa-mix-optimization \
  --image "$IMAGE_MIX" \
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

