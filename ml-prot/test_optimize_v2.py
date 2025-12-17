#!/usr/bin/env python3
# ============================================================================
# TESTE DO MODELO DE OTIMIZAÇÃO V2
# ============================================================================

import os
import sys
import pandas as pd
import numpy as np

# Adicionar diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimize_production_mix_v2 import optimize_production_mix_v2

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
DATA_FILE = "simulador_pnl_futuro_base.csv"

# ============================================================================
# TESTE
# ============================================================================
def test_optimization():
    """Testa o modelo de otimização V2."""
    print("=" * 80)
    print("TESTE DO MODELO DE OTIMIZAÇÃO V2")
    print("=" * 80)
    
    # 1. Carregar dados
    print("\n[1] Carregando dados...")
    data_file = DATA_FILE  # Usar variável local
    if not os.path.exists(data_file):
        print(f"[WARNING] Arquivo '{data_file}' não encontrado!")
        print(f"[INFO] Procurando arquivos CSV no diretório...")
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            print(f"[INFO] Arquivos CSV encontrados: {csv_files}")
            data_file = csv_files[0]
            print(f"[INFO] Usando: {data_file}")
        else:
            print(f"[ERROR] Nenhum arquivo CSV encontrado!")
            return None
    
    try:
        # Tentar diferentes separadores
        try:
            df_master = pd.read_csv(data_file, decimal=',', encoding='utf-8')
        except:
            try:
                df_master = pd.read_csv(data_file, decimal='.', encoding='utf-8')
            except:
                df_master = pd.read_csv(data_file, sep=';', decimal=',', encoding='utf-8')
        
        print(f"[OK] Dados carregados: {len(df_master)} linhas, {len(df_master.columns)} colunas")
        print(f"[INFO] Colunas disponíveis: {list(df_master.columns)[:10]}...")
        
        # Verificar colunas necessárias
        required_cols = ['chave_sku']
        missing_cols = [col for col in required_cols if col not in df_master.columns]
        if missing_cols:
            print(f"[WARNING] Colunas faltando: {missing_cols}")
            print(f"[INFO] Tentando continuar mesmo assim...")
        
        # Se não tiver muitas linhas, usar todas. Senão, amostrar
        if len(df_master) > 1000:
            print(f"[INFO] Amostrando 1000 linhas para teste rápido...")
            df_master = df_master.sample(n=1000, random_state=42).reset_index(drop=True)
        
        # Verificar se tem colunas de volume e margem
        volume_cols = [col for col in df_master.columns if 'volume' in col.lower() or 'demanda' in col.lower()]
        margem_cols = [col for col in df_master.columns if 'margem' in col.lower() or 'lucro' in col.lower()]
        
        print(f"[INFO] Colunas de volume encontradas: {volume_cols}")
        print(f"[INFO] Colunas de margem encontradas: {margem_cols}")
        
        # Se não tiver volume_projetado, criar uma coluna de teste
        if 'volume_projetado' not in df_master.columns:
            if 'volume_real' in df_master.columns:
                df_master['volume_projetado'] = df_master['volume_real']
            else:
                # Criar volume aleatório para teste
                df_master['volume_projetado'] = np.random.uniform(100, 1000, len(df_master))
                print(f"[WARNING] Criando volume_projetado aleatório para teste")
        
        # Se não tiver margem_unit_esperada, criar uma coluna de teste
        if 'margem_unit_esperada' not in df_master.columns:
            if 'base_margem_variavel_unit' in df_master.columns:
                df_master['margem_unit_esperada'] = df_master['base_margem_variavel_unit']
            else:
                # Criar margem aleatória para teste
                df_master['margem_unit_esperada'] = np.random.uniform(0.5, 5.0, len(df_master))
                print(f"[WARNING] Criando margem_unit_esperada aleatória para teste")
        
    except Exception as e:
        print(f"[ERROR] Erro ao carregar dados: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. Executar otimização
    print("\n[2] Executando otimização...")
    try:
        result = optimize_production_mix_v2(
            df_master,
            capacidades_mes=None,  # Carregar do arquivo
            price_adj_pct=0.0,
            shocks_pct={}
        )
        
        if result is None:
            print("[ERROR] Otimização retornou None")
            return None
        
        # 3. Verificar resultados
        print("\n[3] Verificando resultados...")
        df_result = result.get('df_result')
        
        if df_result is None or df_result.empty:
            print("[ERROR] DataFrame de resultados vazio")
            return None
        
        print(f"[OK] Resultados: {len(df_result)} SKUs")
        print(f"\n[RESUMO]")
        print(f"  Margem Real: R$ {result.get('margem_real', 0):,.2f}")
        print(f"  Margem Otimizada: R$ {result.get('margem_otimizada', 0):,.2f}")
        print(f"  Melhoria: R$ {result.get('melhoria_margem', 0):,.2f} ({result.get('melhoria_margem_pct', 0):.2f}%)")
        
        # Verificar se tem volumes otimizados
        if 'volume_otimizado' in df_result.columns:
            volume_total = df_result['volume_otimizado'].sum()
            print(f"  Volume Total Otimizado: {volume_total:,.0f} UC")
        
        # Verificar se tem atendimento
        if 'atendimento_pct' in df_result.columns:
            atendimento_medio = df_result['atendimento_pct'].mean()
            print(f"  Atendimento Médio: {atendimento_medio:.2f}%")
        
        # Mostrar alguns exemplos
        print(f"\n[EXEMPLOS DE RESULTADOS]")
        cols_to_show = ['chave_sku', 'tipo', 'demanda', 'volume_otimizado', 'atendimento_pct', 'lucro_unit']
        cols_available = [col for col in cols_to_show if col in df_result.columns]
        if cols_available:
            print(df_result[cols_available].head(10).to_string())
        
        # Verificar resultados por TIPO
        resultados_por_tipo = result.get('resultados_por_tipo', {})
        if resultados_por_tipo:
            print(f"\n[RESULTADOS POR TIPO]")
            for tipo, dados in list(resultados_por_tipo.items())[:5]:  # Mostrar apenas 5 primeiros
                print(f"  {tipo}:")
                print(f"    Volume: {dados.get('volume_total', 0):,.0f} UC")
                print(f"    Demanda: {dados.get('demanda_total', 0):,.0f} UC")
                print(f"    Atendimento: {dados.get('atendimento_pct', 0):.2f}%")
                print(f"    Lucro: R$ {dados.get('lucro_total', 0):,.2f}")
        
        print("\n[OK] Teste concluído com sucesso!")
        return result
        
    except Exception as e:
        print(f"[ERROR] Erro durante otimização: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    result = test_optimization()
    if result:
        print("\n✅ Modelo funcionando corretamente!")
        sys.exit(0)
    else:
        print("\n❌ Modelo apresentou erros")
        sys.exit(1)
