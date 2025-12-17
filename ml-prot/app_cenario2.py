# app_cenario2.py
import os
import re
import glob
import math
import numpy as np
import pandas as pd
from datetime import datetime
from dash import Dash, dcc, html, dash_table, Input, Output, State, no_update
import plotly.graph_objects as go

# =========================
# Configurações e caminhos
# =========================
OUT_DIR = "outputs"

# Padrões esperados para arquivos
MERGE_AGG_PATTERN = os.path.join(OUT_DIR, "merge_fin_com_AGG_SKU_*.csv")
MERGE_FALLBACK    = os.path.join(OUT_DIR, "merge_fin_com_*.csv")
MP_CUSTOS_PATTERN = os.path.join(OUT_DIR, "mp_custos_base_*.csv")  # opcional

# Colunas de drivers (presentes no df_merged)
COST_BUCKETS = [
    "cvv_concentrate",
    "cvv_sweetener",
    "cvv_pet",
    "cvv_can",
    "cvv_cap",
    "cvv_purcharses",
    "cvv_otherraw",
]

# Legendas "bonitas"
PRETTY = {
    "cvv_concentrate": "Concentrate",
    "cvv_sweetener":   "Sweetener",
    "cvv_pet":         "PET",
    "cvv_can":         "Can",
    "cvv_cap":         "Cap",
    "cvv_purcharses":  "Purchases",
    "cvv_otherraw":    "Other Raw",
}

COLOR_BASE = {
    "cvv_concentrate": "#6F36C5",
    "cvv_sweetener": "#1CCA6E",
    "cvv_pet": "#FF8400",
    "cvv_can": "#EB262C",
    "cvv_cap": "#FFCF08",
    "cvv_purcharses": "#F5025D",
    "cvv_otherraw": "#747577",
}
COLOR_SIM = COLOR_BASE  # mesma paleta para comparável

# =========================
# Utilitários
# =========================
def latest_file(patterns):
    """Retorna o arquivo mais recente considerando um ou mais padrões glob."""
    if isinstance(patterns, str):
        patterns = [patterns]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]

def coerce_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def series_label(key: str) -> str:
    return PRETTY.get(key, key.replace("cvv_", "").upper())

def to_month(dt_like):
    s = pd.to_datetime(dt_like, errors="coerce")
    return s.dt.to_period("M").dt.to_timestamp()

def nonempty_unique(x):
    return sorted([v for v in x.dropna().unique().tolist() if v != ""])

# =========================
# Carregamento de dados
# =========================
merge_path = latest_file([MERGE_AGG_PATTERN, MERGE_FALLBACK])
if not merge_path:
    raise FileNotFoundError(
        "Não encontrei o CSV do merge. "
        "Gere primeiro o arquivo 'merge_fin_com_AGG_SKU_YYYYMMDD_HHMM.csv' em outputs/."
    )

df = pd.read_csv(merge_path)
# Normalizar nomes de colunas esperadas
expected_cols = {
    "depara_mess": "month",
    "estado": "state",
    "diretoria": "strategic_directorate",
    "marca_std": "brand",
    "tamanho_key": "size",
    "retornabilidade": "returnability",
    "embalagem": "package",
    "categoria_br": "category",
    "sub_categoria": "subcategory",
    "territorio_std": "distribution_territory",
    # métricas
    "volume": "volume",
    "gross_revenue": "gross_revenue",
    "taxes": "taxes",
    "discounts": "discounts",
    "encargos": "encargos",
    "net_revenue": "net_revenue",
    "other_revenue": "other_revenue",
    "total_revenue": "total_revenue",
    "variable_margin": "variable_margin",
    "volume_mtd_uc": "volume_mtd_uc",
}
# renomear somente as que existem
rename_map = {k: v for k, v in expected_cols.items() if k in df.columns}
df = df.rename(columns=rename_map)

# converter mês
if "month" not in df.columns:
    raise KeyError("Coluna de mês não encontrada (deveria ser 'depara_mess' no CSV).")
df["month"] = to_month(df["month"])

# numéricas
num_cols = set(["volume","gross_revenue","taxes","discounts","encargos","net_revenue",
                "other_revenue","total_revenue","variable_margin","volume_mtd_uc"] + COST_BUCKETS)
for c in (num_cols & set(df.columns)):
    df[c] = coerce_num(df[c])

# Garantir existência dos drivers (se ausente, cria com zero para não quebrar)
for c in COST_BUCKETS:
    if c not in df.columns:
        df[c] = 0.0

