# 🔧 Correção do Erro Cloud Build

## ❌ Erro Encontrado

```
unable to prepare context: unable to evaluate symlinks in Dockerfile path: 
lstat /workspace/Dockerfile: no such file or directory
```

## 🔍 Causa

O Cloud Build estava procurando os Dockerfiles na raiz do repositório, mas eles estão em `ml-prot/`.

## ✅ Solução Aplicada

Criado `cloudbuild.yaml` na **raiz do repositório** com a configuração `dir: 'ml-prot'` para mudar o diretório antes de fazer o build.

## 📝 O que foi feito

1. ✅ Criado `cloudbuild.yaml` na raiz do repositório
2. ✅ Adicionado `dir: 'ml-prot'` nos steps de build
3. ✅ Configurado para usar os Dockerfiles corretos
4. ✅ Adicionado `--port` nos deploys do Cloud Run

## 🚀 Próximos Passos

1. **Commit e push do novo arquivo:**
```bash
git add cloudbuild.yaml
git commit -m "Fix: Add cloudbuild.yaml in root directory"
git push origin main
```

2. **Ou fazer novo build:**
```bash
gcloud builds submit --config cloudbuild.yaml
```

## 📋 Estrutura Correta

```
FEMSA/
├── cloudbuild.yaml          ← NOVO (na raiz)
└── ml-prot/
    ├── Dockerfile.cenario1
    ├── Dockerfile.mix
    ├── cloudbuild.yaml      ← Pode manter ou remover
    └── ...
```

## ⚠️ Importante

- O `cloudbuild.yaml` na raiz é o que o Cloud Build vai usar automaticamente
- O `cloudbuild.yaml` em `ml-prot/` pode ser removido ou mantido para referência
- Certifique-se de que o arquivo está commitado no repositório

## 🧪 Testar Localmente

Antes de fazer push, você pode testar:

```bash
# Testar build local (simula o que o Cloud Build fará)
cd ml-prot
docker build -f Dockerfile.cenario1 -t test-cenario1 .
docker build -f Dockerfile.mix -t test-mix .
```

## ✅ Checklist

- [x] Criado `cloudbuild.yaml` na raiz
- [x] Configurado `dir: 'ml-prot'` nos steps
- [ ] Commit e push do arquivo
- [ ] Testar build no Cloud Build

