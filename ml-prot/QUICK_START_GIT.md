# 🚀 Guia Rápido - Publicar no Git

## Passo a Passo Simples

### 1. Inicializar Git (se ainda não fez)

```bash
cd ml-prot
git init
```

### 2. Adicionar arquivos

```bash
git add .
```

### 3. Primeiro commit

```bash
git commit -m "Initial commit: Sistema FEMSA P&L e Otimização"
```

### 4. Criar repositório no GitHub

1. Acesse: https://github.com/new
2. Nome do repositório: `femsa-ml-analysis` (ou outro nome)
3. Escolha **Privado** (recomendado para dados sensíveis)
4. **NÃO** marque "Add a README file" (já temos)
5. Clique em "Create repository"

### 5. Conectar e enviar

```bash
# Substitua SEU_USUARIO pelo seu usuário GitHub
git remote add origin https://github.com/SEU_USUARIO/femsa-ml-analysis.git
git branch -M main
git push -u origin main
```

### 6. Compartilhar com cliente

**Opção A - Adicionar como colaborador:**
1. No GitHub: Settings → Collaborators → Add people
2. Digite o email do cliente
3. Envie convite

**Opção B - Enviar link:**
- Compartilhe a URL: `https://github.com/SEU_USUARIO/femsa-ml-analysis`

## ⚠️ Importante

- O `.gitignore` já está configurado para **NÃO** enviar dados sensíveis
- Arquivos em `data/` e `outputs/` não serão enviados
- Apenas código e configurações serão versionados

## ✅ Pronto!

O cliente pode agora:
1. Clonar: `git clone https://github.com/SEU_USUARIO/femsa-ml-analysis.git`
2. Instalar: `pip install -r requirements.txt` (ou `requirements-minimal.txt`)
3. Executar: `python3 start_apps.py`

