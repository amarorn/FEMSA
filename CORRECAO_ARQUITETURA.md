# 🔧 Correção - Erro de Arquitetura (exec format error)

## ❌ Erro Encontrado

```
terminated: Application failed to start: failed to load /usr/local/bin/python: exec format error
```

## 🔍 Causa

O erro "exec format error" indica incompatibilidade de arquitetura:
- **Cloud Run** roda em **linux/amd64** (x86_64)
- Se você está em **Mac M1/M2** (ARM64), o Docker pode buildar para ARM por padrão
- O binário Python compilado para ARM não roda em AMD64

## ✅ Correção Aplicada

Adicionado `--platform linux/amd64` no build do Docker:

```bash
docker build --platform linux/amd64 -f ml-prot/Dockerfile.cenario1 -t "$IMAGE" .
```

Isso força o Docker a buildar para a arquitetura correta do Cloud Run.

## 🚀 Testar Novamente

Execute o deploy:

```bash
cd ml-prot
./deploy-cloud-run.sh
```

## 📋 O que foi corrigido

- ✅ `--platform linux/amd64` adicionado no build do App 1
- ✅ `--platform linux/amd64` adicionado no build do App 2
- ✅ Imagens agora são compatíveis com Cloud Run

## 💡 Nota

Se você estiver em Mac M1/M2, o Docker pode usar emulação (mais lento), mas o resultado será compatível com Cloud Run.

## ✅ Verificar Arquitetura da Imagem

Após o build, você pode verificar:

```bash
docker inspect IMAGE_NAME | grep Architecture
```

Deve mostrar: `"Architecture": "amd64"`

