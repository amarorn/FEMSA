# ============================================================================
# FEMSA - Otimização de Mix de Produtos
# Página dedicada para cálculo de Mix Ótimo
# Baseado em: 04_mix_optimization.ipynb
# ============================================================================
import os
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
COLORS = {
    'primary': '#F40009',
    'primary_dark': '#C00007',
    'primary_light': '#FF4D5A',
    'secondary': '#1A1A1A',
    'accent': '#FFFFFF',
    'gray_dark': '#4A4A4A',
    'gray_medium': '#8A8A8A',
    'gray_light': '#E5E5E5',
    'background': '#F8F8F8',
    'success': '#00A859',
    'warning': '#FFB800',
    'error': '#E60012',
}

app = Dash(__name__)
app.title = "FEMSA - Otimização de Mix de Produtos"

# ============================================================================
# FUNÇÕES DE OTIMIZAÇÃO (do notebook)
# ============================================================================
def optimize_single_tipo_group(df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo):
    """
    Otimiza grupos com APENAS 1 TIPO.
    Modelo mais simples: apenas verificar capacidade e demanda.
    """
    n_tipos = len(df_grupo)
    if n_tipos != 1:
        return None
    
    demanda = demandas[0]
    lucro_unit = lucros_unit[0]
    
    # Para 1 TIPO: simplesmente usar o mínimo entre demanda e capacidade máxima
    volume_otimizado = min(demanda, cap_max) if cap_max < float('inf') else demanda
    
    # Se volume < cap_min e demanda >= cap_min, usar cap_min
    if cap_min > 0 and volume_otimizado < cap_min and demanda >= cap_min:
        volume_otimizado = min(cap_min, cap_max) if cap_max < float('inf') else cap_min
    
    # Não pode exceder demanda
    volume_otimizado = min(volume_otimizado, demanda)
    
    lucro_total = volume_otimizado * lucro_unit
    atendimento_pct = (volume_otimizado / demanda * 100) if demanda > 0 else 0
    
    # Status
    if volume_otimizado > cap_max and cap_max < float('inf'):
        status_grupo = 'Acima Máximo'
    elif volume_otimizado < cap_min and cap_min > 0:
        status_grupo = 'Abaixo Mínimo'
    else:
        status_grupo = 'OK'
    
    return {
        'volumes_otimizados': np.array([volume_otimizado]),
        'lucro_total': lucro_total,
        'atendimento_pct': atendimento_pct,
        'status_grupo': status_grupo,
        'volume_total_final': volume_otimizado
    }

