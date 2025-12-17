# ============================================================================
# FEMSA - Aplicação Unificada
# Combina Simulador de P&L e Otimização de Mix em uma única aplicação
# ============================================================================
import os
import sys
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.graph_objects as go
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# IMPORTAR FUNÇÕES DOS APPS ORIGINAIS
# ============================================================================
# Importar do app_cenario1_corporativo
try:
    from app_cenario1_corporativo import (
        df_master, MONTHS, DIRS, BRANDS, SIZES, RETS, PACKS, TIPOS,
        COLORS, PRETTY, COST_DRIVERS_SLIDERS,
        to_month, nonempty_unique, opts
    )
    PNL_AVAILABLE = True
except Exception as e:
    print(f"[AVISO] Não foi possível importar app_cenario1_corporativo: {e}")
    PNL_AVAILABLE = False
    COLORS = {
        'primary': '#F40009', 'primary_dark': '#C00007', 'primary_light': '#FF4D5A',
        'secondary': '#1A1A1A', 'accent': '#FFFFFF', 'gray_dark': '#4A4A4A',
        'gray_medium': '#8A8A8A', 'gray_light': '#E5E5E5', 'background': '#F8F8F8',
        'success': '#00A859', 'warning': '#FFB800', 'error': '#E60012',
    }

# Importar do app_mix_optimization
try:
    from app_mix_optimization import (
        optimize_by_capacity_group,
        optimize_single_tipo_group,
        optimize_multi_tipo_group,
        load_filter_options,
        nonempty_unique as nonempty_unique_mix
    )
    MIX_AVAILABLE = True
except Exception as e:
    print(f"[AVISO] Não foi possível importar app_mix_optimization: {e}")
    MIX_AVAILABLE = False

