# 🌐 Deploy Online - Disponibilizar Apps para Cliente

Este guia mostra como disponibilizar os apps Dash online para o cliente testar, similar ao GitHub Pages mas para aplicações Python.

## 🎯 Opções Gratuitas Recomendadas

### 1. Render.com (⭐ RECOMENDADO - Mais Fácil)

**Vantagens:**
- ✅ Gratuito (com limitações)
- ✅ Deploy automático do GitHub
- ✅ Suporta múltiplos serviços
- ✅ Fácil de configurar

**Passos:**

1. **Preparar arquivos de deploy:**

Crie `render.yaml` na raiz do projeto:

```yaml
services:
  - type: web
    name: femsa-cenario1
    env: python
    buildCommand: pip install -r requirements-minimal.txt
    startCommand: python app_cenario1_corporativo.py
    envVars:
      - key: PORT
        value: 8050
    plan: free

  - type: web
    name: femsa-mix-optimization
    env: python
    buildCommand: pip install -r requirements-minimal.txt
    startCommand: python app_mix_optimization.py
    envVars:
      - key: PORT
        value: 8051
    plan: free
```

**OU** crie um único serviço que inicia ambos (mais simples):

Crie `Procfile`:
```
web: python start_apps.py
```

E `render.yaml`:
```yaml
services:
  - type: web
    name: femsa-apps
    env: python
    buildCommand: pip install -r requirements-minimal.txt
    startCommand: python start_apps.py
    plan: free
```

2. **Ajustar apps para usar PORT do ambiente:**

Atualize `start_apps.py` para ler PORT do ambiente.

3. **Deploy no Render:**

- Acesse: https://render.com
- Conecte sua conta GitHub
- New → Web Service
- Selecione seu repositório
- Render detecta automaticamente as configurações
- Clique em "Create Web Service"

**URLs geradas:**
- `https://femsa-cenario1.onrender.com`
- `https://femsa-mix-optimization.onrender.com`

---

### 2. Railway.app

**Vantagens:**
- ✅ Gratuito ($5 crédito/mês)
- ✅ Deploy automático
- ✅ Muito rápido

**Passos:**

1. Crie `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python start_apps.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. Acesse: https://railway.app
3. New Project → Deploy from GitHub repo
4. Selecione seu repositório
5. Railway detecta automaticamente

---

### 3. Fly.io

**Vantagens:**
- ✅ Gratuito (3 VMs grátis)
- ✅ Muito rápido
- ✅ Boa performance

**Passos:**

1. Instale Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Crie `fly.toml`:
```toml
app = "femsa-apps"
primary_region = "gru"  # ou outra região próxima

[build]
  builder = "paketobuildpacks/builder:base"

[[services]]
  internal_port = 8050
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

3. Deploy:
```bash
fly launch
fly deploy
```

---

### 4. PythonAnywhere

**Vantagens:**
- ✅ Gratuito (plano Beginner)
- ✅ Interface web completa
- ✅ Bom para testes

**Passos:**

1. Acesse: https://www.pythonanywhere.com
2. Crie conta gratuita
3. Web → Add a new web app
4. Escolha Flask (pode usar Dash também)
5. Faça upload dos arquivos via Files
6. Configure o WSGI file

---

## 🔧 Ajustes Necessários nos Apps

### Opção A: Modificar start_apps.py para usar PORT

Atualize `start_apps.py` para ler a porta do ambiente:

```python
import os

# Ler porta do ambiente (para deploy) ou usar padrão
PORT = int(os.environ.get('PORT', 8050))
PORT2 = int(os.environ.get('PORT2', 8051))

# Nos apps, use:
# app.run(host='0.0.0.0', port=PORT, debug=False)
```

### Opção B: Criar versão de produção

Crie `start_apps_prod.py` que lê PORT do ambiente.

---

## 📝 Checklist Antes de Deploy

- [ ] Testar apps localmente
- [ ] Verificar que `requirements-minimal.txt` tem todas as dependências
- [ ] Remover `debug=True` nos apps de produção
- [ ] Configurar `host='0.0.0.0'` nos apps
- [ ] Testar que apps funcionam com PORT do ambiente
- [ ] Verificar que dados necessários estão disponíveis (ou usar dados de exemplo)

---

## 🚀 Deploy Rápido (Render.com)

### Passo a Passo Simplificado:

1. **Criar `render.yaml`:**
```yaml
services:
  - type: web
    name: femsa-apps
    env: python
    buildCommand: pip install -r requirements-minimal.txt
    startCommand: python start_apps.py
    plan: free
```

2. **Commit e push:**
```bash
git add render.yaml
git commit -m "Add render config"
git push origin main
```

3. **No Render.com:**
   - New → Web Service
   - Conecte GitHub
   - Selecione repositório
   - Render detecta `render.yaml`
   - Deploy!

4. **Compartilhar URL com cliente:**
   - `https://femsa-apps.onrender.com`

---

## ⚠️ Limitações do Plano Gratuito

### Render.com:
- Apps "dormem" após 15min de inatividade
- Primeira requisição pode demorar ~30s (wake up)
- 750 horas/mês grátis

### Railway:
- $5 crédito/mês
- Apps podem dormir após inatividade

### Fly.io:
- 3 VMs grátis
- Apps não dormem (melhor opção)

---

## 🔗 URLs Finais

Após deploy, você terá URLs como:

- **Render:** `https://femsa-apps.onrender.com`
- **Railway:** `https://femsa-apps.up.railway.app`
- **Fly.io:** `https://femsa-apps.fly.dev`

Compartilhe essas URLs com o cliente para teste!

---

## 📞 Suporte

Se tiver problemas no deploy, verifique:
1. Logs do serviço (disponível no dashboard)
2. Se todas as dependências estão em `requirements-minimal.txt`
3. Se os apps estão configurados para `host='0.0.0.0'`

