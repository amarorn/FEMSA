# simulador.py
import os
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.graph_objects as go
from scipy.optimize import differential_evolution

# =========================
# Configurações
# =========================
DATA_FILE = "simulador_pnl_futuro_base.csv"
PROJECAO_MP_FILE = "data/Materia prima (ajustada porcentagem vs BAU).xlsx"

# 1. Drivers de Custo (para os sliders)
COST_DRIVERS_SLIDERS = [
    "cvv_concentrate",
    "cvv_sweetener",
    "cvv_pet",
    "cvv_can",
    "cvv_cap",
    "cvv_purcharses",
    "cvv_otherraw",
]
# Nomes das colunas de custo no CSV base
COST_BUCKETS_BASE_COLS = [f"base_{c}_unit" for c in COST_DRIVERS_SLIDERS]

# 2. Legendas
PRETTY = {
    "cvv_concentrate": "Concentrate (% Receita)",
    "cvv_sweetener":   "Sweetener (R$/UC)",
    "cvv_pet":         "PET (R$/UC)",
    "cvv_can":         "Can (Lata) (R$/UC)",
    "cvv_cap":         "Cap (Tampa) (R$/UC)",
    "cvv_purcharses":  "Purchases (R$/UC)",
    "cvv_otherraw":    "Other Raw (R$/UC)",
}

# 3. Cores
COLOR_BASE = {
    "cvv_concentrate": "#6F36C5",
    "cvv_sweetener": "#1CCA6E",
    "cvv_pet": "#FF8400",
    "cvv_can": "#EB262C",
    "cvv_cap": "#FFCF08",
    "cvv_purcharses": "#F5025D",
    "cvv_otherraw": "#747577",
}

# =========================
# Utilitários
# =========================
def to_month(dt_like):
    """Converte datetime para primeiro dia do mês. Aceita Timestamp único ou Series."""
    if isinstance(dt_like, pd.Timestamp):
        return pd.Timestamp(dt_like.year, dt_like.month, 1)
    s = pd.to_datetime(dt_like, errors="coerce")
    return s.dt.to_period("M").dt.to_timestamp()

def nonempty_unique(x):
    return sorted([v for v in x.dropna().unique().tolist() if v != ""])

def opts(values, fmt=lambda x: x):
    return [{"label": fmt(v), "value": v} for v in values]

# =========================
# Motor da Simulação (Copiado do Notebook - Bloco 9 Corrigido)
# =========================
def run_pnl_simulation(
    base_df, 
    price_adj_pct=0.0, 
    shocks_pct={}
    ):
    """
    Roda o simulador de P&L com a regra de concentrate como % da receita.
    """
    df_sim = base_df.copy()
    
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
    
    # --- 3a. Custo Especial: Concentrate (% da Receita) ---
    df_sim['perc_concentrate_base'] = 0.0
    df_sim.loc[mask_preco_valido, 'perc_concentrate_base'] = (
        df_sim.loc[mask_preco_valido, 'base_cvv_concentrate_unit'].fillna(0) / 
        df_sim.loc[mask_preco_valido, 'base_preco_liquido_unit']
    )
    shock_conc_pct = shocks_pct.get('cvv_concentrate', 0.0)
    df_sim['perc_concentrate_simulado'] = df_sim['perc_concentrate_base'] * (1 + shock_conc_pct)
    df_sim['cvv_concentrate_simulado_unit'] = df_sim['preco_liquido_simulado_unit'] * df_sim['perc_concentrate_simulado']
    
    # --- 3b. Custos Padrão (os 6 restantes) ---
    df_sim['outros_custos_unit'] = df_sim['custo_total_base_unit']
    for col in COST_BUCKETS_BASE_COLS: # Iterar sobre os 7 drivers
        df_sim['outros_custos_unit'] -= df_sim[col].fillna(0)

    # Custo Total Simulado = Outros + (Concentrate Simulado) + (6 Drivers Simulados)
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

# =========================
# Modelo de Monte Carlo para Otimização
# =========================
def calculate_profitability(df_sim):
    """Calcula a lucratividade total (margem total) de um cenário simulado."""
    if df_sim.empty:
        return 0.0
    return df_sim['margem_total_simulada'].sum()

def monte_carlo_optimization(df_base, n_iterations=1000, price_range=(-0.2, 0.2), cost_range=(-0.5, 0.5)):
    """
    Executa Monte Carlo para encontrar o ponto ótimo de lucratividade.
    
    Args:
        df_base: DataFrame base filtrado
        n_iterations: Número de iterações do Monte Carlo
        price_range: Tupla (min, max) para variação de preço
        cost_range: Tupla (min, max) para variação de custos
    
    Returns:
        dict com os parâmetros ótimos e resultados
    """
    if df_base.empty:
        return None
    
    best_profit = float('-inf')
    best_params = None
    best_summary = None
    
    print(f"[INFO] Iniciando Monte Carlo com {n_iterations} iterações...")
    
    for i in range(n_iterations):
        # Gerar parâmetros aleatórios
        price_adj = np.random.uniform(price_range[0], price_range[1])
        
        shocks = {}
        for driver in COST_DRIVERS_SLIDERS:
            shocks[driver] = np.random.uniform(cost_range[0], cost_range[1])
        
        # Rodar simulação
        df_sim = run_pnl_simulation(df_base, price_adj_pct=price_adj, shocks_pct=shocks)
        
        # Calcular lucratividade
        profit = calculate_profitability(df_sim)
        
        # Atualizar melhor resultado
        if profit > best_profit:
            best_profit = profit
            best_params = {
                'price_adj': price_adj,
                'shocks': shocks.copy()
            }
            best_summary = summarize_pnl_df(df_sim, "Ótimo")
    
    print(f"[INFO] Monte Carlo concluído. Melhor lucratividade: R$ {best_profit:,.2f}")
    
    return {
        'params': best_params,
        'profit': best_profit,
        'summary': best_summary,
        'iterations': n_iterations
    }

