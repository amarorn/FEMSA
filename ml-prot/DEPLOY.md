# Guia de Publicação - FEMSA ML Project

Este guia explica como publicar o projeto no Git para compartilhamento com o cliente.

## 📦 Preparação Inicial

### 1. Inicializar Repositório Git

```bash
cd ml-prot
git init
```

### 2. Adicionar Arquivos

```bash
# Adicionar todos os arquivos (respeitando .gitignore)
git add .

# Verificar o que será commitado
git status
```

### 3. Primeiro Commit

```bash
git commit -m "Initial commit: Sistema de análise P&L e otimização de mix"
```

## 🌐 Opções de Hospedagem

### Opção 1: GitHub (Recomendado)

1. **Criar repositório no GitHub:**
   - Acesse https://github.com
   - Clique em "New repository"
   - Nome sugerido: `femsa-ml-analysis` ou `femsa-pnl-optimization`
   - Escolha se será público ou privado
   - **NÃO** inicialize com README (já temos um)

2. **Conectar repositório local:**
```bash
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPO.git
git branch -M main
git push -u origin main
```

### Opção 2: GitLab

1. **Criar projeto no GitLab:**
   - Acesse https://gitlab.com
   - Crie um novo projeto
   - Copie a URL do repositório

2. **Conectar:**
```bash
git remote add origin https://gitlab.com/SEU_USUARIO/NOME_DO_PROJETO.git
git push -u origin main
```

### Opção 3: Bitbucket

Similar ao GitHub, mas usando https://bitbucket.org

## 🔒 Repositório Privado vs Público

### Privado (Recomendado para dados sensíveis)
- ✅ Dados não ficam expostos
- ✅ Controle de acesso
- ⚠️ Pode ter custo dependendo do plano

### Público
- ✅ Gratuito
- ✅ Fácil compartilhamento
- ⚠️ Código visível para todos
- ⚠️ **NÃO use se houver dados sensíveis**

## 📋 Checklist Antes de Publicar

- [ ] Verificar que `.gitignore` está configurado corretamente
- [ ] Remover dados sensíveis (arquivos grandes de `data/` e `outputs/`)
- [ ] Verificar que `requirements.txt` está completo
- [ ] Testar que as aplicações funcionam após clone
- [ ] Revisar README.md com instruções claras
- [ ] Verificar que não há credenciais hardcoded no código

## 🚀 Deploy das Aplicações (Opcional)

Se quiser que o cliente acesse as aplicações sem instalar localmente:

### Opção A: Heroku (Gratuito para testes)

1. Instalar Heroku CLI
2. Criar arquivo `Procfile`:
```
web: python start_apps.py
```

3. Deploy:
```bash
heroku create femsa-ml-app
git push heroku main
```

### Opção B: Render.com (Gratuito)

1. Conectar repositório GitHub
2. Configurar build: `pip install -r requirements.txt`
3. Comando de start: `python start_apps.py`

### Opção C: Servidor Próprio

1. Clonar repositório no servidor
2. Instalar dependências
3. Executar com `screen` ou `tmux`:
```bash
screen -S femsa-apps
python3 start_apps.py
# Pressionar Ctrl+A depois D para desanexar
```

## 📤 Compartilhar com Cliente

### Via Git

1. **Adicionar colaborador (GitHub/GitLab):**
   - Settings → Collaborators → Add people
   - Enviar convite por email

2. **Cliente clona:**
```bash
git clone https://github.com/SEU_USUARIO/NOME_DO_REPO.git
cd ml-prot
pip install -r requirements.txt
python3 start_apps.py
```

### Via Release/ZIP

1. **Criar release no GitHub:**
   - Releases → Create a new release
   - Tag: v1.0.0
   - Adicionar notas de release
   - Publicar

2. **Cliente baixa ZIP:**
   - Baixa o ZIP da release
   - Extrai e segue instruções do README

## 🔐 Segurança

### Dados Sensíveis

- ✅ **NÃO** commitar arquivos com dados reais de clientes
- ✅ Usar `.gitignore` para excluir `data/` e `outputs/`
- ✅ Se necessário, usar variáveis de ambiente para configurações

### Exemplo de .env (não versionado):
```
DATABASE_URL=...
API_KEY=...
```

## 📝 Comandos Úteis

```bash
# Ver status
git status

# Adicionar mudanças
git add .

# Commit
git commit -m "Descrição das mudanças"

# Push
git push origin main

# Ver histórico
git log --oneline

# Criar branch
git checkout -b feature/nova-funcionalidade
```

## ❓ Troubleshooting

### Erro: "fatal: not a git repository"
```bash
git init
```

### Erro: "permission denied"
Verificar permissões do repositório remoto

### Arquivos grandes não sobem
Verificar `.gitignore` ou usar Git LFS para arquivos grandes

