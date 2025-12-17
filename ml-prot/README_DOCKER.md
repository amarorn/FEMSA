# 🐳 Docker e Google Cloud Run - Resumo

## 📦 Arquivos Criados

### Dockerfiles
- ✅ **Dockerfile.cenario1** - Imagem para App Cenário 1 Corporativo
- ✅ **Dockerfile.mix** - Imagem para App Mix Optimization

### Configuração
- ✅ **.dockerignore** - Arquivos ignorados no build
- ✅ **docker-compose.yml** - Para testar localmente
- ✅ **cloudbuild.yaml** - Build automático no Cloud Build
- ✅ **deploy-cloud-run.sh** - Script de deploy automático

### Documentação
- ✅ **DEPLOY_CLOUD_RUN.md** - Guia completo
- ✅ **QUICK_DEPLOY_CLOUD_RUN.md** - Guia rápido (10 min)

## 🚀 Como Usar

### Opção 1: Script Automático (Mais Fácil)

```bash
export GCP_PROJECT_ID="seu-project-id"
./deploy-cloud-run.sh
```

### Opção 2: Manual

```bash
# Build
docker build -f Dockerfile.cenario1 -t gcr.io/PROJECT_ID/femsa-cenario1 .

# Push
docker push gcr.io/PROJECT_ID/femsa-cenario1

# Deploy
gcloud run deploy femsa-cenario1 \
  --image gcr.io/PROJECT_ID/femsa-cenario1 \
  --region us-central1 \
  --allow-unauthenticated
```

### Opção 3: Testar Localmente

```bash
# Usar docker-compose
docker-compose up --build

# Ou build individual
docker build -f Dockerfile.cenario1 -t femsa-cenario1 .
docker run -p 8050:8050 femsa-cenario1
```

## 📋 Estrutura dos Dockerfiles

```
Dockerfile.cenario1:
├── Base: python:3.11-slim
├── Instala: requirements-minimal.txt
├── Copia: app_cenario1_corporativo.py
├── Copia: assets/
├── Copia: simulador_pnl_futuro_base.csv
└── Copia: data/

Dockerfile.mix:
├── Base: python:3.11-slim
├── Instala: requirements-minimal.txt
├── Copia: app_mix_optimization.py
├── Copia: assets/
└── Copia: data_unified*.csv
```

## ⚙️ Configurações

### Portas
- App 1: Porta 8050 (lê PORT do ambiente)
- App 2: Porta 8051 (lê PORT do ambiente)

### Variáveis de Ambiente
- `PORT` - Porta do app (Cloud Run define automaticamente)
- `DEBUG` - Modo debug (padrão: false em produção)

## 🌐 URLs Após Deploy

- `https://femsa-cenario1-XXXXX-uc.a.run.app`
- `https://femsa-mix-optimization-XXXXX-uc.a.run.app`

## 💡 Dicas

1. **Teste localmente primeiro** com `docker-compose up`
2. **Verifique logs** se algo der errado: `gcloud run services logs read`
3. **Use o script** `deploy-cloud-run.sh` para facilitar
4. **Cloud Run escala automaticamente** conforme demanda

## 📚 Documentação Completa

- **QUICK_DEPLOY_CLOUD_RUN.md** - Guia rápido (10 min)
- **DEPLOY_CLOUD_RUN.md** - Guia completo com todas as opções

## ✅ Pronto para Deploy!

Tudo configurado. Basta executar o script ou seguir o guia rápido!

