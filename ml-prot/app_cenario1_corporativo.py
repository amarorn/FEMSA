# ============================================================================
# FEMSA - Simulador de P&L e Otimização de Mix
# Plataforma Corporativa de Análise de Cenários
# ============================================================================
import os
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import differential_evolution

# ============================================================================
# CONFIGURAÇÕES CORPORATIVAS - PALETA COCA-COLA
# ============================================================================
DATA_FILE = "simulador_pnl_futuro_base.csv"
PROJECAO_MP_FILE = "data/Materia prima (ajustada porcentagem vs BAU).xlsx"
CAPACIDADES_FILE = "data/Capacidades Produção UC V2.xlsx"

# Paleta de Cores Corporativa Coca-Cola
COLORS = {
    'primary': '#F40009',      # Vermelho Coca-Cola
    'primary_dark': '#C00007', # Vermelho escuro
    'primary_light': '#FF4D5A', # Vermelho claro
    'secondary': '#1A1A1A',    # Preto
    'accent': '#FFFFFF',       # Branco
    'gray_dark': '#4A4A4A',    # Cinza escuro
    'gray_medium': '#8A8A8A',  # Cinza médio
    'gray_light': '#E5E5E5',   # Cinza claro
    'background': '#F8F8F8',   # Fundo claro
    'success': '#00A859',      # Verde sucesso
    'warning': '#FFB800',      # Amarelo alerta
    'error': '#E60012',        # Vermelho erro
}

# Drivers de Custo
COST_DRIVERS_SLIDERS = [
    "cvv_concentrate",
    "cvv_sweetener",
    "cvv_pet",
    "cvv_can",
    "cvv_cap",
    "cvv_purcharses",
    "cvv_otherraw",
]

COST_BUCKETS_BASE_COLS = [f"base_{c}_unit" for c in COST_DRIVERS_SLIDERS]

# Legendas Profissionais
PRETTY = {
    "cvv_concentrate": "Concentrate (% Receita)",
    "cvv_sweetener":   "Sweetener (R$/UC)",
    "cvv_pet":         "PET (R$/UC)",
    "cvv_can":         "Can (Lata) (R$/UC)",
    "cvv_cap":         "Cap (Tampa) (R$/UC)",
    "cvv_purcharses":  "Purchases (R$/UC)",
    "cvv_otherraw":    "Other Raw (R$/UC)",
}

# Cores para drivers (escala de vermelhos e cinzas corporativos)
COLOR_DRIVERS = {
    "cvv_concentrate": COLORS['primary'],
    "cvv_sweetener":   COLORS['gray_dark'],
    "cvv_pet":         COLORS['primary_light'],
    "cvv_can":         COLORS['primary_dark'],
    "cvv_cap":         COLORS['gray_medium'],
    "cvv_purcharses":  COLORS['primary'],
    "cvv_otherraw":    COLORS['gray_dark'],
}

# ============================================================================
# UTILITÁRIOS
# ============================================================================
def to_month(dt_like):
    """Converte datetime para primeiro dia do mês."""
    if isinstance(dt_like, pd.Timestamp):
        return pd.Timestamp(dt_like.year, dt_like.month, 1)
    s = pd.to_datetime(dt_like, errors="coerce")
    return s.dt.to_period("M").dt.to_timestamp()

def nonempty_unique(x):
    return sorted([v for v in x.dropna().unique().tolist() if v != ""])

def opts(values, fmt=lambda x: x):
    return [{"label": fmt(v), "value": v} for v in values]

# ============================================================================
# SISTEMA DE DE-PARA PARA CORRELAÇÃO DE DADOS
# ============================================================================
def parse_size_to_liters(size_str):
    """
    Converte tamanho em string para litros (float).
    Exemplos: '350ml' -> 0.35, '1L' -> 1.0, '290-310ml' -> 0.30 (média)
    """
    if pd.isna(size_str):
        return None
    
    size_str = str(size_str).strip().upper()
    
    # Remover espaços
    size_str = size_str.replace(' ', '')
    
    # Tratar ranges (ex: 290-310ml -> usar média)
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
    
    # Procurar por ML
    import re
    ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ML', size_str)
    if ml_match:
        ml_val = float(ml_match.group(1).replace(',', '.'))
        return ml_val / 1000.0
    
    # Procurar por L
    l_match = re.search(r'(\d+(?:[.,]\d+)?)\s*L(?:ITRO)?S?', size_str)
    if l_match:
        return float(l_match.group(1).replace(',', '.'))
    
    return None

def normalize_package_name(package_str):
    """
    Normaliza nomes de embalagem para facilitar matching.
    Mapeia tipos de embalagem do sistema para os nomes do arquivo de capacidades.
    """
    if pd.isna(package_str):
        return None
    
    pkg = str(package_str).strip().upper()
    
    # Mapeamentos: do formato do sistema (chave_sku) para formato do arquivo de capacidades
    mappings = {
        'ALUMINIO': 'Mini Lata',  # ALUMINIO com tamanho pequeno (0.22, 0.29, etc) → Mini Lata
        'LATA': 'Lata',
        'MINI LATA': 'Mini Lata',
        'SLEEK CAN': 'Sleek Can',
        'KS': 'KS',
        'LS': 'LS',
        'REFPET': 'Refpet',
        'REF PET': 'Refpet',
        'VIDRO NÃO RETORNAVEL': 'Vidro não Retornável',
        'VIDRO NAO RETORNAVEL': 'Vidro não Retornável',
        'VIDRO': 'Vidro não Retornável',
        'BAG IN BOX': 'BIB',
        'BIB': 'BIB',
        'PET': 'Pet',
    }
    
    for key, value in mappings.items():
        if key in pkg:
            return value
    
    return pkg

def extract_package_from_sku(chave_sku):
    """
    Extrai o tipo de embalagem da chave_sku.
    Formato: MARCA|TAMANHO|TIPO_CONSUMO|RETORNABILIDADE|EMBALAGEM
    Retorna o último campo (EMBALAGEM).
    """
    if pd.isna(chave_sku):
        return None
    
    parts = str(chave_sku).split('|')
    if len(parts) >= 5:
        return parts[4].strip().upper()  # Último campo é a embalagem
    return None

def extract_size_from_sku(chave_sku):
    """
    Extrai o tamanho da chave_sku.
    Formato: MARCA|TAMANHO|TIPO_CONSUMO|RETORNABILIDADE|EMBALAGEM
    Retorna o segundo campo (TAMANHO) como float.
    """
    if pd.isna(chave_sku):
        return None
    
    parts = str(chave_sku).split('|')
    if len(parts) >= 2:
        try:
            return float(parts[1].strip())
        except (ValueError, TypeError):
            return None
    return None

def map_package_to_capacity_type(package_str, size_val=None):
    """
    Mapeia o tipo de embalagem do sistema para o tipo do arquivo de capacidades.
    CORREÇÃO: Categorização correta conforme especificação:
    - Lata, Mini Lata, Sleek Can → Alumínio (categoria)
    - KS, LS → Vidro não Retornável
    - BIB → BIB
    - PET, Refpet → Pet
    Considera o tamanho para diferenciar Mini Lata de Lata.
    """
    if pd.isna(package_str):
        return None
    
    pkg = str(package_str).strip().upper()
    
    # ALUMINIO: Lata, Mini Lata, Sleek Can são todos alumínio
    # Diferenciar Mini Lata (< 0.5L) de Lata (>= 0.5L) baseado no tamanho
    if any(x in pkg for x in ['LATA', 'MINI LATA', 'SLEEK CAN', 'ALUMINIO']):
        if size_val is not None and size_val < 0.5:
            return 'Mini Lata'  # Para capacidades
        else:
            return 'Lata'  # Para capacidades (inclui Sleek Can)
    
    # VIDRO: KS, LS são vidro não retornável
    if 'KS' in pkg or 'LS' in pkg:
        return 'Vidro não Retornável'
    
    # BIB
    if 'BIB' in pkg or 'BAG IN BOX' in pkg:
        return 'BIB'
    
    # PET: Refpet, PET são todos PET
    if any(x in pkg for x in ['PET', 'REFPET', 'REF PET']):
        return 'Pet'
    
    # Fallback para outros tipos de vidro
    if 'VIDRO' in pkg:
        return 'Vidro não Retornável'
    
    return None

