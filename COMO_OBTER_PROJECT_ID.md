# 📋 Como Obter o Project ID

## 🔍 Diferença entre Project ID e Project Number

- **Project ID:** Nome do projeto (ex: `meu-projeto-femsa`)
- **Project Number:** Número único (ex: `426244243362`)

## ✅ Como Obter o Project ID

### Opção 1: Via Console Web
1. Acesse: https://console.cloud.google.com
2. No topo, veja o nome do projeto (esse é o Project ID)

### Opção 2: Via gcloud CLI
```bash
# Listar todos os projetos
gcloud projects list

# Ver projeto atual
gcloud config get-value project

# Ver detalhes de um projeto específico
gcloud projects describe PROJECT_NUMBER --format="value(projectId)"
```

### Opção 3: Converter Project Number para Project ID
```bash
# Se você tem o project number (426244243362)
gcloud projects list --filter="projectNumber=426244243362" --format="value(projectId)"
```

## 🚀 Usar no Script

### Opção A: Definir como variável de ambiente
```bash
export GCP_PROJECT_ID="meu-projeto-femsa"
cd ml-prot
./deploy-cloud-run.sh
```

### Opção B: Digitar quando solicitado
```bash
cd ml-prot
./deploy-cloud-run.sh
# Quando pedir, digite o Project ID (nome), não o número
```

## ⚠️ Importante

O script agora tenta converter automaticamente se você digitar um número, mas é melhor usar o **Project ID (nome)** diretamente.

## 📝 Exemplo

**❌ Errado:**
```
Digite o Project ID: 426244243362
```

**✅ Correto:**
```
Digite o Project ID: meu-projeto-femsa
```

## 🔧 Se o Script Não Converter Automaticamente

Execute manualmente:
```bash
# Obter Project ID do Project Number
gcloud projects list --filter="projectNumber=426244243362" --format="value(projectId)"

# Usar o resultado no script
export GCP_PROJECT_ID="resultado-do-comando-acima"
./deploy-cloud-run.sh
```

