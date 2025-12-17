# 🚀 Como Publicar Aplicação Python no GCP com URL Pública

Guia completo para publicar aplicações Python (Dash, Flask, FastAPI) no Google Cloud Platform e obter uma URL pública.

## 🎯 Opções no GCP

### 1. Cloud Run (⭐ RECOMENDADO)
- ✅ Serverless (paga apenas pelo uso)
- ✅ Escala automaticamente
- ✅ HTTPS automático
- ✅ URL pública automática
- ✅ Gratuito até 2M requisições/mês

### 2. App Engine
- ✅ Gerenciado pelo Google
- ✅ Escala automática
- ⚠️ Mais complexo de configurar

### 3. Compute Engine (VM)
- ⚠️ Mais trabalho manual
- ⚠️ Precisa gerenciar servidor

## 🚀 Cloud Run - Passo a Passo Completo

### Pré-requisitos

1. **Conta Google Cloud Platform**
   - Acesse: https://console.cloud.google.com
   - Crie um projeto ou use existente

2. **Google Cloud SDK instalado**
```bash
# macOS
brew install google-cloud-sdk

# Ou baixe: https://cloud.google.com/sdk/docs/install
```

3. **Docker instalado** (para testar localmente)
```bash
# macOS
brew install docker

# Ou baixe: https://www.docker.com/products/docker-desktop
```

### Passo 1: Preparar a Aplicação

#### 1.1 Criar Dockerfile

Crie um `Dockerfile` na raiz do seu projeto:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .
COPY assets/ ./assets/  # Se tiver assets

# Cloud Run usa PORT automaticamente
ENV PORT=8080
EXPOSE 8080

# Comando para iniciar
CMD ["python", "app.py"]
```

#### 1.2 Ajustar App para Ler PORT

No seu `app.py`:

```python
import os

# Ler porta do ambiente (Cloud Run define automaticamente)
port = int(os.environ.get('PORT', 8080))

# Iniciar app
app.run(host='0.0.0.0', port=port, debug=False)
```

### Passo 2: Configurar GCP

#### 2.1 Autenticar

```bash
# Login
gcloud auth login

# Configurar projeto
gcloud config set project SEU_PROJECT_ID

# Habilitar APIs necessárias
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Configurar Docker
gcloud auth configure-docker
```

### Passo 3: Build e Deploy

#### Opção A: Build e Deploy Manual

```bash
# 1. Build da imagem Docker
docker build -t gcr.io/SEU_PROJECT_ID/minha-app .

# 2. Push para Container Registry
docker push gcr.io/SEU_PROJECT_ID/minha-app

# 3. Deploy no Cloud Run
gcloud run deploy minha-app \
  --image gcr.io/SEU_PROJECT_ID/minha-app \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

#### Opção B: Build Automático (Recomendado)

```bash
# Build e deploy em um comando
gcloud run deploy minha-app \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

O Cloud Run vai:
1. Detectar o Dockerfile automaticamente
2. Fazer build da imagem
3. Fazer deploy
4. Gerar URL pública automaticamente

### Passo 4: Obter URL Pública

Após o deploy, você receberá uma URL como:

```
https://minha-app-XXXXX-uc.a.run.app
```

**Essa URL já é pública e acessível de qualquer lugar!**

## 📋 Exemplo Completo - App Dash

### 1. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY assets/ ./assets/

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
```

### 2. app.py

```python
from dash import Dash, html
import os

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Minha App Python"),
    html.P("Funcionando no Cloud Run!")
])

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
```

### 3. requirements.txt

```
dash>=2.14.0
plotly>=5.17.0
pandas>=2.0.0
```

### 4. Deploy

```bash
gcloud run deploy minha-app-dash \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔧 Configurações Avançadas

### Aumentar Memória/CPU

```bash
gcloud run deploy minha-app \
  --memory 2Gi \
  --cpu 2 \
  --region us-central1
