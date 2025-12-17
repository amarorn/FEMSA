#!/usr/bin/env python3
"""
Script standalone para testar e corrigir o modelo de otimização
Não depende do app principal - apenas testa a lógica
"""

import os
import pandas as pd
import numpy as np
import re

print("=" * 80)
print("TESTE STANDALONE - CORREÇÃO DO MODELO DE OTIMIZAÇÃO")
print("=" * 80)

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def parse_size_to_liters(size_str):
    """Converte tamanho em string para litros (float)."""
    if pd.isna(size_str):
        return None
    
    size_str = str(size_str).strip().upper().replace(' ', '')
    
    # Tratar ranges
    if '-' in size_str:
        parts = size_str.split('-')
        if len(parts) == 2:
            try:
                val1 = parse_size_to_liters(parts[0])
                val2 = parse_size_to_liters(parts[1])
                if val1 is not None and val2 is not None:
                    return (val1 + val2) / 2
            except:
                pass
    
    # Procurar por ML
    ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ML', size_str)
    if ml_match:
        ml_val = float(ml_match.group(1).replace(',', '.'))
        return ml_val / 1000.0
    
    # Procurar por L
    l_match = re.search(r'(\d+(?:[.,]\d+)?)\s*L(?:ITRO)?S?', size_str)
    if l_match:
        return float(l_match.group(1).replace(',', '.'))
    
    return None

def correct_package_categorization(package_str, size_val=None):
    """
    CORREÇÃO: Categorização correta de embalagens
    - Lata, Mini Lata, Sleek Can → ALUMINIO (categoria)
    - KS, LS → VIDRO (vidro não retornável)
    - BIB → BIB
    - PET, Refpet → PET
    """
    if pd.isna(package_str):
        return None
    
    pkg = str(package_str).strip().upper()
    
    # ALUMINIO: Lata, Mini Lata, Sleek Can
    if any(x in pkg for x in ['LATA', 'MINI LATA', 'SLEEK CAN', 'ALUMINIO']):
        # Se tem tamanho, diferenciar Mini Lata de Lata
        if size_val is not None and size_val < 0.5:
            return 'Mini Lata'  # Para capacidades
        else:
            return 'Lata'  # Para capacidades
    
    # VIDRO: KS, LS (vidro não retornável)
    if 'KS' in pkg or 'LS' in pkg:
        return 'Vidro não Retornável'
    
    # BIB
    if 'BIB' in pkg or 'BAG IN BOX' in pkg:
        return 'BIB'
    
    # PET
    if any(x in pkg for x in ['PET', 'REFPET', 'REF PET']):
        return 'Pet'
    
    return None

# ============================================================================
# TESTE 1: CATEGORIZAÇÃO
# ============================================================================
print("\n[TESTE 1] Categorização de produtos:")
test_cases = [
    ('LATA', 0.35, 'Lata'),
    ('MINI LATA', 0.22, 'Mini Lata'),
    ('SLEEK CAN', 0.22, 'Lata'),
    ('ALUMINIO', 0.22, 'Mini Lata'),
    ('ALUMINIO', 0.35, 'Lata'),
    ('KS', 0.29, 'Vidro não Retornável'),
    ('LS', 0.29, 'Vidro não Retornável'),
    ('BIB', 5.0, 'BIB'),
    ('PET', 1.5, 'Pet'),
    ('REFPET', 1.5, 'Pet'),
]

all_passed = True
for pkg, size, expected in test_cases:
    result = correct_package_categorization(pkg, size)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_passed = False
    print(f"  {status} {pkg:15s} ({size:4.2f}L) → {result:25s} (esperado: {expected})")

if all_passed:
    print("\n  ✓ Todos os testes de categorização passaram!")
else:
    print("\n  ✗ Alguns testes falharam!")

# ============================================================================
# TESTE 2: CARREGAR E ANALISAR DADOS
# ============================================================================
print("\n[TESTE 2] Carregando e analisando dados...")

# Arquivo de projeção
proj_file = "data/Projeção Vol UC com Territorio_Envio.xlsx"
if os.path.exists(proj_file):
    df_proj = pd.read_excel(proj_file)
    print(f"  ✓ Arquivo de projeção: {len(df_proj)} linhas")
    print(f"    Colunas: {df_proj.columns.tolist()[:5]}...")
    
    # Identificar colunas de data
    date_cols = [col for col in df_proj.columns if isinstance(col, pd.Timestamp)]
    print(f"    Colunas de data (volumes): {len(date_cols)} meses")
    
    # Analisar estrutura
    if 'Marca' in df_proj.columns:
        marcas = df_proj['Marca'].unique()
        print(f"    Marcas únicas: {len(marcas)} ({', '.join(marcas[:5].tolist())}...)")
    
    if 'Tamanho' in df_proj.columns:
        tamanhos = df_proj['Tamanho'].unique()
        print(f"    Tamanhos únicos: {len(tamanhos)} ({', '.join(tamanhos[:5].tolist())}...)")
else:
    print(f"  ✗ Arquivo não encontrado: {proj_file}")
    df_proj = None