def optimize_profitability(df_base, price_range=(-0.2, 0.2), cost_ranges=None):
    """
    Otimização usando scipy.optimize.differential_evolution.
    Mais eficiente que Monte Carlo puro.
    
    Args:
        df_base: DataFrame base filtrado
        price_range: Tupla (min, max) para variação de preço
        cost_ranges: Dicionário com ranges por driver, ex: {'cvv_concentrate': (-0.5, 0.5), ...}
                    Se None, usa (-0.5, 0.5) para todos
    """
    if df_base.empty:
        return None
    
    def objective(x):
        """Função objetivo: maximizar margem total (retorna negativo para minimização)."""
        price_adj = x[0]
        shocks = {COST_DRIVERS_SLIDERS[i]: x[i+1] for i in range(len(COST_DRIVERS_SLIDERS))}
        
        df_sim = run_pnl_simulation(df_base, price_adj_pct=price_adj, shocks_pct=shocks)
        profit = calculate_profitability(df_sim)
        
        return -profit  # Negativo porque scipy minimiza
    
    # Bounds: [price_adj, cvv_concentrate, cvv_sweetener, cvv_pet, cvv_can, cvv_cap, cvv_purcharses, cvv_otherraw]
    if cost_ranges is None:
        cost_ranges = {driver: (-0.5, 0.5) for driver in COST_DRIVERS_SLIDERS}
    
    bounds = [price_range] + [cost_ranges.get(driver, (-0.5, 0.5)) for driver in COST_DRIVERS_SLIDERS]
    
    print(f"[INFO] Iniciando otimização com Differential Evolution...")
    
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
        
        # Rodar simulação final com parâmetros ótimos
        df_optimal = run_pnl_simulation(df_base, price_adj_pct=optimal_price, shocks_pct=optimal_shocks)
        optimal_summary = summarize_pnl_df(df_optimal, "Ótimo")
        
        print(f"[INFO] Otimização concluída. Lucratividade ótima: R$ {-result.fun:,.2f}")
        
        return {
            'params': {
                'price_adj': optimal_price,
                'shocks': optimal_shocks
            },
            'profit': -result.fun,
            'summary': optimal_summary,
            'df_optimal': df_optimal
        }
    except Exception as e:
        print(f"[ERROR] Erro na otimização: {e}")
        import traceback
        traceback.print_exc()
        return None

def build_big_numbers_card(optimal_result):
    """Cria cards com big numbers do cenário ótimo."""
    if optimal_result is None:
        return html.Div([
            html.H3("Cenário Ótimo", style={"textAlign":"center","color":"#666"}),
            html.P("Execute a otimização para ver os resultados", style={"textAlign":"center","color":"#999"})
        ])
    
    summary = optimal_result['summary']
    params = optimal_result['params']
    
    return html.Div([
        html.H3("🎯 Cenário Ótimo de Lucratividade", style={
            "textAlign":"center",
            "color":"#1CCA6E",
            "marginBottom":"20px",
            "fontSize":"24px",
            "fontWeight":"bold"
        }),
        html.Div([
            html.Div([
                html.Div([
                    html.H4("Receita Total", style={"margin":"0","color":"#666","fontSize":"14px"}),
                    html.H2(f"R$ {summary['Receita Total']:,.0f}", style={
                        "margin":"5px 0",
                        "color":"#6F36C5",
                        "fontSize":"32px",
                        "fontWeight":"bold"
                    })
                ], style={"textAlign":"center","padding":"20px","backgroundColor":"#f8f9fa","borderRadius":"8px","margin":"5px"})
            ], style={"width":"24%","display":"inline-block"}),
            html.Div([
                html.Div([
                    html.H4("Margem Total", style={"margin":"0","color":"#666","fontSize":"14px"}),
                    html.H2(f"R$ {summary['Margem Total']:,.0f}", style={
                        "margin":"5px 0",
                        "color":"#1CCA6E",
                        "fontSize":"32px",
                        "fontWeight":"bold"
                    })
                ], style={"textAlign":"center","padding":"20px","backgroundColor":"#f8f9fa","borderRadius":"8px","margin":"5px"})
            ], style={"width":"24%","display":"inline-block"}),
            html.Div([
                html.Div([
                    html.H4("Volume Total", style={"margin":"0","color":"#666","fontSize":"14px"}),
                    html.H2(f"{summary['Volume Total']:,.0f} UC", style={
                        "margin":"5px 0",
                        "color":"#FF8400",
                        "fontSize":"32px",
                        "fontWeight":"bold"
                    })
                ], style={"textAlign":"center","padding":"20px","backgroundColor":"#f8f9fa","borderRadius":"8px","margin":"5px"})
            ], style={"width":"24%","display":"inline-block"}),
            html.Div([
                html.Div([
                    html.H4("Margem %", style={"margin":"0","color":"#666","fontSize":"14px"}),
                    html.H2(f"{summary['Margem %']:.2%}", style={
                        "margin":"5px 0",
                        "color":"#EB262C",
                        "fontSize":"32px",
                        "fontWeight":"bold"
                    })
                ], style={"textAlign":"center","padding":"20px","backgroundColor":"#f8f9fa","borderRadius":"8px","margin":"5px"})
            ], style={"width":"24%","display":"inline-block"}),
        ], style={"display":"flex","justifyContent":"space-around","marginBottom":"20px"}),
        html.Div([
            html.H5("Parâmetros Ótimos Aplicados:", style={"marginBottom":"10px","color":"#333"}),
            html.Div([
                html.P(f"📈 Choque de Preço: {params['price_adj']:.2%}", style={"margin":"5px","fontSize":"14px"}),
            ] + [
                html.P(f"📊 {PRETTY.get(driver, driver)}: {params['shocks'][driver]:.2%}", 
                      style={"margin":"5px","fontSize":"14px"})
                for driver in COST_DRIVERS_SLIDERS
            ], style={"backgroundColor":"#fff","padding":"15px","borderRadius":"8px","border":"1px solid #ddd"})
        ], style={"marginTop":"20px"})
    ], style={"backgroundColor":"#ffffff","padding":"30px","borderRadius":"12px","boxShadow":"0 2px 4px rgba(0,0,0,0.1)","marginBottom":"30px"})

# =========================
# Funções de Plotagem e Tabela
# =========================

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

