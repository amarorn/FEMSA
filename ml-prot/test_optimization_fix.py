#!/usr/bin/env python3
"""
Script de teste e correção do modelo de otimização de mix
Foca em:
1. Corrigir categorização de produtos (Alumínio, Vidro, BIB, PET)
2. Adicionar limites por MARCA (CC, FANTA, SPRITE) além de embalagem
3. Usar volumes de consumo do arquivo de projeção
4. Otimizar baseado em rentabilidade de cada SKU
"""

import os
import sys
import pandas as pd
import numpy as np
import traceback

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funções do app principal
from app_cenario1_corporativo import (
    parse_size_to_liters,
    normalize_package_name,
    extract_package_from_sku,
    extract_size_from_sku,
    map_package_to_capacity_type,
    load_capacidades_data,
    run_pnl_simulation
)

print("=" * 80)
print("TESTE E CORREÇÃO DO MODELO DE OTIMIZAÇÃO DE MIX")
print("=" * 80)

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1] Carregando dados...")

# Carregar arquivo de projeção
proj_file = "data/Projeção Vol UC com Territorio_Envio.xlsx"
if not os.path.exists(proj_file):
    print(f"[ERROR] Arquivo não encontrado: {proj_file}")
    sys.exit(1)

df_proj = pd.read_excel(proj_file)
print(f"[INFO] Arquivo de projeção carregado: {len(df_proj)} linhas")
print(f"[INFO] Colunas: {df_proj.columns.tolist()}")

# Carregar capacidades
capacidades_file = "data/Capacidades Produção UC V2.xlsx"
df_capacidades = load_capacidades_data(capacidades_file)

# Carregar dados base (simulador_pnl_futuro_base.csv)
base_file = "simulador_pnl_futuro_base.csv"
if os.path.exists(base_file):
    df_base = pd.read_csv(base_file)
    print(f"[INFO] Dados base carregados: {len(df_base)} linhas")
else:
    print(f"[WARNING] Arquivo base não encontrado: {base_file}")
    df_base = None

# ============================================================================
# 2. CORRIGIR CATEGORIZAÇÃO DE PRODUTOS
# ============================================================================
print("\n[2] Corrigindo categorização de produtos...")

def correct_package_categorization(package_str, size_val=None):
    """
    Corrige a categorização de embalagens conforme especificação:
    - Lata, Mini Lata, Sleek Can → ALUMINIO
    - KS, LS → VIDRO (vidro não retornável)
    - BIB → BIB
    - PET, Refpet → PET
    """
    if pd.isna(package_str):
        return None
    
    pkg = str(package_str).strip().upper()
    
    # Mapeamento correto
    if 'LATA' in pkg or 'MINI LATA' in pkg or 'SLEEK CAN' in pkg or 'ALUMINIO' in pkg:
        # Se tem tamanho, diferenciar Mini Lata de Lata
        if size_val is not None and size_val < 0.5:
            return 'Mini Lata'
        else:
            return 'Lata'  # Para capacidades, usar 'Lata' como categoria
    
    if 'KS' in pkg or 'LS' in pkg:
        return 'Vidro não Retornável'
    
    if 'BIB' in pkg or 'BAG IN BOX' in pkg:
        return 'BIB'
    
    if 'PET' in pkg or 'REFPET' in pkg or 'REF PET' in pkg:
        return 'Pet'
    
    return None

# Testar categorização
test_cases = [
    ('LATA', 0.35, 'Lata'),
    ('MINI LATA', 0.22, 'Mini Lata'),
    ('SLEEK CAN', 0.22, 'Lata'),
    ('ALUMINIO', 0.22, 'Mini Lata'),
    ('KS', 0.29, 'Vidro não Retornável'),
    ('LS', 0.29, 'Vidro não Retornável'),
    ('BIB', 5.0, 'BIB'),
    ('PET', 1.5, 'Pet'),
    ('REFPET', 1.5, 'Pet'),
]

print("\n[TESTE] Categorização de produtos:")
for pkg, size, expected in test_cases:
    result = correct_package_categorization(pkg, size)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {pkg} ({size}L) → {result} (esperado: {expected})")

# ============================================================================
# 3. PROCESSAR ARQUIVO DE PROJEÇÃO
# ============================================================================
print("\n[3] Processando arquivo de projeção...")

# Identificar colunas de data (volumes mensais)
date_cols = [col for col in df_proj.columns if isinstance(col, pd.Timestamp)]
print(f"[INFO] Encontradas {len(date_cols)} colunas de data: {[str(c)[:7] for c in date_cols]}")

# Normalizar nomes de colunas
df_proj_clean = df_proj.copy()
df_proj_clean.columns = [str(c) if isinstance(c, pd.Timestamp) else c for c in df_proj_clean.columns]

# Renomear colunas principais
col_mapping = {
    'Marca': 'marca',
    'Tamanho': 'tamanho',
    'Retornabilidade': 'retornabilidade',
    'Diretoria Estratégica': 'diretoria',
    'Território Supply': 'territorio'
}

for old, new in col_mapping.items():
    if old in df_proj_clean.columns:
        df_proj_clean = df_proj_clean.rename(columns={old: new})

# Extrair tipo de embalagem do tamanho (se possível) ou inferir
# Por enquanto, vamos assumir que precisamos mapear do arquivo base
print(f"[INFO] Marcas únicas: {df_proj_clean['marca'].unique().tolist()}")
print(f"[INFO] Tamanhos únicos: {df_proj_clean['tamanho'].unique().tolist()[:10]}...")

# ============================================================================
# 4. CRIAR DE-PARA MELHORADO COM MARCA
# ============================================================================
print("\n[4] Criando de-para melhorado (incluindo MARCA)...")

