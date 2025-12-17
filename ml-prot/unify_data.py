#!/usr/bin/env python3
# ============================================================================
# UNIFICAÇÃO DE DADOS - EXPLORAÇÃO E CONSOLIDAÇÃO
# ============================================================================
# Objetivo: Unificar todos os dados em um único dataframe com contexto completo
# de cada SKU e seu grupo (Item|Embalagem)
# ============================================================================

import os
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Arquivos de dados
CSV_BASE = BASE_DIR / "simulador_pnl_futuro_base.csv"
CAPACIDADES_FILE = DATA_DIR / "Capacidades Produção UC V2.xlsx"
PROJECAO_FILE = DATA_DIR / "Projeção Vol UC com Territorio_Envio.xlsx"
MP_FILE = DATA_DIR / "Materia prima (ajustada porcentagem vs BAU).xlsx"
VOLUME_REGIONAL_FILE = DATA_DIR / "Volume com regionais.xlsx"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def parse_size_to_liters(size_str):
    """Converte tamanho em string para litros (float)."""
    if pd.isna(size_str):
        return None
    size_str = str(size_str).strip().upper().replace(' ', '')
    if '-' in size_str:
        parts = size_str.split('-')
        if len(parts) == 2:
            try:
                val1 = parse_size_to_liters(parts[0])
                val2 = parse_size_to_liters(parts[1])
                if val1 is not None and val2 is not None:
                    return (val1 + val2) / 2
            except (ValueError, TypeError):
                pass
    import re
    ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ML', size_str)
    if ml_match:
        ml_val = float(ml_match.group(1).replace(',', '.'))
        return ml_val / 1000.0
    l_match = re.search(r'(\d+(?:[.,]\d+)?)\s*L(?:ITRO)?S?', size_str)
    if l_match:
        return float(l_match.group(1).replace(',', '.'))
    return None

def normalize_package_name(package_str):
    """Normaliza nomes de embalagem.
    
    IMPORTANTE: Ordem de verificação é crítica!
    - Sleek Can deve ser verificado ANTES de Lata/Alumínio
    - Refpet deve ser verificado ANTES de Pet
    """
    if pd.isna(package_str):
        return None
    pkg = str(package_str).strip().upper()
    
    # ORDEM CRÍTICA: Verificar casos específicos ANTES de genéricos
    # 1. Sleek Can (deve vir ANTES de Lata/Alumínio)
    if 'SLEEK CAN' in pkg or 'SLEEK' in pkg:
        return 'Sleek Can'
    # 2. Mini Lata (deve vir ANTES de Lata genérica)
    elif 'MINI LATA' in pkg or ('MINI' in pkg and 'LATA' in pkg):
        return 'Mini Lata'
    # 3. Refpet (deve vir ANTES de Pet)
    elif 'REFPET' in pkg or 'REF PET' in pkg:
        return 'Refpet'
    # 4. Lata/Alumínio (genérico)
    elif 'ALUMINIO' in pkg or 'LATA' in pkg:
        return 'Lata'
    # 5. KS
    elif 'KS' in pkg:
        return 'KS'
    # 6. LS
    elif 'LS' in pkg:
        return 'LS'
    # 7. Vidro não Retornável
    elif 'VIDRO' in pkg:
        return 'Vidro não Retornável'
    # 8. BIB
    elif 'BAG IN BOX' in pkg or 'BIB' in pkg:
        return 'BIB'
    # 9. Pet (genérico, deve vir DEPOIS de Refpet)
    elif 'PET' in pkg:
        return 'Pet'
    
    return pkg

def extract_sku_parts(chave_sku):
    """Extrai partes do SKU da chave_sku."""
    if pd.isna(chave_sku):
        return {}
    parts = str(chave_sku).split('|')
    return {
        'brand': parts[0] if len(parts) > 0 else None,
        'size': float(parts[1]) if len(parts) > 1 else None,
        'tipo_consumo': parts[2] if len(parts) > 2 else None,
        'returnability': parts[3] if len(parts) > 3 else None,
        'package': parts[4] if len(parts) > 4 else None,
    }