# =========================
# Função de Otimização Monte Carlo
# =========================
def objective_function(params, df_base):
    """
    Função objetivo: maximizar margem total (minimizar negativo da margem).
    params: [price_adj, shock_conc, shock_sweet, shock_pet, shock_can, shock_cap, shock_purch, shock_other]
    """
    price_adj = params[0]
    shocks = {
        'cvv_concentrate': params[1],
        'cvv_sweetener': params[2],
        'cvv_pet': params[3],
        'cvv_can': params[4],
        'cvv_cap': params[5],
        'cvv_purcharses': params[6],
        'cvv_otherraw': params[7]
    }
    
    df_sim = run_pnl_simulation(df_base, price_adj_pct=price_adj, shocks_pct=shocks)
    total_margem = df_sim['margem_total_simulada'].sum()
    
    # Retornar negativo porque estamos minimizando
    return -total_margem

# =========================
# Funções de Plotagem e Tabela
# =========================
def calculate_average_pu(df_base, df_sim, df_proj=None):
    """Calcula o P&L Unitário (R$/UC) MÉDIO PONDERADO para o baseline, simulado e projetado."""
    
    # Baseline
    vol_base = df_base['volume_projetado'].sum()
    if vol_base == 0:
        return None, None, None
        
    pu_base = {}
    pu_base['rev_total'] = (df_base['volume_projetado'] * df_base['base_preco_liquido_unit']).sum() / vol_base
    for col_key in COST_DRIVERS_SLIDERS:
        col_base_name = f"base_{col_key}_unit"
        pu_base[col_key] = (df_base['volume_projetado'] * df_base[col_base_name]).sum() / vol_base
    pu_base['var_margin'] = pu_base['rev_total'] - sum(pu_base.get(c, 0) for c in COST_DRIVERS_SLIDERS)

    # Simulado
    vol_sim = df_sim['volume_simulado'].sum()
    pu_sim = None
    if vol_sim > 0:
        pu_sim = {}
        pu_sim['rev_total'] = (df_sim['volume_simulado'] * df_sim['preco_liquido_simulado_unit']).sum() / vol_sim
        for col_key in COST_DRIVERS_SLIDERS:
            sim_col_name = f'{col_key}_simulado_unit'
            pu_sim[col_key] = (df_sim['volume_simulado'] * df_sim[sim_col_name]).sum() / vol_sim
        pu_sim['var_margin'] = pu_sim['rev_total'] - sum(pu_sim.get(c, 0) for c in COST_DRIVERS_SLIDERS)
    
    # Projetado
    pu_proj = None
    if df_proj is not None:
        vol_proj = df_proj['volume_projetado'].sum()
        if vol_proj > 0:
            pu_proj = {}
            pu_proj['rev_total'] = (df_proj['volume_projetado'] * df_proj['base_preco_liquido_unit']).sum() / vol_proj
            for col_key in COST_DRIVERS_SLIDERS:
                col_base_name = f"base_{col_key}_unit"
                pu_proj[col_key] = (df_proj['volume_projetado'] * df_proj[col_base_name]).sum() / vol_proj
            pu_proj['var_margin'] = pu_proj['rev_total'] - sum(pu_proj.get(c, 0) for c in COST_DRIVERS_SLIDERS)

    return pu_base, pu_sim, pu_proj


def build_pnl_total_fig(df_base, df_sim, df_proj=None):
    """Cria o gráfico de barras agrupadas para P&L Total com 3 cenários."""
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
        name='Receita Total', marker_color='#6F36C5',
        text=receita_text,
        textposition='auto', textfont_size=14
    ))
    fig.add_trace(go.Bar(
        x=x_labels, y=margem_vals,
        name='Margem Total', marker_color='#1CCA6E',
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

def build_tabela_razao(df_base, df_sim, df_proj=None):
    """Cria tabela razão com dados importantes para análise detalhada."""
    if df_base.empty:
        return html.Div("Sem dados para o filtro selecionado.", style={"color":"#900"})
    
    # Criar lista de dataframes para cada cenário
    dfs_razao = []
    
    # Cenário Base
    if 'month' in df_base.columns and 'diretoria' in df_base.columns and 'chave_sku' in df_base.columns:
        df_base_razao = pd.DataFrame({
            'Cenário': 'Base',
            'Mês': pd.to_datetime(df_base['month']).dt.strftime('%Y-%m'),
            'Diretoria': df_base['diretoria'],
            'SKU': df_base['chave_sku'],
            'Volume': df_base['volume_projetado'],
            'Preço Unitário': df_base['base_preco_liquido_unit'],
            'Receita Total': df_base['volume_projetado'] * df_base['base_preco_liquido_unit'],
            'Margem Unitária': df_base['base_margem_variavel_unit'],
            'Margem Total': df_base['volume_projetado'] * df_base['base_margem_variavel_unit']
        })
        if 'elasticidade' in df_base.columns:
            df_base_razao['Elasticidade'] = df_base['elasticidade']
        dfs_razao.append(df_base_razao)
    
    # Cenário Simulado
    if not df_sim.empty and 'chave_sku' in df_sim.columns:
        df_sim_razao = pd.DataFrame({
            'Cenário': 'Simulado',
            'Mês': pd.to_datetime(df_sim['month']).dt.strftime('%Y-%m') if 'month' in df_sim.columns else '',
            'Diretoria': df_sim['diretoria'] if 'diretoria' in df_sim.columns else '',
            'SKU': df_sim['chave_sku'],
            'Volume': df_sim['volume_simulado'],
            'Preço Unitário': df_sim['preco_liquido_simulado_unit'],
            'Receita Total': df_sim['receita_total_simulada'],
            'Margem Unitária': df_sim['margem_simulada_unit'],
            'Margem Total': df_sim['margem_total_simulada']
        })
        if 'elasticidade' in df_sim.columns:
            df_sim_razao['Elasticidade'] = df_sim['elasticidade']
        dfs_razao.append(df_sim_razao)
    
    # Cenário Projetado
    if df_proj is not None and not df_proj.empty and 'chave_sku' in df_proj.columns:
        df_proj_razao = pd.DataFrame({
            'Cenário': 'Projetado',
            'Mês': pd.to_datetime(df_proj['month']).dt.strftime('%Y-%m') if 'month' in df_proj.columns else '',
            'Diretoria': df_proj['diretoria'] if 'diretoria' in df_proj.columns else '',
            'SKU': df_proj['chave_sku'],
            'Volume': df_proj['volume_simulado'],
            'Preço Unitário': df_proj['preco_liquido_simulado_unit'],
            'Receita Total': df_proj['receita_total_simulada'],
            'Margem Unitária': df_proj['margem_simulada_unit'],
            'Margem Total': df_proj['margem_total_simulada']
        })
        if 'elasticidade' in df_proj.columns:
            df_proj_razao['Elasticidade'] = df_proj['elasticidade']
        dfs_razao.append(df_proj_razao)
    
    if not dfs_razao:
        return html.Div("Sem dados para exibir na tabela razão.", style={"color":"#900"})
    
    # Concatenar todos os dataframes
    df_razao_final = pd.concat(dfs_razao, ignore_index=True)
    
    # Formatar valores numéricos
    if 'Volume' in df_razao_final.columns:
        df_razao_final['Volume'] = df_razao_final['Volume'].apply(lambda x: f"{x:,.2f} UC" if pd.notna(x) else "0,00 UC")
    
    if 'Preço Unitário' in df_razao_final.columns:
        df_razao_final['Preço Unitário'] = df_razao_final['Preço Unitário'].apply(lambda x: f"R$ {x:,.4f}" if pd.notna(x) else "R$ 0,0000")
    
    if 'Receita Total' in df_razao_final.columns:
        df_razao_final['Receita Total'] = df_razao_final['Receita Total'].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "R$ 0,00")
    
    if 'Margem Unitária' in df_razao_final.columns:
        df_razao_final['Margem Unitária'] = df_razao_final['Margem Unitária'].apply(lambda x: f"R$ {x:,.4f}" if pd.notna(x) else "R$ 0,0000")
    
    if 'Margem Total' in df_razao_final.columns:
        df_razao_final['Margem Total'] = df_razao_final['Margem Total'].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "R$ 0,00")
    
    if 'Elasticidade' in df_razao_final.columns:
        df_razao_final['Elasticidade'] = df_razao_final['Elasticidade'].apply(lambda x: f"{x:,.4f}" if pd.notna(x) else "0,0000")
    
    tabela = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in df_razao_final.columns],
        data=df_razao_final.to_dict('records'),
        style_cell={"textAlign":"left","padding":"6px","fontSize":"11px"},
        style_header={"backgroundColor":"#f4f4f4","fontWeight":"600"},
        style_table={"overflowX":"auto"},
        page_size=20,
        sort_action="native",
        filter_action="native"
    )
    
    return tabela

