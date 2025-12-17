# 🔄 Migração para Artifact Registry

## ✅ Atualização Aplicada

O script `deploy-cloud-run.sh` foi atualizado para usar **Artifact Registry** ao invés de Container Registry (deprecated).

## 🔍 O que mudou

### Antes (Container Registry - Deprecated)
```bash
gcr.io/$PROJECT_ID/femsa-cenario1:latest
```

### Agora (Artifact Registry)
```bash
us-central1-docker.pkg.dev/$PROJECT_ID/femsa-apps/femsa-cenario1:latest
```

## 📋 Mudanças no Script

1. ✅ **Criação automática do repositório** no Artifact Registry
2. ✅ **Autenticação** configurada para Artifact Registry
3. ✅ **Imagens** agora usam o novo formato
4. ✅ **API habilitada** automaticamente

## 🚀 Como Usar

O script funciona da mesma forma:

```bash
cd ml-prot
./deploy-cloud-run.sh
```

O script agora:
1. Cria o repositório `femsa-apps` no Artifact Registry (se não existir)
2. Faz build das imagens
3. Faz push para Artifact Registry
4. Faz deploy no Cloud Run

## 🔧 Configuração

O repositório criado:
- **Nome:** `femsa-apps`
- **Formato:** Docker
- **Localização:** `us-central1` (mesma região do Cloud Run)
- **Descrição:** "FEMSA Applications"

## 📍 URLs das Imagens

As imagens agora estão em:
```
us-central1-docker.pkg.dev/426244243362/femsa-apps/femsa-cenario1:latest
us-central1-docker.pkg.dev/426244243362/femsa-apps/femsa-mix-optimization:latest
```

## ✅ Vantagens do Artifact Registry

- ✅ **Não está deprecated** (Container Registry está)
- ✅ **Melhor performance**
- ✅ **Mais recursos de segurança**
- ✅ **Integração melhor com Cloud Run**

## 🧪 Testar

Execute o script novamente:

```bash
cd ml-prot
./deploy-cloud-run.sh
```

Agora não deve aparecer mais o aviso sobre Container Registry deprecated!