def load_capacidades_data(file_path):
    """
    Carrega dados de capacidades de produção.
    Estrutura esperada: Tipo Embalagem | Tamanho | Mín | Máx
    """
    if not os.path.exists(file_path):
        print(f"[WARNING] Arquivo de capacidades não encontrado: {file_path}")
        return None
    
    try:
        # Tentar ler com diferentes headers
        df_raw = pd.read_excel(file_path, header=0)
        
        # Procurar colunas relevantes (case insensitive)
        col_map = {}
        for col in df_raw.columns:
            col_lower = str(col).lower().strip()
            if 'tipo' in col_lower and 'embalagem' in col_lower:
                col_map['tipo_embalagem'] = col
            elif 'tamanho' in col_lower:
                col_map['tamanho'] = col
            elif 'mín' in col_lower or 'min' in col_lower:
                col_map['min'] = col
            elif 'máx' in col_lower or 'max' in col_lower:
                col_map['max'] = col
        
        if len(col_map) < 4:
            print(f"[WARNING] Estrutura de capacidades não reconhecida. Colunas encontradas: {list(df_raw.columns)}")
            # Tentar usar primeiras 4 colunas
            if len(df_raw.columns) >= 4:
                df = df_raw.iloc[:, :4].copy()
                df.columns = ['tipo_embalagem', 'tamanho', 'min', 'max']
            else:
                return None
        else:
            df = df_raw[[col_map['tipo_embalagem'], col_map['tamanho'], col_map['min'], col_map['max']]].copy()
            df.columns = ['tipo_embalagem', 'tamanho', 'min', 'max']
        
        # Limpar dados
        df = df.dropna(subset=['tipo_embalagem', 'tamanho'])
        df = df[df['tipo_embalagem'].astype(str).str.upper() != 'TOTAL']
        
        # Normalizar
        df['tipo_embalagem_norm'] = df['tipo_embalagem'].apply(normalize_package_name)
        df['tamanho_litros'] = df['tamanho'].apply(parse_size_to_liters)
        
        # Converter min/max para numérico
        df['min'] = pd.to_numeric(df['min'], errors='coerce')
        df['max'] = pd.to_numeric(df['max'], errors='coerce')
        
        # Remover linhas inválidas
        df = df.dropna(subset=['tipo_embalagem_norm', 'tamanho_litros', 'min', 'max'])
        
        print(f"[INFO] Dados de capacidades carregados: {len(df)} linhas")
        print(f"[INFO] Tipos de embalagem: {df['tipo_embalagem_norm'].unique().tolist()}")
        
        return df
        
    except Exception as e:
        print(f"[WARNING] Erro ao carregar capacidades: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_de_para_mapping(df_master, df_capacidades=None):
    """
    Cria mapeamento de-para entre dados do master e capacidades de produção.
    Extrai tipo de embalagem e tamanho da chave_sku e correlaciona com capacidades.
    Retorna o df_master modificado com as colunas de capacidade.
    """
    if df_capacidades is None or df_capacidades.empty:
        print("[INFO] Sem dados de capacidades para criar de-para")
        return df_master
    
    print("[INFO] Correlacionando dados de capacidades com master...")
    print(f"[INFO] Total de linhas no master: {len(df_master)}")
    print(f"[INFO] Total de capacidades disponíveis: {len(df_capacidades)}")
    
    # Criar dicionário de capacidades para lookup rápido
    # Chave: tipo_embalagem_norm|tamanho_litros (arredondado)
    capacidades_dict = {}
    for _, row in df_capacidades.iterrows():
        pkg = row['tipo_embalagem_norm']
        size = row['tamanho_litros']
        if pd.notna(pkg) and pd.notna(size):
            # Criar múltiplas chaves para ranges (ex: 5-18L)
            key = f"{pkg}|{size:.3f}"
            capacidades_dict[key] = {
                'min': row['min'],
                'max': row['max'],
                'tamanho_original': row.get('tamanho', '')
            }
    
    print(f"[INFO] Dicionário de capacidades criado com {len(capacidades_dict)} entradas")
    
    # Adicionar colunas de capacidade ao master
    df_master['capacidade_min'] = None
    df_master['capacidade_max'] = None
    df_master['tipo_embalagem_capacidade'] = None
    df_master['tamanho_capacidade'] = None
    
    matched_count = 0
    
    # Processar cada linha do master
    for idx, row in df_master.iterrows():
        # Extrair embalagem e tamanho da chave_sku
        chave_sku = row.get('chave_sku', '')
        package_from_sku = extract_package_from_sku(chave_sku)
        size_from_sku = extract_size_from_sku(chave_sku)
        
        if package_from_sku and size_from_sku is not None:
            # Mapear para tipo de capacidade (considerando tamanho)
            tipo_capacidade = map_package_to_capacity_type(package_from_sku, size_from_sku)
            
            if tipo_capacidade:
                # Buscar match nas capacidades
                best_match = None
                best_diff = float('inf')
                
                for cap_key, cap_data in capacidades_dict.items():
                    cap_pkg, cap_size_str = cap_key.split('|')
                    cap_size = float(cap_size_str)
                    
                    # Match exato de tipo de embalagem
                    if cap_pkg == tipo_capacidade:
                        # Match de tamanho (tolerância de 0.1L ou range)
                        diff = abs(cap_size - size_from_sku)
                        if diff < best_diff and diff < 0.15:  # Tolerância de 0.15L
                            best_diff = diff
                            best_match = cap_data
                
                if best_match:
                    df_master.at[idx, 'capacidade_min'] = best_match['min']
                    df_master.at[idx, 'capacidade_max'] = best_match['max']
                    df_master.at[idx, 'tipo_embalagem_capacidade'] = tipo_capacidade
                    df_master.at[idx, 'tamanho_capacidade'] = best_match.get('tamanho_original', '')
                    matched_count += 1
    
    print(f"[INFO] Capacidades correlacionadas: {matched_count}/{len(df_master)} linhas ({matched_count/len(df_master)*100:.1f}%)")
    
    # Estatísticas por tipo de embalagem
    if matched_count > 0:
        tipos_match = df_master[df_master['tipo_embalagem_capacidade'].notna()]['tipo_embalagem_capacidade'].value_counts()
        print("[INFO] Match por tipo de embalagem:")
        for tipo, count in tipos_match.items():
            print(f"  - {tipo}: {count} SKUs")
    
    return df_master

# ============================================================================
# ANÁLISE DE MIX DE PRODUTOS
# ============================================================================
def analyze_product_mix(df_sim):
    """
    Analisa o mix de produtos e identifica oportunidades de otimização.
    Retorna análise de participação, margem por produto, e verifica restrições de capacidade.
    """
    if df_sim.empty:
        return None
    
    # Normalizar campos: se vier de otimização, pode ter volume_otimizado em vez de volume_simulado
    df_sim = df_sim.copy()
    if 'volume_otimizado' in df_sim.columns and 'volume_simulado' not in df_sim.columns:
        df_sim['volume_simulado'] = df_sim['volume_otimizado']
    if 'margem_total_otimizada' in df_sim.columns and 'margem_total_simulada' not in df_sim.columns:
        df_sim['margem_total_simulada'] = df_sim['margem_total_otimizada']
    if 'receita_total_otimizada' in df_sim.columns and 'receita_total_simulada' not in df_sim.columns:
        df_sim['receita_total_simulada'] = df_sim['receita_total_otimizada']
    
    analysis = {}
    
    # Análise por marca
    if 'brand' in df_sim.columns:
        mix_brand = df_sim.groupby('brand').agg({
            'volume_simulado': 'sum',
            'receita_total_simulada': 'sum',
            'margem_total_simulada': 'sum'
        }).reset_index()
        mix_brand['participacao_volume'] = mix_brand['volume_simulado'] / mix_brand['volume_simulado'].sum()
        mix_brand['participacao_receita'] = mix_brand['receita_total_simulada'] / mix_brand['receita_total_simulada'].sum()
        mix_brand['margem_pct'] = mix_brand['margem_total_simulada'] / mix_brand['receita_total_simulada']
        analysis['por_marca'] = mix_brand
    
    # Análise por tamanho
    if 'size' in df_sim.columns:
        mix_size = df_sim.groupby('size').agg({
            'volume_simulado': 'sum',
            'receita_total_simulada': 'sum',
            'margem_total_simulada': 'sum'
        }).reset_index()
        mix_size['participacao_volume'] = mix_size['volume_simulado'] / mix_size['volume_simulado'].sum()
        mix_size['margem_pct'] = mix_size['margem_total_simulada'] / mix_size['receita_total_simulada']
        analysis['por_tamanho'] = mix_size
    
    # Análise por tipo de embalagem (com capacidades)
    if 'package' in df_sim.columns:
        # Criar campo package_display que agrupa Aluminio (Lata, Mini Lata, Sleek Can)
        df_sim = df_sim.copy()
        df_sim['package_display'] = df_sim['package'].copy()
        
        # Mapear tipos de Aluminio para "Aluminio" para o gráfico
        # Aluminio = Lata, Mini Lata, Sleek Can
        mask_aluminio = (
            df_sim['package'].str.contains('ALUMINIO|LATA', case=False, na=False) |
            (df_sim.get('tipo_embalagem_capacidade', pd.Series()) == 'Lata') |
            (df_sim.get('tipo_embalagem_capacidade', pd.Series()) == 'Mini Lata') |
            (df_sim.get('tipo_embalagem_capacidade', pd.Series()) == 'Sleek Can')
        )
        df_sim.loc[mask_aluminio, 'package_display'] = 'Aluminio'
        
        # Construir dicionário de agregação dinamicamente
        agg_dict = {
            'volume_simulado': 'sum',
            'receita_total_simulada': 'sum',
            'margem_total_simulada': 'sum'
        }
        
        # Adicionar capacidades apenas se existirem
        # Para Aluminio (que agrupa Lata, Mini Lata, Sleek Can), usar max para não duplicar
        if 'capacidade_min' in df_sim.columns:
            agg_dict['capacidade_min'] = 'max'  # Máximo para evitar duplicação
        if 'capacidade_max' in df_sim.columns:
            agg_dict['capacidade_max'] = 'max'  # Máximo para evitar duplicação
        
        # Adicionar volume_demanda/volume_projetado se disponível (para comparativo)
        # IMPORTANTE: Usar volume_real (demanda original) se disponível, senão volume_projetado
        if 'volume_real' in df_sim.columns:
            agg_dict['volume_real'] = 'sum'
        elif 'volume_demanda' in df_sim.columns:
            agg_dict['volume_demanda'] = 'sum'
        elif 'volume_projetado' in df_sim.columns:
            agg_dict['volume_projetado'] = 'sum'
        
        # Agrupar por package_display em vez de package
        mix_package = df_sim.groupby('package_display').agg(agg_dict).reset_index()
        mix_package = mix_package.rename(columns={'package_display': 'package'})  # Renomear para compatibilidade
        
        # Normalizar: criar volume_demanda a partir do campo disponível
        if 'volume_real' in mix_package.columns:
            mix_package['volume_demanda'] = mix_package['volume_real']
        elif 'volume_projetado' in mix_package.columns and 'volume_demanda' not in mix_package.columns:
            mix_package['volume_demanda'] = mix_package['volume_projetado']
        
        mix_package['participacao_volume'] = mix_package['volume_simulado'] / mix_package['volume_simulado'].sum()
        mix_package['margem_pct'] = mix_package['margem_total_simulada'] / mix_package['receita_total_simulada']
        
        # Verificar se está dentro das capacidades (apenas se as colunas existirem)
        if 'capacidade_min' in mix_package.columns and 'capacidade_max' in mix_package.columns:
            # Filtrar apenas linhas com capacidades válidas (não None/NaN)
            mask_valid = (
                mix_package['capacidade_min'].notna() & 
                mix_package['capacidade_max'].notna() &
                (mix_package['capacidade_min'] != float('inf')) &
                (mix_package['capacidade_max'] != float('inf'))
            )
            
            # Inicializar colunas com None
            mix_package['dentro_capacidade'] = None
            mix_package['uso_capacidade_pct'] = None
            
            # Calcular apenas para linhas válidas
            if mask_valid.any():
                mix_package.loc[mask_valid, 'dentro_capacidade'] = (
                    (mix_package.loc[mask_valid, 'volume_simulado'] >= mix_package.loc[mask_valid, 'capacidade_min']) &
                    (mix_package.loc[mask_valid, 'volume_simulado'] <= mix_package.loc[mask_valid, 'capacidade_max'])
                )
                
                # Calcular uso de capacidade apenas se capacidade_max for válida e > 0
                mask_valid_max = mask_valid & (mix_package['capacidade_max'] > 0)
                if mask_valid_max.any():
                    mix_package.loc[mask_valid_max, 'uso_capacidade_pct'] = (
                        mix_package.loc[mask_valid_max, 'volume_simulado'] / 
                        mix_package.loc[mask_valid_max, 'capacidade_max'] * 100
                    )
        else:
            mix_package['dentro_capacidade'] = None
            mix_package['uso_capacidade_pct'] = None
        
        analysis['por_embalagem'] = mix_package
    
    # Top 10 SKUs por margem
    if 'chave_sku' in df_sim.columns:
        top_skus = df_sim.nlargest(10, 'margem_total_simulada')[
            ['chave_sku', 'volume_simulado', 'receita_total_simulada', 'margem_total_simulada']
        ].copy()
        top_skus['margem_pct'] = top_skus['margem_total_simulada'] / top_skus['receita_total_simulada']
        analysis['top_skus'] = top_skus
    
    # Verificação de restrições de capacidade
    if 'capacidade_min' in df_sim.columns and 'capacidade_max' in df_sim.columns:
        # Filtrar apenas linhas com capacidades válidas antes de comparar
        mask_valid = (
            df_sim['capacidade_min'].notna() & 
            df_sim['capacidade_max'].notna() &
            (df_sim['capacidade_min'] != float('inf')) &
            (df_sim['capacidade_max'] != float('inf'))
        )
        
        if mask_valid.any():
            # Usar .loc para comparar apenas nas linhas válidas
            volume_valid = df_sim.loc[mask_valid, 'volume_simulado']
            cap_min_valid = df_sim.loc[mask_valid, 'capacidade_min']
            cap_max_valid = df_sim.loc[mask_valid, 'capacidade_max']
            
            mask_violations_valid = (
                (volume_valid < cap_min_valid) |
                (volume_valid > cap_max_valid)
            )
            
            # Criar mask completo com False para linhas não válidas
            mask_violations = pd.Series(False, index=df_sim.index)
            mask_violations.loc[mask_valid] = mask_violations_valid
            capacidade_violations = df_sim[mask_violations]
            analysis['violacoes_capacidade'] = capacidade_violations
            analysis['total_violacoes'] = len(capacidade_violations)
        else:
            analysis['violacoes_capacidade'] = pd.DataFrame()
            analysis['total_violacoes'] = 0
    else:
        analysis['total_violacoes'] = 0
    
    return analysis

# Otimização de mix movida para app_mix_optimization.py (porta 8051)
OPTIMIZE_PRODUCTION_MIX_AVAILABLE = False

def optimize_product_mix(df_base, price_adj_pct=0.0, shocks_pct={}, max_iterations=100):
    """
    Otimiza o mix de produtos considerando:
    - Capacidades mínimas e máximas de produção (por tipo de embalagem/tamanho)
    - Elasticidade de preço
    - Demanda projetada
    - Maximização de margem total
    
    Retorna DataFrame com volumes otimizados e métricas de otimização.
    """
    from scipy.optimize import minimize
    
    if df_base.empty:
        return None
    
    # 1. Preparar dados base - AGRUPAR POR SKU (somar volumes de múltiplos meses)
    # Se há múltiplos meses, agregar por SKU antes de otimizar
    if 'month' in df_base.columns:
        n_months = df_base['month'].nunique()
        print(f"[INFO] Dados contêm {n_months} mês(es). Agregando volumes por SKU...")
        
        # Agregar por SKU: somar volumes, manter médias/primeiros valores para outros campos
        agg_dict = {
            'volume_projetado': 'sum',  # SOMA volumes de todos os meses
            'elasticidade': 'first',  # Elasticidade é a mesma por SKU
            'base_preco_liquido_unit': 'first',
            'base_margem_variavel_unit': 'first',
        }
        
        # Adicionar outros campos necessários
        for col in ['base_cvv_concentrate_unit', 'base_cvv_sweetener_unit', 
                    'base_cvv_pet_unit', 'base_cvv_can_unit', 'base_cvv_cap_unit',
                    'base_cvv_purcharses_unit', 'base_cvv_otherraw_unit']:
            if col in df_base.columns:
                agg_dict[col] = 'first'
        
        # Preservar colunas de capacidade (usar first, pois são iguais por SKU)
        if 'capacidade_min' in df_base.columns:
            agg_dict['capacidade_min'] = 'first'
        if 'capacidade_max' in df_base.columns:
            agg_dict['capacidade_max'] = 'first'
        if 'tipo_embalagem_capacidade' in df_base.columns:
            agg_dict['tipo_embalagem_capacidade'] = 'first'
        if 'size' in df_base.columns:
            agg_dict['size'] = 'first'
        if 'package' in df_base.columns:
            agg_dict['package'] = 'first'
        
        df_work = df_base.groupby('chave_sku', as_index=False).agg(agg_dict)
        
        # AJUSTAR CAPACIDADES: multiplicar pelo número de meses (capacidades são mensais)
        # IMPORTANTE: Isso deve ser feito ANTES de criar os grupos de capacidade
        if 'capacidade_min' in df_work.columns and n_months > 0:
            mask_valid_min = df_work['capacidade_min'].notna()
            if mask_valid_min.any():
                df_work.loc[mask_valid_min, 'capacidade_min'] = df_work.loc[mask_valid_min, 'capacidade_min'] * n_months
                print(f"[INFO] Capacidades mínimas ajustadas para {n_months} mês(es) (multiplicadas por {n_months})")
        
        if 'capacidade_max' in df_work.columns and n_months > 0:
            mask_valid_max = df_work['capacidade_max'].notna()
            if mask_valid_max.any():
                df_work.loc[mask_valid_max, 'capacidade_max'] = df_work.loc[mask_valid_max, 'capacidade_max'] * n_months
                print(f"[INFO] Capacidades máximas ajustadas para {n_months} mês(es) (multiplicadas por {n_months})")
    else:
        df_work = df_base.copy()
    
    # Preservar colunas de capacidade se existirem
    capacity_cols = []
    if 'capacidade_min' in df_work.columns:
        capacity_cols.append('capacidade_min')
    if 'capacidade_max' in df_work.columns:
        capacity_cols.append('capacidade_max')
    
    # Filtrar apenas SKUs com dados válidos
    required_cols = ['chave_sku', 'volume_projetado', 'elasticidade', 
                     'base_preco_liquido_unit', 'base_margem_variavel_unit']
    df_work = df_work.dropna(subset=required_cols)
    
    if df_work.empty:
        return None
    
    # IMPORTANTE: Verificar se volumes são mensais ou anuais
    # Se o df_base tem coluna 'month', os volumes podem estar agregados por múltiplos meses
    # As capacidades são MENSais, então precisamos ajustar
    n_months_in_data = 1
    if 'month' in df_base.columns:
        n_months_in_data = df_base['month'].nunique()
        if n_months_in_data == 0:
            n_months_in_data = 1
        print(f"[INFO] Dados contêm {n_months_in_data} mês(es). Capacidades são mensais, volumes estão agregados.")
    
    # Verificar se há dados de capacidade
    if capacity_cols:
        has_capacity = df_work[capacity_cols].notna().any(axis=1).sum()
        print(f"[INFO] SKUs com dados de capacidade: {has_capacity}/{len(df_work)}")
        if has_capacity == 0:
            print("[WARNING] Nenhum SKU tem dados de capacidade. Verifique o de-para.")
    
    # 2. Calcular margem unitária base (considerando preço e custos ajustados)
    df_sim_base = run_pnl_simulation(df_work, price_adj_pct=price_adj_pct, shocks_pct=shocks_pct)
    
    # Margem unitária esperada para cada SKU
    df_work['margem_unit_esperada'] = df_sim_base['margem_simulada_unit'].values
    df_work['preco_unit_esperado'] = df_sim_base['preco_liquido_simulado_unit'].values
    
    # 3. Preparar restrições de capacidade
    # Agrupar por tipo_embalagem_capacidade e tamanho para criar restrições globais
    capacity_constraints = {}
    
    # Criar grupos de capacidade baseado em tipo_embalagem_capacidade e tamanho
    # Filtrar apenas SKUs com dados de capacidade válidos
    if 'tipo_embalagem_capacidade' in df_work.columns and 'size' in df_work.columns:
        # Criar grupo apenas para SKUs com tipo_embalagem_capacidade válido (não None/nan)
        mask_valid_capacity = (
            df_work['tipo_embalagem_capacidade'].notna() & 
            (df_work['tipo_embalagem_capacidade'] != 'None') &
            (df_work['tipo_embalagem_capacidade'] != 'nan')
        )
        
        # Criar grupo_capacidade apenas para SKUs válidos
        df_work.loc[mask_valid_capacity, 'grupo_capacidade'] = (
            df_work.loc[mask_valid_capacity, 'tipo_embalagem_capacidade'].astype(str) + '|' + 
            df_work.loc[mask_valid_capacity, 'size'].astype(str)
        )
        df_work.loc[~mask_valid_capacity, 'grupo_capacidade'] = None
        
        # Agregar capacidades por grupo (usando min/max globais da classe)
        if 'capacidade_min' in df_work.columns and 'capacidade_max' in df_work.columns:
            # Filtrar apenas grupos válidos
            df_valid = df_work[mask_valid_capacity].copy()
            
            if not df_valid.empty:
                # Agregar: para cada grupo, usar o min/max global (já devem ser iguais, mas usar min/max para garantir)
                capacity_groups = df_valid.groupby('grupo_capacidade').agg({
                    'capacidade_min': 'first',  # Todos os SKUs do mesmo grupo têm o mesmo min
                    'capacidade_max': 'first',  # Todos os SKUs do mesmo grupo têm o mesmo max
                    'volume_projetado': 'sum'   # Somar volumes de todos os SKUs do grupo
                }).reset_index()
                
                # NOTA: As capacidades já foram ajustadas acima (multiplicadas por n_months)
                # Então aqui não precisamos ajustar novamente
                
                # Criar dicionário de restrições (validando compatibilidade)
                for _, row in capacity_groups.iterrows():
                    grupo = row['grupo_capacidade']
                    cap_min = row.get('capacidade_min', 0) if pd.notna(row.get('capacidade_min')) else 0
                    cap_max = row.get('capacidade_max', float('inf')) if pd.notna(row.get('capacidade_max')) else float('inf')
                    volume_proj_grupo = row.get('volume_projetado', 0)
                    
                    # Validar que min <= max
                    if cap_min > cap_max:
                        print(f"[WARNING] Restrição inválida para {grupo}: min ({cap_min:.0f}) > max ({cap_max:.0f}). Ajustando...")
                        cap_min = min(cap_min, cap_max)
                    
                    # Se volume projetado está fora dos limites, ajustar limites ou avisar
                    if volume_proj_grupo > 0:
                        if cap_max < float('inf') and volume_proj_grupo > cap_max * 1.5:
                            print(f"[WARNING] Volume projetado ({volume_proj_grupo:.0f}) muito maior que capacidade máxima ({cap_max:.0f}) para {grupo}")
                        if cap_min > 0 and volume_proj_grupo < cap_min * 0.5:
                            print(f"[WARNING] Volume projetado ({volume_proj_grupo:.0f}) muito menor que capacidade mínima ({cap_min:.0f}) para {grupo}")
                    
                    capacity_constraints[grupo] = {'min': cap_min, 'max': cap_max}
            else:
                print("[WARNING] Nenhum SKU com dados de capacidade válidos para criar restrições")
        else:
            print("[WARNING] Colunas de capacidade não encontradas")
    else:
        # Se não temos tipo_embalagem_capacidade, usar package e size como fallback
        if 'package' in df_work.columns and 'size' in df_work.columns:
            df_work['grupo_capacidade'] = (
                df_work['package'].astype(str) + '|' + 
                df_work['size'].astype(str)
            )
        else:
            df_work['grupo_capacidade'] = None
    
    # 4. Função objetivo: maximizar margem total
    # Variáveis: multiplicadores de volume para cada SKU (0 a 2x do volume projetado)
    n_skus = len(df_work)
    sku_indices = df_work.index.tolist()
    
    def objective(x):
        """
        x: array de multiplicadores de volume (um para cada SKU)
        Retorna: margem total negativa (para minimização)
        """
        volumes_otimizados = df_work['volume_projetado'].values * x
        
        # Calcular margem total
        margem_total = (volumes_otimizados * df_work['margem_unit_esperada'].values).sum()
        
        # Penalizar se violar restrições de capacidade
        penalty = 0.0
        
        if capacity_constraints:
            for grupo, constraints in capacity_constraints.items():
                mask_grupo = df_work['grupo_capacidade'] == grupo
                volume_grupo = volumes_otimizados[mask_grupo].sum()
                
                # Penalidade por violar mínimo
                if volume_grupo < constraints['min']:
                    penalty += (constraints['min'] - volume_grupo) * 1e6
                
                # Penalidade por violar máximo
                if volume_grupo > constraints['max']:
                    penalty += (volume_grupo - constraints['max']) * 1e6
        
        return -(margem_total - penalty)
    
    # 5. Restrições
    constraints_list = []
    
    # Restrições de capacidade por grupo (apenas se forem compatíveis)
    if capacity_constraints:
        for grupo, constraints in capacity_constraints.items():
            mask_grupo = df_work['grupo_capacidade'] == grupo
            indices_grupo = [i for i, idx in enumerate(sku_indices) if df_work.loc[idx, 'grupo_capacidade'] == grupo]
            
            if not indices_grupo:
                continue
            
            # Calcular volume projetado mínimo e máximo possível do grupo
            volumes_proj = df_work.iloc[indices_grupo]['volume_projetado'].values
            vol_min_possivel = volumes_proj.sum() * 0.1  # 10% do projetado
            vol_max_possivel = volumes_proj.sum() * 2.0  # 200% do projetado
            
            cap_min = constraints['min']
            cap_max = constraints['max']
            
            # Validar compatibilidade das restrições
            if cap_min > 0 and cap_min > vol_max_possivel:
                print(f"[WARNING] Capacidade mínima ({cap_min:.0f}) maior que máximo possível ({vol_max_possivel:.0f}) para {grupo}. Ignorando restrição mínima.")
                cap_min = 0
            
            if cap_max < float('inf') and cap_max < vol_min_possivel:
                print(f"[WARNING] Capacidade máxima ({cap_max:.0f}) menor que mínimo possível ({vol_min_possivel:.0f}) para {grupo}. Ajustando para {vol_max_possivel:.0f}.")
                cap_max = vol_max_possivel
            
            if cap_min >= cap_max:
                print(f"[WARNING] Restrições incompatíveis para {grupo}: min ({cap_min:.0f}) >= max ({cap_max:.0f}). Ignorando restrições deste grupo.")
                continue
            
            # Adicionar restrições apenas se forem válidas
            if cap_min > 0 and cap_min < vol_max_possivel:
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda x, idxs=indices_grupo, vmin=cap_min, vols=volumes_proj: 
                        sum(vols * x[idxs]) - vmin
                })
            
            if cap_max < float('inf') and cap_max > vol_min_possivel:
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda x, idxs=indices_grupo, vmax=cap_max, vols=volumes_proj: 
                        vmax - sum(vols * x[idxs])
                })
    
    # 6. Limites: multiplicadores entre 0.1 e 2.0 (10% a 200% do volume projetado)
    # Validar que temos SKUs suficientes
    if n_skus == 0:
        print("[ERROR] Nenhum SKU válido para otimização")
        return None
    
    bounds = [(0.1, 2.0) for _ in range(n_skus)]
    
    # 7. Ponto inicial: usar 1.0 (volume projetado original)
    x0 = np.ones(n_skus)
    
    # Validar que x0 está dentro dos bounds
    for i in range(n_skus):
        if x0[i] < bounds[i][0] or x0[i] > bounds[i][1]:
            x0[i] = (bounds[i][0] + bounds[i][1]) / 2
    
    # 8. Otimização
    try:
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list,
            options={'maxiter': max_iterations, 'disp': False}
        )
        
        if not result.success:
            print(f"[WARNING] Otimização não convergiu: {result.message}")
            print("[INFO] Tentando otimização sem restrições de capacidade...")
            
            # Tentar novamente sem restrições de capacidade se falhar
            try:
                result_relaxed = minimize(
                    objective,
                    x0,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=[],  # Sem restrições
                    options={'maxiter': max_iterations, 'disp': False}
                )
                
                if result_relaxed.success:
                    print("[INFO] Otimização sem restrições convergiu. Usando esta solução.")
                    result = result_relaxed
                else:
                    print(f"[WARNING] Otimização sem restrições também falhou: {result_relaxed.message}")
                    # Usar solução mesmo assim se houver
                    if result.x is None:
                        return None
            except Exception as e:
                print(f"[WARNING] Erro ao tentar otimização sem restrições: {e}")
                # Usar solução mesmo assim se houver
                if result.x is None:
                    return None
        
        # 9. Aplicar volumes otimizados
        df_result = df_work.copy()
        df_result['volume_otimizado'] = df_result['volume_projetado'].values * result.x
        df_result['multiplicador_volume'] = result.x
        
        # Preservar colunas de capacidade se existirem
        if 'capacidade_min' in df_work.columns:
            df_result['capacidade_min'] = df_work['capacidade_min'].values
        if 'capacidade_max' in df_work.columns:
            df_result['capacidade_max'] = df_work['capacidade_max'].values
        if 'grupo_capacidade' in df_work.columns:
            df_result['grupo_capacidade'] = df_work['grupo_capacidade'].values
        
        # Recalcular P&L com volumes otimizados
        df_result['receita_total_otimizada'] = (
            df_result['volume_otimizado'] * df_result['preco_unit_esperado']
        )
        df_result['margem_total_otimizada'] = (
            df_result['volume_otimizado'] * df_result['margem_unit_esperada']
        )
        
        # Métricas de otimização
        metrics = {
            'margem_total_antes': (df_work['volume_projetado'] * df_work['margem_unit_esperada']).sum(),
            'margem_total_depois': df_result['margem_total_otimizada'].sum(),
            'volume_total_antes': df_work['volume_projetado'].sum(),
            'volume_total_depois': df_result['volume_otimizado'].sum(),
            'melhoria_margem_pct': (
                (df_result['margem_total_otimizada'].sum() - 
                 (df_work['volume_projetado'] * df_work['margem_unit_esperada']).sum()) /
                (df_work['volume_projetado'] * df_work['margem_unit_esperada']).sum() * 100
            ) if (df_work['volume_projetado'] * df_work['margem_unit_esperada']).sum() > 0 else 0,
            'violacoes_capacidade': 0
        }
        
        # Verificar violações de capacidade
        if capacity_constraints:
            for grupo, constraints in capacity_constraints.items():
                mask_grupo = df_result['grupo_capacidade'] == grupo
                volume_grupo = df_result.loc[mask_grupo, 'volume_otimizado'].sum()
                
                if volume_grupo < constraints['min'] or volume_grupo > constraints['max']:
                    metrics['violacoes_capacidade'] += 1
        
        df_result.attrs['optimization_metrics'] = metrics
        
        return df_result
        
    except Exception as e:
        print(f"[ERROR] Erro na otimização de mix: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# MOTOR DE SIMULAÇÃO P&L
# ============================================================================
def run_pnl_simulation(base_df, price_adj_pct=0.0, shocks_pct={}):
    """
    Roda o simulador de P&L com a regra de concentrate como % da receita.
    Preserva todas as colunas do DataFrame base, incluindo capacidades.
    """
    df_sim = base_df.copy()
    
    # Garantir que colunas de capacidade sejam preservadas se existirem
    # (já são preservadas pelo .copy(), mas garantimos explicitamente)
    
    # 1. Simular Preço
    df_sim['preco_liquido_simulado_unit'] = df_sim['base_preco_liquido_unit'].fillna(0) * (1 + price_adj_pct)
    
    # 2. Simular Volume (Elasticidade)
    df_sim['variacao_preco_pct'] = 0.0
    mask_preco_valido = df_sim['base_preco_liquido_unit'] != 0
    df_sim.loc[mask_preco_valido, 'variacao_preco_pct'] = (
        df_sim.loc[mask_preco_valido, 'preco_liquido_simulado_unit'] / 
        df_sim.loc[mask_preco_valido, 'base_preco_liquido_unit']
    ) - 1
    
    df_sim['variacao_volume_pct'] = df_sim['variacao_preco_pct'] * df_sim['elasticidade']
    df_sim['volume_simulado'] = df_sim['volume_projetado'] * (1 + df_sim['variacao_volume_pct'])

    # 3. Simular Custos Unitários
    df_sim['custo_total_base_unit'] = df_sim['base_preco_liquido_unit'] - df_sim['base_margem_variavel_unit']
    
    # Concentrate (% da Receita)
    df_sim['perc_concentrate_base'] = 0.0
    df_sim.loc[mask_preco_valido, 'perc_concentrate_base'] = (
        df_sim.loc[mask_preco_valido, 'base_cvv_concentrate_unit'].fillna(0) / 
        df_sim.loc[mask_preco_valido, 'base_preco_liquido_unit']
    )
    shock_conc_pct = shocks_pct.get('cvv_concentrate', 0.0)
    df_sim['perc_concentrate_simulado'] = df_sim['perc_concentrate_base'] * (1 + shock_conc_pct)
    df_sim['cvv_concentrate_simulado_unit'] = df_sim['preco_liquido_simulado_unit'] * df_sim['perc_concentrate_simulado']
    
    # Outros custos
    df_sim['outros_custos_unit'] = df_sim['custo_total_base_unit']
    for col in COST_BUCKETS_BASE_COLS:
        df_sim['outros_custos_unit'] -= df_sim[col].fillna(0)

    df_sim['custo_total_simulado_unit'] = df_sim['outros_custos_unit'] + df_sim['cvv_concentrate_simulado_unit']

    standard_drivers = [c for c in COST_DRIVERS_SLIDERS if c != 'cvv_concentrate']
    
    for driver_key in standard_drivers: 
        base_cost_col = f'base_{driver_key}_unit'
        shock_pct = shocks_pct.get(driver_key, 0.0)
        sim_cost_col = f'{driver_key}_simulado_unit'
        
        df_sim[sim_cost_col] = df_sim[base_cost_col].fillna(0) * (1 + shock_pct)
        df_sim['custo_total_simulado_unit'] += df_sim[sim_cost_col] 

    # 4. Calcular P&L Simulado
    df_sim['margem_simulada_unit'] = (
        df_sim['preco_liquido_simulado_unit'] - df_sim['custo_total_simulado_unit']
    )
    
    # 5. Calcular Totais
    df_sim['receita_total_simulada'] = df_sim['volume_simulado'] * df_sim['preco_liquido_simulado_unit']
    df_sim['margem_total_simulada'] = df_sim['volume_simulado'] * df_sim['margem_simulada_unit']
    
    return df_sim

# ============================================================================
# OTIMIZAÇÃO
# ============================================================================
def calculate_profitability(df_sim):
    """Calcula a lucratividade total (margem total) de um cenário simulado."""
    if df_sim.empty:
        return 0.0
    return df_sim['margem_total_simulada'].sum()

def optimize_profitability(df_base, price_range=(-0.2, 0.2), cost_ranges=None):
    """Otimização usando scipy.optimize.differential_evolution."""
    if df_base.empty:
        return None
    
    def objective(x):
        price_adj = x[0]
        shocks = {COST_DRIVERS_SLIDERS[i]: x[i+1] for i in range(len(COST_DRIVERS_SLIDERS))}
        
        df_sim = run_pnl_simulation(df_base, price_adj_pct=price_adj, shocks_pct=shocks)
        profit = calculate_profitability(df_sim)
        
        return -profit
    
    if cost_ranges is None:
        cost_ranges = {driver: (-0.5, 0.5) for driver in COST_DRIVERS_SLIDERS}
    
    bounds = [price_range] + [cost_ranges.get(driver, (-0.5, 0.5)) for driver in COST_DRIVERS_SLIDERS]
    
    print("[INFO] Iniciando otimização com Differential Evolution...")
    
    try:
        result = differential_evolution(
            objective,
            bounds,
            maxiter=100,
            popsize=15,
            seed=42,
            polish=True,
            workers=1
        )
        
        optimal_price = result.x[0]
        optimal_shocks = {COST_DRIVERS_SLIDERS[i]: result.x[i+1] for i in range(len(COST_DRIVERS_SLIDERS))}
        
        df_optimal = run_pnl_simulation(df_base, price_adj_pct=optimal_price, shocks_pct=optimal_shocks)
        optimal_summary = summarize_pnl_df(df_optimal, "Ótimo")
        mix_analysis = analyze_product_mix(df_optimal)
        
        print(f"[INFO] Otimização concluída. Lucratividade ótima: R$ {-result.fun:,.2f}")
        
        return {
            'params': {
                'price_adj': optimal_price,
                'shocks': optimal_shocks
            },
            'profit': -result.fun,
            'summary': optimal_summary,
            'df_optimal': df_optimal,
            'mix_analysis': mix_analysis
        }
    except Exception as e:
        print(f"[ERROR] Erro na otimização: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO CORPORATIVA
# ============================================================================
def summarize_pnl_df(df, scenario_name):
    """Resume os TOTAIS de um dataframe de simulação."""
    if df.empty:
        return pd.Series({'Cenário': scenario_name, 'Receita Total': 0, 'Margem Total': 0, 'Volume Total': 0, 'Margem %': 0})
        
    total_receita = df['receita_total_simulada'].sum()
    total_margem = df['margem_total_simulada'].sum()
    total_volume = df['volume_simulado'].sum()
    margem_pct = (total_margem / total_receita) if total_receita != 0 else 0
    
    return pd.Series({
        'Cenário': scenario_name,
        'Receita Total': total_receita,
        'Margem Total': total_margem,
        'Volume Total': total_volume,
        'Margem %': margem_pct
    })

def create_export_button(table_id, filename):
    """Cria um botão de exportação para uma tabela."""
    return html.Button(
        "📥 Exportar para Excel",
        id=f"btn-export-{table_id}",
        n_clicks=0,
        style={
            "backgroundColor": COLORS['success'],
            "color": COLORS['accent'],
            "border": "none",
            "padding": "8px 16px",
            "borderRadius": "4px",
            "fontSize": "12px",
            "fontWeight": "600",
            "cursor": "pointer",
            "marginBottom": "12px"
        }
    )

def build_kpi_card(title, value, subtitle="", color=COLORS['primary']):
    """Cria um card KPI corporativo."""
    return html.Div([
        html.Div([
            html.H4(title, style={
                "margin": "0",
                "color": COLORS['gray_dark'],
                "fontSize": "12px",
                "fontWeight": "600",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px"
            }),
            html.H2(value, style={
                "margin": "8px 0 4px 0",
                "color": color,
                "fontSize": "28px",
                "fontWeight": "700"
            }),
            html.P(subtitle, style={
                "margin": "0",
                "color": COLORS['gray_medium'],
                "fontSize": "11px"
            }) if subtitle else html.Div()
        ], style={
            "padding": "20px",
            "backgroundColor": COLORS['accent'],
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
        })
    ])

def build_big_numbers_card(optimal_result):
    """Cria cards com big numbers do cenário ótimo - estilo corporativo."""
    if optimal_result is None:
        return html.Div([
            html.H3("Cenário Ótimo", style={"textAlign": "center", "color": COLORS['gray_medium']}),
            html.P("Execute a otimização para ver os resultados", style={"textAlign": "center", "color": COLORS['gray_medium']})
        ])
    
    summary = optimal_result['summary']
    # Converter summary para dict se for Series
    if isinstance(summary, pd.Series):
        summary = summary.to_dict()
    params = optimal_result['params']
    
    return html.Div([
        html.Div([
            html.H3("Cenário Ótimo de Lucratividade", style={
                "textAlign": "left",
                "color": COLORS['secondary'],
                "marginBottom": "24px",
                "fontSize": "20px",
                "fontWeight": "700",
                "borderBottom": f"3px solid {COLORS['primary']}",
                "paddingBottom": "12px"
            }),
            html.Div([
                build_kpi_card(
                    "Receita Total",
                    f"R$ {summary['Receita Total']:,.0f}",
                    "Receita projetada no cenário ótimo",
                    COLORS['primary']
                ),
                build_kpi_card(
                    "Margem Total",
                    f"R$ {summary['Margem Total']:,.0f}",
                    f"Margem de {summary['Margem %']:.2%}",
                    COLORS['success']
                ),
                build_kpi_card(
                    "Volume Total",
                    f"{summary['Volume Total']:,.0f} UC",
                    "Volume total projetado",
                    COLORS['gray_dark']
                ),
                build_kpi_card(
                    "Margem Percentual",
                    f"{summary['Margem %']:.2%}",
                    "Percentual de margem",
                    COLORS['primary_dark']
                ),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gap": "16px",
                "marginBottom": "24px"
            }),
            html.Div([
                html.H5("Parâmetros Ótimos Aplicados", style={
                    "marginBottom": "12px",
                    "color": COLORS['secondary'],
                    "fontSize": "14px",
                    "fontWeight": "600"
                }),
                html.Div([
                    html.P(f"Choque de Preço: {params['price_adj']:.2%}", style={
                        "margin": "4px 0",
                        "fontSize": "13px",
                        "color": COLORS['gray_dark']
                    }),
                ] + [
                    html.P(f"{PRETTY.get(driver, driver)}: {params['shocks'][driver]:.2%}", 
                          style={"margin": "4px 0", "fontSize": "13px", "color": COLORS['gray_dark']})
                    for driver in COST_DRIVERS_SLIDERS
                ], style={
                    "backgroundColor": COLORS['background'],
                    "padding": "16px",
                    "borderRadius": "4px",
                    "border": f"1px solid {COLORS['gray_light']}"
                })
            ])
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "32px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)"
        })
    ])

def build_pnl_total_fig(df_base, df_sim, df_proj=None):
    """Cria o gráfico de barras agrupadas para P&L Total - estilo corporativo."""
    base = summarize_pnl_df(df_base, "Cenário Base")
    sim = summarize_pnl_df(df_sim, "Cenário Simulado")
    
    x_labels = ['Cenário Base', 'Cenário Simulado']
    receita_vals = [base['Receita Total'], sim['Receita Total']]
    margem_vals = [base['Margem Total'], sim['Margem Total']]
    receita_text = [f"R$ {base['Receita Total']:,.0f}", f"R$ {sim['Receita Total']:,.0f}"]
    margem_text = [f"R$ {base['Margem Total']:,.0f}", f"R$ {sim['Margem Total']:,.0f}"]
    
    if df_proj is not None:
        proj = summarize_pnl_df(df_proj, "Cenário Projetado")
        x_labels.append('Cenário Projetado')
        receita_vals.append(proj['Receita Total'])
        margem_vals.append(proj['Margem Total'])
        receita_text.append(f"R$ {proj['Receita Total']:,.0f}")
        margem_text.append(f"R$ {proj['Margem Total']:,.0f}")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels, y=receita_vals,
        name='Receita Total', marker_color=COLORS['primary'],
        text=receita_text,
        textposition='auto', textfont_size=14
    ))
    fig.add_trace(go.Bar(
        x=x_labels, y=margem_vals,
        name='Margem Total', marker_color=COLORS['success'],
        text=margem_text,
        textposition='auto', textfont_size=14
    ))
    title = "<b>P&L Total Projetado (Baseline vs. Simulado vs. Projetado)</b>" if df_proj is not None else "<b>P&L Total Projetado (Baseline vs. Simulado)</b>"
    fig.update_layout(
        title_text=title,
        yaxis_title="Valor (R$)", barmode='group', plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    return fig

def build_cost_driver_fig(pu_base, pu_sim, pu_proj=None):
    """Cria o gráfico de barras empilhadas de Custo Unitário (R$/UC) - estilo corporativo."""
    fig = go.Figure()
    
    if pu_base is None:
        return fig.update_layout(title="Sem dados para o filtro selecionado.")
        
    order = COST_DRIVERS_SLIDERS
    
    # Calcular totais para rótulos
    total_base = sum([pu_base.get(k, 0.0) for k in order])
    total_sim = sum([pu_sim.get(k, 0.0) for k in order]) if pu_sim is not None else None
    total_proj = sum([pu_proj.get(k, 0.0) for k in order]) if pu_proj is not None else None
    
    # Barras do Baseline
    for k in order:
        val_base = pu_base.get(k, 0.0)
        fig.add_bar(
            x=["Baseline"], y=[val_base],
            name=PRETTY.get(k, k),
            legendgroup=k,
            showlegend=False,
            marker_color=COLOR_DRIVERS.get(k, COLORS['gray_medium']),
            hovertemplate=PRETTY.get(k, k) + " — Baseline: R$%{y:.4f}/UC<extra></extra>"
        )
    
    # Adicionar rótulo do total no Baseline (apenas no último segmento)
    if total_base > 0:
        fig.add_annotation(
            x="Baseline",
            y=total_base,
            text=f"R$ {total_base:.4f}",
            showarrow=False,
            font=dict(size=12, color=COLORS['secondary']),
            yshift=15
        )
    
    # Barras do Simulado
    if pu_sim is not None:
        for k in order:
            val_sim = pu_sim.get(k, 0.0)
            fig.add_bar(
                x=["Simulado"], y=[val_sim],
                name=PRETTY.get(k, k),
                legendgroup=k,
                showlegend=False,
                marker_color=COLOR_DRIVERS.get(k, COLORS['gray_medium']), 
                hovertemplate=PRETTY.get(k, k) + " — Simulado: R$%{y:.4f}/UC<extra></extra>"
            )
        
        # Adicionar rótulo do total no Simulado
        if total_sim is not None and total_sim > 0:
            fig.add_annotation(
                x="Simulado",
                y=total_sim,
                text=f"R$ {total_sim:.4f}",
                showarrow=False,
                font=dict(size=12, color=COLORS['secondary']),
                yshift=15
            )
    
    # Barras do Projetado
    if pu_proj is not None:
        for k in order:
            val_proj = pu_proj.get(k, 0.0)
            fig.add_bar(
                x=["Projetado"], y=[val_proj],
                name=PRETTY.get(k, k),
                legendgroup=k,
                showlegend=False,
                marker_color=COLOR_DRIVERS.get(k, COLORS['gray_medium']), 
                hovertemplate=PRETTY.get(k, k) + " — Projetado: R$%{y:.4f}/UC<extra></extra>"
            )
        
        # Adicionar rótulo do total no Projetado
        if total_proj is not None and total_proj > 0:
            fig.add_annotation(
                x="Projetado",
                y=total_proj,
                text=f"R$ {total_proj:.4f}",
                showarrow=False,
                font=dict(size=12, color=COLORS['secondary']),
                yshift=15
            )

    title = "<b>Custo por Unidade (R$/UC) – Drivers de Custo (3 Cenários)</b>" if pu_proj is not None else "<b>Custo por Unidade (R$/UC) – Drivers de Custo</b>"
    fig.update_layout(
        barmode="stack",
        height=450,
        title=title,
        xaxis_title="Cenário",
        yaxis_title="R$/UC",
        plot_bgcolor="white",
        bargap=0.45,
        showlegend=False,
        margin=dict(l=60, r=20, t=50, b=50)
    )
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    return fig

def build_mix_analysis_fig(mix_analysis):
    """Cria gráficos de análise de mix de produtos."""
    if mix_analysis is None:
        return go.Figure()
    
    # Determinar número de subplots baseado nos dados disponíveis
    num_plots = 0
    if 'por_marca' in mix_analysis:
        num_plots += 1
    if 'por_embalagem' in mix_analysis:
        num_plots += 1
    if 'top_skus' in mix_analysis:
        num_plots += 1
    
    if num_plots == 0:
        return go.Figure()
    
    cols = min(3, num_plots)
    rows = (num_plots + cols - 1) // cols
    
    subplot_titles = []
    if 'por_marca' in mix_analysis:
        subplot_titles.append('Participação por Marca')
    if 'por_embalagem' in mix_analysis:
        subplot_titles.append('Volume vs Capacidade')
    if 'top_skus' in mix_analysis:
        subplot_titles.append('Top 10 SKUs por Margem')
    
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=subplot_titles,
        specs=[[{"type": "bar"}] * cols] * rows
    )
    
    plot_idx = 1
    
    # Gráfico 1: Participação por marca
    if 'por_marca' in mix_analysis:
        df_marca = mix_analysis['por_marca']
        row = (plot_idx - 1) // cols + 1
        col = (plot_idx - 1) % cols + 1
        fig.add_trace(
            go.Bar(
                x=df_marca['brand'],
                y=df_marca['participacao_receita'],
                name='Participação Receita',
                marker_color=COLORS['primary'],
                showlegend=False
            ),
            row=row, col=col
        )
        plot_idx += 1
    
    # Gráfico 2: Volume vs Capacidade por Embalagem (com comparativo de demanda e atendimento)
    if 'por_embalagem' in mix_analysis:
        df_pkg = mix_analysis['por_embalagem']
        row = (plot_idx - 1) // cols + 1
        col = (plot_idx - 1) % cols + 1
        
        # Calcular nível de atendimento (%)
        # IMPORTANTE: Usar volume_demanda (demanda original) como base, não volume_projetado que pode estar agregado
        # Validar se a demanda não é muito pequena (pode indicar erro de agregação)
        if 'volume_demanda' in df_pkg.columns and 'volume_simulado' in df_pkg.columns:
            # Validar: se volume_demanda muito menor que volume_simulado, pode ser erro de agregação
            # Limitar atendimento a máximo de 150% (razoável para redistribuição)
            df_pkg['atendimento_pct'] = np.where(
                df_pkg['volume_demanda'] > 0,
                np.minimum((df_pkg['volume_simulado'] / df_pkg['volume_demanda']) * 100, 150),
                0
            )
            # Se ainda assim for muito alto, pode ser erro - marcar como suspeito
            mask_suspeito = df_pkg['atendimento_pct'] > 150
            if mask_suspeito.any():
                print(f"[WARNING] Atendimento > 150% detectado para alguns packages. Verificando agregação...")
                for idx in df_pkg[mask_suspeito].index:
                    pkg = df_pkg.loc[idx, 'package']
                    demanda = df_pkg.loc[idx, 'volume_demanda']
                    simulado = df_pkg.loc[idx, 'volume_simulado']
                    print(f"  {pkg}: demanda={demanda:,.0f}, simulado={simulado:,.0f}, atendimento={(simulado/demanda*100) if demanda > 0 else 0:.1f}%")
        elif 'volume_projetado' in df_pkg.columns and 'volume_simulado' in df_pkg.columns:
            # Validar: se volume_projetado muito menor que volume_simulado, pode ser erro
            # Limitar atendimento a máximo de 150% (razoável para redistribuição)
            df_pkg['atendimento_pct'] = np.where(
                df_pkg['volume_projetado'] > 0,
                np.minimum((df_pkg['volume_simulado'] / df_pkg['volume_projetado']) * 100, 150),
                0
            )
        else:
            df_pkg['atendimento_pct'] = 0
        
        # Determinar cor baseada em atendimento e capacidade
        def get_bar_color(row):
            if pd.isna(row.get('atendimento_pct', 0)) or row.get('atendimento_pct', 0) == 0:
                return COLORS['gray_medium']
            
            atendimento = row.get('atendimento_pct', 0)
            dentro_cap = row.get('dentro_capacidade', None)
            
            # Se está dentro da capacidade
            if dentro_cap == True:
                if atendimento >= 95:
                    return COLORS['success']  # Verde: atendimento excelente
                elif atendimento >= 80:
                    return '#90EE90'  # Verde claro: atendimento bom
                elif atendimento >= 60:
                    return COLORS['warning']  # Amarelo: atendimento moderado
                else:
                    return '#FF6B6B'  # Vermelho claro: atendimento baixo
            # Se está abaixo do mínimo
            elif dentro_cap == False and 'capacidade_min' in row and not pd.isna(row.get('capacidade_min')):
                if row.get('volume_simulado', 0) < row.get('capacidade_min', 0):
                    return '#FF6B6B'  # Vermelho: abaixo do mínimo
                else:
                    return '#FFA500'  # Laranja: acima do máximo
            # Se não tem informação de capacidade
            else:
                if atendimento >= 80:
                    return COLORS['primary']  # Azul: sem info mas atendimento bom
                else:
                    return COLORS['gray_medium']  # Cinza: sem info
        
        # Aplicar cores
        df_pkg['bar_color'] = df_pkg.apply(get_bar_color, axis=1)
        
        # Volume simulado (demanda atendida)
        fig.add_trace(
            go.Bar(
                x=df_pkg['package'],
                y=df_pkg['volume_simulado'],
                name='Volume Otimizado',
                marker_color=df_pkg['bar_color'],
                showlegend=(plot_idx == 2),
                text=[f"{row.get('atendimento_pct', 0):.1f}%" if not pd.isna(row.get('atendimento_pct', 0)) else "" 
                      for _, row in df_pkg.iterrows()],
                textposition='outside',
                textfont=dict(size=10, color=COLORS['gray_dark'])
            ),
            row=row, col=col
        )
        
        # Demanda do mercado (se disponível)
        if 'volume_demanda' in df_pkg.columns:
            fig.add_trace(
                go.Bar(
                    x=df_pkg['package'],
                    y=df_pkg['volume_demanda'],
                    name='Demanda Mercado',
                    marker_color=COLORS['gray_medium'],
                    opacity=0.3,
                    showlegend=(plot_idx == 2)
                ),
                row=row, col=col
            )
        elif 'volume_projetado' in df_pkg.columns:
            fig.add_trace(
                go.Bar(
                    x=df_pkg['package'],
                    y=df_pkg['volume_projetado'],
                    name='Demanda Mercado',
                    marker_color=COLORS['gray_medium'],
                    opacity=0.3,
                    showlegend=(plot_idx == 2)
                ),
                row=row, col=col
            )
        
        # Capacidade máxima
        if 'capacidade_max' in df_pkg.columns:
            fig.add_trace(
                go.Bar(
                    x=df_pkg['package'],
                    y=df_pkg['capacidade_max'],
                    name='Capacidade Máx',
                    marker_color='#E0E0E0',
                    opacity=0.4,
                    marker_line=dict(color='#999', width=1),
                    showlegend=(plot_idx == 2)
                ),
                row=row, col=col
            )
        
        # Capacidade mínima (linha)
        if 'capacidade_min' in df_pkg.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_pkg['package'],
                    y=df_pkg['capacidade_min'],
                    mode='lines+markers',
                    name='Capacidade Mín',
                    line=dict(color='#FF6B6B', width=2, dash='dash'),
                    marker=dict(symbol='diamond', size=8),
                    showlegend=(plot_idx == 2)
                ),
                row=row, col=col
            )
        
        plot_idx += 1
    
    # Gráfico 3: Top SKUs
    if 'top_skus' in mix_analysis:
        df_top = mix_analysis['top_skus']
        row = (plot_idx - 1) // cols + 1
        col = (plot_idx - 1) % cols + 1
        
        # Truncar nomes de SKU para visualização
        df_top['sku_short'] = df_top['chave_sku'].str[:30] + '...'
        
        fig.add_trace(
            go.Bar(
                x=df_top['sku_short'],
                y=df_top['margem_total_simulada'],
                name='Margem Total',
                marker_color=COLORS['success'],
                showlegend=False
            ),
            row=row, col=col
        )
        plot_idx += 1
    
    fig.update_layout(
        title=dict(
            text="Análise de Mix de Produtos",
            font=dict(size=16, color=COLORS['secondary']),
            x=0.5
        ),
        height=400 * rows,
        plot_bgcolor=COLORS['accent'],
        paper_bgcolor=COLORS['accent'],
        font=dict(color=COLORS['gray_dark'], size=12),
        barmode='group' if 'por_embalagem' in mix_analysis else 'stack'
    )
    
    return fig

