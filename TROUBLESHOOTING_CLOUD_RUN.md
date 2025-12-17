# 🔍 Troubleshooting - Cloud Run Deployment

## ❌ Erro: Container failed to start

```
The user-provided container failed to start and listen on the port 
defined provided by the PORT=8080 environment variable
```

## 🔍 Possíveis Causas

1. **App não está escutando na porta correta**
2. **App demora muito para iniciar (timeout)**
3. **Erro no carregamento de dados**
4. **App não está usando host='0.0.0.0'**

## ✅ Correções Aplicadas

### 1. App ajustado
- ✅ `host='0.0.0.0'` configurado
- ✅ `port` lido de `os.environ.get('PORT')`
- ✅ `use_reloader=False` (importante para produção)
- ✅ Logs melhorados com flush
- ✅ Tratamento de erro melhorado

### 2. Dockerfile ajustado
- ✅ `EXPOSE 8080` (porta padrão Cloud Run)
- ✅ Sem `ENV PORT` (Cloud Run define automaticamente)

### 3. Deploy ajustado
- ✅ `--port 8080`
- ✅ `--timeout 600` (10 minutos)
- ✅ `--memory 2Gi`
- ✅ `--cpu 2`

## 🧪 Verificar Logs

```bash
# Ver logs do Cloud Run
gcloud run services logs read femsa-cenario1 \
  --region us-central1 \
  --limit 100 \
  --project beanalytic-raw-data
```

## 🔍 Verificar se App Está Funcionando Localmente

```bash
# Testar localmente com Docker
cd ml-prot
docker build -f ../ml-prot/Dockerfile.cenario1 -t test-app ..
docker run -p 8080:8080 -e PORT=8080 test-app
```

Acesse: http://localhost:8080

## 📋 Checklist

- [ ] App usa `host='0.0.0.0'`
- [ ] App lê `PORT` de `os.environ.get('PORT')`
- [ ] `use_reloader=False` no `app.run()`
- [ ] Dockerfile não define `ENV PORT`
- [ ] Deploy usa `--port 8080`
- [ ] Timeout suficiente (`--timeout 600`)
- [ ] Memória suficiente (`--memory 2Gi`)

## 🚀 Próximos Passos

1. **Verificar logs** para ver onde está falhando
2. **Testar localmente** com Docker
3. **Aumentar timeout** se necessário
4. **Verificar carregamento de dados** (pode estar demorando)

## 💡 Dica

Se o app demora muito para carregar dados, considere:
- Carregar dados de forma assíncrona
- Usar cache
- Otimizar carregamento de arquivos grandes