def optimize_multi_tipo_group(df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo):
    """
    Otimiza grupos com MÚLTIPLOS TIPOs (2+).
    Usa otimização SLSQP para distribuir capacidade entre TIPOs.
    """
    n_tipos = len(df_grupo)
    if n_tipos < 2:
        return None
    
    demanda_total = demandas.sum()
    
    # Função objetivo: maximizar lucro total (minimizar negativo)
    def objetivo(x):
        lucro_total = -np.sum(lucros_unit * x)
        
        # Penalidades
        volume_total = np.sum(x)
        
        # Penalidade por exceder capacidade máxima
        if volume_total > cap_max and cap_max < float('inf'):
            lucro_total += 1e10 * (volume_total - cap_max)
        
        # Penalidade por não atingir capacidade mínima
        if volume_total < cap_min and cap_min > 0 and cap_min < cap_max:
            lucro_total += 1e6 * (cap_min - volume_total)
        
        # Penalidade por exceder demanda individual
        excesso_demanda = np.sum(np.maximum(0, x - demandas))
        if excesso_demanda > 0:
            lucro_total += 1e8 * excesso_demanda
        
        # Penalidade por volumes negativos
        volumes_negativos = np.sum(np.maximum(0, -x))
        if volumes_negativos > 0:
            lucro_total += 1e10 * volumes_negativos
        
        return lucro_total
    
    # Restrições
    constraints = []
    
    # Restrição: volume total <= capacidade máxima
    if cap_max < float('inf'):
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: cap_max - np.sum(x)
        })
    
    # Bounds: apenas limitar pela demanda individual
    bounds = [(0.0, dem) for dem in demandas]
    
    # Restrição: volume total >= capacidade mínima (se viável)
    soma_bounds_max = sum(b[1] for b in bounds)
    if (cap_min > 0 and 
        cap_min < cap_max and
        soma_bounds_max >= cap_min):
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: np.sum(x) - cap_min
        })
    
    # Ponto inicial: priorizar TIPOs mais lucrativos
    x0 = np.zeros(n_tipos)
    idxs_ordenados = np.argsort(lucros_unit)[::-1]
    
    if cap_max < float('inf') and demanda_total > cap_max:
        # Demanda excede capacidade: alocar para os mais lucrativos
        capacidade_restante = cap_max
        for idx in idxs_ordenados:
            if capacidade_restante <= 0:
                break
            alocacao = min(demandas[idx], capacidade_restante)
            x0[idx] = alocacao
            capacidade_restante -= alocacao
    else:
        # Se cabe tudo, usar demanda
        x0 = demandas.copy()
    
    # Verificar viabilidade
    soma_bounds_max = sum(b[1] for b in bounds)
    viável = True
    
    if cap_max < float('inf'):
        if cap_min > 0 and soma_bounds_max < cap_min:
            viável = False
        elif cap_min > cap_max:
            viável = False
    
    # Otimizar
    try:
        if viável:
            result = minimize(
                objetivo,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-6, 'disp': False}
            )
        else:
            result = type('obj', (object,), {'success': False, 'message': 'Problema inviável', 'x': x0})()
        
        if result.success:
            volumes_otimizados = np.maximum(0, result.x)
            volumes_otimizados = np.minimum(volumes_otimizados, demandas)
            
            # Ajustar se exceder capacidade total
            volume_total = volumes_otimizados.sum()
            if volume_total > cap_max and cap_max < float('inf'):
                # Redistribuir capacidade para os mais lucrativos
                idxs_ordenados = np.argsort(lucros_unit)[::-1]
                volumes_otimizados = np.zeros(n_tipos)
                capacidade_restante = cap_max
                for idx in idxs_ordenados:
                    if capacidade_restante <= 0:
                        break
                    alocacao = min(demandas[idx], capacidade_restante)
                    volumes_otimizados[idx] = alocacao
                    capacidade_restante -= alocacao
            
            volume_total_final = volumes_otimizados.sum()
            lucro_total = np.sum(lucros_unit * volumes_otimizados)
            atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
            
            # Status
            if volume_total_final > cap_max and cap_max < float('inf'):
                status_grupo = 'Acima Máximo'
            elif volume_total_final < cap_min and cap_min > 0:
                status_grupo = 'Abaixo Mínimo'
            else:
                status_grupo = 'OK'
            
            return {
                'volumes_otimizados': volumes_otimizados,
                'lucro_total': lucro_total,
                'atendimento_pct': atendimento_pct,
                'status_grupo': status_grupo,
                'volume_total_final': volume_total_final
            }
        else:
            # Fallback: alocar por lucratividade
            idxs_ordenados = np.argsort(lucros_unit)[::-1]
            volumes_fallback = np.zeros(n_tipos)
            capacidade_restante = cap_max if cap_max < float('inf') else demanda_total
            
            for idx in idxs_ordenados:
                if capacidade_restante <= 0:
                    break
                alocacao = min(demandas[idx], capacidade_restante)
                volumes_fallback[idx] = alocacao
                capacidade_restante -= alocacao
            
            volume_total_final = volumes_fallback.sum()
            lucro_total = np.sum(lucros_unit * volumes_fallback)
            atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
            
            status_grupo = 'OK'
            if volume_total_final > cap_max and cap_max < float('inf'):
                status_grupo = 'Acima Máximo'
            elif volume_total_final < cap_min and cap_min > 0:
                status_grupo = 'Abaixo Mínimo'
            
            return {
                'volumes_otimizados': volumes_fallback,
                'lucro_total': lucro_total,
                'atendimento_pct': atendimento_pct,
                'status_grupo': status_grupo,
                'volume_total_final': volume_total_final
            }
    except Exception:
        # Fallback em caso de erro
        idxs_ordenados = np.argsort(lucros_unit)[::-1]
        volumes_fallback = np.zeros(n_tipos)
        capacidade_restante = cap_max if cap_max < float('inf') else demanda_total
        
        for idx in idxs_ordenados:
            if capacidade_restante <= 0:
                break
            alocacao = min(demandas[idx], capacidade_restante)
            volumes_fallback[idx] = alocacao
            capacidade_restante -= alocacao
        
        volume_total_final = volumes_fallback.sum()
        lucro_total = np.sum(lucros_unit * volumes_fallback)
        atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
        
        return {
            'volumes_otimizados': volumes_fallback,
            'lucro_total': lucro_total,
            'atendimento_pct': atendimento_pct,
            'status_grupo': 'OK',
            'volume_total_final': volume_total_final
        }