def calculate_average_pu(df_base, df_sim, df_proj=None):
    """Calcula o P&L Unitário (R$/UC) MÉDIO PONDERADO."""
    
    # Verificar e tratar valores None/NaN
    if df_base.empty or 'volume_projetado' not in df_base.columns:
        return None, None, None
    
    vol_base = df_base['volume_projetado'].fillna(0).sum()
    if vol_base == 0 or pd.isna(vol_base):
        return None, None, None
        
    pu_base = {}
    pu_base['rev_total'] = (df_base['volume_projetado'].fillna(0) * df_base['base_preco_liquido_unit'].fillna(0)).sum() / vol_base
    for col_key in COST_DRIVERS_SLIDERS:
        col_base_name = f"base_{col_key}_unit"
        if col_base_name in df_base.columns:
            pu_base[col_key] = (df_base['volume_projetado'].fillna(0) * df_base[col_base_name].fillna(0)).sum() / vol_base
        else:
            pu_base[col_key] = 0
    pu_base['var_margin'] = pu_base['rev_total'] - sum(pu_base.get(c, 0) for c in COST_DRIVERS_SLIDERS)

    if df_sim.empty or 'volume_simulado' not in df_sim.columns:
        return pu_base, None, None
    
    vol_sim = df_sim['volume_simulado'].fillna(0).sum()
    pu_sim = None
    if vol_sim > 0 and not pd.isna(vol_sim):
        pu_sim = {}
        pu_sim['rev_total'] = (df_sim['volume_simulado'].fillna(0) * df_sim['preco_liquido_simulado_unit'].fillna(0)).sum() / vol_sim
        for col_key in COST_DRIVERS_SLIDERS:
            sim_col_name = f'{col_key}_simulado_unit'
            if sim_col_name in df_sim.columns:
                pu_sim[col_key] = (df_sim['volume_simulado'].fillna(0) * df_sim[sim_col_name].fillna(0)).sum() / vol_sim
            else:
                pu_sim[col_key] = 0
        pu_sim['var_margin'] = pu_sim['rev_total'] - sum(pu_sim.get(c, 0) for c in COST_DRIVERS_SLIDERS)
    
    pu_proj = None
    if df_proj is not None and not df_proj.empty and 'volume_projetado' in df_proj.columns:
        vol_proj = df_proj['volume_projetado'].fillna(0).sum()
        if vol_proj > 0 and not pd.isna(vol_proj):
            pu_proj = {}
            pu_proj['rev_total'] = (df_proj['volume_projetado'].fillna(0) * df_proj['base_preco_liquido_unit'].fillna(0)).sum() / vol_proj
            for col_key in COST_DRIVERS_SLIDERS:
                col_base_name = f"base_{col_key}_unit"
                if col_base_name in df_proj.columns:
                    pu_proj[col_key] = (df_proj['volume_projetado'].fillna(0) * df_proj[col_base_name].fillna(0)).sum() / vol_proj
                else:
                    pu_proj[col_key] = 0
            pu_proj['var_margin'] = pu_proj['rev_total'] - sum(pu_proj.get(c, 0) for c in COST_DRIVERS_SLIDERS)

    return pu_base, pu_sim, pu_proj

