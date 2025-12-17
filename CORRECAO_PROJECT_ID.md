# 🔧 Correção - Project ID vs Project Number

## ❌ Erro Encontrado

```
ERROR: The value of ``core/project'' property is set to project number.
To use this command, set ``--project'' flag to PROJECT ID
```

## 🔍 Causa

O script estava recebendo o **Project Number** (426244243362) ao invés do **Project ID** (nome do projeto).

## ✅ Correção Aplicada

O script agora:
1. **Detecta** se o valor é um número (project number)
2. **Converte** automaticamente para Project ID
3. **Usa** o Project ID correto em todos os comandos

## 🚀 Como Funciona Agora

O script aceita tanto:
- **Project ID:** `meu-projeto-femsa`
- **Project Number:** `426244243362` (converte automaticamente)

## 📋 Exemplo

```bash
# Com Project Number (converte automaticamente)
./deploy-cloud-run.sh
# Digite: 426244243362
# Script converte para Project ID automaticamente

# Ou defina como variável de ambiente
export GCP_PROJECT_ID="meu-projeto-femsa"
./deploy-cloud-run.sh
```

## ✅ Testar Novamente

Execute o script:

```bash
cd ml-prot
./deploy-cloud-run.sh
```

Agora deve funcionar corretamente!

