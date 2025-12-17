# 📋 Como Ver Logs do Cloud Scheduler

Guia para verificar logs e diagnosticar erros no Google Cloud Scheduler.

## 🔍 Ver Logs do Cloud Scheduler

### Opção 1: Via Console Web (Mais Fácil)

1. Acesse: https://console.cloud.google.com/cloudscheduler
2. Selecione seu projeto
3. Clique no job que está com erro
4. Vá na aba **"Execuções"** ou **"History"**
5. Clique na execução que falhou
6. Veja os detalhes do erro

### Opção 2: Via gcloud CLI

```bash
# Listar jobs do Cloud Scheduler
gcloud scheduler jobs list

# Ver detalhes de um job específico
gcloud scheduler jobs describe JOB_NAME --location=LOCATION

# Ver histórico de execuções
gcloud scheduler jobs describe JOB_NAME --location=LOCATION --format="yaml"

# Ver logs das execuções
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=JOB_NAME" --limit 50
```

### Opção 3: Via Cloud Logging

```bash
# Ver logs do Cloud Scheduler
gcloud logging read "resource.type=cloud_scheduler_job" --limit 50 --format json

# Ver logs de um job específico
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=JOB_NAME" --limit 50

# Ver logs com filtro de erro
gcloud logging read "resource.type=cloud_scheduler_job AND severity>=ERROR" --limit 50

# Ver logs das últimas 24 horas
gcloud logging read "resource.type=cloud_scheduler_job AND timestamp>=\"$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)\"" --limit 100
```

## 🔍 Ver Logs do Cloud Run (Se o Scheduler chama Cloud Run)

```bash
# Ver logs do Cloud Run
gcloud run services logs read SERVICE_NAME --region=REGION --limit 50

# Ver logs em tempo real
gcloud run services logs read SERVICE_NAME --region=REGION --follow

# Ver logs com filtro de erro
gcloud run services logs read SERVICE_NAME --region=REGION --limit 50 | grep -i error

# Ver logs das últimas execuções
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" --limit 50
```

## 🐛 Erros Comuns e Soluções

### Erro: "Permission denied"

```bash
# Verificar permissões
gcloud projects get-iam-policy PROJECT_ID

# Adicionar permissão ao service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Erro: "Job not found"

```bash
# Listar todos os jobs
gcloud scheduler jobs list --location=LOCATION

# Verificar se o job existe
gcloud scheduler jobs describe JOB_NAME --location=LOCATION
```

### Erro: "HTTP 404" ou "Service not found"

Verifique se:
- O Cloud Run service existe
- A URL está correta
- O serviço está ativo

```bash
# Listar serviços Cloud Run
gcloud run services list

# Verificar URL do serviço
gcloud run services describe SERVICE_NAME --region=REGION --format="value(status.url)"
```

### Erro: "Authentication failed"

```bash
# Verificar service account
gcloud scheduler jobs describe JOB_NAME --location=LOCATION --format="value(httpTarget.oidcToken.serviceAccountEmail)"

# Adicionar permissão ao service account
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker"
```

## 📊 Script para Ver Logs Completos

Crie um script `ver_logs.sh`:

```bash
#!/bin/bash
# Script para ver logs do Cloud Scheduler e Cloud Run

PROJECT_ID="${GCP_PROJECT_ID:-}"
JOB_NAME="${1:-}"
SERVICE_NAME="${2:-}"
REGION="${GCP_REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Erro: GCP_PROJECT_ID não definido"
    exit 1
fi

echo "=========================================================================="
echo "Logs do Cloud Scheduler"
echo "=========================================================================="

if [ -z "$JOB_NAME" ]; then
    echo "Listando todos os jobs..."
    gcloud scheduler jobs list --location=$REGION
else
    echo "Logs do job: $JOB_NAME"
    gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=$JOB_NAME" \
        --limit 50 --format="table(timestamp,severity,textPayload,jsonPayload.message)"
fi

if [ ! -z "$SERVICE_NAME" ]; then
    echo ""
    echo "=========================================================================="
    echo "Logs do Cloud Run: $SERVICE_NAME"
    echo "=========================================================================="
    gcloud run services logs read $SERVICE_NAME --region=$REGION --limit 50
fi
```

Tornar executável:
```bash
chmod +x ver_logs.sh
```

Uso:
```bash
./ver_logs.sh JOB_NAME SERVICE_NAME
```

## 🔧 Verificar Status do Job

```bash
# Ver status de um job
gcloud scheduler jobs describe JOB_NAME --location=LOCATION

# Ver última execução
gcloud scheduler jobs describe JOB_NAME --location=LOCATION \
  --format="value(state,lastAttemptTime,status.code,status.message)"
```

## 📝 Comandos Úteis

```bash
# Ver todos os logs recentes (últimas 2 horas)
gcloud logging read "timestamp>=\"$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)\"" --limit 100

# Exportar logs para arquivo
gcloud logging read "resource.type=cloud_scheduler_job" --limit 1000 --format json > logs.json

# Ver logs com filtro de tempo específico
gcloud logging read "resource.type=cloud_scheduler_job AND timestamp>=\"2024-01-01T00:00:00Z\" AND timestamp<=\"2024-01-02T00:00:00Z\"" --limit 100
```

## 🎯 Ver Logs no Console Web

### Cloud Scheduler:
1. https://console.cloud.google.com/cloudscheduler
2. Clique no job
3. Aba "Execuções" → Veja histórico
4. Clique em uma execução → Veja detalhes

### Cloud Logging:
1. https://console.cloud.google.com/logs
2. Filtros:
   - Resource: `Cloud Scheduler Job`
   - Ou: `Cloud Run Revision`
3. Veja logs em tempo real

## ⚠️ Troubleshooting Rápido

```bash
# 1. Ver se o job existe
gcloud scheduler jobs list

# 2. Ver detalhes do job
gcloud scheduler jobs describe JOB_NAME --location=LOCATION

# 3. Ver logs do job
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=JOB_NAME" --limit 20

# 4. Testar manualmente
gcloud scheduler jobs run JOB_NAME --location=LOCATION

# 5. Ver logs do Cloud Run (se aplicável)
gcloud run services logs read SERVICE_NAME --region=REGION --limit 20
```

## 📞 Próximos Passos

1. Execute os comandos acima para ver os logs
2. Identifique o erro específico
3. Use as soluções sugeridas
4. Se necessário, compartilhe o erro para mais ajuda