# ============================================================================
# FUNÇÕES DE DE-PARA E CARREGAMENTO DE DADOS
# ============================================================================
def map_item_to_driver(item_name):
    """Mapeia item de matéria-prima para driver de custo."""
    if not item_name or pd.isna(item_name):
        return None
    
    item_lower = str(item_name).lower().strip()
    
    if 'lata' in item_lower:
        return 'cvv_can'
    elif 'garrafa pet' in item_lower:
        return 'cvv_pet'
    elif 'garrafa owg' in item_lower or ('owg' in item_lower and 'garrafa' in item_lower):
        return 'cvv_pet'
    elif 'tampa' in item_lower:
        return 'cvv_cap'
    elif 'açúcar' in item_lower or 'acucar' in item_lower:
        return 'cvv_sweetener'
    elif 'bag' in item_lower:
        return 'cvv_purcharses'
    elif 'papelão' in item_lower or 'bib' in item_lower:
        return 'cvv_purcharses'
    
    return None

def load_mp_yoy_percentages(file_path):
    """Carrega percentuais YoY do arquivo de matéria-prima."""
    if not os.path.exists(file_path):
        print(f"[WARNING] Arquivo de matéria-prima não encontrado: {file_path}")
        return None
    
    try:
        df = pd.read_excel(file_path, header=0)
        
        if 'ITEM' not in df.columns:
            print("[WARNING] Coluna 'ITEM' não encontrada no arquivo")
            return None
        
        yoy_columns = []
        month_map = {
            'JAN': 1, 'FEB': 2, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'APR': 4,
            'MAI': 5, 'MAY': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8, 'AUG': 8,
            'SET': 9, 'SEP': 9, 'OUT': 10, 'OCT': 10, 'NOV': 11, 'DEZ': 12, 'DEC': 12
        }
        
        for i, col in enumerate(df.columns):
            col_str = str(col).upper().strip()
            for month_name, month_num in month_map.items():
                if month_name in col_str and ('25' in col_str or '2025' in col_str):
                    date_val = pd.to_datetime(f'2025-{month_num:02d}-01')
                    yoy_columns.append((col, date_val, i))
                    break
        
        if not yoy_columns:
            for i, col in enumerate(df.columns):
                if i >= 3 and i <= 14:
                    try:
                        date_val = pd.to_datetime(col)
                        yoy_columns.append((col, date_val, i))
                    except (ValueError, TypeError):
                        pass
        
        if not yoy_columns:
            return None
        
        results = []
        for idx, row in df.iterrows():
            item_name = row['ITEM']
            
            if pd.isna(item_name) or str(item_name).strip() == '':
                continue
            
            driver = map_item_to_driver(item_name)
            if driver is None:
                continue
            
            for col_name, date_val, col_idx in yoy_columns:
                pct_val = row.iloc[col_idx]
                if pd.notna(pct_val):
                    try:
                        pct = float(pct_val)
                        if abs(pct) > 1 and abs(pct) <= 100:
                            pct = pct / 100
                        
                        results.append({
                            'driver': driver,
                            'month': to_month(date_val),
                            'yoy_pct': pct,
                            'item': str(item_name)
                        })
                    except (ValueError, TypeError):
                        pass
        
        if not results:
            return None
        
        df_yoy = pd.DataFrame(results)
        df_yoy_agg = df_yoy.groupby(['driver', 'month'])['yoy_pct'].mean().reset_index()
        
        return df_yoy_agg
        
    except Exception as e:
        print(f"[WARNING] Erro ao carregar percentuais YoY: {e}")
        return None

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================
if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(
        f"Arquivo '{DATA_FILE}' não encontrado. "
        "Execute o notebook Jupyter para gerar o arquivo CSV primeiro."
    )