def create_tipo_key(package, size):
    """Cria chave TIPO = Embalagem|Tamanho."""
    if pd.isna(package) or pd.isna(size):
        return None
    pkg_norm = normalize_package_name(package)
    if pkg_norm is None:
        return None
    size_rounded = round(float(size), 2)
    return f"{pkg_norm}|{size_rounded}"

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================
def load_base_data():
    """Carrega dados base do CSV."""
    print("\n[1] Carregando dados base...")
    
    if not CSV_BASE.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {CSV_BASE}")
    
    try:
        df = pd.read_csv(CSV_BASE, decimal=',', encoding='utf-8')
    except:
        try:
            df = pd.read_csv(CSV_BASE, sep=';', decimal=',', encoding='utf-8')
        except:
            df = pd.read_csv(CSV_BASE, decimal='.', encoding='utf-8')
    
    print(f"  ✓ Carregado: {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Colunas: {list(df.columns)}")
    
    # Extrair partes do SKU
    if 'chave_sku' in df.columns:
        sku_parts = df['chave_sku'].apply(extract_sku_parts)
        for key in ['brand', 'size', 'tipo_consumo', 'returnability', 'package']:
            df[key] = sku_parts.apply(lambda x: x.get(key))
    
    # Criar TIPO (Item|Embalagem = Embalagem|Tamanho)
    if 'package' in df.columns and 'size' in df.columns:
        df['tipo'] = df.apply(lambda row: create_tipo_key(row['package'], row['size']), axis=1)
    
    return df

def map_tipo_to_capacity_group(tipo_embalagem, tamanho_litros):
    """
    Mapeia TIPO específico (ex: BIB|10.0) para grupo de capacidade (ex: BIB|5-18L).
    
    IMPORTANTE: Ordem de verificação é crítica!
    - Sleek Can deve ser verificado ANTES de Lata (ambos podem ser 0.31L)
    - Refpet deve ser verificado ANTES de Pet (ambos podem ser 2.0L)
    
    Grupos de capacidade conforme arquivo de capacidades:
    - BIB 5-18L: BIB|5.0, BIB|10.0, BIB|18.0, etc. (qualquer BIB entre 5L e 18L)
    - Pet 1-1,5L: Pet|1.0, Pet|1.5
    - Pet 2-3L: Pet|2.0, Pet|3.0
    - Pet 200ml: Pet|0.2
    - Pet 600ml: Pet|0.6
    - KS 290-310ml: Vidro não Retornável|0.29, Vidro não Retornável|0.31
    - Sleek Can 310ml: Lata|0.31 (Sleek Can tem capacidade própria, NÃO compartilha com Lata|350ml)
    - LS 1L: Vidro não Retornável|1.0
    - Lata 350ml: Lata|0.35 (NÃO inclui Sleek Can)
    - Mini Lata 220ml: Lata|0.22
    - Refpet 2L: Refpet|2.0 (tem capacidade própria, NÃO compartilha com Pet|2-3L)
    """
    if pd.isna(tipo_embalagem) or pd.isna(tamanho_litros):
        return None
    
    pkg_norm = normalize_package_name(tipo_embalagem)
    size = float(tamanho_litros)
    
    # ORDEM CRÍTICA: Verificar casos específicos ANTES de casos genéricos
    
    # 1. Sleek Can 310ml (deve vir ANTES de Lata, pois ambos podem ser 0.31L)
    if pkg_norm == 'Sleek Can':
        if abs(size - 0.31) < 0.05:
            return 'Sleek Can|310ml'  # Capacidade própria, não compartilha
    
    # 2. Refpet 2L (deve vir ANTES de Pet, pois ambos podem ser 2.0L)
    elif pkg_norm == 'Refpet':
        if abs(size - 2.0) < 0.05:
            return 'Refpet|2L'  # Capacidade própria, não compartilha
    
    # 3. BIB 5-18L
    elif pkg_norm == 'BIB' or pkg_norm == 'BAG IN BOX':
        if 5.0 <= size <= 18.0:
            return 'BIB|5-18L'
    
    # 4. Pet (verificar grupos específicos antes de genéricos)
    elif pkg_norm == 'Pet':
        # Pet 200ml: 0.2L (tolerância 0.05) - VERIFICAR ANTES de outros
        if abs(size - 0.2) < 0.05:
            return 'Pet|200ml'
        # Pet 600ml: 0.6L (tolerância 0.05) - VERIFICAR ANTES de outros
        elif abs(size - 0.6) < 0.05:
            return 'Pet|600ml'
        # Pet 1-1,5L: 1.0L a 1.5L
        elif 1.0 <= size <= 1.5:
            return 'Pet|1-1.5L'
        # Pet 2-3L: 2.0L a 3.0L (mas NÃO Refpet, que já foi verificado)
        elif 2.0 <= size <= 3.0:
            return 'Pet|2-3L'
        # Pet 0.51L: específico (sem grupo, usar TIPO específico)
        elif abs(size - 0.51) < 0.05:
            return create_tipo_key(pkg_norm, size)  # Sem grupo, usar TIPO específico
    
    # 5. Vidro não Retornável
    elif pkg_norm == 'Vidro não Retornável':
        # KS 290-310ml: 0.29L a 0.31L (qualquer vidro entre 290ml e 310ml)
        # NOTA: Sleek Can (Lata|0.31) NÃO vai para KS, só vidro
        if 0.29 <= size <= 0.31:
            return 'KS|290-310ml'
        # LS 1L: 1.0L (vidro de 1L)
        elif abs(size - 1.0) < 0.05:
            return 'LS|1L'
        # Vidro 250ml: 0.25L
        elif abs(size - 0.25) < 0.05:
            return 'Vidro não Retornável|250ml'
    
    # 6. Lata (verificar Mini Lata antes de Lata genérica)
    elif pkg_norm == 'Lata':
        # Mini Lata 220ml: 0.22L (Lata de 220ml = Mini Lata)
        if abs(size - 0.22) < 0.05:
            return 'Mini Lata|220ml'
        # Lata 350ml: 0.35L (NÃO inclui Sleek Can 0.31L, que já foi verificado)
        elif abs(size - 0.35) < 0.05:
            return 'Lata|350ml'
        # Lata 0.31L que NÃO é Sleek Can (se package é "Lata" mas tamanho é 0.31)
        # Isso não deveria acontecer, mas se acontecer, vai para KS|290-310ml?
        # Na verdade, se package é "Lata" e size é 0.31, provavelmente é Sleek Can
        # mas não foi normalizado corretamente. Vamos deixar como Lata|0.31 específico.
        elif abs(size - 0.31) < 0.05:
            # Se chegou aqui, é Lata|0.31 mas não foi identificado como Sleek Can
            # Isso pode ser um erro de normalização. Vamos criar TIPO específico.
            return create_tipo_key(pkg_norm, size)
    
    # Se não mapeou para grupo, retornar TIPO específico
    return create_tipo_key(pkg_norm, size)