def build_cost_driver_fig(pu_base, pu_sim, pu_proj=None):
    """Cria o gráfico de barras empilhadas de Custo Unitário (R$/UC) com 3 cenários."""
    fig = go.Figure()
    
    if pu_base is None:
        return fig.update_layout(title="Sem dados para o filtro selecionado.")
        
    order = COST_DRIVERS_SLIDERS # Nomes dos 7 drivers
    
    # Barras do Baseline
    for k in order:
        fig.add_bar(
            x=["Baseline"], y=[pu_base.get(k, 0.0)],
            name=PRETTY.get(k, k),
            legendgroup=k,
            showlegend=True,
            marker_color=COLOR_BASE.get(k, "#222"),
            hovertemplate=PRETTY.get(k, k) + " — Baseline: R$%{y:.4f}/UC<extra></extra>"
        )
    
    # Barras do Simulado
    if pu_sim is not None:
        for k in order:
            fig.add_bar(
                x=["Simulado"], y=[pu_sim.get(k, 0.0)],
                name=PRETTY.get(k, k),
                legendgroup=k,
                showlegend=False,
                marker_color=COLOR_BASE.get(k, "#C00"), 
                hovertemplate=PRETTY.get(k, k) + " — Simulado: R$%{y:.4f}/UC<extra></extra>"
            )
    
    # Barras do Projetado
    if pu_proj is not None:
        for k in order:
            fig.add_bar(
                x=["Projetado"], y=[pu_proj.get(k, 0.0)],
                name=PRETTY.get(k, k),
                legendgroup=k,
                showlegend=False,
                marker_color=COLOR_BASE.get(k, "#888"), 
                hovertemplate=PRETTY.get(k, k) + " — Projetado: R$%{y:.4f}/UC<extra></extra>"
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
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.2, yanchor="top", itemsizing="constant",
            font=dict(size=11), bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=60, r=20, t=50, b=120)
    )
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    return fig