print(f"[INFO] Carregando dados base: {DATA_FILE}")
df_master = pd.read_csv(DATA_FILE, decimal=',')
df_master['month'] = to_month(df_master['depara_mess'])

# Carregar dados de capacidades para de-para
df_capacidades = load_capacidades_data(CAPACIDADES_FILE)

# Criar de-para e adicionar capacidades ao master
df_master = create_de_para_mapping(df_master, df_capacidades)
print("[INFO] De-para criado. Capacidades integradas ao master DataFrame.")

# Carregar percentuais YoY
df_mp_yoy = load_mp_yoy_percentages(PROJECAO_MP_FILE)

# Quebrar chave SKU
print("[INFO] Criando colunas de filtro a partir da 'chave_sku'...")
try:
    sku_parts = df_master['chave_sku'].str.split('|', expand=True)
    df_master['brand'] = sku_parts[0]
    df_master['size'] = pd.to_numeric(sku_parts[1], errors='coerce')
    df_master['tipo_consumo'] = sku_parts[2]
    df_master['returnability'] = sku_parts[3]
    df_master['package'] = sku_parts[4]
except Exception as e:
    print(f"Erro ao quebrar a chave_sku: {e}")
    raise

print("[INFO] Dados carregados com sucesso.")

# Preparar listas para filtros
MONTHS = nonempty_unique(df_master["month"])
DIRS = nonempty_unique(df_master["diretoria"])
BRANDS = nonempty_unique(df_master["brand"])
SIZES = nonempty_unique(df_master["size"])
RETS = nonempty_unique(df_master["returnability"])
PACKS = nonempty_unique(df_master["package"])
TIPOS = nonempty_unique(df_master["tipo_consumo"])

# ============================================================================
# LAYOUT CORPORATIVO - ESTILO POWERBI
# ============================================================================
app = Dash(__name__)
app.title = "FEMSA - Simulador de P&L e Otimização"

