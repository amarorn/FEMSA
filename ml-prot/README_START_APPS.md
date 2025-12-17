# Como Iniciar os Apps Dash

Este diretório contém dois apps Dash que precisam rodar simultaneamente:

- **app_cenario1_corporativo.py** - Simulador de P&L Corporativo (porta 8050)
- **app_mix_optimization.py** - Otimização de Mix de Produtos (porta 8051)

## Opção 1: Script Python (Recomendado)

Execute o script Python que gerencia ambos os processos:

```bash
python3 start_apps.py
```

**Vantagens:**
- Gerencia ambos os processos automaticamente
- Encerra ambos ao pressionar Ctrl+C
- Mostra mensagens de status claras
- Funciona em qualquer sistema operacional

## Opção 2: Shell Script (Linux/macOS)

Execute o shell script:

```bash
./start_apps.sh
```

ou

```bash
bash start_apps.sh
```

**Vantagens:**
- Rápido e simples
- Logs salvos em `/tmp/app_*.log`

## URLs Disponíveis

Após iniciar, os apps estarão disponíveis em:

- **Cenário 1 Corporativo (P&L):** http://localhost:8050
- **Otimização de Mix:** http://localhost:8051

## Encerrar os Apps

Pressione `Ctrl+C` no terminal onde os scripts estão rodando. Ambos os processos serão encerrados automaticamente.

## Troubleshooting

### Porta já em uso

Se uma das portas (8050 ou 8051) já estiver em uso:

```bash
# Verificar processos nas portas
lsof -i :8050
lsof -i :8051

# Encerrar processo específico (substitua PID pelo número do processo)
kill -9 PID
```

### Verificar logs (shell script)

```bash
# Logs do app_cenario1_corporativo
tail -f /tmp/app_cenario1_corporativo.log

# Logs do app_mix_optimization
tail -f /tmp/app_mix_optimization.log
```