# =========================
# Função para carregar percentuais YoY de matéria-prima
# =========================
def map_item_to_driver(item_name):
    """
    De-para direto: mapeia item de matéria-prima para driver de custo.
    
    De-para:
    - Lata → cvv_can (Can/Lata)
    - Garrafa PET → cvv_pet (PET)
    - Garrafa OWG → cvv_pet (PET)
    - Tampas → cvv_cap (Cap/Tampa)
    - Açúcar → cvv_sweetener (Sweetener)
    - Bag → cvv_purcharses (Purchases)
    - Cx. Papelão/BIB → cvv_purcharses (Purchases)
    - Concentrate não está na tabela (é % da receita, não tem YoY)
    """
    if not item_name or pd.isna(item_name):
        return None
    
    item_lower = str(item_name).lower().strip()
    
    # De-para direto
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
    """
    Carrega percentuais YoY do arquivo de matéria-prima.
    Estrutura: Linha 0 tem "ITEM" na coluna 1 e datas nas colunas 3-14.
    Os percentuais YoY estão nas colunas 3-14 para cada item.
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] Arquivo de matéria-prima não encontrado: {file_path}")
        return None
    
    try:
        # Ler arquivo com header na linha 0
        df = pd.read_excel(file_path, header=0)
        
        # Verificar se coluna "ITEM" existe
        if 'ITEM' not in df.columns:
            print("[ERROR] Coluna 'ITEM' não encontrada no arquivo")
            return None
        
        # Procurar colunas de percentuais YoY
        # Primeiro, tentar encontrar colunas com nomes como "Jan-25", "Fev-25", etc.
        yoy_columns = []
        month_map = {
            'JAN': 1, 'FEB': 2, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'APR': 4,
            'MAI': 5, 'MAY': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8, 'AUG': 8,
            'SET': 9, 'SEP': 9, 'OUT': 10, 'OCT': 10, 'NOV': 11, 'DEZ': 12, 'DEC': 12
        }
        
        for i, col in enumerate(df.columns):
            col_str = str(col).upper().strip()
            # Procurar por padrões como "JAN-25", "JAN 25", "JAN/25", etc.
            for month_name, month_num in month_map.items():
                if month_name in col_str and ('25' in col_str or '2025' in col_str):
                    date_val = pd.to_datetime(f'2025-{month_num:02d}-01')
                    yoy_columns.append((col, date_val, i))
                    break
        
        # Se não encontrou colunas nomeadas, usar colunas 3-14 (assumindo que são os percentuais)
        if not yoy_columns:
            print("[INFO] Colunas 'Jan-25', 'Fev-25', etc. não encontradas. Usando colunas 3-14 como percentuais YoY.")
            for i, col in enumerate(df.columns):
                if i >= 3 and i <= 14:  # Colunas 3-14
                    try:
                        date_val = pd.to_datetime(col)
                        yoy_columns.append((col, date_val, i))
                    except:
                        pass
        
        if not yoy_columns:
            print("[ERROR] Não foi possível identificar colunas de percentuais YoY")
            return None
        
        print(f"[INFO] Encontradas {len(yoy_columns)} colunas de percentuais YoY")
        
        # Criar DataFrame para armazenar percentuais
        results = []
        items_processed = 0
        items_mapped = {}
        
        # Processar cada linha de dados
        for idx, row in df.iterrows():
            item_name = row['ITEM']
            
            if pd.isna(item_name) or str(item_name).strip() == '' or str(item_name).lower() == 'nan':
                continue
            
            items_processed += 1
            
            # Mapear item para driver
            driver = map_item_to_driver(item_name)
            
            if driver is None:
                continue  # Pular itens que não mapeiam para drivers conhecidos
            
            items_mapped[driver] = items_mapped.get(driver, []) + [str(item_name)]
            
            # Extrair percentuais YoY de cada coluna
            for col_name, date_val, col_idx in yoy_columns:
                pct_val = row.iloc[col_idx]  # Usar índice da coluna
                if pd.notna(pct_val):
                    try:
                        pct = float(pct_val)
                        # Se estiver entre -1 e 1, usar direto. Se maior, dividir por 100
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
        
        print(f"[INFO] Itens processados: {items_processed}")
        print(f"[INFO] Itens mapeados por driver: {[(k, len(v)) for k, v in items_mapped.items()]}")
        
        if not results:
            print("[ERROR] Nenhum percentual YoY encontrado após processamento")
            print(f"[ERROR] Itens processados: {items_processed}, mas nenhum percentual extraído")
            return None
        
        df_yoy = pd.DataFrame(results)
        
        # Agregar por driver e mês (média dos itens do mesmo driver)
        df_yoy_agg = df_yoy.groupby(['driver', 'month'])['yoy_pct'].mean().reset_index()
        
        print(f"[INFO] ✅ Percentuais YoY carregados: {len(df_yoy_agg)} combinações driver/mês")
        print(f"[INFO] ✅ Drivers encontrados: {sorted(df_yoy_agg['driver'].unique())}")
        
        # Validar que temos os drivers principais (exceto concentrate que não tem na tabela)
        expected_drivers = ['cvv_sweetener', 'cvv_pet', 'cvv_can', 'cvv_cap', 'cvv_purcharses']
        found_drivers = set(df_yoy_agg['driver'].unique())
        missing = set(expected_drivers) - found_drivers
        if missing:
            print(f"[WARNING] Drivers esperados mas não encontrados: {missing}")
        
        # Garantir que temos pelo menos alguns drivers
        if len(found_drivers) == 0:
            print("[ERROR] Nenhum driver foi mapeado corretamente!")
            return None
        
        return df_yoy_agg
        
    except Exception as e:
        print(f"[ERROR] Erro ao carregar percentuais YoY: {e}")
        import traceback
        traceback.print_exc()
        return None

# =========================
# Carregamento de dados
# =========================
if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(
        f"Arquivo '{DATA_FILE}' não encontrado. "
        "Execute o notebook Jupyter para gerar o arquivo CSV primeiro."
    )

print(f"[INFO] Carregando dados base: {DATA_FILE}")
df_master = pd.read_csv(DATA_FILE, decimal=',')

# Converter colunas de data
df_master['month'] = to_month(df_master['depara_mess'])

# Carregar percentuais YoY de matéria-prima
df_mp_yoy = load_mp_yoy_percentages(PROJECAO_MP_FILE)

# =========================
# "Quebrar" a Chave SKU para os Filtros
# =========================
print("[INFO] Criando colunas de filtro a partir da 'chave_sku'...")
try:
    sku_parts = df_master['chave_sku'].str.split('|', expand=True)
    df_master['brand'] = sku_parts[0]
    df_master['size'] = pd.to_numeric(sku_parts[1], errors='coerce')
    df_master['tipo_consumo'] = sku_parts[2]
    df_master['returnability'] = sku_parts[3]
    df_master['package'] = sku_parts[4]
except Exception as e:
    print(f"Erro ao quebrar a chave_sku: {e}. Verifique o formato do CSV.")
    raise

print("[INFO] Dados carregados com sucesso.")

# =========================
# Preparar listas para filtros (CORRIGIDO)
# =========================
MONTHS = nonempty_unique(df_master["month"])
DIRS   = nonempty_unique(df_master["diretoria"])
# REGIONS = nonempty_unique(df_master["regional"]) # <-- COLUNA REMOVIDA
# Adicionando os filtros de SKU
BRANDS = nonempty_unique(df_master["brand"])
SIZES  = nonempty_unique(df_master["size"])
RETS   = nonempty_unique(df_master["returnability"])
PACKS  = nonempty_unique(df_master["package"])
TIPOS  = nonempty_unique(df_master["tipo_consumo"])

# =========================
# App Dash
# =========================
app = Dash(__name__)
app.title = "Simulador de P&L Futuro"

app.layout = html.Div([
    html.H2("Simulador de Cenário de P&L Futuro (2025)"),
    html.P("Selecione filtros e ajuste os 'choques' de preço e custo para simular o impacto no P&L total projetado."),
    
    # --- SEÇÃO DE OTIMIZAÇÃO E BIG NUMBERS ---
    html.Div([
        html.Div([
            html.H4("🎯 Otimização de Lucratividade", style={"marginBottom":"10px"}),
            html.P("Encontre o ponto ótimo de lucratividade testando diferentes combinações de preço e custos de matéria-prima.", 
                   style={"marginBottom":"15px","color":"#666"}),
            
            # Configuração de Limites
            html.Div([
                html.H5("Configuração de Limites para Otimização", style={"marginBottom":"15px","color":"#333","fontSize":"16px"}),
                html.P("Defina os limites mínimo e máximo (em %) para cada variável na otimização:", 
                       style={"marginBottom":"10px","color":"#666","fontSize":"13px"}),
                
                # Preço
                html.Div([
                    html.Label("Choque de Preço:", style={"fontWeight":"bold","width":"200px","display":"inline-block"}),
                    html.Label("Min: ", style={"marginLeft":"10px","display":"inline-block"}),
                    dcc.Input(id="opt-price-min", type="number", value=-0.2, step=0.01, 
                             style={"width":"80px","marginRight":"15px","display":"inline-block"}),
                    html.Label("Max: ", style={"display":"inline-block"}),
                    dcc.Input(id="opt-price-max", type="number", value=0.2, step=0.01, 
                             style={"width":"80px","display":"inline-block"})
                ], style={"marginBottom":"10px","padding":"8px","backgroundColor":"#f8f9fa","borderRadius":"4px"}),
                
                # Drivers de Custo
                html.Div([
                    html.Div([
                        html.Label(f"{PRETTY.get(driver, driver)}:", style={"fontWeight":"bold","width":"200px","display":"inline-block"}),
                        html.Label("Min: ", style={"marginLeft":"10px","display":"inline-block"}),
                        dcc.Input(id=f"opt-{driver}-min", type="number", value=-0.5, step=0.01, 
                                 style={"width":"80px","marginRight":"15px","display":"inline-block"}),
                        html.Label("Max: ", style={"display":"inline-block"}),
                        dcc.Input(id=f"opt-{driver}-max", type="number", value=0.5, step=0.01, 
                                 style={"width":"80px","display":"inline-block"})
                    ], style={"marginBottom":"8px","padding":"6px","backgroundColor":"#f8f9fa","borderRadius":"4px"})
                    for driver in COST_DRIVERS_SLIDERS
                ]),
                
            ], style={"marginBottom":"20px","padding":"15px","backgroundColor":"#ffffff","border":"1px solid #ddd","borderRadius":"8px"}),
            
            html.Button("Executar Otimização", id="btn-optimize", n_clicks=0, style={
                "backgroundColor":"#1CCA6E",
                "color":"white",
                "border":"none",
                "padding":"12px 24px",
                "borderRadius":"6px",
                "fontSize":"16px",
                "fontWeight":"bold",
                "cursor":"pointer"
            }),
            html.Div(id="optimization-status", style={"marginTop":"10px","fontSize":"14px","color":"#666"})
        ], style={"textAlign":"left","marginBottom":"20px"}),
        html.Div(id="big-numbers-card")
    ], style={"marginBottom":"30px"}),
    
    html.Hr(),
    
    # --- FILTROS (CORRIGIDO: Sem Regional) ---
    html.Div([
        html.Div([
            html.Label("Mês (Projeção)"),
            dcc.Dropdown(options=[{'label': pd.to_datetime(m).strftime('%Y-%m'), 'value': str(m)} for m in MONTHS], value=None, multi=True, id="f-month"),
        ], style={"width":"20%","display":"inline-block","marginRight":"1%"}),
        html.Div([
            html.Label("Diretoria"),
            dcc.Dropdown(options=DIRS, value=None, multi=True, id="f-dir"),
        ], style={"width":"24%","display":"inline-block","marginRight":"1%"}),
        html.Div([
            html.Label("Marca"),
            dcc.Dropdown(options=BRANDS, value=None, multi=True, id="f-brand"),
        ], style={"width":"24%","display":"inline-block","marginRight":"1%"}),
        html.Div([
            html.Label("Tamanho (L)"),
            dcc.Dropdown(options=opts(SIZES, fmt=lambda v: f"{float(v):.2f}"), value=None, multi=True, id="f-size"),
        ], style={"width":"14%","display":"inline-block", "marginRight":"1%"}),
        html.Div([
            html.Label("Embalagem"),
            dcc.Dropdown(options=PACKS, value=None, multi=True, id="f-pack"),
        ], style={"width":"14%","display":"inline-block"}),
        
    ], style={"marginBottom":"10px"}),
    
    html.Hr(),

    html.Div([
        # --- SLIDERS ---
        html.Div([
            html.H4("1. Choque de Preço"),
            dcc.Slider(min=-0.2, max=0.2, step=0.01, value=0.0, id="adj-price",
                       marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Small("valor em % (ex.: 0.05 = +5%)"),
            html.Hr(),
            html.H4("2. Choques de Custo (MP)"),
            
            html.Label(PRETTY.get('cvv_concentrate')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_concentrate", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_sweetener')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_sweetener", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_pet')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_pet", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_can')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_can", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_cap')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_cap", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_purcharses')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_purcharses", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            html.Label(PRETTY.get('cvv_otherraw')),
            dcc.Slider(min=-0.5, max=0.5, step=0.01, value=0.0, id="shock-cvv_otherraw", marks=None, tooltip={"placement":"bottom","always_visible":True}),
            
        ], style={"width":"34%","display":"inline-block","verticalAlign":"top","paddingRight":"16px"}),
        
        # --- GRÁFICOS (DOIS GRÁFICOS) ---
        html.Div([
            dcc.Graph(id="fig-pnl-total"),
            html.Hr(),
            dcc.Graph(id="fig-cost-driver-breakdown"), # O gráfico de R$/UC
        ], style={"width": "64%", "display": "inline-block", "verticalAlign": "top"}),
    ]),

    html.Hr(),
    html.H4("Resumo do P&L Simulado"),
    html.Div(id="pnl-table"), # Tabela de resumo
    html.Hr(),
    html.H4("Tabela Razão - Detalhamento dos Dados"),
    html.Div(id="tabela-razao"), # Tabela razão com dados importantes
    
    # Store para resultado da otimização
    dcc.Store(id="store-optimization-result")
])

# =========================
# Callback de Otimização
# =========================
@app.callback(
    Output("store-optimization-result", "data"),
    Output("big-numbers-card", "children"),
    Output("optimization-status", "children"),
    Input("btn-optimize", "n_clicks"),
    State("f-month","value"),
    State("f-dir","value"),
    State("f-brand","value"),
    State("f-size","value"),
    State("f-pack","value"),
    State("opt-price-min","value"),
    State("opt-price-max","value"),
    State("opt-cvv_concentrate-min","value"),
    State("opt-cvv_concentrate-max","value"),
    State("opt-cvv_sweetener-min","value"),
    State("opt-cvv_sweetener-max","value"),
    State("opt-cvv_pet-min","value"),
    State("opt-cvv_pet-max","value"),
    State("opt-cvv_can-min","value"),
    State("opt-cvv_can-max","value"),
    State("opt-cvv_cap-min","value"),
    State("opt-cvv_cap-max","value"),
    State("opt-cvv_purcharses-min","value"),
    State("opt-cvv_purcharses-max","value"),
    State("opt-cvv_otherraw-min","value"),
    State("opt-cvv_otherraw-max","value"),
    prevent_initial_call=True
)
def run_optimization(n_clicks, months, directorias, marcas, tamanhos, embalagens,
                    price_min, price_max,
                    conc_min, conc_max,
                    sweet_min, sweet_max,
                    pet_min, pet_max,
                    can_min, can_max,
                    cap_min, cap_max,
                    purch_min, purch_max,
                    other_min, other_max):
    """Executa otimização quando o botão é clicado."""
    if n_clicks == 0:
        return None, html.Div(), ""
    
    # Filtrar dados base
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
        return None, html.Div(), html.P("❌ Sem dados para otimizar com os filtros selecionados.", style={"color":"#EB262C"})
    
    # Validar e preparar limites
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
        
        # Validar que min < max para todos
        if price_range[0] >= price_range[1]:
            return None, html.Div(), html.P("❌ Erro: Min de Preço deve ser menor que Max.", style={"color":"#EB262C"})
        
        for driver, (min_val, max_val) in cost_ranges.items():
            if min_val >= max_val:
                return None, html.Div(), html.P(f"❌ Erro: Min de {PRETTY.get(driver, driver)} deve ser menor que Max.", style={"color":"#EB262C"})
        
    except (ValueError, TypeError) as e:
        return None, html.Div(), html.P(f"❌ Erro ao processar limites: {str(e)}", style={"color":"#EB262C"})
    
    # Executar otimização
    status_msg = html.P("⏳ Executando otimização... Isso pode levar alguns segundos.", style={"color":"#FF8400"})
    
    try:
        optimal_result = optimize_profitability(df_base_filtrado, price_range=price_range, cost_ranges=cost_ranges)
        
        if optimal_result is None:
            return None, html.Div(), html.P("❌ Erro na otimização.", style={"color":"#EB262C"})
        
        # Criar big numbers card
        big_numbers = build_big_numbers_card(optimal_result)
        
        # Preparar dados para store (serializar)
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
        
        status_msg = html.P("✅ Otimização concluída com sucesso!", style={"color":"#1CCA6E","fontWeight":"bold"})
        
        return store_data, big_numbers, status_msg
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro: {str(e)}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return None, html.Div(), html.P(error_msg, style={"color":"#EB262C"})

# =========================
# Callback Principal (CORRIGIDO)
# =========================
@app.callback(
    Output("fig-pnl-total", "figure"),
    Output("fig-cost-driver-breakdown", "figure"),
    Output("pnl-table", "children"),
    Output("tabela-razao", "children"),
    [
        Input("f-month","value"),
        Input("f-dir","value"),
        # Input("f-ter","value"), # <-- REMOVIDO
        Input("f-brand","value"),
        Input("f-size","value"),
        Input("f-pack","value"),
        Input("adj-price","value"),
        Input("shock-cvv_concentrate","value"),
        Input("shock-cvv_sweetener","value"),
        Input("shock-cvv_pet","value"),
        Input("shock-cvv_can","value"),
        Input("shock-cvv_cap","value"),
        Input("shock-cvv_purcharses","value"),
        Input("shock-cvv_otherraw","value"),
    ]
)
def update_simulation_view(
    months, directorias, marcas, tamanhos, embalagens, # 'regionais' removido
    price_adj, 
    s_conc, s_sweet, s_pet, s_can, s_cap, s_purch, s_other
    ):

    # 1. Filtrar o Master DataFrame
    df_base_filtrado = df_master.copy()
    if months:
        months_dt = pd.to_datetime(months)
        df_base_filtrado = df_base_filtrado[df_base_filtrado['month'].isin(months_dt)]
    if directorias:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['diretoria'].isin(directorias)]
    # if regionais: # <-- REMOVIDO
    #     df_base_filtrado = df_base_filtrado[df_base_filtrado['regional'].isin(regionais)]
    if marcas:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['brand'].isin(marcas)]
    if tamanhos:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['size'].isin(tamanhos)]
    if embalagens:
        df_base_filtrado = df_base_filtrado[df_base_filtrado['package'].isin(embalagens)]

    # Criar um figuro "vazio" para caso não haja dados
    fig_vazia = go.Figure().update_layout(title="Sem dados para o filtro selecionado.")
    
    if df_base_filtrado.empty:
        return fig_vazia, fig_vazia, html.Div("Sem dados para o filtro selecionado.", style={"color":"#900"}), html.Div("Sem dados para o filtro selecionado.", style={"color":"#900"})

    # 2. Preparar Dicionário de 'Shocks'
    shocks = {
        "cvv_concentrate": s_conc or 0.0,
        "cvv_sweetener":   s_sweet or 0.0,
        "cvv_pet":         s_pet or 0.0,
        "cvv_can":         s_can or 0.0,
        "cvv_cap":         s_cap or 0.0,
        "cvv_purcharses":  s_purch or 0.0,
        "cvv_otherraw":    s_other or 0.0,
    }
    
    # 3. Rodar as Simulações
    # CENÁRIO BASE: Preço base, volume projetado (sem elasticidade), custos base
    df_cenario_base = run_pnl_simulation(
        df_base_filtrado, 
        price_adj_pct=0.0, 
        shocks_pct={}
    )
    # Garantir que volume base é igual ao volume_projetado (sem elasticidade)
    df_cenario_base['volume_simulado'] = df_cenario_base['volume_projetado']
    df_cenario_base['preco_liquido_simulado_unit'] = df_cenario_base['base_preco_liquido_unit']
    df_cenario_base['receita_total_simulada'] = (
        df_cenario_base['volume_simulado'] * 
        df_cenario_base['preco_liquido_simulado_unit']
    )
    
    # CENÁRIO SIMULADO: Preço varia com slider, volume varia com elasticidade, custos variam com sliders
    df_cenario_simulado = run_pnl_simulation(
        df_base_filtrado, 
        price_adj_pct=price_adj or 0.0, 
        shocks_pct=shocks
    )
    
    # 3b. Preparar cenário projetado usando percentuais YoY de matéria-prima
    # IMPORTANTE: No cenário projetado, a receita é a mesma do base (volume_projetado * preço_base)
    # Apenas os CUSTOS mudam com os percentuais YoY, afetando a MARGEM
    df_cenario_projetado = None
    
    # SEMPRE criar cenário projetado, mesmo se não houver percentuais YoY
    df_proj_base = df_base_filtrado.copy()
    
    # Preparar dicionário de choques por driver
    shocks_proj = {}
    
    if df_mp_yoy is not None and not df_mp_yoy.empty:
        # Filtrar percentuais YoY pelos meses selecionados
        df_yoy_filtrado = df_mp_yoy.copy()
        if months:
            months_dt = pd.to_datetime(months)
            df_yoy_filtrado = df_yoy_filtrado[df_yoy_filtrado['month'].isin(months_dt)]
        
        # Para cada driver, obter percentual YoY médio dos meses filtrados
        for driver in COST_DRIVERS_SLIDERS:
            driver_yoy = df_yoy_filtrado[df_yoy_filtrado['driver'] == driver]
            if not driver_yoy.empty:
                # Usar média dos percentuais YoY para o driver
                avg_yoy = driver_yoy['yoy_pct'].mean()
                shocks_proj[driver] = avg_yoy
            else:
                # Se não encontrar, usar 0 (sem variação YoY)
                shocks_proj[driver] = 0.0
    else:
        # Se não houver percentuais YoY carregados, usar 0 para todos
        for driver in COST_DRIVERS_SLIDERS:
            shocks_proj[driver] = 0.0
        print("[WARNING] Percentuais YoY não disponíveis. Usando 0% para todos os drivers no cenário projetado.")
    
    print(f"[INFO] Aplicando percentuais YoY aos custos: {shocks_proj}")
    
    # Criar cenário projetado:
    # - Preço: igual ao base (price_adj_pct=0.0)
    # - Volume: igual ao base (volume_projetado, sem elasticidade)
    # - Custos: aplicam percentuais YoY
    df_cenario_projetado = run_pnl_simulation(
        df_proj_base,
        price_adj_pct=0.0,  # Preço não muda
        shocks_pct=shocks_proj  # Custos mudam com YoY
    )
    
    # Garantir que volume e receita são iguais ao base (sem elasticidade)
    df_cenario_projetado['volume_simulado'] = df_cenario_projetado['volume_projetado']
    df_cenario_projetado['preco_liquido_simulado_unit'] = df_cenario_projetado['base_preco_liquido_unit']
    df_cenario_projetado['receita_total_simulada'] = (
        df_cenario_projetado['volume_simulado'] * 
        df_cenario_projetado['preco_liquido_simulado_unit']
    )
    # Margem já está calculada corretamente com os custos YoY
    
    print(f"[INFO] ✅ Cenário projetado criado: {len(df_cenario_projetado)} linhas")
    print(f"[INFO] Receita projetada: R$ {df_cenario_projetado['receita_total_simulada'].sum():,.2f}")
    print(f"[INFO] Margem projetada: R$ {df_cenario_projetado['margem_total_simulada'].sum():,.2f}")
    
    # 4. Construir Gráfico 1 (P&L Total)
    fig_pnl = build_pnl_total_fig(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
    
    # 5. Construir Gráfico 2 (R$/UC Breakdown)
    pu_base, pu_sim, pu_proj = calculate_average_pu(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
    fig_cost = build_cost_driver_fig(pu_base, pu_sim, pu_proj)
    
    # 6. Construir Tabela de Resultados
    base_summary = summarize_pnl_df(df_cenario_base, "1. Cenário Base")
    sim_summary = summarize_pnl_df(df_cenario_simulado, "2. Cenário Simulado")
    resultados_list = [base_summary, sim_summary]
    
    if df_cenario_projetado is not None:
        proj_summary = summarize_pnl_df(df_cenario_projetado, "3. Cenário Projetado")
        resultados_list.append(proj_summary)
    
    df_resultados = pd.DataFrame(resultados_list)
    
    # Formatar para a tabela
    df_resultados['Receita Total'] = df_resultados['Receita Total'].apply(lambda x: f"R$ {x:,.0f}")
    df_resultados['Margem Total'] = df_resultados['Margem Total'].apply(lambda x: f"R$ {x:,.0f}")
    df_resultados['Volume Total'] = df_resultados['Volume Total'].apply(lambda x: f"{x:,.0f} UC")
    df_resultados['Margem %'] = df_resultados['Margem %'].apply(lambda x: f"{x:.2%}")
    
    table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in df_resultados.columns],
        data=df_resultados.to_dict('records'),
        style_cell={"textAlign":"center","padding":"6px"},
        style_header={"backgroundColor":"#f4f4f4","fontWeight":"600"},
        style_table={"overflowX":"auto"},
        page_size=10
    )
    
    # 7. Construir Tabela Razão
    tabela_razao = build_tabela_razao(df_cenario_base, df_cenario_simulado, df_cenario_projetado)
    
    return fig_pnl, fig_cost, table, tabela_razao

# =========================
# Main
# =========================
if __name__ == "__main__":
    print(f"[INFO] CSV do 'Master DataFrame' carregado: {DATA_FILE}")
    print(f"Total de linhas no Master DF: {len(df_master)}")
    print("Iniciando o servidor Dash...")
    app.run(debug=True, port=8050)