# CSS Customizado
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #F8F8F8;
            }
            .header {
                background: linear-gradient(135deg, #F40009 0%, #C00007 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
                font-weight: 700;
            }
            .header p {
                margin: 8px 0 0 0;
                font-size: 14px;
                opacity: 0.9;
            }
            .section-title {
                font-size: 16px;
                font-weight: 600;
                color: #1A1A1A;
                margin: 24px 0 16px 0;
                padding-bottom: 8px;
                border-bottom: 2px solid #F40009;
            }
            .card {
                background: white;
                border-radius: 4px;
                border: 1px solid #E5E5E5;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            .input-group {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 12px;
            }
            .input-group label {
                min-width: 200px;
                font-weight: 600;
                color: #4A4A4A;
                font-size: 13px;
            }
            .btn-primary {
                background-color: #F40009;
                color: white;
                border: none;
                padding: 12px 32px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            .btn-primary:hover {
                background-color: #C00007;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    # Header Corporativo
    html.Div([
        html.Div([
            html.Img(
                src=app.get_asset_url("logo-femsa.png"),
                style={
                    "height": "60px",
                    "marginRight": "24px"
                }
            ),
            html.Div([
                html.H1("FEMSA - Simulador de P&L e Otimização de Mix", style={
                    "margin": "0",
                    "fontSize": "24px",
                    "fontWeight": "700"
                }),
                html.P("Plataforma de Análise de Cenários e Otimização de Lucratividade", style={
                    "margin": "8px 0 0 0",
                    "fontSize": "14px",
                    "opacity": "0.9"
                })
            ])
        ], style={"display": "flex", "alignItems": "center"})
    ], style={
        "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%)",
        "color": COLORS['accent'],
        "padding": "24px 40px",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
    }),
    
    # Container Principal
    html.Div([
        # FILTROS - PRIMEIRO (ANTES DE TUDO)
        html.Div([
            html.H3("Filtros de Análise", className="section-title", style={"marginTop": "0"}),
            html.Div([
                html.Div([
                    html.Label("Mês (Projeção)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        options=[{'label': pd.to_datetime(m).strftime('%Y-%m'), 'value': str(m)} for m in MONTHS],
                        value=None, multi=True, id="f-month",
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Diretoria", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(options=DIRS, value=None, multi=True, id="f-dir", style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Marca", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(options=BRANDS, value=None, multi=True, id="f-brand", style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Tamanho (L)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(options=opts(SIZES, fmt=lambda v: f"{float(v):.2f}"), value=None, multi=True, id="f-size", style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Embalagem", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(options=PACKS, value=None, multi=True, id="f-pack", style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block"}),
            ], style={"marginBottom": "24px"})
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        }),
        
        # Seção de Otimização
        html.Div([
            html.Div([
                html.H3("Otimização de Lucratividade", className="section-title", style={
                    "marginTop": "0",
                    "fontSize": "18px",
                    "fontWeight": "700",
                    "color": COLORS['secondary']
                }),
                html.P("Configure os limites de otimização e encontre o ponto ótimo de lucratividade.", style={
                    "color": COLORS['gray_medium'],
                    "fontSize": "13px",
                    "marginBottom": "20px"
                }),
                
                # Configuração de Limites
                html.Div([
                    html.H5("Limites de Otimização", style={
                        "marginBottom": "16px",
                        "color": COLORS['secondary'],
                        "fontSize": "14px",
                        "fontWeight": "600"
                    }),
                    
                    # Preço
                    html.Div([
                        html.Label("Choque de Preço", style={
                            "minWidth": "200px",
                            "fontWeight": "600",
                            "color": COLORS['gray_dark'],
                            "fontSize": "13px"
                        }),
                        html.Label("Mín: ", style={"marginLeft": "10px"}),
                        dcc.Input(id="opt-price-min", type="number", value=-0.2, step=0.01, 
                                 style={"width": "80px", "marginRight": "15px"}),
                        html.Label("Máx: "),
                        dcc.Input(id="opt-price-max", type="number", value=0.2, step=0.01, 
                                 style={"width": "80px"})
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
                    
                    # Drivers de Custo
                    html.Div([
                        html.Div([
                            html.Label(f"{PRETTY.get(driver, driver)}", style={
                                "minWidth": "200px",
                                "fontWeight": "600",
                                "color": COLORS['gray_dark'],
                                "fontSize": "13px"
                            }),
                            html.Label("Mín: ", style={"marginLeft": "10px"}),
                            dcc.Input(id=f"opt-{driver}-min", type="number", value=-0.5, step=0.01, 
                                     style={"width": "80px", "marginRight": "15px"}),
                            html.Label("Máx: "),
                            dcc.Input(id=f"opt-{driver}-max", type="number", value=0.5, step=0.01, 
                                     style={"width": "80px"})
                        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"})
                        for driver in COST_DRIVERS_SLIDERS
                    ]),
                    
                ], style={
                    "backgroundColor": COLORS['background'],
                    "padding": "20px",
                    "borderRadius": "4px",
                    "border": f"1px solid {COLORS['gray_light']}",
                    "marginBottom": "20px"
                }),
                
                html.Div([
                    html.Button("Executar Otimização", id="btn-optimize", n_clicks=0, style={
                        "backgroundColor": COLORS['primary'],
                        "color": COLORS['accent'],
                        "border": "none",
                        "padding": "12px 32px",
                        "borderRadius": "4px",
                        "fontSize": "14px",
                        "fontWeight": "600",
                        "cursor": "pointer",
                        "marginRight": "12px"
                    }),
                    html.A(
                        html.Button("Calcular Mix Ótimo", style={
                            "backgroundColor": COLORS['success'],
                            "color": COLORS['accent'],
                            "border": "none",
                            "padding": "12px 32px",
                            "borderRadius": "4px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "cursor": "pointer"
                        }),
                        href="http://localhost:8051",
                        target="_blank",
                        style={"textDecoration": "none"}
                    )
                ], style={"display": "flex", "alignItems": "center"}),
                html.Div(id="optimization-status", style={"marginTop": "12px", "fontSize": "13px"}),
                html.Div(id="optimization-report", style={"marginTop": "24px"})
            ], style={
                "backgroundColor": COLORS['accent'],
                "padding": "32px",
                "borderRadius": "4px",
                "border": f"1px solid {COLORS['gray_light']}",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                "marginBottom": "24px"
            }),
            
            # Removido: html.Div(id="big-numbers-card")
        ]),
        
        # Controles de Simulação - Layout Horizontal
        html.Div([
            html.H3("Controles de Simulação", className="section-title", style={"marginTop": "0"}),
            
            # Choque de Preço
            html.Div([
                html.Div([
                    html.Label("Choque de Preço", style={
                        "fontSize": "13px",
                        "fontWeight": "600",
                        "color": COLORS['gray_dark'],
                        "marginBottom": "8px",
                        "textAlign": "center"
                    }),
                    dcc.Slider(
                        min=-0.2, max=0.2, step=0.01, value=0.0, id="adj-price",
                        marks=None, tooltip={"placement": "bottom", "always_visible": True},
                        vertical=False
                    ),
                    html.Small("Variação % (ex.: 0.05 = +5%)", style={
                        "color": COLORS['gray_medium'],
                        "fontSize": "10px",
                        "display": "block",
                        "textAlign": "center",
                        "marginTop": "4px"
                    })
                ], style={
                    "width": "100%",
                    "padding": "12px",
                    "backgroundColor": COLORS['background'],
                    "borderRadius": "4px",
                    "marginBottom": "16px"
                })
            ]),
            
            # Choques de Custo - Layout Horizontal em Grid
            html.Div([
                html.H4("Choques de Custo (Matéria-Prima)", style={
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "color": COLORS['gray_dark'],
                    "marginBottom": "16px"
                }),
                html.Div([
                    html.Div([
                        html.Label(PRETTY.get(driver), style={
                            "fontSize": "11px",
                            "fontWeight": "600",
                            "color": COLORS['gray_dark'],
                            "marginBottom": "6px",
                            "textAlign": "center",
                            "height": "32px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center"
                        }),
                        dcc.Slider(
                            min=-0.5, max=0.5, step=0.01, value=0.0, id=f"shock-{driver}",
                            marks=None, tooltip={"placement": "bottom", "always_visible": True},
                            vertical=False
                        )
                    ], style={
                        "width": "14%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                        "padding": "8px",
                        "backgroundColor": COLORS['background'],
                        "borderRadius": "4px",
                        "marginRight": "1%",
                        "marginBottom": "12px"
                    })
                    for driver in COST_DRIVERS_SLIDERS
                ], style={"width": "100%", "display": "flex", "flexWrap": "wrap", "justifyContent": "space-between"})
            ])
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        }),
        
        # Gráficos
        html.Div([
            dcc.Graph(id="fig-pnl-total", style={"marginBottom": "24px"}),
            dcc.Graph(id="fig-cost-driver-breakdown", style={"marginBottom": "24px"}),
            dcc.Graph(id="fig-mix-analysis")
        ], style={"marginBottom": "24px"}),
        
        # Tabelas
        html.Div([
            html.H3("Resumo do P&L Simulado", className="section-title"),
            html.Div(id="pnl-table"),
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        }),
        
        html.Div([
            html.H3("Tabela Razão - Detalhamento", className="section-title"),
            html.Div(id="tabela-razao")
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}"
        }),
        
        dcc.Store(id="store-optimization-result")
    ], style={"padding": "40px", "maxWidth": "1400px", "margin": "0 auto"})
], style={"backgroundColor": COLORS['background'], "minHeight": "100vh"})

# ============================================================================
# CALLBACKS
# ============================================================================
@app.callback(
    Output("store-optimization-result", "data"),
    Output("optimization-status", "children"),
    Output("optimization-report", "children"),
    Input("btn-optimize", "n_clicks"),
    State("f-month", "value"),
    State("f-dir", "value"),
    State("f-brand", "value"),
    State("f-size", "value"),
    State("f-pack", "value"),
    State("opt-price-min", "value"),
    State("opt-price-max", "value"),
    State("opt-cvv_concentrate-min", "value"),
    State("opt-cvv_concentrate-max", "value"),
    State("opt-cvv_sweetener-min", "value"),
    State("opt-cvv_sweetener-max", "value"),
    State("opt-cvv_pet-min", "value"),
    State("opt-cvv_pet-max", "value"),
    State("opt-cvv_can-min", "value"),
    State("opt-cvv_can-max", "value"),
    State("opt-cvv_cap-min", "value"),
    State("opt-cvv_cap-max", "value"),
    State("opt-cvv_purcharses-min", "value"),
    State("opt-cvv_purcharses-max", "value"),
    State("opt-cvv_otherraw-min", "value"),
    State("opt-cvv_otherraw-max", "value"),
    prevent_initial_call=True
)
def run_optimization(n_clicks, months, directorias, marcas, tamanhos, embalagens,
                    price_min, price_max, conc_min, conc_max, sweet_min, sweet_max,
                    pet_min, pet_max, can_min, can_max, cap_min, cap_max,
                    purch_min, purch_max, other_min, other_max):
    """Executa otimização quando o botão é clicado."""
    if n_clicks == 0:
        return None, html.Div(), html.Div(), html.Div()
    
    df_base_filtrado = df_master.copy()
    if months:
        months_dt = pd.to_datetime(months)
        df_base_filtrado = df_base_filtrado[df_base_filtrado['month'].isin(months_dt)]
    if directorias:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['diretoria'].isin(directorias)]
    if marcas:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['brand'].isin(marcas)]
    if tamanhos:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['size'].isin(tamanhos)]
    if embalagens:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['package'].isin(embalagens)]
    
    if df_base_filtrado.empty:
        return None, html.Div(), html.P("Sem dados para otimizar com os filtros selecionados.", style={"color": COLORS['error']}), html.Div()
    
    try:
        price_range = (float(price_min) if price_min is not None else -0.2, 
                      float(price_max) if price_max is not None else 0.2)
        
        cost_ranges = {
            'cvv_concentrate': (float(conc_min) if conc_min is not None else -0.5, 
                               float(conc_max) if conc_max is not None else 0.5),
            'cvv_sweetener': (float(sweet_min) if sweet_min is not None else -0.5, 
                            float(sweet_max) if sweet_max is not None else 0.5),
            'cvv_pet': (float(pet_min) if pet_min is not None else -0.5, 
                       float(pet_max) if pet_max is not None else 0.5),
            'cvv_can': (float(can_min) if can_min is not None else -0.5, 
                       float(can_max) if can_max is not None else 0.5),
            'cvv_cap': (float(cap_min) if cap_min is not None else -0.5, 
                       float(cap_max) if cap_max is not None else 0.5),
            'cvv_purcharses': (float(purch_min) if purch_min is not None else -0.5, 
                              float(purch_max) if purch_max is not None else 0.5),
            'cvv_otherraw': (float(other_min) if other_min is not None else -0.5, 
                            float(other_max) if other_max is not None else 0.5),
        }
        
        if price_range[0] >= price_range[1]:
            return None, html.P("Erro: Mínimo de Preço deve ser menor que Máximo.", style={"color": COLORS['error']}), html.Div()
        
        for driver, (min_val, max_val) in cost_ranges.items():
            if min_val >= max_val:
                return None, html.P(f"Erro: Mínimo de {PRETTY.get(driver, driver)} deve ser menor que Máximo.", style={"color": COLORS['error']}), html.Div()
        
    except (ValueError, TypeError) as e:
            return None, html.P(f"Erro ao processar limites: {str(e)}", style={"color": COLORS['error']}), html.Div()
    
    try:
        optimal_result = optimize_profitability(df_base_filtrado, price_range=price_range, cost_ranges=cost_ranges)
        
        if optimal_result is None:
            return None, html.P("Erro na otimização.", style={"color": COLORS['error']}), html.Div()
        
        # Removido: big_numbers = build_big_numbers_card(optimal_result)
        
        store_data = {
            'price_adj': optimal_result['params']['price_adj'],
            'shocks': optimal_result['params']['shocks'],
            'profit': optimal_result['profit'],
            'summary': {
                'Receita Total': optimal_result['summary']['Receita Total'],
                'Margem Total': optimal_result['summary']['Margem Total'],
                'Volume Total': optimal_result['summary']['Volume Total'],
                'Margem %': optimal_result['summary']['Margem %']
            }
        }
        
        # Status de sucesso
        status_msg = html.P("Otimização concluída com sucesso!", style={
            "color": COLORS['success'], 
            "fontWeight": "600",
            "marginBottom": "8px"
        })
        
        # Gerar relatório detalhado dos pontos ótimos
        try:
            print("[DEBUG] Gerando relatório de otimização...")
            optimization_report = build_optimization_report(optimal_result, df_base_filtrado)
            if optimization_report is None:
                print("[WARNING] build_optimization_report retornou None")
                optimization_report = html.Div("Erro: Relatório não pôde ser gerado.", style={"color": COLORS['error']})
            else:
                print(f"[DEBUG] Relatório gerado com sucesso. Tipo: {type(optimization_report)}")
        except Exception as e:
            import traceback
            print(f"[ERROR] Erro ao gerar relatório: {e}")
            traceback.print_exc()
            optimization_report = html.Div([
                html.P(f"Erro ao gerar relatório: {str(e)}", style={"color": COLORS['error']})
            ])
        
        print(f"[DEBUG] Retornando do callback: store_data={store_data is not None}, status_msg={status_msg is not None}, optimization_report={optimization_report is not None}")
        return store_data, status_msg, optimization_report
        
    except Exception as e:
        import traceback
        error_msg = f"Erro: {str(e)}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return None, html.P(error_msg, style={"color": COLORS['error']}), html.Div()

def build_optimization_report(optimal_result, df_base):
    """
    Constrói relatório corporativo detalhado dos pontos ótimos encontrados
    pela otimização Differential Evolution.
    """
    try:
        if optimal_result is None:
            return html.Div("Sem dados para exibir relatório.", style={"color": COLORS['error']})
        
        params = optimal_result.get('params', {})
        summary = optimal_result.get('summary', {})
        profit = optimal_result.get('profit', 0)
        
        # Verificar se params e summary são válidos (summary pode ser Series ou dict)
        if not params:
            return html.Div("Dados incompletos: parâmetros não encontrados.", style={"color": COLORS['error']})
        
        if summary is None:
            return html.Div("Dados incompletos: resumo não encontrado.", style={"color": COLORS['error']})
        
        # Converter summary para dict se for Series
        if isinstance(summary, pd.Series):
            summary = summary.to_dict()
        
        # Calcular cenário base para comparação
        df_base_sim = run_pnl_simulation(df_base, price_adj_pct=0.0, shocks_pct={})
        base_profit = calculate_profitability(df_base_sim)
        base_summary = summarize_pnl_df(df_base_sim, "Base")
        # Converter base_summary para dict se for Series
        if isinstance(base_summary, pd.Series):
            base_summary = base_summary.to_dict()
        
        # 1. Resumo Executivo
        summary_cards = html.Div([
        html.Div([
            html.H4("Margem Total Base", style={
                "margin": "0 0 8px 0",
                "fontSize": "12px",
                "fontWeight": "600",
                "color": COLORS['gray_dark'],
                "textTransform": "uppercase"
            }),
            html.H2(f"R$ {base_profit:,.0f}", style={
                "margin": "0",
                "fontSize": "24px",
                "fontWeight": "700",
                "color": COLORS['gray_dark']
            })
        ], style={
            "flex": "1",
            "padding": "20px",
            "backgroundColor": COLORS['accent'],
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginRight": "12px"
        }),
        html.Div([
            html.H4("Margem Total Ótima", style={
                "margin": "0 0 8px 0",
                "fontSize": "12px",
                "fontWeight": "600",
                "color": COLORS['gray_dark'],
                "textTransform": "uppercase"
            }),
            html.H2(f"R$ {profit:,.0f}", style={
                "margin": "0",
                "fontSize": "24px",
                "fontWeight": "700",
                "color": COLORS['success']
            })
        ], style={
            "flex": "1",
            "padding": "20px",
            "backgroundColor": COLORS['accent'],
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginRight": "12px"
        }),
        html.Div([
            html.H4("Melhoria", style={
                "margin": "0 0 8px 0",
                "fontSize": "12px",
                "fontWeight": "600",
                "color": COLORS['gray_dark'],
                "textTransform": "uppercase"
            }),
            html.H2(f"{((profit - base_profit) / base_profit * 100) if base_profit > 0 else 0:.2f}%", style={
                "margin": "0",
                "fontSize": "24px",
                "fontWeight": "700",
                "color": COLORS['success']
            })
        ], style={
            "flex": "1",
            "padding": "20px",
            "backgroundColor": COLORS['accent'],
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}"
        })
        ], style={"display": "flex", "marginBottom": "24px"})
        
        # 2. Tabela de Parâmetros Ótimos
        optimal_params_data = []
        
        # Preço
        optimal_params_data.append({
        'Parâmetro': 'Choque de Preço',
        'Valor Ótimo': f"{params.get('price_adj', 0):.4f}",
        'Valor Percentual': f"{params.get('price_adj', 0) * 100:.2f}%",
            'Descrição': 'Ajuste percentual no preço líquido unitário'
        })
        
        # Drivers de Custo
        shocks = params.get('shocks', {})
        for driver in COST_DRIVERS_SLIDERS:
            driver_name = PRETTY.get(driver, driver)
            driver_value = shocks.get(driver, 0.0)
            
            if driver == 'cvv_concentrate':
                desc = 'Percentual de ajuste no custo de concentrate (aplicado sobre % da receita)'
            else:
                desc = f'Ajuste percentual no custo unitário de {driver_name}'
            
            optimal_params_data.append({
                'Parâmetro': driver_name,
                'Valor Ótimo': f"{driver_value:.4f}",
                'Valor Percentual': f"{driver_value * 100:.2f}%",
                'Descrição': desc
            })
        
        params_table = dash_table.DataTable(
        columns=[
            {"name": "Parâmetro", "id": "Parâmetro"},
            {"name": "Valor Ótimo", "id": "Valor Ótimo"},
            {"name": "Valor Percentual", "id": "Valor Percentual"},
            {"name": "Descrição", "id": "Descrição"}
        ],
        data=optimal_params_data,
        id="data-params-table",
        export_format="xlsx",
        export_headers="display",
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "fontSize": "12px",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        },
        style_header={
            "backgroundColor": COLORS['primary'],
            "color": COLORS['accent'],
            "fontWeight": "600",
            "textTransform": "uppercase",
            "fontSize": "11px",
            "letterSpacing": "0.5px"
        },
        style_data={
            "backgroundColor": COLORS['accent'],
            "borderBottom": f"1px solid {COLORS['gray_light']}",
            "color": COLORS['success']
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{Valor Percentual} contains '-'"},
                "color": COLORS['error']
            }
        ]
    )
        
        # 3. Comparação de Cenários
        comparison_data = [
        {
            'Métrica': 'Receita Total',
            'Cenário Base': f"R$ {base_summary.get('Receita Total', 0):,.0f}",
            'Cenário Ótimo': f"R$ {summary.get('Receita Total', 0):,.0f}",
            'Variação': f"{((summary.get('Receita Total', 0) - base_summary.get('Receita Total', 0)) / base_summary.get('Receita Total', 1) * 100):.2f}%"
        },
        {
            'Métrica': 'Margem Total',
            'Cenário Base': f"R$ {base_summary.get('Margem Total', 0):,.0f}",
            'Cenário Ótimo': f"R$ {summary.get('Margem Total', 0):,.0f}",
            'Variação': f"{((summary.get('Margem Total', 0) - base_summary.get('Margem Total', 0)) / base_summary.get('Margem Total', 1) * 100):.2f}%"
        },
        {
            'Métrica': 'Volume Total',
            'Cenário Base': f"{base_summary.get('Volume Total', 0):,.0f} UC",
            'Cenário Ótimo': f"{summary.get('Volume Total', 0):,.0f} UC",
            'Variação': f"{((summary.get('Volume Total', 0) - base_summary.get('Volume Total', 0)) / base_summary.get('Volume Total', 1) * 100):.2f}%"
        },
        {
            'Métrica': 'Margem %',
            'Cenário Base': f"{base_summary.get('Margem %', 0):.2f}%",
            'Cenário Ótimo': f"{summary.get('Margem %', 0):.2f}%",
            'Variação': f"{(summary.get('Margem %', 0) - base_summary.get('Margem %', 0)):.2f} p.p."
        }
        ]
        
        comparison_table = dash_table.DataTable(
            columns=[
                {"name": "Métrica", "id": "Métrica"},
                {"name": "Cenário Base", "id": "Cenário Base"},
                {"name": "Cenário Ótimo", "id": "Cenário Ótimo"},
                {"name": "Variação", "id": "Variação"}
            ],
            data=comparison_data,
            id="data-comparison-table",
            export_format="xlsx",
            export_headers="display",
            style_cell={
                "textAlign": "left",
                "padding": "10px",
                "fontSize": "12px"
            },
            style_header={
                "backgroundColor": COLORS['primary'],
                "color": COLORS['accent'],
                "fontWeight": "600"
            },
            style_data={
                "backgroundColor": COLORS['accent'],
                "borderBottom": f"1px solid {COLORS['gray_light']}",
                "color": COLORS['success']
            },
            style_data_conditional=[
                {
                    "if": {"filter_query": "{Variação} contains '-'"},
                    "color": COLORS['error']
                }
            ]
        )
        
        # 4. Montar relatório completo
        report_content = html.Div([
            html.H3("Relatório de Otimização - Differential Evolution", style={
                "marginBottom": "24px",
                "color": COLORS['secondary'],
                "fontSize": "20px",
                "fontWeight": "700"
            }),
            summary_cards,
            html.H4("Parâmetros Ótimos Encontrados", style={
                "marginTop": "24px",
                "marginBottom": "16px",
                "color": COLORS['secondary'],
                "fontSize": "16px",
                "fontWeight": "600"
            }),
            html.Div([
                create_export_button("params", "parametros_otimos"),
                params_table
            ]),
            html.H4("Comparação de Cenários", style={
                "marginTop": "24px",
                "marginBottom": "16px",
                "color": COLORS['secondary'],
                "fontSize": "16px",
                "fontWeight": "600"
            }),
            html.Div([
                create_export_button("comparison", "comparacao_cenarios"),
                comparison_table
            ])
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "32px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginTop": "24px"
        })
        
        print(f"[INFO] Relatório construído com sucesso. Parâmetros: {len(optimal_params_data)} itens")
        return report_content
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Erro ao construir relatório de otimização: {e}")
        traceback.print_exc()
        return html.Div([
            html.P(f"Erro ao construir relatório: {str(e)}", style={"color": COLORS['error']})
        ])

