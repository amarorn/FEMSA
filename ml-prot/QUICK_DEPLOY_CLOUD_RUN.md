# ⚡ Deploy Rápido - Google Cloud Run (10 minutos)

## 🎯 Passo a Passo Simplificado

### 1. Pré-requisitos

```bash
# Instalar Google Cloud SDK
# macOS:
brew install google-cloud-sdk

# Ou baixe de: https://cloud.google.com/sdk/docs/install
```

### 2. Configuração Inicial (Uma vez só)

```bash
# Autenticar
gcloud auth login

# Criar projeto (ou usar existente)
gcloud projects create femsa-ml-apps --name="FEMSA ML Apps"

# Definir projeto
gcloud config set project femsa-ml-apps

# Habilitar APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Configurar Docker
gcloud auth configure-docker
```

### 3. Deploy Automático (Script)

```bash
# Definir variável de ambiente
export GCP_PROJECT_ID="femsa-ml-apps"

# Executar script de deploy
./deploy-cloud-run.sh
```

**Pronto!** O script faz tudo automaticamente:
- ✅ Build das imagens Docker
- ✅ Push para Container Registry
- ✅ Deploy no Cloud Run
- ✅ Mostra as URLs finais

### 4. Deploy Manual (Passo a Passo)

#### App Cenário 1:

```bash
PROJECT_ID="femsa-ml-apps"

# Build
docker build -f Dockerfile.cenario1 -t gcr.io/$PROJECT_ID/femsa-cenario1 .

# Push
docker push gcr.io/$PROJECT_ID/femsa-cenario1

# Deploy
gcloud run deploy femsa-cenario1 \
  --image gcr.io/$PROJECT_ID/femsa-cenario1 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8050
```

#### App Mix Optimization:

```bash
# Build
docker build -f Dockerfile.mix -t gcr.io/$PROJECT_ID/femsa-mix-optimization .

# Push
docker push gcr.io/$PROJECT_ID/femsa-mix-optimization

# Deploy
gcloud run deploy femsa-mix-optimization \
  --image gcr.io/$PROJECT_ID/femsa-mix-optimization \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8051
```

## 🌐 URLs Geradas

Após deploy, você receberá URLs como:

- **App 1:** `https://femsa-cenario1-XXXXX-uc.a.run.app`
- **App 2:** `https://femsa-mix-optimization-XXXXX-uc.a.run.app`

## 🧪 Testar Localmente Antes

```bash
# Build local
docker build -f Dockerfile.cenario1 -t femsa-cenario1 .

# Rodar
docker run -p 8050:8050 femsa-cenario1

# Acessar: http://localhost:8050
```

## 💰 Custos

### Free Tier:
- **2 milhões de requisições/mês** grátis
- **360.000 GB-segundos** de memória grátis
- **180.000 vCPU-segundos** grátis

**Estimativa:** Gratuito para uso moderado!

## ✅ Checklist

- [ ] Google Cloud SDK instalado
- [ ] Projeto GCP criado
- [ ] Autenticado (`gcloud auth login`)
- [ ] APIs habilitadas
- [ ] Dockerfiles testados localmente
- [ ] Deploy realizado
- [ ] URLs testadas

## 🎉 Pronto!

Agora seus apps estão no Cloud Run e podem ser acessados de qualquer lugar!

---

**Dúvidas?** Veja `DEPLOY_CLOUD_RUN.md` para guia completo.

