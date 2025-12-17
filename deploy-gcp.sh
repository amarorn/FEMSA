#!/bin/bash
# ============================================================================
# Script para deploy rápido de aplicação Python no Google Cloud Run
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurações
APP_NAME="${1:-minha-app}"
REGION="${GCP_REGION:-us-central1}"
PROJECT_ID="${GCP_PROJECT_ID:-}"

echo "=========================================================================="
echo -e "${BLUE}Deploy Python App - Google Cloud Run${NC}"
echo "=========================================================================="
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERRO] Google Cloud SDK não encontrado!${NC}"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verificar PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ ! -z "$CURRENT_PROJECT" ]; then
        PROJECT_ID="$CURRENT_PROJECT"
        echo -e "${GREEN}Usando projeto: $PROJECT_ID${NC}"
    else
        echo -e "${BLUE}Digite o Project ID:${NC}"
        read -r PROJECT_ID
    fi
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}[ERRO] Project ID é obrigatório!${NC}"
    exit 1
fi

gcloud config set project "$PROJECT_ID"

# Verificar se Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo -e "${YELLOW}[AVISO] Dockerfile não encontrado na raiz.${NC}"
    echo "Criando Dockerfile básico..."
    
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY assets/ ./assets/ 2>/dev/null || true

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
EOF
    
    echo -e "${GREEN}✓ Dockerfile criado${NC}"
    echo -e "${YELLOW}[AVISO] Verifique se o Dockerfile está correto antes de continuar.${NC}"
    read -p "Continuar? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 0
    fi
fi

# Verificar se requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}[ERRO] requirements.txt não encontrado!${NC}"
    exit 1
fi

# Habilitar APIs
echo -e "${YELLOW}[INFO] Habilitando APIs necessárias...${NC}"
gcloud services enable run.googleapis.com --quiet
gcloud services enable cloudbuild.googleapis.com --quiet

# Deploy
echo ""
echo "=========================================================================="
echo -e "${BLUE}Fazendo deploy: $APP_NAME${NC}"
echo "=========================================================================="
echo ""

gcloud run deploy "$APP_NAME" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================================================="
    echo -e "${GREEN}✓ Deploy concluído com sucesso!${NC}"
    echo "=========================================================================="
    echo ""
    
    # Obter URL
    URL=$(gcloud run services describe "$APP_NAME" --region "$REGION" --format="value(status.url)" 2>/dev/null)
    
    if [ ! -z "$URL" ]; then
        echo -e "${GREEN}📍 URL Pública:${NC}"
        echo -e "   ${BLUE}$URL${NC}"
        echo ""
        echo "Acesse a URL acima para ver sua aplicação!"
    fi
else
    echo ""
    echo -e "${RED}[ERRO] Falha no deploy${NC}"
    echo "Verifique os logs acima para mais detalhes."
    exit 1
fi

