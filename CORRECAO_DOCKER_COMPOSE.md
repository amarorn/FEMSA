# 🔧 Correção do Docker Compose

## ❌ Erro Encontrado

```
"/ml-prot/assets": not found
```

## 🔍 Causa

O `docker-compose.yml` estava sendo executado de dentro de `ml-prot/`, mas os Dockerfiles esperam o contexto da **raiz do projeto** (com caminhos `ml-prot/...`).

## ✅ Correção Aplicada

Ajustei o `docker-compose.yml` para:
1. **Usar contexto da raiz:** `context: ..`
2. **Caminho correto do Dockerfile:** `dockerfile: ml-prot/Dockerfile.cenario1`
3. **Portas ajustadas:** Mapeamento correto (8050:8080)

## 🚀 Como Usar Agora

Execute o docker-compose da raiz do projeto:

```bash
# Da raiz do projeto
cd /Users/joseamaro/Documents/Projeto/FEMSA
docker-compose -f ml-prot/docker-compose.yml up
```

Ou de dentro de `ml-prot/`:

```bash
cd ml-prot
docker-compose up
```

O docker-compose agora usa o contexto correto automaticamente.

## 📋 Mudanças

**Antes:**
```yaml
context: .
dockerfile: Dockerfile.cenario1
```

**Agora:**
```yaml
context: ..
dockerfile: ml-prot/Dockerfile.cenario1
```

## ✅ Testar

```bash
cd ml-prot
docker-compose up
```

Agora deve funcionar corretamente!