def build_mix_optimization_report(df_optimal_mix, metrics, filters_info=None):
    """
    Constrói relatório SIMPLIFICADO do mix otimizado por TIPO.
    Mostra apenas: TIPO, Volume Projetado (demanda), Volume Otimizado (sugerido).
    
    Args:
        df_optimal_mix: DataFrame com resultados da otimização
        metrics: Dicionário com métricas (opcional)
        filters_info: Dicionário com informações dos filtros aplicados (mês, diretoria, etc.)
    """
    if df_optimal_mix is None or df_optimal_mix.empty:
        return html.Div("Sem dados para exibir relatório.", style={"color": COLORS['error']})
    
    # Extrair informações de filtros do DataFrame se não foram fornecidas
    if filters_info is None:
        filters_info = {}
        if 'depara_mess' in df_optimal_mix.columns:
            meses_unicos = df_optimal_mix['depara_mess'].dropna().unique()
            if len(meses_unicos) > 0:
                filters_info['meses'] = sorted([pd.to_datetime(m).strftime('%b-%Y') if pd.notna(m) else '' for m in meses_unicos])
        if 'diretoria' in df_optimal_mix.columns:
            diretorias_unicas = df_optimal_mix['diretoria'].dropna().unique()
            if len(diretorias_unicas) > 0:
                filters_info['diretorias'] = sorted(diretorias_unicas.tolist())
    
    # Preparar dados: apenas TIPO, demanda e volume otimizado
    df_report = df_optimal_mix.copy()
    
    # FILTRAR: Remover linhas sem TIPO (essencial para evitar dados órfãos)
    if 'tipo' in df_report.columns:
        # Filtrar apenas linhas com tipo válido (não nulo, não vazio, não NaN)
        mask_tipo_valido = (
            df_report['tipo'].notna() & 
            (df_report['tipo'] != '') &
            (df_report['tipo'].astype(str).str.strip() != '') &
            (df_report['tipo'].astype(str).str.strip() != 'nan')
        )
        df_report = df_report[mask_tipo_valido].copy()
        print(f"[INFO] Filtrando relatório: {len(mask_tipo_valido)} linhas totais, {mask_tipo_valido.sum()} com TIPO válido")
    
    # Selecionar apenas colunas essenciais
    display_cols = []
    col_mapping = {}
    
    # TIPO (obrigatório)
    if 'tipo' in df_report.columns:
        display_cols.append('tipo')
        col_mapping['tipo'] = 'TIPO'
    
    # Grupo de Capacidade (opcional, para contexto)
    if 'grupo_capacidade' in df_report.columns:
        display_cols.append('grupo_capacidade')
        col_mapping['grupo_capacidade'] = 'Grupo Capacidade'
    
    # Volume Projetado (demanda)
    if 'volume_projetado' in df_report.columns:
        display_cols.append('volume_projetado')
        col_mapping['volume_projetado'] = 'Demanda (UC)'
    
    # Volume Otimizado (sugestão)
    if 'volume_otimizado' in df_report.columns:
        display_cols.append('volume_otimizado')
        col_mapping['volume_otimizado'] = 'Volume Sugerido (UC)'
    
    # Margem por Unidade
    if 'base_margem_variavel_unit' in df_report.columns:
        display_cols.append('base_margem_variavel_unit')
        col_mapping['base_margem_variavel_unit'] = 'Margem por Unidade (R$)'
    elif 'margem_unit_esperada' in df_report.columns:
        display_cols.append('margem_unit_esperada')
        col_mapping['margem_unit_esperada'] = 'Margem por Unidade (R$)'
    
    # % de Consumo da Capacidade
    if 'uso_capacidade_pct' in df_report.columns:
        display_cols.append('uso_capacidade_pct')
        col_mapping['uso_capacidade_pct'] = '% Consumo Capacidade'
    elif 'capacidade_max' in df_report.columns and 'volume_otimizado' in df_report.columns:
        # Calcular se não existir
        mask_cap_valida = (
            df_report['capacidade_max'].notna() & 
            (df_report['capacidade_max'] > 0) & 
            (df_report['capacidade_max'] != float('inf'))
        )
        df_report['uso_capacidade_pct'] = 0.0
        # Calcular por grupo de capacidade (capacidade é compartilhada)
        if 'grupo_capacidade' in df_report.columns:
            for grupo in df_report['grupo_capacidade'].dropna().unique():
                mask_grupo = df_report['grupo_capacidade'] == grupo
                df_grupo = df_report[mask_grupo].copy()
                volume_total_grupo = df_grupo['volume_otimizado'].sum()
                cap_max = df_grupo['capacidade_max'].iloc[0] if df_grupo['capacidade_max'].notna().any() else float('inf')
                if cap_max < float('inf') and cap_max > 0:
                    uso_pct = (volume_total_grupo / cap_max) * 100
                    df_report.loc[mask_grupo, 'uso_capacidade_pct'] = uso_pct
        display_cols.append('uso_capacidade_pct')
        col_mapping['uso_capacidade_pct'] = '% Consumo Capacidade'
    
    # Filtrar apenas colunas que existem
    display_cols = [c for c in display_cols if c in df_report.columns]
    if not display_cols:
        return html.Div("Erro: Colunas necessárias não encontradas.", style={"color": COLORS['error']})
    
    # Verificar se há dados após filtro
    if df_report.empty:
        return html.Div("Nenhum dado válido para exibir. Verifique se os TIPOs estão corretamente preenchidos.", 
                       style={"color": COLORS['error']})
    
    df_table = df_report[display_cols].copy()
    
    # Garantir que TIPO não está vazio (filtro adicional de segurança)
    if 'TIPO' in df_table.columns:
        df_table = df_table[df_table['TIPO'].notna() & (df_table['TIPO'].astype(str).str.strip() != '')].copy()
    
    # Renomear colunas
    df_table = df_table.rename(columns=col_mapping)
    
    # Formatar valores numéricos
    for col in df_table.columns:
        if 'Volume' in col or 'Demanda' in col:
            df_table[col] = df_table[col].apply(lambda x: f"{float(x):,.0f}" if pd.notna(x) else "-")
        elif 'Margem por Unidade' in col:
            # Formatar como moeda (R$)
            def format_margem(x):
                if pd.isna(x):
                    return "-"
                try:
                    val = float(x)
                    return f"R$ {val:,.2f}"
                except (ValueError, TypeError):
                    return "-"
            df_table[col] = df_table[col].apply(format_margem)
        elif '% Consumo' in col or 'Consumo Capacidade' in col:
            # Formatar percentual
            def format_pct_capacidade(x):
                if pd.isna(x) or x == float('inf'):
                    return "-"
                try:
                    val = float(x)
                    if val > 1000:  # Se muito alto, pode ser erro
                        return ">100%"
                    return f"{val:.1f}%"
                except (ValueError, TypeError):
                    return "-"
            df_table[col] = df_table[col].apply(format_pct_capacidade)
    
    # Ordenar por TIPO
    if 'TIPO' in df_table.columns:
        df_table = df_table.sort_values('TIPO')
    
    # Tabela simples com botão de exportação
    table_div = html.Div([
        create_export_button("mix-optimization-table", "volumes_otimizados_tipo"),
        dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in df_table.columns],
            data=df_table.to_dict('records'),
            style_cell={
                "textAlign": "left",
                "padding": "12px",
                "fontSize": "13px",
                "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
            },
            style_header={
                "backgroundColor": COLORS['primary'],
                "color": COLORS['accent'],
                "fontWeight": "600",
                "textTransform": "uppercase",
                "fontSize": "12px"
            },
            style_data={
                "backgroundColor": COLORS['accent'],
                "borderBottom": f"1px solid {COLORS['gray_light']}"
            },
            style_data_conditional=[
                # Cores para % de consumo da capacidade
                {
                    "if": {
                        "filter_query": "{% Consumo Capacidade} >= 95 && {% Consumo Capacidade} != '-'"
                    },
                    "backgroundColor": "#F8D7DA",  # Vermelho claro: próximo ou acima do máximo
                    "color": "#721C24",
                    "fontWeight": "600"
                },
                {
                    "if": {
                        "filter_query": "{% Consumo Capacidade} >= 80 && {% Consumo Capacidade} < 95 && {% Consumo Capacidade} != '-'"
                    },
                    "backgroundColor": "#FFF3CD",  # Amarelo: alto uso
                    "color": "#856404"
                },
                {
                    "if": {
                        "filter_query": "{% Consumo Capacidade} >= 50 && {% Consumo Capacidade} < 80 && {% Consumo Capacidade} != '-'"
                    },
                    "backgroundColor": "#D1ECF1",  # Azul claro: uso moderado
                    "color": "#0C5460"
                },
                {
                    "if": {
                        "filter_query": "{% Consumo Capacidade} < 50 && {% Consumo Capacidade} != '-'"
                    },
                    "backgroundColor": "#D4EDDA",  # Verde claro: uso baixo
                    "color": "#155724"
                }
            ],
            page_size=50,
            id="data-mix-optimization-table",
            export_format="xlsx",
            export_headers="display"
        )
    ])
    table = table_div
    
    # Criar cabeçalho com informações de filtros
    header_sections = []
    
    # Título
    header_sections.append(
        html.H3("Volumes Otimizados por TIPO", style={
            "marginBottom": "16px",
            "color": COLORS['gray_dark']
        })
    )
    
    # Informações de filtros aplicados
    filter_info_text = []
    if filters_info:
        if 'meses' in filters_info and filters_info['meses']:
            meses_str = ', '.join(filters_info['meses'])
            filter_info_text.append(f"Mês (Projeção): {meses_str}")
        if 'diretorias' in filters_info and filters_info['diretorias']:
            diretorias_str = ', '.join(filters_info['diretorias'])
            filter_info_text.append(f"Diretoria: {diretorias_str}")
        if 'marcas' in filters_info and filters_info['marcas']:
            marcas_str = ', '.join(filters_info['marcas'])
            filter_info_text.append(f"Marca: {marcas_str}")
        if 'tamanhos' in filters_info and filters_info['tamanhos']:
            tamanhos_str = ', '.join([str(t) for t in filters_info['tamanhos']])
            filter_info_text.append(f"Tamanho: {tamanhos_str}")
        if 'embalagens' in filters_info and filters_info['embalagens']:
            embalagens_str = ', '.join(filters_info['embalagens'])
            filter_info_text.append(f"Embalagem: {embalagens_str}")
    
    # Se não há filtros explícitos, tentar extrair do DataFrame
    if not filter_info_text:
        if 'depara_mess' in df_optimal_mix.columns:
            meses_unicos = df_optimal_mix['depara_mess'].dropna().unique()
            if len(meses_unicos) > 0:
                meses_str = ', '.join([pd.to_datetime(m).strftime('%b-%Y') if pd.notna(m) else '' for m in sorted(meses_unicos)])
                filter_info_text.append(f"Mês (Projeção): {meses_str}")
        if 'diretoria' in df_optimal_mix.columns:
            diretorias_unicas = df_optimal_mix['diretoria'].dropna().unique()
            if len(diretorias_unicas) > 0:
                diretorias_str = ', '.join(sorted(diretorias_unicas.astype(str).tolist()))
                filter_info_text.append(f"Diretoria: {diretorias_str}")
    
    if filter_info_text:
        header_sections.append(
            html.Div([
                html.P("Filtros Aplicados:", style={
                    "fontSize": "12px",
                    "fontWeight": "600",
                    "color": COLORS['gray_dark'],
                    "marginBottom": "8px"
                }),
                html.Div([
                    html.P(text, style={
                        "fontSize": "11px",
                        "color": COLORS['gray_medium'],
                        "margin": "2px 0",
                        "display": "inline-block",
                        "marginRight": "16px"
                    }) for text in filter_info_text
                ], style={"marginBottom": "16px"})
            ], style={
                "backgroundColor": COLORS['accent'],
                "padding": "12px",
                "borderRadius": "4px",
                "border": f"1px solid {COLORS['gray_light']}",
                "marginBottom": "20px"
            })
        )
    
    return html.Div(header_sections + [table])