def optimize_by_capacity_group(df_work):
    """
    Otimiza mix de produção por GRUPO DE CAPACIDADE.
    
    Objetivo: Maximizar lucro total
    Restrições:
    - Volume total do grupo <= capacidade_max
    - Volume total do grupo >= capacidade_min (se aplicável)
    - Volume de cada SKU <= demanda (volume_projetado)
    - Volume de cada SKU >= 0
    """
    # Preparar resultado
    df_result = df_work.copy()
    df_result['volume_otimizado'] = 0.0
    df_result['lucro_otimizado'] = 0.0
    df_result['atendimento_pct'] = 0.0
    df_result['status_capacidade'] = 'OK'
    
    # Agrupar por grupo_capacidade
    grupos_unicos = df_work['grupo_capacidade'].dropna().unique()
    
    resultados = {}
    
    for grupo in grupos_unicos:
        df_grupo = df_work[df_work['grupo_capacidade'] == grupo].copy()
        
        if df_grupo.empty:
            continue
        
        n_tipos = len(df_grupo)
        
        # Dados do grupo (agora por TIPO, não por SKU)
        demandas = df_grupo['volume_projetado'].fillna(0).values
        lucros_unit = df_grupo['base_margem_variavel_unit'].fillna(0).values
        indices_tipo = df_grupo.index.tolist()
        
        # Capacidade compartilhada do grupo
        cap_min = df_grupo['capacidade_min'].iloc[0] if df_grupo['capacidade_min'].notna().any() else 0
        cap_max = df_grupo['capacidade_max'].iloc[0] if df_grupo['capacidade_max'].notna().any() else float('inf')
        
        demanda_total = demandas.sum()
        
        # ESCOLHER MODELO BASEADO NO NÚMERO DE TIPOs
        if n_tipos == 1:
            resultado = optimize_single_tipo_group(
                df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo
            )
        else:
            resultado = optimize_multi_tipo_group(
                df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo
            )
        
        if resultado is None:
            continue
        
        # Extrair resultados
        volumes_otimizados = resultado['volumes_otimizados']
        lucro_total = resultado['lucro_total']
        atendimento_pct = resultado['atendimento_pct']
        status_grupo = resultado['status_grupo']
        volume_total_final = resultado['volume_total_final']
        
        # Atualizar resultado POR TIPO (não por grupo)
        for i, idx in enumerate(indices_tipo):
            df_result.at[idx, 'volume_otimizado'] = volumes_otimizados[i]
            df_result.at[idx, 'lucro_otimizado'] = lucros_unit[i] * volumes_otimizados[i]
            df_result.at[idx, 'atendimento_pct'] = (volumes_otimizados[i] / demandas[i] * 100) if demandas[i] > 0 else 0
            df_result.at[idx, 'status_capacidade'] = status_grupo
        
        resultados[grupo] = {
            'volume_total': volume_total_final,
            'demanda_total': demanda_total,
            'lucro_total': lucro_total,
            'atendimento_pct': atendimento_pct,
            'status': status_grupo,
            'n_tipos': n_tipos
        }
    
    # Retornar resultados finais
    return df_result, resultados

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def nonempty_unique(x):
    """Retorna lista única de valores não vazios."""
    return sorted([v for v in x.dropna().unique().tolist() if v != ""])

def to_month(dt_like):
    """Converte datetime para primeiro dia do mês."""
    if isinstance(dt_like, pd.Timestamp):
        return pd.Timestamp(dt_like.year, dt_like.month, 1)
    s = pd.to_datetime(dt_like, errors="coerce")
    return s.dt.to_period("M").dt.to_timestamp()

