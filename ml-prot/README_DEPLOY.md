# 📦 Resumo: Como Publicar para Cliente Testar

## 🎯 Duas Opções Principais

### 1️⃣ GitHub (Código) + Deploy Online (Apps Funcionando)

**Melhor para:** Cliente que quer ver código E testar apps online

**Passos:**
1. Publicar código no GitHub (veja `QUICK_START_GIT.md`)
2. Fazer deploy online (veja `QUICK_DEPLOY.md`)
3. Compartilhar:
   - Link do GitHub (código)
   - URLs dos apps (teste online)

---

### 2️⃣ Apenas Deploy Online (Apps Funcionando)

**Melhor para:** Cliente que só quer testar, sem ver código

**Passos:**
1. Fazer deploy no Render.com (5 minutos)
2. Compartilhar apenas as URLs dos apps

---

## 🚀 Opção Mais Rápida: Render.com

### Tempo: ~10 minutos

1. **Criar conta:** https://render.com (conecte GitHub)
2. **Deploy App 1:**
   - New → Web Service
   - Selecione repositório
   - Start Command: `python app_cenario1_corporativo.py`
   - Create
3. **Deploy App 2:**
   - Repita com: `python app_mix_optimization.py`
4. **Pronto!** URLs geradas automaticamente

**URLs finais:**
- `https://femsa-cenario1.onrender.com`
- `https://femsa-mix-optimization.onrender.com`

---

## 📋 Arquivos Criados para Deploy

✅ **render.yaml** - Configuração Render.com  
✅ **railway.json** - Configuração Railway.app  
✅ **Procfile** - Configuração Heroku  
✅ **Apps ajustados** - Agora leem PORT do ambiente  
✅ **requirements-minimal.txt** - Dependências mínimas  

---

## ⚡ Quick Start

```bash
# 1. Publicar no GitHub
git add .
git commit -m "Preparar para deploy"
git push origin main

# 2. Ir para Render.com e fazer deploy
# (veja QUICK_DEPLOY.md para detalhes)

# 3. Compartilhar URLs com cliente
```

---

## 📚 Documentação Completa

- **QUICK_START_GIT.md** - Como publicar código no GitHub
- **QUICK_DEPLOY.md** - Como fazer deploy online (5 min)
- **DEPLOY_ONLINE.md** - Guia completo com todas as opções

---

## ✅ Checklist

Antes de compartilhar com cliente:

- [ ] Apps testados localmente
- [ ] Código publicado no GitHub (opcional)
- [ ] Deploy feito no Render/Railway/Fly
- [ ] URLs testadas e funcionando
- [ ] Dados necessários disponíveis nos apps
- [ ] Cliente tem acesso às URLs

---

## 🎉 Pronto!

Agora o cliente pode:
- ✅ Testar os apps pela internet
- ✅ Ver código no GitHub (se compartilhar)
- ✅ Não precisa instalar nada!