@app.callback(
    Output("fig-pnl-total", "figure"),
    Output("fig-cost-driver-breakdown", "figure"),
    Output("fig-mix-analysis", "figure"),
    Output("pnl-table", "children"),
    Output("tabela-razao", "children"),
    [
        Input("f-month", "value"),
        Input("f-dir", "value"),
        Input("f-brand", "value"),
        Input("f-size", "value"),
        Input("f-pack", "value"),
        Input("adj-price", "value"),
        Input("shock-cvv_concentrate", "value"),
        Input("shock-cvv_sweetener", "value"),
        Input("shock-cvv_pet", "value"),
        Input("shock-cvv_can", "value"),
        Input("shock-cvv_cap", "value"),
        Input("shock-cvv_purcharses", "value"),
        Input("shock-cvv_otherraw", "value"),
    ]
)
def update_simulation_view(months, directorias, marcas, tamanhos, embalagens,
                          price_adj, s_conc, s_sweet, s_pet, s_can, s_cap, s_purch, s_other):
    """Atualiza visualizações baseado nos filtros e controles."""
    
    try:
        df_base_filtrado = df_master.copy()
        
        if months:
            months_dt = pd.to_datetime(months)
            df_base_filtrado = df_base_filtrado[df_base_filtrado['month'].isin(months_dt)]
        if directorias:
            df_base_filtrado = df_base_filtrado[df_base_filtrado['diretoria'].isin(directorias)]
        if marcas:
            df_base_filtrado = df_base_filtrado[df_base_filtrado['brand'].isin(marcas)]
        if tamanhos:
            df_base_filtrado = df_base_filtrado[df_base_filtrado['size'].isin(tamanhos)]
        if embalagens:
            df_base_filtrado = df_base_filtrado[df_base_filtrado['package'].isin(embalagens)]
        
        fig_vazia = go.Figure().update_layout(title="Sem dados para o filtro selecionado.")
        
        if df_base_filtrado.empty:
            empty_table = dash_table.DataTable(data=[])
            return fig_vazia, fig_vazia, fig_vazia, empty_table, html.Div("Sem dados.", style={"color": COLORS['error']})
        
        shocks = {
            "cvv_concentrate": s_conc or 0.0,
            "cvv_sweetener": s_sweet or 0.0,
            "cvv_pet": s_pet or 0.0,
            "cvv_can": s_can or 0.0,
            "cvv_cap": s_cap or 0.0,
            "cvv_purcharses": s_purch or 0.0,
            "cvv_otherraw": s_other or 0.0,
        }
        
        # Cenário Base
        df_cenario_base = run_pnl_simulation(df_base_filtrado, price_adj_pct=0.0, shocks_pct={})
        df_cenario_base['volume_simulado'] = df_cenario_base['volume_projetado']
        df_cenario_base['preco_liquido_simulado_unit'] = df_cenario_base['base_preco_liquido_unit']
        df_cenario_base['receita_total_simulada'] = df_cenario_base['volume_simulado'] * df_cenario_base['preco_liquido_simulado_unit']
        
        # Cenário Simulado
        df_cenario_simulado = run_pnl_simulation(df_base_filtrado, price_adj_pct=price_adj or 0.0, shocks_pct=shocks)
        
        # Cenário Projetado
        df_proj_base = df_base_filtrado.copy()
        shocks_proj = {}
        
        if df_mp_yoy is not None and not df_mp_yoy.empty:
            df_yoy_filtrado = df_mp_yoy.copy()
            if months:
                months_dt = pd.to_datetime(months)
                df_yoy_filtrado = df_yoy_filtrado[df_yoy_filtrado['month'].isin(months_dt)]
            
            for driver in COST_DRIVERS_SLIDERS:
                driver_yoy = df_yoy_filtrado[df_yoy_filtrado['driver'] == driver]
                if not driver_yoy.empty:
                    avg_yoy = driver_yoy['yoy_pct'].mean()
                    shocks_proj[driver] = avg_yoy
                else:
                    shocks_proj[driver] = 0.0
        else:
            for driver in COST_DRIVERS_SLIDERS:
                shocks_proj[driver] = 0.0
        
        df_cenario_projetado = run_pnl_simulation(df_proj_base, price_adj_pct=0.0, shocks_pct=shocks_proj)
        df_cenario_projetado['volume_simulado'] = df_cenario_projetado['volume_projetado']
        df_cenario_projetado['preco_liquido_simulado_unit'] = df_cenario_projetado['base_preco_liquido_unit']
        df_cenario_projetado['receita_total_simulada'] = df_cenario_projetado['volume_simulado'] * df_cenario_projetado['preco_liquido_simulado_unit']
        
        # Análise de Mix
        mix_analysis = analyze_product_mix(df_cenario_simulado)
        
        # Gráficos
        fig_pnl = build_pnl_total_fig(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
        pu_base, pu_sim, pu_proj = calculate_average_pu(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
        fig_cost = build_cost_driver_fig(pu_base, pu_sim, pu_proj)
        fig_mix = build_mix_analysis_fig(mix_analysis)
        
        # Tabela Resumo
        base_summary = summarize_pnl_df(df_cenario_base, "Cenário Base")
        sim_summary = summarize_pnl_df(df_cenario_simulado, "Cenário Simulado")
        resultados_list = [base_summary, sim_summary]
        
        if df_cenario_projetado is not None:
            proj_summary = summarize_pnl_df(df_cenario_projetado, "Cenário Projetado")
            resultados_list.append(proj_summary)
        
        df_resultados = pd.DataFrame(resultados_list)
        df_resultados['Receita Total'] = df_resultados['Receita Total'].apply(lambda x: f"R$ {x:,.0f}")
        df_resultados['Margem Total'] = df_resultados['Margem Total'].apply(lambda x: f"R$ {x:,.0f}")
        df_resultados['Volume Total'] = df_resultados['Volume Total'].apply(lambda x: f"{x:,.0f} UC")
        df_resultados['Margem %'] = df_resultados['Margem %'].apply(lambda x: f"{x:.2%}")
        
        table_div = html.Div([
            create_export_button("pnl-table", "resumo_pnl_simulado"),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df_resultados.columns],
                data=df_resultados.to_dict('records'),
                style_cell={"textAlign": "center", "padding": "8px", "fontSize": "12px"},
                style_header={"backgroundColor": COLORS['gray_light'], "fontWeight": "600", "color": COLORS['secondary']},
                style_table={"overflowX": "auto"},
                page_size=10,
                id="data-pnl-table",
                export_format="xlsx",
                export_headers="display"
            )
        ])
        table = table_div
        
        # Tabela Razão
        tabela_razao = build_tabela_razao(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
        
        return fig_pnl, fig_cost, fig_mix, table, tabela_razao
    
    except Exception as e:
        import traceback
        error_msg = f"Erro ao atualizar visualizações: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        
        # Retornar figuras vazias e mensagem de erro
        fig_vazia = go.Figure().update_layout(title="Erro ao carregar dados")
        error_div = html.Div([
            html.P(f"Erro: {str(e)}", style={"color": COLORS['error'], "fontWeight": "bold"}),
            html.P("Verifique os filtros e tente novamente.", style={"color": COLORS['gray_medium']})
        ])
        empty_table = dash_table.DataTable(data=[])
        
        return fig_vazia, fig_vazia, fig_vazia, empty_table, error_div

def build_tabela_razao(df_base, df_sim, df_proj=None):
    """Cria tabela razão com dados importantes para análise detalhada."""
    if df_base.empty:
        return html.Div("Sem dados para o filtro selecionado.", style={"color": COLORS['error']})
    
    dfs_razao = []
    
    if 'month' in df_base.columns and 'diretoria' in df_base.columns and 'chave_sku' in df_base.columns:
        df_base_razao = pd.DataFrame({
            'Cenário': 'Base',
            'Mês': pd.to_datetime(df_base['month']).dt.strftime('%Y-%m'),
            'Diretoria': df_base['diretoria'],
            'SKU': df_base['chave_sku'],
            'Volume': df_base['volume_projetado'].fillna(0),
            'Preço Unitário': df_base['base_preco_liquido_unit'].fillna(0),
            'Receita Total': (df_base['volume_projetado'].fillna(0) * df_base['base_preco_liquido_unit'].fillna(0)),
            'Margem Unitária': df_base['base_margem_variavel_unit'].fillna(0),
            'Margem Total': (df_base['volume_projetado'].fillna(0) * df_base['base_margem_variavel_unit'].fillna(0))
        })
        if 'elasticidade' in df_base.columns:
            df_base_razao['Elasticidade'] = df_base['elasticidade'].fillna(0)
        dfs_razao.append(df_base_razao)
    
    if not df_sim.empty and 'chave_sku' in df_sim.columns:
        df_sim_razao = pd.DataFrame({
            'Cenário': 'Simulado',
            'Mês': pd.to_datetime(df_sim['month']).dt.strftime('%Y-%m') if 'month' in df_sim.columns else '',
            'Diretoria': df_sim['diretoria'] if 'diretoria' in df_sim.columns else '',
            'SKU': df_sim['chave_sku'],
            'Volume': df_sim['volume_simulado'].fillna(0),
            'Preço Unitário': df_sim['preco_liquido_simulado_unit'].fillna(0),
            'Receita Total': df_sim['receita_total_simulada'].fillna(0),
            'Margem Unitária': df_sim['margem_simulada_unit'].fillna(0) if 'margem_simulada_unit' in df_sim.columns else 0,
            'Margem Total': df_sim['margem_total_simulada'].fillna(0)
        })
        if 'elasticidade' in df_sim.columns:
            df_sim_razao['Elasticidade'] = df_sim['elasticidade'].fillna(0)
        dfs_razao.append(df_sim_razao)
    
    if df_proj is not None and not df_proj.empty and 'chave_sku' in df_proj.columns:
        df_proj_razao = pd.DataFrame({
            'Cenário': 'Projetado',
            'Mês': pd.to_datetime(df_proj['month']).dt.strftime('%Y-%m') if 'month' in df_proj.columns else '',
            'Diretoria': df_proj['diretoria'] if 'diretoria' in df_proj.columns else '',
            'SKU': df_proj['chave_sku'],
            'Volume': df_proj['volume_simulado'].fillna(0) if 'volume_simulado' in df_proj.columns else 0,
            'Preço Unitário': df_proj['preco_liquido_simulado_unit'].fillna(0) if 'preco_liquido_simulado_unit' in df_proj.columns else 0,
            'Receita Total': df_proj['receita_total_simulada'].fillna(0) if 'receita_total_simulada' in df_proj.columns else 0,
            'Margem Unitária': df_proj['margem_simulada_unit'].fillna(0) if 'margem_simulada_unit' in df_proj.columns else 0,
            'Margem Total': df_proj['margem_total_simulada'].fillna(0) if 'margem_total_simulada' in df_proj.columns else 0
        })
        if 'elasticidade' in df_proj.columns:
            df_proj_razao['Elasticidade'] = df_proj['elasticidade'].fillna(0)
        dfs_razao.append(df_proj_razao)
    
    if not dfs_razao:
        return html.Div("Sem dados para exibir na tabela razão.", style={"color": COLORS['error']})
    
    df_razao_final = pd.concat(dfs_razao, ignore_index=True)
    
    # Formatar valores - garantir que todos sejam numéricos antes de formatar
    def safe_format_volume(x):
        try:
            if pd.isna(x) or x is None:
                return "0,00 UC"
            val = float(x)
            return f"{val:,.2f} UC"
        except (ValueError, TypeError):
            return "0,00 UC"
    
    def safe_format_currency(x, decimals=4):
        try:
            if pd.isna(x) or x is None:
                return f"R$ {0:.{decimals}f}"
            val = float(x)
            return f"R$ {val:,.{decimals}f}"
        except (ValueError, TypeError):
            return f"R$ {0:.{decimals}f}"
    
    def safe_format_number(x, decimals=4):
        try:
            if pd.isna(x) or x is None:
                return f"{0:.{decimals}f}"
            val = float(x)
            return f"{val:,.{decimals}f}"
        except (ValueError, TypeError):
            return f"{0:.{decimals}f}"
    
    # Aplicar formatação segura
    if 'Volume' in df_razao_final.columns:
        df_razao_final['Volume'] = df_razao_final['Volume'].apply(safe_format_volume)
    if 'Preço Unitário' in df_razao_final.columns:
        df_razao_final['Preço Unitário'] = df_razao_final['Preço Unitário'].apply(lambda x: safe_format_currency(x, 4))
    if 'Receita Total' in df_razao_final.columns:
        df_razao_final['Receita Total'] = df_razao_final['Receita Total'].apply(lambda x: safe_format_currency(x, 2))
    if 'Margem Unitária' in df_razao_final.columns:
        df_razao_final['Margem Unitária'] = df_razao_final['Margem Unitária'].apply(lambda x: safe_format_currency(x, 4))
    if 'Margem Total' in df_razao_final.columns:
        df_razao_final['Margem Total'] = df_razao_final['Margem Total'].apply(lambda x: safe_format_currency(x, 2))
    if 'Elasticidade' in df_razao_final.columns:
        df_razao_final['Elasticidade'] = df_razao_final['Elasticidade'].apply(lambda x: safe_format_number(x, 4))
    
    tabela_div = html.Div([
        create_export_button("tabela-razao", "tabela_razao_detalhamento"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in df_razao_final.columns],
            data=df_razao_final.to_dict('records'),
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "11px"},
            style_header={"backgroundColor": COLORS['gray_light'], "fontWeight": "600", "color": COLORS['secondary']},
            style_table={"overflowX": "auto"},
            page_size=20,
            sort_action="native",
            filter_action="native",
            id="data-tabela-razao",
            export_format="xlsx",
            export_headers="display"
        )
    ])
    
    return tabela_div

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print(f"[INFO] CSV do 'Master DataFrame' carregado: {DATA_FILE}")
    print(f"Total de linhas no Master DF: {len(df_master)}")
    print("Iniciando o servidor Dash...")
    app.run(debug=True, port=8050)

