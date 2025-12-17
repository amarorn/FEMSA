# 🚀 Commit do cloudbuild.yaml - Instruções

## ✅ Problema Identificado

O arquivo `cloudbuild.yaml` existe localmente mas **não está commitado no Git**. O Cloud Build usa o código do repositório, então precisa do arquivo no Git.

## 📝 Comandos para Fazer Commit

Execute estes comandos:

```bash
cd /Users/joseamaro/Documents/Projeto/FEMSA

# Adicionar o arquivo
git add cloudbuild.yaml

# Fazer commit
git commit -m "Fix: Add cloudbuild.yaml in root directory for Cloud Build

- Configured to build from ml-prot/ directory
- Builds both apps: femsa-cenario1 and femsa-mix-optimization
- Deploys to Cloud Run with correct ports"

# Fazer push
git push origin main
```

## 🔍 Verificar Antes do Push

```bash
# Ver o que será commitado
git status

# Ver o conteúdo do arquivo
cat cloudbuild.yaml
```

## ⚠️ Importante

Após o push:
1. O Cloud Build vai detectar automaticamente o novo arquivo
2. O próximo build deve funcionar
3. Se tiver um trigger configurado, ele vai rodar automaticamente

## 🧪 Testar Localmente (Opcional)

Antes de fazer push, você pode testar:

```bash
# Testar se os Dockerfiles funcionam
cd ml-prot
docker build -f Dockerfile.cenario1 -t test-cenario1 .
docker build -f Dockerfile.mix -t test-mix .
```

Se os builds locais funcionarem, o Cloud Build também deve funcionar.

