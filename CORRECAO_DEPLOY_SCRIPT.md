# 🔧 Correção do Script de Deploy

## ❌ Erro Encontrado

```
ERROR: failed to build: failed to solve: failed to compute cache key: 
"/ml-prot/data": not found
```

## 🔍 Causa

O script `deploy-cloud-run.sh` estava sendo executado de dentro de `ml-prot/`, mas os Dockerfiles esperam o contexto da **raiz do projeto** (com caminhos `ml-prot/...`).

## ✅ Correção Aplicada

Ajustei o script para:
1. **Detectar automaticamente a raiz do projeto**
2. **Mudar para a raiz antes de fazer build**
3. **Usar caminhos corretos:** `-f ml-prot/Dockerfile.cenario1`

## 🚀 Como Usar Agora

O script pode ser executado de qualquer lugar:

```bash
# De dentro de ml-prot/
cd ml-prot
./deploy-cloud-run.sh

# Ou da raiz
cd /Users/joseamaro/Documents/Projeto/FEMSA
./ml-prot/deploy-cloud-run.sh
```

O script automaticamente vai para a raiz antes de fazer o build.

## 📋 O que foi corrigido

- ✅ Script detecta e muda para raiz automaticamente
- ✅ Caminhos dos Dockerfiles ajustados: `-f ml-prot/Dockerfile.*`
- ✅ Contexto do build agora é a raiz (`.`)
- ✅ Caminhos `ml-prot/...` nos Dockerfiles funcionam corretamente

## 🧪 Testar

```bash
cd ml-prot
./deploy-cloud-run.sh
```

O build deve funcionar agora!

