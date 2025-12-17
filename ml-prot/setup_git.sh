#!/bin/bash
# ============================================================================
# Script para configurar Git e preparar para publicação
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================================================="
echo -e "${BLUE}FEMSA - Setup Git Repository${NC}"
echo "=========================================================================="
echo ""

# Verificar se já é um repositório Git
if [ -d ".git" ]; then
    echo -e "${YELLOW}[INFO] Repositório Git já existe${NC}"
    read -p "Deseja continuar mesmo assim? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 0
    fi
else
    echo -e "${GREEN}[INFO] Inicializando repositório Git...${NC}"
    git init
fi

# Verificar .gitignore
if [ ! -f ".gitignore" ]; then
    echo -e "${RED}[ERRO] Arquivo .gitignore não encontrado!${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO] Adicionando arquivos...${NC}"
git add .

echo ""
echo -e "${YELLOW}[INFO] Status do repositório:${NC}"
git status --short

echo ""
read -p "Deseja fazer o commit inicial? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    git commit -m "Initial commit: Sistema FEMSA P&L e Otimização de Mix"
    echo -e "${GREEN}✓ Commit realizado!${NC}"
else
    echo -e "${YELLOW}[INFO] Commit não realizado. Execute manualmente:${NC}"
    echo "   git commit -m 'Initial commit: Sistema FEMSA P&L e Otimização de Mix'"
fi

echo ""
echo "=========================================================================="
echo -e "${BLUE}Próximos passos:${NC}"
echo "=========================================================================="
echo ""
echo "1. Crie um repositório no GitHub/GitLab:"
echo "   https://github.com/new"
echo ""
echo "2. Conecte o repositório local:"
echo -e "   ${GREEN}git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPO.git${NC}"
echo ""
echo "3. Envie para o repositório:"
echo -e "   ${GREEN}git branch -M main${NC}"
echo -e "   ${GREEN}git push -u origin main${NC}"
echo ""
echo "=========================================================================="

