# ⚡ Deploy Rápido - Python no GCP (5 minutos)

## 🎯 Comando Único para Deploy

```bash
gcloud run deploy minha-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

**Pronto!** Você terá uma URL pública em segundos.

## 📋 Pré-requisitos (Uma vez só)

```bash
# 1. Login
gcloud auth login

# 2. Configurar projeto
gcloud config set project SEU_PROJECT_ID

# 3. Habilitar APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## ✅ Checklist Mínimo

- [ ] Dockerfile existe
- [ ] App lê `os.environ.get('PORT')`
- [ ] App usa `host='0.0.0.0'`
- [ ] `gcloud auth login` feito

## 🚀 Deploy

```bash
# No diretório do seu projeto
gcloud run deploy minha-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## 🌐 Obter URL

Após deploy, a URL aparece no output. Ou:

```bash
gcloud run services describe minha-app \
  --region us-central1 \
  --format="value(status.url)"
```

## 💡 Dica

O Cloud Run detecta automaticamente:
- ✅ Dockerfile
- ✅ requirements.txt
- ✅ Estrutura Python

Não precisa configurar nada além do Dockerfile!

## 📝 Exemplo Mínimo

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
ENV PORT=8080
CMD ["python", "app.py"]
```

### app.py
```python
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Olá do Cloud Run!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

### Deploy
```bash
gcloud run deploy minha-app --source . --region us-central1 --allow-unauthenticated
```

**Pronto!** URL pública gerada automaticamente.