def load_filter_options(data_file):
    """Carrega opções de filtros do arquivo de dados."""
    if not os.path.exists(data_file):
        return {}
    
    try:
        # Ler todas as colunas (será filtrado depois)
        df = pd.read_csv(data_file, decimal=',', encoding='utf-8')
        
        options = {}
        
        # Mês (depara_mess)
        if 'depara_mess' in df.columns:
            df['depara_mess'] = pd.to_datetime(df['depara_mess'], errors='coerce')
            meses = df['depara_mess'].dropna().unique()
            options['months'] = [{'label': pd.to_datetime(m).strftime('%Y-%m'), 'value': str(m)} for m in sorted(meses)]
        
        # Diretoria
        if 'diretoria' in df.columns:
            dirs = nonempty_unique(df['diretoria'])
            options['dirs'] = [{'label': d, 'value': d} for d in dirs]
        
        # Marca
        if 'brand' in df.columns:
            brands = nonempty_unique(df['brand'])
            options['brands'] = [{'label': b, 'value': b} for b in brands]
        
        # Tamanho
        if 'size' in df.columns:
            sizes = nonempty_unique(df['size'])
            # Manter valores numéricos, formatar label
            options['sizes'] = [{'label': f"{float(v):.2f}", 'value': float(v)} for v in sizes if pd.notna(v) and pd.notnull(v)]
        
        # Embalagem
        if 'package' in df.columns:
            packs = nonempty_unique(df['package'])
            options['packs'] = [{'label': p, 'value': p} for p in packs]
        
        return options
    except Exception as e:
        print(f"Erro ao carregar opções de filtros: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ============================================================================
# LAYOUT
# ============================================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Header
    html.Div([
        html.Div([
            html.A("← Voltar", href="https://femsa-cenario1-tfhauqj6vq-uc.a.run.app", target="_self", style={
                "color": COLORS['accent'],
                "textDecoration": "none",
                "fontSize": "14px",
                "marginRight": "20px"
            }),
            html.Img(
                src=app.get_asset_url("logo-femsa.png"),
                style={
                    "height": "50px",
                    "marginRight": "20px"
                }
            ),
            html.H1("Otimização de Mix de Produtos", style={
                "color": COLORS['accent'],
                "margin": "0",
                "fontSize": "24px"
            })
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "backgroundColor": COLORS['primary'],
        "padding": "20px 40px",
        "marginBottom": "30px"
    }),
    
    # Conteúdo Principal
    html.Div([
        # Seleção de Arquivo
        html.Div([
            html.H3("Configuração", className="section-title", style={
                "marginTop": "0",
                "fontSize": "18px",
                "fontWeight": "700",
                "color": COLORS['secondary']
            }),
            html.Div([
                html.Label("Arquivo de Dados:", style={
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": COLORS['gray_dark'],
                    "marginBottom": "8px"
                }),
                dcc.Dropdown(
                    id="data-file-select",
                    options=[
                        {"label": "data_unified_filtered.csv", "value": "data_unified_filtered.csv"},
                        {"label": "data_unified.csv", "value": "data_unified.csv"}
                    ],
                    value="data_unified_filtered.csv" if os.path.exists("data_unified_filtered.csv") else "data_unified.csv",
                    style={"marginBottom": "20px"}
                )
            ])
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        }),
        
        # Filtros
        html.Div([
            html.H3("Filtros", className="section-title", style={
                "marginTop": "0",
                "fontSize": "18px",
                "fontWeight": "700",
                "color": COLORS['secondary']
            }),
            html.Div([
                html.Div([
                    html.Label("Mês (depara_mess)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        id="f-month",
                        options=[],
                        value=None,
                        multi=True,
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Diretoria", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        id="f-dir",
                        options=[],
                        value=None,
                        multi=True,
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Marca", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        id="f-brand",
                        options=[],
                        value=None,
                        multi=True,
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Tamanho (L)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        id="f-size",
                        options=[],
                        value=None,
                        multi=True,
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Embalagem", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(
                        id="f-pack",
                        options=[],
                        value=None,
                        multi=True,
                        style={"fontSize": "13px"}
                    ),
                ], style={"width": "18%", "display": "inline-block"}),
            ], style={"marginBottom": "20px"}),
            html.Button("Calcular Mix Ótimo", id="btn-calculate", n_clicks=0, style={
                "backgroundColor": COLORS['primary'],
                "color": COLORS['accent'],
                "border": "none",
                "padding": "12px 32px",
                "borderRadius": "4px",
                "fontSize": "14px",
                "fontWeight": "600",
                "cursor": "pointer",
                "width": "100%"
            })
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        }),
        
        # Status e Resultados
        html.Div(id="optimization-status", style={"marginTop": "12px", "fontSize": "13px"}),
        html.Div(id="optimization-results")
    ], style={"padding": "40px", "maxWidth": "1400px", "margin": "0 auto"}),
], style={"backgroundColor": COLORS['background'], "minHeight": "100vh"})

# ============================================================================
# CALLBACKS
# ============================================================================
@app.callback(
    Output("f-month", "options"),
    Output("f-dir", "options"),
    Output("f-brand", "options"),
    Output("f-size", "options"),
    Output("f-pack", "options"),
    Input("data-file-select", "value")
)
def update_filter_options(data_file):
    """Atualiza as opções dos filtros quando o arquivo é selecionado."""
    if not data_file or not os.path.exists(data_file):
        return [], [], [], [], []
    
    options = load_filter_options(data_file)
    
    return (
        options.get('months', []),
        options.get('dirs', []),
        options.get('brands', []),
        options.get('sizes', []),
        options.get('packs', [])
    )

@app.callback(
    Output("optimization-status", "children"),
    Output("optimization-results", "children"),
    Input("btn-calculate", "n_clicks"),
    State("data-file-select", "value"),
    State("f-month", "value"),
    State("f-dir", "value"),
    State("f-brand", "value"),
    State("f-size", "value"),
    State("f-pack", "value"),
    prevent_initial_call=True
)
def calculate_mix_optimization(n_clicks, data_file, months, directorias, marcas, tamanhos, embalagens):
    """Executa a otimização de mix quando o botão é clicado."""
    if n_clicks == 0:
        return "", html.Div()
    
    try:
        # Carregar dados
        if not os.path.exists(data_file):
            return html.P(f"Arquivo não encontrado: {data_file}", style={"color": COLORS['error']}), html.Div()
        
        df_filtered = pd.read_csv(data_file, decimal=',', encoding='utf-8')
        
        # Converter colunas numéricas
        numeric_cols = ['volume_projetado', 'elasticidade', 'base_preco_bruto_unit', 
                        'base_preco_liquido_unit', 'base_gvv_labor_unit', 
                        'base_margem_variavel_unit', 'capacidade_min', 'capacidade_max']
        
        for col in numeric_cols:
            if col in df_filtered.columns:
                df_filtered[col] = df_filtered[col].astype(str).str.replace(',', '.').astype(float)
        
        # Aplicar filtros
        # Filtro de mês
        if months and 'depara_mess' in df_filtered.columns:
            months_dt = pd.to_datetime(months)
            df_filtered['depara_mess'] = pd.to_datetime(df_filtered['depara_mess'], errors='coerce')
            df_filtered = df_filtered[df_filtered['depara_mess'].isin(months_dt)]
        
        # Filtro de diretoria
        if directorias and 'diretoria' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['diretoria'].isin(directorias)]
        
        # Filtro de marca
        if marcas and 'brand' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['brand'].isin(marcas)]
        
        # Filtro de tamanho
        if tamanhos and 'size' in df_filtered.columns:
            df_filtered['size'] = pd.to_numeric(df_filtered['size'], errors='coerce')
            # Converter valores de filtro para float
            tamanhos_num = [float(t) if not isinstance(t, float) else t for t in tamanhos]
            df_filtered = df_filtered[df_filtered['size'].isin(tamanhos_num)]
        
        # Filtro de embalagem
        if embalagens and 'package' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['package'].isin(embalagens)]
        
        if df_filtered.empty:
            return html.P("Nenhum dado encontrado com os filtros selecionados.", style={"color": COLORS['error']}), html.Div()
        
        # Agregar por TIPO dentro de cada GRUPO_CAPACIDADE
        df_work = df_filtered.groupby(['grupo_capacidade', 'tipo']).agg({
            'volume_projetado': 'sum',
            'elasticidade': 'mean',
            'base_margem_variavel_unit': 'mean',
            'base_preco_liquido_unit': 'mean',
            'capacidade_min': 'first',
            'capacidade_max': 'first',
            'brand': lambda x: ', '.join(x.unique()[:3]),
            'package': 'first',
            'returnability': 'first'
        }).reset_index()
        
        # Executar otimização
        df_result, resultados = optimize_by_capacity_group(df_work)
        
        # Calcular resumo por TIPO
        df_tipo_summary = df_result.groupby('tipo').agg({
            'volume_projetado': 'sum',
            'volume_otimizado': 'sum',
            'lucro_otimizado': 'sum',
            'grupo_capacidade': 'first',
            'capacidade_max': 'first'
        }).reset_index()
        
        df_tipo_summary['atendimento_pct'] = (
            (df_tipo_summary['volume_otimizado'] / df_tipo_summary['volume_projetado'] * 100)
            .round(2)
        )
        
        df_tipo_summary = df_tipo_summary.sort_values('volume_otimizado', ascending=False)
        
        # Criar visualizações
        status_msg = html.P(f"✓ Otimização concluída! Processados {len(resultados)} grupos de capacidade.", 
                          style={"color": COLORS['success'], "fontWeight": "600"})
        
        # Tabela de resultados
        table = dash_table.DataTable(
            data=df_tipo_summary.to_dict('records'),
            columns=[
                {"name": "TIPO", "id": "tipo"},
                {"name": "GRUPO_CAPACIDADE", "id": "grupo_capacidade"},
                {"name": "DEMANDA", "id": "volume_projetado", "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "OTIMIZADO", "id": "volume_otimizado", "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "ATEND.%", "id": "atendimento_pct", "type": "numeric", "format": {"specifier": ".1f"}},
                {"name": "LUCRO (R$)", "id": "lucro_otimizado", "type": "numeric", "format": {"specifier": ",.2f"}}
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": COLORS['primary'], "color": COLORS['accent'], "fontWeight": "600"},
            sort_action="native"
        )
        
        # Métricas resumidas
        volume_total = df_tipo_summary['volume_otimizado'].sum()
        lucro_total = df_tipo_summary['lucro_otimizado'].sum()
        
        metrics_card = html.Div([
            html.H4("Resumo Geral", style={"marginBottom": "16px"}),
            html.Div([
                html.Div([
                    html.P("Volume Otimizado Total", style={"fontSize": "12px", "color": COLORS['gray_medium']}),
                    html.H3(f"{volume_total:,.0f} UC", style={"margin": "0", "color": COLORS['primary']})
                ], style={"flex": "1", "padding": "16px", "backgroundColor": COLORS['background'], "borderRadius": "4px", "marginRight": "16px"}),
                html.Div([
                    html.P("Lucro Total Otimizado", style={"fontSize": "12px", "color": COLORS['gray_medium']}),
                    html.H3(f"R$ {lucro_total:,.2f}", style={"margin": "0", "color": COLORS['success']})
                ], style={"flex": "1", "padding": "16px", "backgroundColor": COLORS['background'], "borderRadius": "4px"})
            ], style={"display": "flex", "marginBottom": "24px"})
        ], style={
            "backgroundColor": COLORS['accent'],
            "padding": "24px",
            "borderRadius": "4px",
            "border": f"1px solid {COLORS['gray_light']}",
            "marginBottom": "24px"
        })
        
        results_div = html.Div([
            metrics_card,
            html.Div([
                html.H4("Resultados Detalhados por TIPO", style={"marginBottom": "16px"}),
                table
            ], style={
                "backgroundColor": COLORS['accent'],
                "padding": "24px",
                "borderRadius": "4px",
                "border": f"1px solid {COLORS['gray_light']}"
            })
        ])
        
        return status_msg, results_div
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = html.P(f"Erro na otimização: {str(e)}", style={"color": COLORS['error']})
        return error_msg, html.Div()

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import os
    import sys
    
    try:
        print("Iniciando servidor Dash para Otimização de Mix...")
        # Cloud Run define PORT automaticamente (padrão 8080)
        # Se não definido, usar 8051 para desenvolvimento local
        port = int(os.environ.get('PORT', 8051))
        print(f"[INFO] Iniciando na porta: {port}")
        # Em produção, usar debug=False e host='0.0.0.0'
        debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
        print(f"[INFO] Debug mode: {debug_mode}")
        print(f"[INFO] Host: 0.0.0.0")
        
        # Forçar flush para garantir que logs apareçam
        sys.stdout.flush()
        sys.stderr.flush()
        
        # use_reloader=False é importante para produção
        app.run(debug=debug_mode, host='0.0.0.0', port=port, use_reloader=False)
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar servidor: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