def load_capacidades():
    """Carrega capacidades de produção."""
    print("\n[2] Carregando capacidades...")
    
    if not CAPACIDADES_FILE.exists():
        print(f"  ⚠ Arquivo não encontrado: {CAPACIDADES_FILE}")
        return None
    
    try:
        df = pd.read_excel(CAPACIDADES_FILE)
        df.columns = ['tipo_embalagem', 'tamanho', 'min', 'max']
        
        # Normalizar
        df['tipo_embalagem_norm'] = df['tipo_embalagem'].apply(normalize_package_name)
        
        # Criar grupo de capacidade baseado na descrição do tamanho do arquivo Excel
        # Usar exatamente como está no arquivo para garantir match correto
        def create_capacity_group(row):
            pkg = row['tipo_embalagem_norm']
            tamanho_str = str(row['tamanho']).upper().strip()
            
            # Mapear conforme arquivo Excel (exatamente como está)
            if pkg == 'BIB' and ('5' in tamanho_str and '18' in tamanho_str):
                return 'BIB|5-18L'
            elif pkg == 'Pet' and ('1' in tamanho_str and ('1.5' in tamanho_str or '1,5' in tamanho_str or '1-1.5' in tamanho_str)):
                return 'Pet|1-1.5L'
            elif pkg == 'Pet' and ('2' in tamanho_str and ('3' in tamanho_str or '2-3' in tamanho_str)):
                return 'Pet|2-3L'
            elif pkg == 'Pet' and '200' in tamanho_str:
                return 'Pet|200ml'
            elif pkg == 'Pet' and '600' in tamanho_str:
                return 'Pet|600ml'
            elif pkg == 'Vidro não Retornável' and ('290' in tamanho_str or '310' in tamanho_str or '290-310' in tamanho_str):
                return 'KS|290-310ml'
            elif pkg == 'Vidro não Retornável' and '250' in tamanho_str:
                return 'Vidro não Retornável|250ml'
            elif pkg == 'Lata' and '350' in tamanho_str:
                return 'Lata|350ml'
            elif pkg == 'Mini Lata' and '220' in tamanho_str:
                return 'Mini Lata|220ml'
            elif pkg == 'Sleek Can' and '310' in tamanho_str:
                return 'Sleek Can|310ml'
            elif pkg == 'Refpet' and '2' in tamanho_str:
                return 'Refpet|2L'
            elif pkg == 'Vidro não Retornável' and '1' in tamanho_str and 'L' in tamanho_str and '1L' in tamanho_str:
                return 'LS|1L'
            elif pkg == 'KS' and ('290' in tamanho_str or '310' in tamanho_str):
                return 'KS|290-310ml'
            elif pkg == 'LS' and '1' in tamanho_str and 'L' in tamanho_str:
                return 'LS|1L'
            
            # Fallback: tentar criar TIPO específico
            tamanho_litros = parse_size_to_liters(row['tamanho'])
            if tamanho_litros:
                return create_tipo_key(pkg, tamanho_litros)
            return None
        
        df['grupo_capacidade'] = df.apply(create_capacity_group, axis=1)
        df = df[df['grupo_capacidade'].notna()].copy()
        
        # Verificar se todos os grupos foram criados corretamente
        grupos_esperados = ['BIB|5-18L', 'Pet|1-1.5L', 'Pet|2-3L', 'Pet|200ml', 'Pet|600ml', 
                           'KS|290-310ml', 'LS|1L', 'Lata|350ml', 'Mini Lata|220ml', 
                           'Sleek Can|310ml', 'Refpet|2L', 'Vidro não Retornável|250ml']
        grupos_criados = df['grupo_capacidade'].unique()
        grupos_faltando = set(grupos_esperados) - set(grupos_criados)
        if grupos_faltando:
            print(f"  ⚠ Grupos esperados mas não criados: {grupos_faltando}")
        
        print(f"  ✓ Carregado: {len(df)} linhas")
        print(f"  Grupos de capacidade: {df['grupo_capacidade'].unique()}")
        
        # Mostrar mapeamento
        print(f"\n  Mapeamento de grupos:")
        for grupo in sorted(df['grupo_capacidade'].unique()):
            row = df[df['grupo_capacidade'] == grupo].iloc[0]
            print(f"    {grupo}: Cap {row['min']:,.0f} - {row['max']:,.0f} UC")
        
        return df
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_projecao():
    """Carrega projeção de volumes."""
    print("\n[3] Carregando projeção de volumes...")
    
    if not PROJECAO_FILE.exists():
        print(f"  ⚠ Arquivo não encontrado: {PROJECAO_FILE}")
        return None
    
    try:
        df_raw = pd.read_excel(PROJECAO_FILE)
        
        # Identificar colunas de ID e colunas de data
        id_cols = ['Marca', 'Tamanho', 'Retornabilidade', 'Diretoria Estratégica', 'Território Supply']
        id_cols = [col for col in id_cols if col in df_raw.columns]
        date_cols = [col for col in df_raw.columns if col not in id_cols]
        
        # Unpivot
        df = pd.melt(
            df_raw,
            id_vars=id_cols,
            value_vars=date_cols,
            var_name='month',
            value_name='volume_projetado'
        )
        
        # Normalizar marca
        if 'Marca' in df.columns:
            df['Marca'] = df['Marca'].astype(str).str.strip().str.upper()
            df['Marca'] = df['Marca'].replace({
                'COCA-COLA': 'CC',
                'COCA COLA': 'CC',
            })
            # Renomear para 'brand' para consistência
            df = df.rename(columns={'Marca': 'brand'})
        elif 'brand' not in df.columns:
            print(f"  ⚠ Coluna 'Marca' ou 'brand' não encontrada. Colunas disponíveis: {list(df.columns)}")
        
        # Normalizar tamanho
        if 'Tamanho' in df.columns:
            df['size_litros'] = df['Tamanho'].apply(parse_size_to_liters)
        elif 'size_litros' not in df.columns and 'size' in df.columns:
            # Se já existe 'size', usar ele
            df['size_litros'] = df['size']
        
        # Renomear outras colunas para consistência
        if 'Retornabilidade' in df.columns:
            df = df.rename(columns={'Retornabilidade': 'returnability'})
        
        print(f"  ✓ Carregado: {len(df)} linhas")
        print(f"  Colunas: {list(df.columns)}")
        
        return df
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_materia_prima():
    """Carrega dados de matéria prima."""
    print("\n[4] Carregando matéria prima...")
    
    if not MP_FILE.exists():
        print(f"  ⚠ Arquivo não encontrado: {MP_FILE}")
        return None
    
    try:
        xl = pd.ExcelFile(MP_FILE)
        print(f"  Abas disponíveis: {xl.sheet_names}")
        
        # Tentar carregar primeira aba
        df = pd.read_excel(MP_FILE, sheet_name=xl.sheet_names[0])
        
        print(f"  ✓ Carregado: {len(df)} linhas")
        print(f"  Colunas: {list(df.columns)}")
        
        return df
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return None