```

### Configurar Variáveis de Ambiente

```bash
gcloud run deploy minha-app \
  --set-env-vars "DEBUG=false,API_KEY=valor" \
  --region us-central1
```

### Configurar Timeout

```bash
gcloud run deploy minha-app \
  --timeout 300 \
  --region us-central1
```

### Configurar Concorrência

```bash
gcloud run deploy minha-app \
  --concurrency 10 \
  --region us-central1
```

## 💰 Custos

### Free Tier (Gratuito)
- **2 milhões de requisições/mês**
- **360.000 GB-segundos** de memória
- **180.000 vCPU-segundos**

### Após Free Tier
- **$0.40 por milhão de requisições**
- **$0.0000025 por GB-segundo** de memória
- **$0.0000100 por vCPU-segundo**

**Estimativa para uso moderado:** ~$5-10/mês

## 🔒 Segurança

### Tornar App Privado (Opcional)

```bash
# Remover --allow-unauthenticated
gcloud run deploy minha-app \
  --no-allow-unauthenticated \
  --region us-central1
```

Para acessar:
```bash
# Obter token
TOKEN=$(gcloud auth print-identity-token)

# Fazer requisição
curl -H "Authorization: Bearer $TOKEN" \
  https://minha-app-XXXXX-uc.a.run.app
```

## 📊 Monitoramento

### Ver Logs

```bash
# Logs em tempo real
gcloud run services logs read minha-app --region us-central1 --follow

# Últimos logs
gcloud run services logs read minha-app --region us-central1 --limit 50
```

### Ver Métricas

Acesse: https://console.cloud.google.com/run
- Ver requisições
- Ver uso de CPU/memória
- Ver latência

## 🔄 Atualizar Aplicação

```bash
# Fazer alterações no código
# ...

# Deploy novamente (mesmo comando)
gcloud run deploy minha-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

A URL permanece a mesma!

## 🐛 Troubleshooting

### Erro: "Permission denied"
```bash
gcloud auth login
gcloud auth application-default login
```

### Erro: "Service not found"
```bash
# Listar serviços
gcloud run services list

# Verificar se o serviço existe
gcloud run services describe minha-app --region us-central1
```

### App não inicia
```bash
# Ver logs
gcloud run services logs read minha-app --region us-central1 --limit 100
```

### Porta incorreta
Certifique-se de que o app lê `os.environ.get('PORT')` e usa `host='0.0.0.0'`.

## ✅ Checklist Rápido

- [ ] Dockerfile criado
- [ ] App ajustado para ler PORT do ambiente
- [ ] `host='0.0.0.0'` configurado
- [ ] Google Cloud SDK instalado
- [ ] Autenticado (`gcloud auth login`)
- [ ] Projeto configurado
- [ ] APIs habilitadas
- [ ] Deploy realizado
- [ ] URL pública obtida

## 🎉 Resultado Final

Após o deploy, você terá:

✅ **URL pública:** `https://minha-app-XXXXX-uc.a.run.app`  
✅ **HTTPS automático**  
✅ **Escala automática**  
✅ **Sem servidor para gerenciar**  
✅ **Gratuito para uso moderado**  

## 📚 Comandos Úteis

```bash
# Listar serviços
gcloud run services list

# Ver detalhes de um serviço
gcloud run services describe minha-app --region us-central1

# Ver URL do serviço
gcloud run services describe minha-app --region us-central1 \
  --format="value(status.url)"

# Deletar serviço
gcloud run services delete minha-app --region us-central1
```

## 🚀 Deploy Rápido (1 Comando)

Para apps simples, você pode fazer tudo em um comando:

```bash
gcloud run deploy minha-app \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

O Cloud Run detecta automaticamente:
- Dockerfile
- requirements.txt
- Estrutura do projeto

## 🎯 Para o Projeto FEMSA

Você já tem tudo configurado! Basta:

```bash
# Deploy do app unificado
cd ml-prot
gcloud run deploy femsa-app-unificado \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8052
```

Ou usar o `cloudbuild.yaml` que já criamos para deploy automático via GitHub!

