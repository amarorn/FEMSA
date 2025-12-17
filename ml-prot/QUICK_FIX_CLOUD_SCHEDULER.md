# ⚡ Correção Rápida - Erro no Cloud Scheduler

## 🔍 Ver Logs Rápido

### Via Console Web (Mais Rápido)
1. Acesse: https://console.cloud.google.com/cloudscheduler
2. Clique no job com erro
3. Aba **"Execuções"** → Veja a execução que falhou
4. Clique nela → Veja o erro detalhado

### Via Script
```bash
# Ver logs de um job específico
./ver_logs.sh JOB_NAME

# Ver logs do job e do Cloud Run
./ver_logs.sh JOB_NAME SERVICE_NAME
```

### Via CLI Direto
```bash
# Ver logs do Cloud Scheduler
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=JOB_NAME" --limit 20

# Ver logs do Cloud Run
gcloud run services logs read SERVICE_NAME --region=REGION --limit 20
```

## 🐛 Erros Mais Comuns

### 1. "Permission denied" ou "403 Forbidden"

**Solução:**
```bash
# Adicionar permissão ao service account
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### 2. "404 Not Found" - Service não encontrado

**Solução:**
```bash
# Verificar se o serviço existe
gcloud run services list

# Verificar URL no job
gcloud scheduler jobs describe JOB_NAME --location=REGION
```

### 3. "Authentication failed"

**Solução:**
```bash
# Verificar service account do job
gcloud scheduler jobs describe JOB_NAME --location=REGION \
  --format="value(httpTarget.oidcToken.serviceAccountEmail)"

# Adicionar permissão
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker"
```

### 4. "Timeout" ou "Deadline exceeded"

**Solução:**
```bash
# Aumentar timeout do Cloud Run
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --timeout=300
```

## 🔧 Comandos de Diagnóstico

```bash
# 1. Ver status do job
gcloud scheduler jobs describe JOB_NAME --location=REGION

# 2. Testar manualmente
gcloud scheduler jobs run JOB_NAME --location=REGION

# 3. Ver logs imediatamente após teste
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=JOB_NAME" --limit 5

# 4. Ver logs do Cloud Run
gcloud run services logs read SERVICE_NAME --region=REGION --limit 10 --follow
```

## 📋 Checklist de Verificação

- [ ] Job existe no Cloud Scheduler?
- [ ] Service account tem permissão `roles/run.invoker`?
- [ ] URL do Cloud Run está correta?
- [ ] Cloud Run service está ativo?
- [ ] Timeout está configurado corretamente?
- [ ] Região está correta?

## 🎯 Próximos Passos

1. Execute `./ver_logs.sh JOB_NAME` para ver o erro
2. Identifique o tipo de erro (permissão, 404, timeout, etc.)
3. Aplique a solução correspondente acima
4. Teste novamente com `gcloud scheduler jobs run`



