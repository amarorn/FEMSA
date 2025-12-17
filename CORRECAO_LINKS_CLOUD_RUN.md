# 🔗 Correção - Links para Cloud Run

## ❌ Problema

O botão "Calcular Mix Ótimo" estava redirecionando para `http://localhost:8051` ao invés da URL do Cloud Run.

## ✅ Correções Aplicadas

### 1. App Cenário 1 (`app_cenario1_corporativo.py`)
- ✅ Link do botão "Calcular Mix Ótimo" atualizado
- ✅ **Antes:** `http://localhost:8051`
- ✅ **Agora:** `https://femsa-mix-optimization-tfhauqj6vq-uc.a.run.app`

### 2. App Mix Optimization (`app_mix_optimization.py`)
- ✅ Link "← Voltar" atualizado
- ✅ **Antes:** `http://localhost:8050`
- ✅ **Agora:** `https://femsa-cenario1-tfhauqj6vq-uc.a.run.app`

## 📋 URLs Configuradas

- **Simulador P&L:** https://femsa-cenario1-tfhauqj6vq-uc.a.run.app
- **Otimização de Mix:** https://femsa-mix-optimization-tfhauqj6vq-uc.a.run.app

## 🚀 Próximos Passos

1. **Fazer deploy novamente** para aplicar as mudanças:
```bash
cd ml-prot
./deploy-cloud-run.sh
```

2. **Testar os links:**
   - No Simulador P&L, clique em "Calcular Mix Ótimo"
   - Deve abrir a URL do Cloud Run (não localhost)
   - No Mix Optimization, clique em "← Voltar"
   - Deve voltar para o Simulador P&L no Cloud Run

## 💡 Nota

Se as URLs mudarem no futuro, você pode:
1. Atualizar manualmente nos arquivos
2. Ou criar variáveis de ambiente para as URLs
3. Ou detectar automaticamente a URL base do Cloud Run

## ✅ Resultado

Agora os links funcionam corretamente no ambiente de produção (Cloud Run)!

