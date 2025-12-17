# 🚀 Deploy no Google Cloud Run

Guia completo para fazer deploy dos apps Dash no Google Cloud Run usando Docker.

## 📋 Pré-requisitos

1. Conta Google Cloud Platform (GCP)
2. Google Cloud SDK instalado (`gcloud`)
3. Docker instalado (para testar localmente)
4. Projeto criado no GCP

## 🔧 Setup Inicial

### 1. Instalar Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Windows
# Baixe do site: https://cloud.google.com/sdk/docs/install
```

### 2. Autenticar

```bash
gcloud auth login
gcloud auth configure-docker
```

### 3. Configurar Projeto

```bash
# Listar projetos
gcloud projects list

# Definir projeto (substitua SEU_PROJECT_ID)
gcloud config set project SEU_PROJECT_ID

# Habilitar APIs necessárias
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## 🐳 Build e Deploy Manual

### Opção 1: Build Local e Push

#### App Cenário 1:

```bash
# Build da imagem
docker build -f Dockerfile.cenario1 -t gcr.io/SEU_PROJECT_ID/femsa-cenario1 .

# Push para Container Registry
docker push gcr.io/SEU_PROJECT_ID/femsa-cenario1

# Deploy no Cloud Run
gcloud run deploy femsa-cenario1 \
  --image gcr.io/SEU_PROJECT_ID/femsa-cenario1 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8050
```

#### App Mix Optimization:

```bash
# Build da imagem
docker build -f Dockerfile.mix -t gcr.io/SEU_PROJECT_ID/femsa-mix-optimization .

# Push para Container Registry
docker push gcr.io/SEU_PROJECT_ID/femsa-mix-optimization

# Deploy no Cloud Run
gcloud run deploy femsa-mix-optimization \
  --image gcr.io/SEU_PROJECT_ID/femsa-mix-optimization \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8051
```

### Opção 2: Build no Cloud Build

```bash
# Build e deploy automático usando cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml
```

## 🧪 Testar Localmente com Docker

### Build e Run Individual

```bash
# App Cenário 1
docker build -f Dockerfile.cenario1 -t femsa-cenario1 .
docker run -p 8050:8050 femsa-cenario1

# App Mix Optimization
docker build -f Dockerfile.mix -t femsa-mix .
docker run -p 8051:8051 femsa-mix
```

### Usar Docker Compose

```bash
# Build e iniciar ambos os serviços
docker-compose up --build

# Rodar em background
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

Acesse:
- http://localhost:8050 (Cenário 1)
- http://localhost:8051 (Mix Optimization)

## 📝 Scripts de Automação

### Script para Build e Deploy

Crie `deploy-cloud-run.sh`:

```bash
#!/bin/bash
PROJECT_ID="SEU_PROJECT_ID"
REGION="us-central1"

echo "Building and deploying to Cloud Run..."

# App 1
echo "Building femsa-cenario1..."
docker build -f Dockerfile.cenario1 -t gcr.io/$PROJECT_ID/femsa-cenario1 .
docker push gcr.io/$PROJECT_ID/femsa-cenario1

gcloud run deploy femsa-cenario1 \
  --image gcr.io/$PROJECT_ID/femsa-cenario1 \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8050

# App 2
echo "Building femsa-mix-optimization..."
docker build -f Dockerfile.mix -t gcr.io/$PROJECT_ID/femsa-mix-optimization .
docker push gcr.io/$PROJECT_ID/femsa-mix-optimization

gcloud run deploy femsa-mix-optimization \
  --image gcr.io/$PROJECT_ID/femsa-mix-optimization \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8051

echo "Deploy concluído!"
```

Tornar executável:
```bash
chmod +x deploy-cloud-run.sh
```

## 🌐 URLs Geradas

Após o deploy, você receberá URLs como:

- **App Cenário 1:** `https://femsa-cenario1-XXXXX-uc.a.run.app`
- **App Mix:** `https://femsa-mix-optimization-XXXXX-uc.a.run.app`

## ⚙️ Configurações Avançadas

### Aumentar Memória/CPU

```bash
gcloud run services update femsa-cenario1 \
  --memory 2Gi \
  --cpu 2 \
  --region us-central1
```

### Configurar Variáveis de Ambiente

```bash
gcloud run services update femsa-cenario1 \
  --set-env-vars "DEBUG=false,ENV=production" \
  --region us-central1
```

### Configurar Concorrência

```bash
gcloud run services update femsa-cenario1 \
  --concurrency 10 \
  --region us-central1
```

### Configurar Timeout

```bash
gcloud run services update femsa-cenario1 \
  --timeout 300 \
  --region us-central1
```

## 💰 Custos

### Plano Gratuito (Free Tier)

- **2 milhões de requisições/mês** grátis
- **360.000 GB-segundos** de memória grátis
- **180.000 vCPU-segundos** grátis

### Após Free Tier

- **$0.40 por milhão de requisições**
- **$0.0000025 por GB-segundo de memória**
- **$0.0000100 por vCPU-segundo**

**Estimativa para uso moderado:** ~$5-10/mês

## 🔒 Segurança

### Autenticação (Opcional)

Para tornar os serviços privados:

```bash
# Remover --allow-unauthenticated
gcloud run deploy femsa-cenario1 \
  --image gcr.io/SEU_PROJECT_ID/femsa-cenario1 \
  --region us-central1 \
  --no-allow-unauthenticated
```

Acessar com token:
```bash
# Obter token
TOKEN=$(gcloud auth print-identity-token)

# Fazer requisição
curl -H "Authorization: Bearer $TOKEN" \
  https://femsa-cenario1-XXXXX-uc.a.run.app
```

## 📊 Monitoramento

### Ver Logs

```bash
# Logs em tempo real
gcloud run services logs read femsa-cenario1 --follow

# Logs do Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Métricas

Acesse: https://console.cloud.google.com/run
- Ver métricas de requisições
- Ver uso de CPU/memória
- Ver latência

## 🔄 CI/CD com GitHub Actions

Crie `.github/workflows/cloud-run.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - id: 'auth'
        uses: 'google-github-actions/auth@v1'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: 'Set up Cloud SDK'
        uses: 'google-github-actions/setup-gcloud@v1'
      
      - name: 'Build and Deploy'
        run: |
          gcloud builds submit --config cloudbuild.yaml
```

## 🐛 Troubleshooting

### Erro: "Permission denied"
```bash
gcloud auth login
gcloud auth application-default login
```

### Erro: "Image not found"
Verifique se o push foi bem-sucedido:
```bash
gcloud container images list
```

### App não inicia
Verifique logs:
```bash
gcloud run services logs read femsa-cenario1 --limit 100
```

### Porta incorreta
Cloud Run usa PORT automaticamente. Certifique-se de que os apps leem `os.environ.get('PORT')`.

## ✅ Checklist

- [ ] Google Cloud SDK instalado
- [ ] Projeto GCP criado
- [ ] APIs habilitadas
- [ ] Dockerfiles testados localmente
- [ ] Imagens buildadas e enviadas
- [ ] Deploy realizado
- [ ] URLs testadas
- [ ] Logs verificados

## 🎉 Pronto!

Agora seus apps estão rodando no Google Cloud Run e podem ser acessados de qualquer lugar!