def create_enhanced_de_para(df_master, df_capacidades=None, df_proj=None):
    """
    Cria de-para melhorado que inclui MARCA nas restrições de capacidade.
    Agora agrupa por: MARCA + TIPO_EMBALAGEM + TAMANHO
    """
    if df_master is None or df_master.empty:
        print("[WARNING] DataFrame master vazio")
        return None
    
    print(f"[INFO] Processando {len(df_master)} SKUs do master...")
    
    # Extrair informações da chave_sku
    df_work = df_master.copy()
    
    # Extrair marca, tamanho, embalagem da chave_sku
    sku_parts = df_work['chave_sku'].str.split('|', expand=True)
    if len(sku_parts.columns) >= 5:
        df_work['marca'] = sku_parts[0]
        df_work['tamanho_num'] = pd.to_numeric(sku_parts[1], errors='coerce')
        df_work['tipo_consumo'] = sku_parts[2]
        df_work['retornabilidade'] = sku_parts[3]
        df_work['embalagem_raw'] = sku_parts[4]
    else:
        print("[ERROR] Formato de chave_sku inválido")
        return None
    
    # Corrigir categorização de embalagem
    df_work['tipo_embalagem_capacidade'] = df_work.apply(
        lambda row: correct_package_categorization(row['embalagem_raw'], row['tamanho_num']),
        axis=1
    )
    
    print(f"[INFO] Tipos de embalagem identificados: {df_work['tipo_embalagem_capacidade'].value_counts().to_dict()}")
    
    # Correlacionar com capacidades (se disponível)
    if df_capacidades is not None and not df_capacidades.empty:
        print("[INFO] Correlacionando com capacidades...")
        
        # Criar dicionário de capacidades
        capacidades_dict = {}
        for _, row in df_capacidades.iterrows():
            pkg = row.get('tipo_embalagem_norm', '')
            size = row.get('tamanho_litros', None)
            if pd.notna(pkg) and pd.notna(size):
                key = f"{pkg}|{size:.3f}"
                capacidades_dict[key] = {
                    'min': row.get('min', 0),
                    'max': row.get('max', float('inf'))
                }
        
        # Aplicar capacidades aos SKUs
        df_work['capacidade_min'] = None
        df_work['capacidade_max'] = None
        
        matched = 0
        for idx, row in df_work.iterrows():
            pkg = row.get('tipo_embalagem_capacidade')
            size = row.get('tamanho_num')
            
            if pd.notna(pkg) and pd.notna(size):
                # Buscar match mais próximo
                best_match = None
                best_diff = float('inf')
                
                for cap_key, cap_data in capacidades_dict.items():
                    cap_pkg, cap_size_str = cap_key.split('|')
                    cap_size = float(cap_size_str)
                    
                    if cap_pkg == pkg:
                        diff = abs(cap_size - size)
                        if diff < best_diff and diff < 0.15:  # Tolerância de 0.15L
                            best_diff = diff
                            best_match = cap_data
                
                if best_match:
                    df_work.at[idx, 'capacidade_min'] = best_match['min']
                    df_work.at[idx, 'capacidade_max'] = best_match['max']
                    matched += 1
        
        print(f"[INFO] Capacidades correlacionadas: {matched}/{len(df_work)} SKUs ({matched/len(df_work)*100:.1f}%)")
    else:
        print("[WARNING] Sem dados de capacidades disponíveis")
        df_work['capacidade_min'] = None
        df_work['capacidade_max'] = None
    
    # Criar grupo de capacidade INCLUINDO MARCA
    # IMPORTANTE: Agora agrupa por MARCA + EMBALAGEM + TAMANHO
    mask_valid = (
        df_work['tipo_embalagem_capacidade'].notna() &
        df_work['marca'].notna() &
        df_work['tamanho_num'].notna()
    )
    
    df_work.loc[mask_valid, 'grupo_capacidade'] = (
        df_work.loc[mask_valid, 'marca'].astype(str) + '|' +
        df_work.loc[mask_valid, 'tipo_embalagem_capacidade'].astype(str) + '|' +
        df_work.loc[mask_valid, 'tamanho_num'].astype(str)
    )
    df_work.loc[~mask_valid, 'grupo_capacidade'] = None
    
    print(f"[INFO] Grupos de capacidade criados: {df_work['grupo_capacidade'].nunique()} grupos únicos")
    print(f"[INFO] Exemplos de grupos: {df_work[mask_valid]['grupo_capacidade'].unique()[:5].tolist()}")
    
    return df_work

# Testar de-para melhorado
if df_base is not None:
    df_master_enhanced = create_enhanced_de_para(df_base, df_capacidades, df_proj)
    
    if df_master_enhanced is not None:
        print(f"\n[INFO] De-para criado com sucesso!")
        print(f"[INFO] Total de SKUs: {len(df_master_enhanced)}")
        print(f"[INFO] SKUs com capacidade: {df_master_enhanced['capacidade_max'].notna().sum()}")
        print(f"[INFO] Grupos únicos: {df_master_enhanced['grupo_capacidade'].nunique()}")
        
        # Mostrar exemplos
        print("\n[EXEMPLOS] Primeiros grupos de capacidade:")
        grupos_exemplo = df_master_enhanced[df_master_enhanced['grupo_capacidade'].notna()].groupby('grupo_capacidade').agg({
            'chave_sku': 'count',
            'capacidade_min': 'first',
            'capacidade_max': 'first',
            'volume_projetado': 'sum' if 'volume_projetado' in df_master_enhanced.columns else lambda x: 0
        }).head(10)
        print(grupos_exemplo)
else:
    print("[WARNING] Não foi possível testar de-para melhorado (df_base não disponível)")

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