# ============================================================================
# UNIFICAÇÃO
# ============================================================================
def unify_all_data():
    """Unifica todos os dados em um único dataframe."""
    print("=" * 80)
    print("UNIFICAÇÃO DE DADOS - EXPLORAÇÃO E CONSOLIDAÇÃO")
    print("=" * 80)
    
    # 1. Carregar dados base
    df_base = load_base_data()
    
    # 2. Carregar capacidades
    df_cap = load_capacidades()
    
    # 3. Carregar projeção
    df_proj = load_projecao()
    
    # 4. Carregar matéria prima
    df_mp = load_materia_prima()
    
    # 5. Unificar capacidades com base
    print("\n[5] Unificando capacidades...")
    if df_cap is not None and 'tipo' in df_base.columns:
        # Criar grupo de capacidade para cada SKU na base
        df_base['grupo_capacidade'] = df_base.apply(
            lambda row: map_tipo_to_capacity_group(row.get('package'), row.get('size')),
            axis=1
        )
        
        # Agregar capacidades por grupo_capacidade
        cap_agg = df_cap.groupby('grupo_capacidade').agg({
            'min': 'first',
            'max': 'first'
        }).reset_index()
        cap_agg.columns = ['grupo_capacidade', 'capacidade_min', 'capacidade_max']
        
        print(f"  Grupos de capacidade no arquivo: {len(cap_agg)}")
        print(f"  Grupos: {list(cap_agg['grupo_capacidade'].values)}")
        
        # Merge com base usando grupo_capacidade
        df_base = df_base.merge(cap_agg, on='grupo_capacidade', how='left')
        
        print(f"  ✓ Capacidades unificadas: {df_base['capacidade_min'].notna().sum()} SKUs com capacidade")
        print(f"  Grupos de capacidade mapeados: {df_base['grupo_capacidade'].notna().sum()} SKUs")
        
        # Verificar grupos sem capacidade após merge e fazer match manual
        grupos_sem_cap = df_base[df_base['capacidade_max'].isna()]['grupo_capacidade'].dropna().unique()
        if len(grupos_sem_cap) > 0:
            print(f"  ⚠ Grupos sem capacidade após merge: {list(grupos_sem_cap)}")
            
            # Mapeamento manual para grupos que não fizeram match
            mapeamento_manual = {
                'Mini Lata|220ml': 'Mini Lata|220ml',  # Deveria ter capacidade
                'Pet|0.51': None,  # Sem capacidade definida
            }
            
            # Verificar se "Mini Lata|220ml" está no cap_agg com nome diferente
            # O arquivo Excel tem "Mini Lata|220ml" mas pode estar como "Lata|0.22"
            for grupo_sem in grupos_sem_cap:
                if pd.notna(grupo_sem) and grupo_sem == 'Mini Lata|220ml':
                    # Procurar por "220ml" ou "0.22" no cap_agg
                    for idx, row_cap in cap_agg.iterrows():
                        if '220' in str(row_cap['grupo_capacidade']) or '0.22' in str(row_cap['grupo_capacidade']):
                            print(f"    Match encontrado: {grupo_sem} → {row_cap['grupo_capacidade']}")
                            mask = df_base['grupo_capacidade'] == grupo_sem
                            df_base.loc[mask, 'capacidade_min'] = row_cap['capacidade_min']
                            df_base.loc[mask, 'capacidade_max'] = row_cap['capacidade_max']
                            break
        
        # Mostrar exemplos de mapeamento
        print(f"\n  Exemplos de mapeamento TIPO → Grupo Capacidade:")
        exemplos = df_base[df_base['grupo_capacidade'].notna()][['tipo', 'grupo_capacidade', 'capacidade_max']].drop_duplicates().head(10)
        for _, row in exemplos.iterrows():
            cap_info = f"Cap: {row['capacidade_max']:,.0f}" if pd.notna(row['capacidade_max']) else "Cap: Inf"
            print(f"    {row['tipo']} → {row['grupo_capacidade']} ({cap_info})")
    
    # 6. Unificar projeção com base
    print("\n[6] Unificando projeção...")
    if df_proj is not None and 'brand' in df_base.columns:
        # IMPORTANTE: O arquivo de projeção tem colunas de meses (Jun-25, Jul-25, etc.)
        # Quando fazemos unpivot, cada linha = SKU em um mês específico
        # NÃO devemos somar todos os meses! Devemos usar apenas UM mês ou agregar por mês
        
        # Verificar quantos meses únicos temos
        if 'month' in df_proj.columns:
            # Converter month para datetime se necessário
            df_proj['month'] = pd.to_datetime(df_proj['month'], errors='coerce')
            meses_unicos = df_proj['month'].dropna().unique()
            
            # Garantir que todos são datetime antes de ordenar
            meses_unicos_dt = pd.to_datetime(meses_unicos)
            meses_ordenados = sorted(meses_unicos_dt)
            print(f"  Meses disponíveis: {[m.strftime('%Y-%m') for m in meses_ordenados]}")
            
            # Usar apenas o PRIMEIRO mês disponível (ou o mais recente)
            # Se quiser usar um mês específico, pode filtrar aqui
            mes_selecionado = meses_ordenados[0]  # Primeiro mês
            print(f"  ⚠ Usando apenas o mês: {mes_selecionado.strftime('%Y-%m')}")
            print(f"  ⚠ Se precisar de outro mês, ajuste o código!")
            
            # Filtrar usando comparação de datetime
            df_proj_filtrado = df_proj[df_proj['month'] == mes_selecionado].copy()
            print(f"  Linhas após filtrar por mês: {len(df_proj_filtrado)} (de {len(df_proj)} total)")
        else:
            df_proj_filtrado = df_proj.copy()
            print(f"  ⚠ Coluna 'month' não encontrada, usando todos os dados (pode estar somando meses!)")
        
        # Agregar projeção por marca, tamanho e retornabilidade
        # Agora estamos agregando apenas dentro de um mês, não somando todos os meses
        # Verificar quais colunas existem antes de fazer groupby
        groupby_cols = []
        if 'brand' in df_proj_filtrado.columns:
            groupby_cols.append('brand')
        elif 'Marca' in df_proj_filtrado.columns:
            groupby_cols.append('Marca')
        else:
            print(f"  ⚠ Coluna 'brand' ou 'Marca' não encontrada. Colunas: {list(df_proj_filtrado.columns)}")
            return df_base
        
        if 'size_litros' in df_proj_filtrado.columns:
            groupby_cols.append('size_litros')
        elif 'size' in df_proj_filtrado.columns:
            groupby_cols.append('size')
        else:
            print(f"  ⚠ Coluna 'size_litros' ou 'size' não encontrada. Colunas: {list(df_proj_filtrado.columns)}")
            return df_base
        
        if 'returnability' in df_proj_filtrado.columns:
            groupby_cols.append('returnability')
        elif 'Retornabilidade' in df_proj_filtrado.columns:
            groupby_cols.append('Retornabilidade')
        else:
            print(f"  ⚠ Coluna 'returnability' ou 'Retornabilidade' não encontrada. Colunas: {list(df_proj_filtrado.columns)}")
            return df_base
        
        if not groupby_cols:
            print(f"  ⚠ Nenhuma coluna válida para groupby encontrada")
            return df_base
        
        proj_agg = df_proj_filtrado.groupby(groupby_cols).agg({
            'volume_projetado': 'sum'  # Soma apenas territórios/diretorias dentro do mesmo mês
        }).reset_index()
        
        # Renomear colunas para nomes padrão
        rename_map = {}
        if 'Marca' in proj_agg.columns:
            rename_map['Marca'] = 'brand'
        if 'Retornabilidade' in proj_agg.columns:
            rename_map['Retornabilidade'] = 'returnability'
        if 'size_litros' in proj_agg.columns:
            rename_map['size_litros'] = 'size'
        if rename_map:
            proj_agg = proj_agg.rename(columns=rename_map)
        
        # Garantir que as colunas finais estão corretas
        if 'brand' not in proj_agg.columns:
            proj_agg['brand'] = None
        if 'size' not in proj_agg.columns:
            proj_agg['size'] = None
        if 'returnability' not in proj_agg.columns:
            proj_agg['returnability'] = None
        
        proj_agg = proj_agg.rename(columns={'volume_projetado': 'volume_projetado_agg'})
        
        print(f"  Volumes agregados (exemplo):")
        print(f"    Total de linhas agregadas: {len(proj_agg)}")
        print(f"    Volume total agregado: {proj_agg['volume_projetado_agg'].sum():,.0f} UC")
        print(f"    Volume médio por SKU: {proj_agg['volume_projetado_agg'].mean():,.0f} UC")
        
        # Merge com base
        df_base = df_base.merge(
            proj_agg,
            on=['brand', 'size', 'returnability'],
            how='left',
            suffixes=('', '_proj')
        )
        
        # Se já tinha volume_projetado, manter o maior
        if 'volume_projetado' in df_base.columns:
            df_base['volume_projetado'] = df_base[['volume_projetado', 'volume_projetado_agg']].max(axis=1)
            df_base = df_base.drop(columns=['volume_projetado_agg'])
        else:
            df_base['volume_projetado'] = df_base['volume_projetado_agg']
            df_base = df_base.drop(columns=['volume_projetado_agg'])
        
        print(f"  ✓ Projeção unificada: {df_base['volume_projetado'].notna().sum()} SKUs com projeção")
    
    # 7. Estatísticas finais
    print("\n[7] Estatísticas do dataframe unificado...")
    print(f"  Total de linhas: {len(df_base)}")
    print(f"  Total de colunas: {len(df_base.columns)}")
    print(f"  SKUs únicos: {df_base['chave_sku'].nunique() if 'chave_sku' in df_base.columns else 'N/A'}")
    print(f"  TIPOs únicos: {df_base['tipo'].nunique() if 'tipo' in df_base.columns else 'N/A'}")
    print(f"  Marcas únicas: {df_base['brand'].nunique() if 'brand' in df_base.columns else 'N/A'}")
    
    # Mostrar colunas disponíveis
    print(f"\n  Colunas disponíveis ({len(df_base.columns)}):")
    for i, col in enumerate(df_base.columns, 1):
        print(f"    {i:2d}. {col}")
    
    # Mostrar amostra
    print(f"\n  Amostra dos dados:")
    print(df_base.head(10).to_string())
    
    # Estatísticas por TIPO
    if 'tipo' in df_base.columns:
        print(f"\n  Estatísticas por TIPO:")
        tipo_stats = df_base.groupby('tipo').agg({
            'chave_sku': 'count' if 'chave_sku' in df_base.columns else lambda x: len(x),
            'volume_projetado': 'sum' if 'volume_projetado' in df_base.columns else 'count',
            'capacidade_max': 'first' if 'capacidade_max' in df_base.columns else lambda x: None,
        }).reset_index()
        tipo_stats.columns = ['TIPO', 'N_SKUs', 'Volume_Total', 'Capacidade_Max']
        print(tipo_stats.head(20).to_string())
    
    return df_base

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    df_unified = unify_all_data()
    
    # Salvar dataframe unificado
    output_file = BASE_DIR / "data_unified.csv"
    df_unified.to_csv(output_file, index=False, decimal=',', encoding='utf-8')
    print(f"\n[8] DataFrame unificado salvo em: {output_file}")
    print(f"  ✓ Pronto para uso no modelo de otimização!")