# ============================================================================
# CRIAR APP UNIFICADO
# ============================================================================
app = Dash(__name__)
app.title = "FEMSA - Plataforma Unificada de Análise"

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
            .section-title {
                font-size: 16px;
                font-weight: 600;
                color: #1A1A1A;
                margin: 24px 0 16px 0;
                padding-bottom: 8px;
                border-bottom: 2px solid #F40009;
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

# ============================================================================
# LAYOUT UNIFICADO COM TABS
# ============================================================================
app.layout = html.Div([
    # Header Corporativo
    html.Div([
        html.Div([
            html.Img(
                src=app.get_asset_url("logo-femsa.png"),
                style={"height": "60px", "marginRight": "24px"}
            ),
            html.Div([
                html.H1("FEMSA - Plataforma de Análise e Otimização", style={
                    "margin": "0", "fontSize": "24px", "fontWeight": "700"
                }),
                html.P("Simulador de P&L e Otimização de Mix de Produtos", style={
                    "margin": "8px 0 0 0", "fontSize": "14px", "opacity": "0.9"
                })
            ])
        ], style={"display": "flex", "alignItems": "center"})
    ], style={
        "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%)",
        "color": COLORS['accent'],
        "padding": "24px 40px",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
    }),
    
    # Tabs para navegação
    dcc.Tabs(
        id="main-tabs",
        value="tab-pnl",
        children=[
            dcc.Tab(
                label="📊 Simulador P&L",
                value="tab-pnl",
                style={"fontSize": "16px", "fontWeight": "600", "padding": "12px 24px"},
                selected_style={
                    "backgroundColor": COLORS['primary'],
                    "color": COLORS['accent'],
                    "borderTop": f"3px solid {COLORS['accent']}"
                }
            ),
            dcc.Tab(
                label="🎯 Otimização de Mix",
                value="tab-mix",
                style={"fontSize": "16px", "fontWeight": "600", "padding": "12px 24px"},
                selected_style={
                    "backgroundColor": COLORS['primary'],
                    "color": COLORS['accent'],
                    "borderTop": f"3px solid {COLORS['accent']}"
                }
            ),
        ],
        style={"marginBottom": "0", "backgroundColor": COLORS['background']}
    ),
    
    # Conteúdo das tabs
    html.Div(id="tab-content", style={"padding": "40px", "maxWidth": "1400px", "margin": "0 auto"})
], style={"backgroundColor": COLORS['background'], "minHeight": "100vh"})

# ============================================================================
# LAYOUT DO TAB P&L
# ============================================================================
def create_pnl_layout():
    """Cria o layout do Simulador P&L"""
    if not PNL_AVAILABLE:
        return html.Div([
            html.H2("Simulador de P&L", style={"color": COLORS['secondary']}),
            html.P("Funcionalidade não disponível. Verifique se app_cenario1_corporativo.py está configurado corretamente.",
                   style={"color": COLORS['error']})
        ])
    
    return html.Div([
        html.H2("Simulador de P&L", style={"color": COLORS['secondary'], "marginBottom": "24px"}),
        html.P("Para acessar o Simulador P&L completo, use o app dedicado:",
               style={"color": COLORS['gray_medium'], "marginBottom": "20px"}),
        html.A(
            html.Button("Abrir Simulador P&L Completo", style={
                "backgroundColor": COLORS['primary'],
                "color": COLORS['accent'],
                "border": "none",
                "padding": "12px 32px",
                "borderRadius": "4px",
                "fontSize": "14px",
                "fontWeight": "600",
                "cursor": "pointer"
            }),
            href="http://localhost:8050",
            target="_blank",
            style={"textDecoration": "none"}
        )
    ])

# ============================================================================
# LAYOUT DO TAB MIX
# ============================================================================
def create_mix_layout():
    """Cria o layout do Otimização de Mix"""
    if not MIX_AVAILABLE:
        return html.Div([
            html.H2("Otimização de Mix", style={"color": COLORS['secondary']}),
            html.P("Funcionalidade não disponível. Verifique se app_mix_optimization.py está configurado corretamente.",
                   style={"color": COLORS['error']})
        ])
    
    return html.Div([
        html.H2("Otimização de Mix de Produtos", style={
            "color": COLORS['secondary'],
            "marginBottom": "24px"
        }),
        
        # Seleção de Arquivo
        html.Div([
            html.H3("Configuração", className="section-title", style={
                "marginTop": "0", "fontSize": "18px", "fontWeight": "700", "color": COLORS['secondary']
            }),
            html.Div([
                html.Label("Arquivo de Dados:", style={
                    "fontSize": "13px", "fontWeight": "600", "color": COLORS['gray_dark'], "marginBottom": "8px"
                }),
                dcc.Dropdown(
                    id="data-file-select-mix",
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
                "marginTop": "0", "fontSize": "18px", "fontWeight": "700", "color": COLORS['secondary']
            }),
            html.Div([
                html.Div([
                    html.Label("Mês (depara_mess)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(id="f-month-mix", options=[], value=None, multi=True, style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Diretoria", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(id="f-dir-mix", options=[], value=None, multi=True, style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Marca", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(id="f-brand-mix", options=[], value=None, multi=True, style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Tamanho (L)", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(id="f-size-mix", options=[], value=None, multi=True, style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block", "marginRight": "2%"}),
                html.Div([
                    html.Label("Embalagem", style={"fontSize": "12px", "fontWeight": "600", "color": COLORS['gray_dark']}),
                    dcc.Dropdown(id="f-pack-mix", options=[], value=None, multi=True, style={"fontSize": "13px"}),
                ], style={"width": "18%", "display": "inline-block"}),
            ], style={"marginBottom": "20px"}),
            html.Button("Calcular Mix Ótimo", id="btn-calculate-mix", n_clicks=0, style={
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
        html.Div(id="optimization-status-mix", style={"marginTop": "12px", "fontSize": "13px"}),
        html.Div(id="optimization-results-mix")
    ])

# ============================================================================
# CALLBACKS PARA NAVEGAÇÃO ENTRE TABS
# ============================================================================
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value")
)
def render_tab_content(tab):
    """Renderiza o conteúdo baseado na tab selecionada"""
    if tab == "tab-pnl":
        return create_pnl_layout()
    elif tab == "tab-mix":
        return create_mix_layout()
    return html.Div("Tab não encontrada")

# ============================================================================
# CALLBACKS DO APP MIX
# ============================================================================
if MIX_AVAILABLE:
    @app.callback(
        Output("f-month-mix", "options"),
        Output("f-dir-mix", "options"),
        Output("f-brand-mix", "options"),
        Output("f-size-mix", "options"),
        Output("f-pack-mix", "options"),
        Input("data-file-select-mix", "value")
    )
    def update_filter_options_mix(data_file):
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
        Output("optimization-status-mix", "children"),
        Output("optimization-results-mix", "children"),
        Input("btn-calculate-mix", "n_clicks"),
        State("data-file-select-mix", "value"),
        State("f-month-mix", "value"),
        State("f-dir-mix", "value"),
        State("f-brand-mix", "value"),
        State("f-size-mix", "value"),
        State("f-pack-mix", "value"),
        prevent_initial_call=True
    )
    def calculate_mix_optimization_unified(n_clicks, data_file, months, directorias, marcas, tamanhos, embalagens):
        """Executa a otimização de mix quando o botão é clicado."""
        if n_clicks == 0:
            return "", html.Div()
        
        try:
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
            if months and 'depara_mess' in df_filtered.columns:
                months_dt = pd.to_datetime(months)
                df_filtered['depara_mess'] = pd.to_datetime(df_filtered['depara_mess'], errors='coerce')
                df_filtered = df_filtered[df_filtered['depara_mess'].isin(months_dt)]
            
            if directorias and 'diretoria' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['diretoria'].isin(directorias)]
            
            if marcas and 'brand' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['brand'].isin(marcas)]
            
            if tamanhos and 'size' in df_filtered.columns:
                df_filtered['size'] = pd.to_numeric(df_filtered['size'], errors='coerce')
                tamanhos_num = [float(t) if not isinstance(t, float) else t for t in tamanhos]
                df_filtered = df_filtered[df_filtered['size'].isin(tamanhos_num)]
            
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
    port = int(os.environ.get('PORT', 8052))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("FEMSA - Aplicação Unificada")
    print("=" * 60)
    print(f"Porta: {port}")
    print(f"PNL Disponível: {PNL_AVAILABLE}")
    print(f"Mix Disponível: {MIX_AVAILABLE}")
    print("=" * 60)
    print(f"Acesse: http://localhost:{port}")
    print("=" * 60)
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
