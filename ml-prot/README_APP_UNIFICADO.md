# 🎯 Aplicação Unificada - FEMSA

Aplicação única que combina **Simulador de P&L** e **Otimização de Mix** em uma interface com navegação por abas.

## ✨ Características

- ✅ **Interface única** com navegação por abas
- ✅ **Integração nativa** (sem iframes)
- ✅ **Uma única URL** para o cliente
- ✅ **Navegação fácil** entre funcionalidades
- ✅ **Design profissional** com paleta corporativa

## 🚀 Como Usar

### Opção 1: Script Automático (Recomendado)

```bash
python3 start_apps.py
```

### Opção 2: Direto

```bash
python3 app_unificado.py
```

Acesse: **http://localhost:8052**

## 📱 Interface

A aplicação possui duas abas no topo:

### Tab 1: 📊 Simulador P&L
- Análise de cenários financeiros
- Simulação de choques de preço e custos
- Visualizações interativas
- Filtros dinâmicos

**Nota:** Atualmente redireciona para o app completo. Para integração total, veja abaixo.

### Tab 2: 🎯 Otimização de Mix
- Otimização de mix de produtos
- Cálculo de mix ótimo por capacidade
- Análise de lucratividade
- Relatórios detalhados
- **Totalmente funcional!**

## 🔄 Navegação

Use as **abas no topo** para alternar entre as funcionalidades:
- Clique em **"📊 Simulador P&L"** para análise de cenários
- Clique em **"🎯 Otimização de Mix"** para otimização

## ⚙️ Funcionamento Técnico

O app unificado:
1. Importa funções dos apps originais (`app_cenario1_corporativo.py` e `app_mix_optimization.py`)
2. Cria layouts separados para cada tab
3. Integra callbacks diretamente (sem iframes)
4. Tudo em uma única aplicação Dash

## 🌐 URL Única

Após iniciar:

- **App Unificado:** http://localhost:8052 ⭐ (Use esta!)

## 💡 Vantagens

✅ **Uma única URL** para o cliente  
✅ **Navegação fácil** entre funcionalidades  
✅ **Interface profissional** com abas  
✅ **Sem necessidade de múltiplas janelas**  
✅ **Integração nativa** (melhor performance)  

## 🔧 Integração Completa do P&L

Para integrar completamente o Simulador P&L (ao invés de redirecionar):

1. O app já importa as funções necessárias
2. Basta copiar o layout completo do `app_cenario1_corporativo.py`
3. Adaptar os IDs dos componentes para evitar conflitos
4. Adicionar os callbacks correspondentes

## 🐛 Troubleshooting

### Erro: "Não foi possível importar app_cenario1_corporativo"

Verifique se:
- O arquivo `app_cenario1_corporativo.py` existe
- As dependências estão instaladas
- Os dados necessários estão disponíveis

### Erro: "Não foi possível importar app_mix_optimization"

Verifique se:
- O arquivo `app_mix_optimization.py` existe
- As dependências estão instaladas

### Funcionalidade não aparece

O app detecta automaticamente quais funcionalidades estão disponíveis. Se uma não aparecer, verifique os logs para ver o erro de importação.

## 📝 Notas

- O app unificado importa funções dos apps originais
- Não é necessário rodar os apps individuais separadamente
- Tudo funciona em uma única aplicação
- Para produção, considere integrar completamente o layout do P&L

## ✅ Status

- ✅ **Otimização de Mix:** Totalmente integrada e funcional
- ⚠️ **Simulador P&L:** Redireciona para app completo (pode ser totalmente integrado)
