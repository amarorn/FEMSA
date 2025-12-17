# FEMSA - Sistema de Análise e Otimização de Mix

Sistema completo para análise de P&L e otimização de mix de produtos da FEMSA.

## 📋 Descrição

Este projeto contém duas aplicações Dash principais:

1. **Cenário 1 Corporativo (P&L)** - Dashboard interativo para análise de cenários financeiros
2. **Otimização de Mix de Produtos** - Ferramenta de otimização de mix baseada em capacidades e lucratividade

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passos

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd ml-prot
```

2. Crie um ambiente virtual (recomendado):
```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 🎯 Como Usar

### Iniciar as Aplicações

Existem duas formas de iniciar ambas as aplicações simultaneamente:

#### Opção 1: Script Python (Recomendado)
```bash
python3 start_apps.py
```

#### Opção 2: Shell Script (Linux/macOS)
```bash
./start_apps.sh
```

### Acessar as Aplicações

Após iniciar, as aplicações estarão disponíveis em:

- **Cenário 1 Corporativo (P&L):** http://localhost:8050
- **Otimização de Mix:** http://localhost:8051

### Encerrar

Pressione `Ctrl+C` no terminal para encerrar ambas as aplicações.

## 📁 Estrutura do Projeto

```
ml-prot/
├── app_cenario1_corporativo.py    # App principal de P&L
├── app_mix_optimization.py         # App de otimização de mix
├── start_apps.py                   # Script para iniciar ambos os apps
├── start_apps.sh                   # Shell script alternativo
├── requirements.txt                # Dependências Python
├── data/                           # Dados de entrada (não versionado)
├── outputs/                        # Resultados gerados (não versionado)
├── assets/                         # Assets estáticos (logo, CSS)
└── *.ipynb                         # Notebooks de análise
```

## 📊 Funcionalidades

### Cenário 1 Corporativo
- Análise de P&L por múltiplas dimensões
- Simulação de cenários com ajustes de preço e custos
- Visualizações interativas
- Filtros dinâmicos por mês, estado, diretoria, marca, etc.

### Otimização de Mix
- Otimização de mix de produtos por grupo de capacidade
- Maximização de lucro considerando restrições
- Análise de atendimento de demanda
- Relatórios detalhados por tipo de produto

## 🔧 Configuração

### Dados Necessários

O sistema requer arquivos CSV específicos:

- **Cenário 1 Corporativo:** Arquivo `merge_fin_com_AGG_SKU_*.csv` na pasta `outputs/`
- **Otimização de Mix:** Arquivo `data_unified.csv` ou `data_unified_filtered.csv` na raiz

### Portas

As aplicações usam as seguintes portas (podem ser alteradas nos arquivos):

- Porta 8050: Cenário 1 Corporativo
- Porta 8051: Otimização de Mix

## 🛠️ Desenvolvimento

### Adicionar Novas Funcionalidades

1. Crie uma branch para sua feature:
```bash
git checkout -b feature/nova-funcionalidade
```

2. Faça suas alterações e commit:
```bash
git add .
git commit -m "Adiciona nova funcionalidade"
```

3. Envie para o repositório:
```bash
git push origin feature/nova-funcionalidade
```

## 📝 Notas Importantes

- Os arquivos de dados (`data/` e `outputs/`) não são versionados por padrão
- Certifique-se de ter os dados necessários antes de executar as aplicações
- Para produção, considere usar variáveis de ambiente para configurações sensíveis

## 🤝 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.

## 📄 Licença

[Especificar licença conforme necessário]

