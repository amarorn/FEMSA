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
    app_unificado = os.path.join(base_dir, "app_unificado.py")
    
    # Verificar se o app unificado existe
    if not os.path.exists(app_unificado):
        print(f"[ERRO] Arquivo não encontrado: {app_unificado}")
        print("[INFO] Certifique-se de que app_unificado.py existe no diretório.")
        sys.exit(1)
    
    print("=" * 60)
    print("FEMSA - Iniciando Aplicação Unificada")
    print("=" * 60)
    print()
    
    # Iniciar apenas o app unificado
    process1 = run_app(app_unificado, 8052, "Aplicação Unificada")
    process2 = None
    
    if not process1:
        print("[ERRO] Falha ao iniciar aplicação")
        sys.exit(1)
    
    if process2 and not process2:
        print("[ERRO] Falha ao iniciar segunda aplicação")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ Aplicações iniciadas com sucesso!")
    print("=" * 60)
    print()
    print("📍 URL disponível:")
    print("   • Aplicação Unificada:             http://localhost:8052")
    print()
    print("   A aplicação unificada contém:")
    print("   - Tab 'Simulador P&L': Análise de cenários financeiros")
    print("   - Tab 'Otimização de Mix': Cálculo de mix ótimo")
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
            # process2 não é mais usado
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Encerrar processos
        print("\n[INFO] Encerrando processos...")
        if process1 and process1.poll() is None:
            process1.terminate()
            process1.wait(timeout=5)
        # process2 não é mais usado
        print("[INFO] Processos encerrados.")

if __name__ == "__main__":
    main()
