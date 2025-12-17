#!/usr/bin/env python3
# ============================================================================
# Script para iniciar ambos os apps Dash simultaneamente
# ============================================================================
import subprocess
import sys
import time
import signal
import os

def signal_handler(sig, frame):
    """Handler para Ctrl+C - encerra todos os processos filhos"""
    print("\n[INFO] Encerrando aplicações...")
    sys.exit(0)

def run_app(script_name, port, description):
    """Executa um app Dash em um processo separado"""
    try:
        print(f"[INFO] Iniciando {description} na porta {port}...")
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        return process
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar {description}: {e}")
        return None

def main():
    """Função principal"""
    # Registrar handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Caminhos dos scripts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_cenario1 = os.path.join(base_dir, "app_cenario1_corporativo.py")
    app_mix = os.path.join(base_dir, "app_mix_optimization.py")
    
    # Verificar se os arquivos existem
    if not os.path.exists(app_cenario1):
        print(f"[ERRO] Arquivo não encontrado: {app_cenario1}")
        sys.exit(1)
    
    if not os.path.exists(app_mix):
        print(f"[ERRO] Arquivo não encontrado: {app_mix}")
        sys.exit(1)
    
    print("=" * 60)
    print("FEMSA - Iniciando Aplicações Dash")
    print("=" * 60)
    print()
    
    # Iniciar app_cenario1_corporativo (porta 8050)
    process1 = run_app(app_cenario1, 8050, "Cenário 1 Corporativo (P&L)")
    
    # Aguardar um pouco antes de iniciar o segundo
    time.sleep(2)
    
    # Iniciar app_mix_optimization (porta 8051)
    process2 = run_app(app_mix, 8051, "Otimização de Mix")
    
    if not process1 or not process2:
        print("[ERRO] Falha ao iniciar uma ou mais aplicações")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ Aplicações iniciadas com sucesso!")
    print("=" * 60)
    print()
    print("📍 URLs disponíveis:")
    print("   • Cenário 1 Corporativo (P&L):     http://localhost:8050")
    print("   • Otimização de Mix:   http://localhost:8051")
    print()
    print("⚠️  Pressione Ctrl+C para encerrar ambas as aplicações")
    print("=" * 60)
    print()
    
    # Aguardar até que um dos processos termine ou receba sinal
    try:
        while True:
            # Verificar se os processos ainda estão rodando
            if process1.poll() is not None:
                print(f"[AVISO] app_cenario1_corporativo.py terminou (código: {process1.returncode})")
                break
            if process2.poll() is not None:
                print(f"[AVISO] app_mix_optimization.py terminou (código: {process2.returncode})")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Encerrar processos
        print("\n[INFO] Encerrando processos...")
        if process1 and process1.poll() is None:
            process1.terminate()
            process1.wait(timeout=5)
        if process2 and process2.poll() is None:
            process2.terminate()
            process2.wait(timeout=5)
        print("[INFO] Processos encerrados.")

if __name__ == "__main__":
    main()
