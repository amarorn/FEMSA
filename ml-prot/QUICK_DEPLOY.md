# 🚀 Deploy Rápido - Render.com (5 minutos)

## Passo a Passo Simplificado

### 1. Preparar Repositório

Certifique-se de que seu código está no GitHub:

```bash
git add .
git commit -m "Preparar para deploy"
git push origin main
```

### 2. Criar Conta no Render

1. Acesse: https://render.com
2. Clique em "Get Started for Free"
3. Conecte sua conta GitHub

### 3. Deploy do App 1 (Cenário 1 Corporativo)

1. No dashboard do Render, clique em **"New +"** → **"Web Service"**
2. Conecte seu repositório GitHub
3. Selecione o repositório
4. Configure:
   - **Name:** `femsa-cenario1`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements-minimal.txt`
   - **Start Command:** `python app_cenario1_corporativo.py`
   - **Plan:** `Free`
5. Clique em **"Create Web Service"**
6. Aguarde o deploy (2-5 minutos)

### 4. Deploy do App 2 (Otimização de Mix)

1. Repita o processo acima
2. Configure:
   - **Name:** `femsa-mix-optimization`
   - **Start Command:** `python app_mix_optimization.py`
   - **Plan:** `Free`

### 5. Obter URLs

Após o deploy, você terá URLs como:

- **App 1:** `https://femsa-cenario1.onrender.com`
- **App 2:** `https://femsa-mix-optimization.onrender.com`

### 6. Compartilhar com Cliente

Envie as URLs para o cliente testar!

---

## ⚠️ Importante

### Apps "Dormem" no Plano Gratuito

- Apps ficam inativos após 15 minutos sem uso
- Primeira requisição após dormir pode demorar ~30 segundos
- Isso é normal no plano gratuito

### Solução Alternativa (Apps Não Dormem)

Se precisar que os apps não durmam, considere:

1. **Fly.io** (3 apps grátis que não dormem)
2. **Upgrade para plano pago no Render** ($7/mês por app)

---

## 🔧 Troubleshooting

### Erro: "Module not found"

Adicione a dependência faltante em `requirements-minimal.txt`

### Erro: "Port already in use"

Os apps já estão configurados para ler PORT do ambiente. Não precisa ajustar.

### App não inicia

Verifique os logs no dashboard do Render para ver o erro específico.

---

## ✅ Pronto!

Agora o cliente pode acessar os apps pela internet sem instalar nada!