# (Opcional) Carregar custos de matéria-prima agregados
mp_path = latest_file(MP_CUSTOS_PATTERN)
mp = None
if mp_path:
    try:
        mp = pd.read_csv(mp_path)
        # padroniza nomes caso existam
        for cc in ["mes","month"]:
            if cc in mp.columns:
                mp["month"] = to_month(mp[cc])
                break
    except Exception:
        mp = None  # não é obrigatório

# =========================
# Funções de filtro/PNL
# =========================
FILTER_ORDER = [
    "month",
    "state",
    "strategic_directorate",
    "distribution_territory",
    "brand",
    "size",
    "returnability",
    "package",
    "category",
    "subcategory",
]

def slice_df(d: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Filtra respeitando kwargs nas chaves do df padronizado."""
    x = d
    for key, val in kwargs.items():
        if val in (None, "", []):
            continue
        if key not in x.columns:
            continue
        # month: valor único
        if key == "month":
            m = to_month(pd.Series([val])).iloc[0]
            x = x.loc[x["month"].eq(m)]
        else:
            if isinstance(val, list):
                x = x.loc[x[key].isin(val)]
            else:
                x = x.loc[x[key].eq(val)]
    return x

def per_unit_baseline(d: pd.DataFrame):
    """Calcula valores por unidade (R$/UC) para baseline a partir do dataframe filtrado."""
    if d.empty:
        return None
    vol = coerce_num(d.get("volume", 0)).sum()
    if vol <= 0:
        return None
    rev_total = coerce_num(d.get("total_revenue", 0)).sum()
    if rev_total == 0:
        # fallback
        rev_total = coerce_num(d.get("gross_revenue", 0)).sum() + coerce_num(d.get("other_revenue", 0)).sum()

    pu = {"rev_total": rev_total / vol}
    for c in COST_BUCKETS:
        pu[c] = coerce_num(d.get(c, 0)).sum() / vol
    pu["var_margin"] = pu["rev_total"] - sum(pu[k] for k in COST_BUCKETS)
    return pu

def apply_shocks(pu, shocks_pct, price_adj_pct):
    """Aplica choques percentuais nos drivers e reajuste de preço (por unidade)."""
    sim = pu.copy()
    sim["rev_total"] = pu["rev_total"] * (1 + price_adj_pct)
    for k, pct in shocks_pct.items():
        if k in sim:
            sim[k] = sim[k] * (1 + pct)
    sim["var_margin"] = sim["rev_total"] - sum(sim[k] for k in COST_BUCKETS)
    return sim

def build_fig(pu, sim):
    fig = go.Figure()
    order = COST_BUCKETS

    for k in order:
        fig.add_bar(
            x=["Baseline"], y=[pu.get(k, 0.0)],
            name=series_label(k),
            legendgroup=k,
            showlegend=True,
            marker_color=COLOR_BASE.get(k, "#222"),
            hovertemplate=series_label(k) + " — Baseline: R$%{y:.4f}/UC<extra></extra>"
        )
    for k in order:
        fig.add_bar(
            x=["Simulado"], y=[sim.get(k, 0.0)],
            name=series_label(k),
            legendgroup=k,
            showlegend=False,
            marker_color=COLOR_SIM.get(k, "#C00"),
            hovertemplate=series_label(k) + " — Simulado: R$%{y:.4f}/UC<extra></extra>"
        )

    fig.update_layout(
        barmode="stack",
        height=620,
        title="Custo por unidade (R$/UC) – Drivers de MP (Baseline × Simulado)",
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

def pnl_row(pu, label):
    if pu is None:
        return {}
    keys = ["rev_total"] + COST_BUCKETS + ["var_margin"]
    return {"cenário": label, **{k: round(pu.get(k,0.0), 6) for k in keys}}

# =========================
# Preparar listas para filtros
# =========================
df_filters = df.copy()
# Tipagem leve dos campos de filtro
for c in ["state","strategic_directorate","distribution_territory","brand",
          "size","returnability","package","category","subcategory"]:
    if c in df_filters.columns:
        df_filters[c] = df_filters[c].astype(str).str.strip()

MONTHS = nonempty_unique(df_filters["month"])
STATES = nonempty_unique(df_filters["state"])
DIRS   = nonempty_unique(df_filters["strategic_directorate"])
TERRS  = nonempty_unique(df_filters["distribution_territory"])
BRANDS = nonempty_unique(df_filters["brand"])
SIZES  = sorted([float(x) for x in df_filters["size"].dropna().unique().tolist()]) if "size" in df_filters else []
RETS   = nonempty_unique(df_filters["returnability"])
PACKS  = nonempty_unique(df_filters["package"])
CATS   = nonempty_unique(df_filters["category"])
SUBC   = nonempty_unique(df_filters["subcategory"])

# =========================
# App Dash
# =========================
app = Dash(__name__)
app.title = "P&L • FEMSA – Cenário simulado com premissas iniciais"

def opts(values, fmt=lambda x: x):
    return [{"label": fmt(v), "value": v} for v in values]

def month_label(m):
    return pd.to_datetime(m).strftime("%Y-%m")

app.layout = html.Div([
    html.H2("Simulador de custos por unidade – Cenário simulado com premissas iniciais"),
    html.Div([
        html.Div([
            html.Label("Mês"),
            dcc.Dropdown(
                options=opts(MONTHS, fmt=month_label),
                value=(MONTHS[0] if MONTHS else None),
                id="f-month"
            ),
        ], style={"width":"12%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Estado"),
            dcc.Dropdown(options=opts(STATES), value=None, id="f-state"),
        ], style={"width":"10%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Diretoria"),
            dcc.Dropdown(options=opts(DIRS), value=None, id="f-dir"),
        ], style={"width":"16%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Território"),
            dcc.Dropdown(options=opts(TERRS), value=None, id="f-ter"),
        ], style={"width":"18%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Marca"),
            dcc.Dropdown(options=opts(BRANDS), value=None, id="f-brand"),
        ], style={"width":"12%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Tamanho (L)"),
            dcc.Dropdown(options=opts(SIZES, fmt=lambda v: f"{v:.2f}"), value=None, id="f-size"),
        ], style={"width":"10%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Retornabilidade"),
            dcc.Dropdown(options=opts(RETS), value=None, id="f-ret"),
        ], style={"width":"12%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Embalagem"),
            dcc.Dropdown(options=opts(PACKS), value=None, id="f-pack"),
        ], style={"width":"12%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Categoria"),
            dcc.Dropdown(options=opts(CATS), value=None, id="f-cat"),
        ], style={"width":"12%","display":"inline-block","marginRight":"8px"}),

        html.Div([
            html.Label("Subcategoria"),
            dcc.Dropdown(options=opts(SUBC), value=None, id="f-subcat"),
        ], style={"width":"14%","display":"inline-block"}),
    ], style={"marginBottom":"10px"}),

    html.Hr(),

    html.Div([
        html.Div([
            html.H4("Reajuste de preço"),
            dcc.Slider(-0.2, 0.2, step=0.01, value=0.00, id="adj-price",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Small("valor em % (ex.: 0.05 = +5%)"),
            html.Hr(),
            html.H4("Choques de custo (por unidade)"),
            html.Label("Concentrate"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-conc",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("Sweetener"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-sweet",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("PET"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-pet",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("Can"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-can",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("Cap"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-cap",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("Purchases"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-purch",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
            html.Label("Other Raw"),
            dcc.Slider(-0.5, 0.5, 0.01, value=0.00, id="shock-other",
                       marks=None,
                       tooltip={"placement":"bottom","always_visible":True}),
        ], style={"width":"34%","display":"inline-block","verticalAlign":"top","paddingRight":"16px"}),

        html.Div([
            dcc.Graph(id="fig-breakdown", style={"height": "620px"}),
        ], style={"width": "64%", "display": "inline-block", "verticalAlign": "top"}),
    ]),

    html.Hr(),
    html.Div(id="pnl-table"),

    # Área invisível só para guardar opções encadeadas (evita quebrar ao trocar mês/estado etc.)
    dcc.Store(id="store-options")
])

# =========================
# Callbacks — Filtros encadeados
# =========================
@app.callback(
    Output("store-options", "data"),
    [
        Input("f-month","value"),
        Input("f-state","value"),
        Input("f-dir","value"),
        Input("f-ter","value"),
        Input("f-brand","value"),
        Input("f-size","value"),
        Input("f-ret","value"),
        Input("f-pack","value"),
        Input("f-cat","value"),
        Input("f-subcat","value"),
    ]
)
def update_options(month, state, direc, terr, brand, size, ret, pack, cat, subcat):
    # Aplica filtros progressivos para retornar o conjunto válido para os próximos dropdowns
    flt = {
        "month": month,
        "state": state,
        "strategic_directorate": direc,
        "distribution_territory": terr,
        "brand": brand,
        "size": size,
        "returnability": ret,
        "package": pack,
        "category": cat,
        "subcategory": subcat,
    }
    x = slice_df(df, **flt)
    data = {
        "state": nonempty_unique(x["state"]) if "state" in x else [],
        "strategic_directorate": nonempty_unique(x["strategic_directorate"]) if "strategic_directorate" in x else [],
        "distribution_territory": nonempty_unique(x["distribution_territory"]) if "distribution_territory" in x else [],
        "brand": nonempty_unique(x["brand"]) if "brand" in x else [],
        "size": sorted([float(v) for v in x["size"].dropna().unique().tolist()]) if "size" in x else [],
        "returnability": nonempty_unique(x["returnability"]) if "returnability" in x else [],
        "package": nonempty_unique(x["package"]) if "package" in x else [],
        "category": nonempty_unique(x["category"]) if "category" in x else [],
        "subcategory": nonempty_unique(x["subcategory"]) if "subcategory" in x else [],
    }
    return data

@app.callback(
    Output("f-state","options"),
    Output("f-dir","options"),
    Output("f-ter","options"),
    Output("f-brand","options"),
    Output("f-size","options"),
    Output("f-ret","options"),
    Output("f-pack","options"),
    Output("f-cat","options"),
    Output("f-subcat","options"),
    Input("store-options","data"),
)
def refresh_dropdowns(store):
    if not store:
        raise RuntimeError("Falha ao construir opções de filtros.")
    return (
        opts(store.get("state", [])),
        opts(store.get("strategic_directorate", [])),
        opts(store.get("distribution_territory", [])),
        opts(store.get("brand", [])),
        opts(store.get("size", []), fmt=lambda v: f"{float(v):.2f}"),
        opts(store.get("returnability", [])),
        opts(store.get("package", [])),
        opts(store.get("category", [])),
        opts(store.get("subcategory", [])),
    )

# =========================
# Callback — Gráfico e Tabela
# =========================
@app.callback(
    Output("fig-breakdown", "figure"),
    Output("pnl-table", "children"),
    [
        Input("f-month","value"),
        Input("f-state","value"),
        Input("f-dir","value"),
        Input("f-ter","value"),
        Input("f-brand","value"),
        Input("f-size","value"),
        Input("f-ret","value"),
        Input("f-pack","value"),
        Input("f-cat","value"),
        Input("f-subcat","value"),
        Input("adj-price","value"),
        Input("shock-conc","value"),
        Input("shock-sweet","value"),
        Input("shock-pet","value"),
        Input("shock-can","value"),
        Input("shock-cap","value"),
        Input("shock-purch","value"),
        Input("shock-other","value"),
    ],
)
def update_view(month, state, direc, terr, brand, size, ret, pack, cat, subcat,
                price_adj, s_conc, s_sweet, s_pet, s_can, s_cap, s_purch, s_other):

    # Filtragem
    d = slice_df(
        df,
        month=month, state=state, strategic_directorate=direc,
        distribution_territory=terr, brand=brand, size=size,
        returnability=ret, package=pack, category=cat, subcategory=subcat
    )

    pu = per_unit_baseline(d)
    if pu is None:
        fig = go.Figure().update_layout(title="Sem dados para o filtro selecionado.")
        return fig, html.Div("Sem dados para o filtro selecionado.", style={"color":"#900"})

    shocks = {
        "cvv_concentrate": s_conc or 0.0,
        "cvv_sweetener":   s_sweet or 0.0,
        "cvv_pet":         s_pet or 0.0,
        "cvv_can":         s_can or 0.0,
        "cvv_cap":         s_cap or 0.0,
        "cvv_purcharses":  s_purch or 0.0,
        "cvv_otherraw":    s_other or 0.0,
    }
    sim = apply_shocks(pu, shocks, price_adj or 0.0)
    fig = build_fig(pu, sim)

    rows = [
        pnl_row(pu, "baseline"),
        pnl_row(sim, "simulado"),
    ]
    cols = ["cenário","rev_total"] + COST_BUCKETS + ["var_margin"]

    table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in cols],
        data=rows,
        style_cell={"textAlign":"center","padding":"6px"},
        style_header={"backgroundColor":"#f4f4f4","fontWeight":"600"},
        style_table={"overflowX":"auto"},
        page_size=2
    )
    return fig, table

# =========================
# Main
# =========================
if __name__ == "__main__":
    print(f"[INFO] CSV merge carregado: {merge_path}")
    if mp_path:
        print(f"[INFO] mp_custos_base (opcional) carregado: {mp_path}")
    app.run(host="0.0.0.0", port=8050, debug=True)