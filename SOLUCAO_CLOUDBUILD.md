# 🔧 Solução Completa - Erro Cloud Build

## ❌ Erro Atual

```
unable to prepare context: unable to evaluate symlinks in Dockerfile path: 
lstat /workspace/Dockerfile: no such file or directory
```

## 🔍 Diagnóstico

O Cloud Build está procurando um `Dockerfile` padrão na raiz, mas:
1. Os Dockerfiles estão em `ml-prot/`
2. O `cloudbuild.yaml` pode não estar sendo usado
3. O build pode estar sendo acionado sem especificar o arquivo de configuração

## ✅ Soluções

### Solução 1: Garantir que cloudbuild.yaml está commitado

```bash
# Verificar se o arquivo existe
ls -la cloudbuild.yaml

# Se não estiver no Git, adicionar
git add cloudbuild.yaml
git commit -m "Add cloudbuild.yaml in root"
git push origin main
```

### Solução 2: Especificar o arquivo explicitamente no build

Se o build está sendo acionado manualmente ou via trigger:

```bash
# Fazer build especificando o arquivo
gcloud builds submit --config cloudbuild.yaml

# Ou se estiver em um subdiretório
gcloud builds submit --config ml-prot/cloudbuild.yaml
```

### Solução 3: Criar Dockerfile na raiz (alternativa)

Se o Cloud Build está configurado para usar Dockerfile padrão, podemos criar um na raiz que redireciona:

```dockerfile
# Dockerfile na raiz (apenas para compatibilidade)
# O build real está em ml-prot/
FROM python:3.11-slim
WORKDIR /app
COPY ml-prot/requirements-minimal.txt .
RUN pip install --no-cache-dir -r requirements-minimal.txt
COPY ml-prot/app_unificado.py .
COPY ml-prot/assets/ ./assets/
COPY ml-prot/simulador_pnl_futuro_base.csv* ./
COPY ml-prot/data/ ./data/
ENV PORT=8052
EXPOSE 8052
CMD ["python", "app_unificado.py"]
```

### Solução 4: Verificar configuração do Trigger

Se você tem um Cloud Build Trigger configurado:

1. Acesse: https://console.cloud.google.com/cloud-build/triggers
2. Clique no trigger
3. Verifique:
   - **Configuration:** Deve estar como "Cloud Build configuration file"
   - **Location:** Deve apontar para `cloudbuild.yaml` (na raiz)
   - **Substitution variables:** Verificar se há variáveis necessárias

## 🎯 Solução Recomendada (Passo a Passo)

### 1. Verificar se cloudbuild.yaml está no repositório

```bash
cd /Users/joseamaro/Documents/Projeto/FEMSA
git status
git log --oneline --all -- cloudbuild.yaml
```

### 2. Se não estiver, adicionar e fazer commit

```bash
git add cloudbuild.yaml
git commit -m "Fix: Add cloudbuild.yaml in root for Cloud Build"
git push origin main
```

### 3. Verificar o trigger do Cloud Build

```bash
# Listar triggers
gcloud builds triggers list

# Ver detalhes de um trigger
gcloud builds triggers describe TRIGGER_NAME
```

### 4. Se necessário, atualizar o trigger

```bash
# Atualizar trigger para usar cloudbuild.yaml na raiz
gcloud builds triggers update TRIGGER_NAME \
  --build-config cloudbuild.yaml \
  --included-files cloudbuild.yaml,ml-prot/**
```

### 5. Testar build manualmente

```bash
# Testar build local primeiro
cd ml-prot
docker build -f Dockerfile.cenario1 -t test .

# Se funcionar, fazer build no Cloud
gcloud builds submit --config cloudbuild.yaml
```

## 🔍 Verificar Logs do Build

```bash
# Ver último build
gcloud builds list --limit 1

# Ver logs do último build
BUILD_ID=$(gcloud builds list --limit 1 --format="value(id)")
gcloud builds log $BUILD_ID
```

## 📋 Checklist de Verificação

- [ ] `cloudbuild.yaml` existe na raiz do repositório
- [ ] `cloudbuild.yaml` está commitado no Git
- [ ] Dockerfiles existem em `ml-prot/`
- [ ] Trigger do Cloud Build está configurado corretamente
- [ ] Build foi testado localmente

## 🚨 Se Nada Funcionar

Criar um Dockerfile simples na raiz que funciona:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY ml-prot/ .
RUN pip install --no-cache-dir -r requirements-minimal.txt
ENV PORT=8052
CMD ["python", "app_unificado.py"]
```

E fazer build simples:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/femsa-app
```