# Arquivo de capacidades
cap_file = "data/Capacidades Produção UC V2.xlsx"
if os.path.exists(cap_file):
    try:
        df_cap = pd.read_excel(cap_file)
        print(f"  ✓ Arquivo de capacidades: {len(df_cap)} linhas")
        print(f"    Colunas: {df_cap.columns.tolist()}")
        
        # Tentar identificar colunas
        for col in df_cap.columns:
            col_lower = str(col).lower()
            if 'tipo' in col_lower and 'embalagem' in col_lower:
                tipos = df_cap[col].unique()
                print(f"    Tipos de embalagem: {', '.join([str(t) for t in tipos[:10]])}...")
                break
    except Exception as e:
        print(f"  ✗ Erro ao carregar capacidades: {e}")
        df_cap = None
else:
    print(f"  ✗ Arquivo não encontrado: {cap_file}")
    df_cap = None

# Arquivo base
base_file = "simulador_pnl_futuro_base.csv"
if os.path.exists(base_file):
    try:
        df_base = pd.read_csv(base_file, nrows=100)  # Ler apenas primeiras 100 linhas para teste
        print(f"  ✓ Arquivo base: {len(df_base)} linhas (amostra)")
        print(f"    Colunas: {df_base.columns.tolist()[:10]}...")
        
        # Verificar chave_sku
        if 'chave_sku' in df_base.columns:
            print(f"    Total de SKUs únicos: {df_base['chave_sku'].nunique()}")
            
            # Analisar estrutura da chave_sku
            exemplo_sku = df_base['chave_sku'].iloc[0] if len(df_base) > 0 else None
            if exemplo_sku:
                parts = str(exemplo_sku).split('|')
                print(f"    Exemplo de chave_sku: {exemplo_sku}")
                print(f"    Partes: {len(parts)} ({', '.join(parts)})")
                
                if len(parts) >= 5:
                    marca = parts[0]
                    tamanho = parts[1]
                    embalagem = parts[4]
                    print(f"      Marca: {marca}")
                    print(f"      Tamanho: {tamanho}")
                    print(f"      Embalagem: {embalagem}")
                    
                    # Testar categorização
                    size_num = parse_size_to_liters(tamanho)
                    categoria = correct_package_categorization(embalagem, size_num)
                    print(f"      Categoria corrigida: {categoria}")
    except Exception as e:
        print(f"  ✗ Erro ao carregar base: {e}")
        df_base = None
else:
    print(f"  ✗ Arquivo não encontrado: {base_file}")
    df_base = None

# ============================================================================
# TESTE 3: VERIFICAR PROBLEMA DE AGRUPAMENTO
# ============================================================================
print("\n[TESTE 3] Verificando problema de agrupamento...")

if df_base is not None and 'chave_sku' in df_base.columns:
    # Extrair informações
    sku_parts = df_base['chave_sku'].str.split('|', expand=True)
    if len(sku_parts.columns) >= 5:
        df_base['marca'] = sku_parts[0]
        df_base['tamanho_str'] = sku_parts[1]
        df_base['embalagem_raw'] = sku_parts[4]
        
        df_base['tamanho_num'] = df_base['tamanho_str'].apply(parse_size_to_liters)
        df_base['categoria'] = df_base.apply(
            lambda row: correct_package_categorization(row['embalagem_raw'], row['tamanho_num']),
            axis=1
        )
        
        # PROBLEMA IDENTIFICADO: O modelo atual agrupa apenas por categoria + tamanho
        # Mas deveria agrupar por MARCA + categoria + tamanho
        print("\n  [PROBLEMA IDENTIFICADO]")
        print("    Agrupamento atual (ERRADO): categoria + tamanho")
        print("    Agrupamento correto: MARCA + categoria + tamanho")
        
        # Mostrar exemplos
        print("\n  [EXEMPLOS]")
        grupos_errado = df_base.groupby(['categoria', 'tamanho_num']).size()
        print(f"    Grupos (ERRADO - sem marca): {len(grupos_errado)}")
        print(f"    Exemplos: {grupos_errado.head(5).to_dict()}")
        
        grupos_correto = df_base.groupby(['marca', 'categoria', 'tamanho_num']).size()
        print(f"\n    Grupos (CORRETO - com marca): {len(grupos_correto)}")
        print(f"    Exemplos: {grupos_correto.head(5).to_dict()}")
        
        # Mostrar problema específico: mesma embalagem, marcas diferentes
        print("\n  [PROBLEMA ESPECÍFICO]")
        exemplo = df_base[df_base['categoria'].notna()].groupby(['categoria', 'tamanho_num'])['marca'].apply(lambda x: x.unique().tolist())
        problemas = exemplo[exemplo.apply(len) > 1]
        if len(problemas) > 0:
            print(f"    Encontrados {len(problemas)} grupos com múltiplas marcas:")
            for (cat, tam), marcas in problemas.head(3).items():
                print(f"      {cat} {tam}L: {marcas}")
                print(f"        → Deveria ter limites SEPARADOS por marca!")
        else:
            print("    Nenhum problema encontrado (todos os grupos têm apenas uma marca)")

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
print("\nPRÓXIMOS PASSOS:")
print("1. Corrigir função optimize_product_mix() para agrupar por MARCA + categoria + tamanho")
print("2. Ajustar restrições de capacidade para considerar MARCA")
print("3. Integrar volumes do arquivo de projeção na otimização")
print("4. Testar otimização completa")
