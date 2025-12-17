#!/bin/bash
# ============================================================================
# Shell script para iniciar ambos os apps Dash simultaneamente
# ============================================================================

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================================="
echo "FEMSA - Iniciando Aplicações Dash"
echo "=========================================================================="
echo ""

# Verificar se os arquivos existem
if [ ! -f "app_cenario1_corporativo.py" ]; then
    echo -e "${RED}[ERRO] Arquivo não encontrado: app_cenario1_corporativo.py${NC}"
    exit 1
fi

if [ ! -f "app_mix_optimization.py" ]; then
    echo -e "${RED}[ERRO] Arquivo não encontrado: app_mix_optimization.py${NC}"
    exit 1
fi

# Função para limpar processos ao sair
cleanup() {
    echo ""
    echo -e "${YELLOW}[INFO] Encerrando aplicações...${NC}"
    if [ ! -z "$PID1" ]; then
        kill $PID1 2>/dev/null
    fi
    if [ ! -z "$PID2" ]; then
        kill $PID2 2>/dev/null
    fi
    exit 0
}

# Registrar trap para Ctrl+C
trap cleanup SIGINT SIGTERM

# Iniciar app_cenario1_corporativo (porta 8050)
echo -e "${GREEN}[INFO] Iniciando Cenário 1 Corporativo (P&L) na porta 8050...${NC}"
python3 app_cenario1_corporativo.py > /tmp/app_cenario1_corporativo.log 2>&1 &
PID1=$!

# Aguardar um pouco
sleep 2

# Iniciar app_mix_optimization (porta 8051)
echo -e "${GREEN}[INFO] Iniciando Otimização de Mix na porta 8051...${NC}"
python3 app_mix_optimization.py > /tmp/app_mix_optimization.log 2>&1 &
PID2=$!

# Verificar se os processos iniciaram corretamente
sleep 3

if ! kill -0 $PID1 2>/dev/null; then
    echo -e "${RED}[ERRO] Falha ao iniciar app_cenario1_corporativo.py${NC}"
    exit 1
fi

if ! kill -0 $PID2 2>/dev/null; then
    echo -e "${RED}[ERRO] Falha ao iniciar app_mix_optimization.py${NC}"
    kill $PID1 2>/dev/null
    exit 1
fi

echo ""
echo "=========================================================================="
echo -e "${GREEN}✓ Aplicações iniciadas com sucesso!${NC}"
echo "=========================================================================="
echo ""
echo "📍 URLs disponíveis:"
echo "   • Cenário 1 Corporativo (P&L):     http://localhost:8050"
echo "   • Otimização de Mix:   http://localhost:8051"
echo ""
echo -e "${YELLOW}⚠️  Pressione Ctrl+C para encerrar ambas as aplicações${NC}"
echo "=========================================================================="
echo ""
echo "Logs:"
echo "   • app_cenario1_corporativo.py:        tail -f /tmp/app_cenario1_corporativo.log"
echo "   • app_mix_optimization.py: tail -f /tmp/app_mix_optimization.log"
echo ""

# Aguardar até receber sinal de interrupção
wait

