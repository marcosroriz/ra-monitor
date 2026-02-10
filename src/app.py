#!/usr/bin/env python
# coding: utf-8
# Dashboard de Monitoramento de Scripts para o projeto RA / CEIA-UFG

# Imports básicos
import os
import pandas as pd
from datetime import datetime, timedelta

# Dotenv
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importar bibliotecas do dash
import dash
import dash_bootstrap_components as dbc
import dash_auth
import dash_mantine_components as dmc
from dash import Dash, _dash_renderer, dcc, html, callback, Input, Output, State
import dash_ag_grid as dag

# Dash componentes Mantine e icones
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Graficos
import plotly.graph_objs as go
import plotly.io as pio

# Tema
import tema

# Banco de Dados
from db import PostgresSingleton

# Profiler
from werkzeug.middleware.profiler import ProfilerMiddleware

##############################################################################
# CONFIGURAÇÕES BÁSICAS ######################################################
##############################################################################
# Conexão com os bancos
pgDB = PostgresSingleton.get_instance()
pgEngine = pgDB.get_engine()

# Versão do React
_dash_renderer._set_react_version("18.2.0")

# Configurações de cores e temas
TEMA = dbc.themes.LUMEN
pio.templates.default = "plotly"
pio.templates["plotly"]["layout"]["colorway"] = tema.PALETA_CORES

# Stylesheets do Mantine + nosso tema
stylesheets = [
    TEMA,
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css",
    "https://unpkg.com/@mantine/dates@7/styles.css",
    "https://unpkg.com/@mantine/code-highlight@7/styles.css",
    "https://unpkg.com/@mantine/charts@7/styles.css",
    "https://unpkg.com/@mantine/carousel@7/styles.css",
    "https://unpkg.com/@mantine/notifications@7/styles.css",
    "https://unpkg.com/@mantine/nprogress@7/styles.css",
]

# Scripts
scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/pt.min.js",
    "https://cdn.plot.ly/plotly-locale-pt-br-latest.js",
]

# Seta o tema padrão do plotly
pio.templates["tema"] = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family=tema.FONTE_GRAFICOS,
            size=tema.FONTE_TAMANHO,  # Default font size
        ),
        colorway=tema.PALETA_CORES,
    )
)

# Seta o tema
pio.templates.default = "tema"

##############################################################################
# DASH #######################################################################
##############################################################################

BASE_DIR = os.getcwd()

# Caminhos absolutos
ASSETS_PATH = os.path.join(BASE_DIR, "assets")
PAGES_PATH = os.path.join(BASE_DIR, "pages")

# Dash
app = Dash(
    "Dashboard de Monitoramento de Scripts",
    assets_folder=ASSETS_PATH,
    external_stylesheets=stylesheets,
    external_scripts=scripts,
    use_pages=False,
    suppress_callback_exceptions=True,
)

# Server
server = app.server


# Menu / Navbar
def criarMenu(dirVertical=True):
    return dbc.Nav(
        [dbc.NavLink("Monitoramento", href="/", active="exact")],
        class_name="dash-bootstrap",
        vertical=dirVertical,
        pills=True,
    )


# Cabeçalho
header = dmc.Group(
    [
        dmc.Group(
            [
                dmc.Burger(id="burger-button", opened=False, hiddenFrom="md"),
                # Logo Mobile
                html.Img(
                    src=app.get_asset_url("logo_small.png"),
                    height=32,
                    className="logo-mobile",
                ),
                # Logo Desktop
                html.Img(
                    src=app.get_asset_url("logo.png"),
                    height=40,
                    className="logo-desktop",
                ),
                # Título
                dmc.Stack(
                    [
                        dmc.Text("Painel de Monitoramento de", size="sm", fw=400, visibleFrom="sm"),
                        dmc.Text("Monitoramento de", size="sm", fw=400, hiddenFrom="sm"),
                        dmc.Text("Scripts", size="1.5rem", fw=700),
                    ],
                    gap=0,
                    align="flex-start",
                ),
            ]
        ),
        dmc.Group(
            [
                criarMenu(dirVertical=False),
            ],
            ml="xl",
            gap=0,
            visibleFrom="sm",
        ),
    ],
    justify="space-between",
    style={"flex": 1},
    h="100%",
    px="md",
)


# Corpo do app
def criarLayoutPagina():
    return dmc.MantineProvider(
        dmc.AppShell(
            [
                dmc.AppShellHeader(header, p=24, style={"backgroundColor": "#f8f9fa"}),
                dmc.AppShellNavbar(id="navbar", children=criarMenu(dirVertical=True), py="md", px=4),
                dmc.AppShellMain(
                    dmc.DatesProvider(
                        children=dbc.Container(
                            [
                                dcc.Location(id="url", refresh="callback-nav"),
                                html.Div(id="scroll-hook", style={"display": "none"}),
                                dcc.Store(id="store-window-size"),
                                dcc.Interval(id="refresh-interval", interval=30 * 1000, n_intervals=0),
                                html.Div(
                                    id="main-content",
                                    children=[
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dcc.DatePickerRange(
                                                            id="date-range",
                                                            display_format="YYYY-MM-DD",
                                                            clearable=True,
                                                            start_date=(datetime.now() - timedelta(days=30)).strftime(
                                                                "%Y-%m-%d"
                                                            ),
                                                            end_date=datetime.now().strftime("%Y-%m-%d"),
                                                        )
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dcc.Dropdown(
                                                            id="script-filter",
                                                            multi=True,
                                                            placeholder="Filtrar por script",
                                                        )
                                                    ],
                                                    md=5,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Checklist(
                                                            id="only-failures",
                                                            options=[
                                                                {
                                                                    "label": "Apenas falhas",
                                                                    "value": "only",
                                                                }
                                                            ],
                                                            value=[],
                                                            switch=True,
                                                        )
                                                    ],
                                                    md=3,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H6("Execuções no período"),
                                                                html.H3(id="kpi-total-runs"),
                                                            ]
                                                        ),
                                                        className="mb-3",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H6("Taxa de sucesso"),
                                                                html.H3(id="kpi-success-rate"),
                                                            ]
                                                        ),
                                                        className="mb-3",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H6("Última falha"),
                                                                html.H5(id="kpi-last-failure"),
                                                            ]
                                                        ),
                                                        className="mb-3",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H6("Scripts distintos"),
                                                                html.H3(id="kpi-distinct-scripts"),
                                                            ]
                                                        ),
                                                        className="mb-3",
                                                    ),
                                                    md=3,
                                                ),
                                            ]
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dcc.Graph(
                                                        id="runs-over-time",
                                                        # style={"height": "350px"},
                                                    ),
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    dcc.Graph(
                                                        id="execution-time-by-script",
                                                        # style={"height": "350px"},
                                                    ),
                                                    md=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    html.Div(
                                                        id="table-container",
                                                    )
                                                )
                                            ]
                                        ),
                                    ],
                                ),
                            ],
                            fluid=True,
                            className="dbc dbc-ag-grid",
                        ),
                        settings={"locale": "pt"},
                    ),
                ),
            ],
            header={"height": 100},
            navbar={
                "width": 300,
                "breakpoint": "sm",
                "collapsed": {"desktop": True, "mobile": True},
            },
            padding="md",
            id="app-shell",
        )
    )


app.layout = criarLayoutPagina


@callback(
    Output("app-shell", "navbar"),
    Input("burger-button", "opened"),
    State("app-shell", "navbar"),
)
def toggle_navbar(opened, navbar):
    navbar["collapsed"] = {"mobile": not opened, "desktop": True}
    return navbar


def _load_script_log(start_date=None, end_date=None):
    """
    Carrega os registros da tabela de log de execução de scripts filtrados por data.
    """
    query = """
        SELECT
            id,
            executed_at,
            script_name,
            status_complete,
            exception_text,
            execution_time_ms
        FROM public.script_execution_log
        WHERE 1=1
    """

    if start_date:
        start_date_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
        query += f" AND executed_at >= '{start_date_str}'"

    if end_date:
        end_date_str = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        query += f" AND executed_at < '{end_date_str}'"

    query += " ORDER BY executed_at DESC "

    df = pd.read_sql(query, pgEngine)
    if not df.empty:
        df["executed_at"] = pd.to_datetime(df["executed_at"])
    return df


@callback(
    Output("kpi-total-runs", "children"),
    Output("kpi-success-rate", "children"),
    Output("kpi-last-failure", "children"),
    Output("kpi-distinct-scripts", "children"),
    Output("runs-over-time", "figure"),
    Output("execution-time-by-script", "figure"),
    Output("table-container", "children"),
    Output("script-filter", "options"),
    Input("refresh-interval", "n_intervals"),
    Input("script-filter", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("only-failures", "value"),
)
def atualizar_dashboard(n_intervals, scripts, start_date, end_date, only_failures_values):
    df = _load_script_log(start_date=start_date, end_date=end_date)

    if df.empty:
        empty_fig = go.Figure().update_layout(
            title="Sem dados",
            xaxis_title="",
            yaxis_title="",
        )
        table = html.Div("Nenhum registro encontrado.")
        return (
            "0",
            "0%",
            "Sem falhas",
            "0",
            empty_fig,
            empty_fig,
            table,
            [],
        )

    # Filtros
    if scripts:
        df = df[df["script_name"].isin(scripts)]

    only_failures = only_failures_values and "only" in only_failures_values
    if only_failures:
        df = df[~df["status_complete"]]

    # KPIs
    total_runs = len(df)
    if total_runs > 0:
        success_rate = df["status_complete"].mean() * 100
        success_rate_str = f"{success_rate:.1f}%"
        failures = df[~df["status_complete"]]
        if not failures.empty:
            last_failure = failures["executed_at"].max().strftime("%Y-%m-%d %H:%M")
        else:
            last_failure = "Sem falhas no período"
        distinct_scripts = df["script_name"].nunique()
    else:
        success_rate_str = "0%"
        last_failure = "Sem dados"
        distinct_scripts = 0

    # Gráfico 1: execuções ao longo do tempo (tempo de execução)
    # Converter de ms para minutos
    df["execution_time_min"] = df["execution_time_ms"] / 60000

    fig_time = go.Figure()
    for status_value, nome_status, color in [
        (True, "Sucesso", tema.PALETA_CORES[0] if hasattr(tema, "PALETA_CORES") else "#2ca02c"),
        (False, "Falha", tema.PALETA_CORES[1] if hasattr(tema, "PALETA_CORES") else "#d62728"),
    ]:
        df_status = df[df["status_complete"] == status_value]
        if df_status.empty:
            continue
        fig_time.add_trace(
            go.Scatter(
                x=df_status["executed_at"],
                y=df_status["execution_time_min"],
                mode="markers",
                name=nome_status,
                marker=dict(color=color, size=8, opacity=0.8),
                hovertemplate=(
                    "Script: %{customdata[0]}<br>"
                    "Tempo: %{y:.2f} min<br>"
                    "Executado em: %{x|%Y-%m-%d %H:%M:%S}<extra></extra>"
                ),
                customdata=df_status[["script_name"]],
            )
        )

    fig_time.update_layout(
        title="Tempo de execução por execução",
        xaxis_title="Executado em",
        yaxis_title="Tempo de execução (min)",
        legend_title="Status",
        margin=dict(l=80, r=20, t=60, b=80),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
        height=500,
    )

    # Gráfico 2: tempo médio por script
    df_time_script = (
        df.groupby("script_name")["execution_time_min"]
        .mean()
        .reset_index()
        .sort_values("execution_time_min", ascending=False)
    )

    fig_script = go.Figure(
        data=[
            go.Bar(
                x=df_time_script["execution_time_min"],
                y=df_time_script["script_name"],
                orientation="h",
            )
        ]
    )
    fig_script.update_layout(
        title="Tempo médio de execução por script",
        xaxis_title="Tempo médio (min)",
        yaxis_title="Script",
        margin=dict(l=250, r=20, t=60, b=40),
        yaxis=dict(automargin=True),
        height=500,
    )

    # Tabela de execuções recentes
    df_table = df.copy()
    df_table["executed_at"] = df_table["executed_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_table["status"] = df_table["status_complete"].map({True: "Sucesso", False: "Falha"})
    df_table["execution_time_min"] = df_table["execution_time_min"].round(2)
    df_table = df_table.sort_values("executed_at", ascending=False).head(200)

    columns = [
        {"field": "id", "headerName": "ID"},
        {"field": "executed_at", "headerName": "Executado em"},
        {"field": "script_name", "headerName": "Script"},
        {"field": "status", "headerName": "Status"},
        {"field": "execution_time_min", "headerName": "Tempo (min)"},
        {"field": "exception_text", "headerName": "Exceção", "wrapText": True, "autoHeight": True, "flex": 1},
    ]

    table = dag.AgGrid(
        id="runs-table",
        rowData=df_table.to_dict("records"),
        columnDefs=columns,
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        dashGridOptions={
            "enableCellTextSelection": True,
            "pagination": True,
            "paginationPageSize": 20,
            "rowClassRules": {
                "row-success": "params.data && params.data.status === 'Sucesso'",
                "row-fail": "params.data && params.data.status === 'Falha'",
            },
        },
        style={"height": "600px", "resize": "vertical", "overflow": "hidden"},
        className="ag-theme-quartz",
    )

    # Opções do filtro de script
    script_options = [{"label": s, "value": s} for s in sorted(df["script_name"].dropna().unique())]

    return (
        str(total_runs),
        success_rate_str,
        last_failure,
        str(distinct_scripts),
        fig_time,
        fig_script,
        table,
        script_options,
    )


# Hook para levar para o topo ao mudar a url
app.clientside_callback(
    """
    function(pathname) {
        setTimeout(function() {
            window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        }, 1000);  // Pequeno delay
        return "";
    }

    """,
    Output("scroll-hook", "children"),
    Input("url", "pathname"),
)

# Script para armazerar o tamanho do navegador
app.clientside_callback(
    """
    function(n) {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            device: window.innerWidth < 768 ? "Mobile" : "Desktop"
        };
    }
    """,
    Output("store-window-size", "data"),
    Input("url", "pathname"),
)


##############################################################################
# Auth #######################################################################
##############################################################################
df_users = pd.read_sql("SELECT * FROM users_ra_dash", pgEngine)
dict_users = df_users.set_index("ra_username")["ra_password"].to_dict()
SECRET_KEY = os.getenv("SECRET_KEY")

auth = dash_auth.BasicAuth(app, dict_users, secret_key=SECRET_KEY)

##############################################################################
# MAIN #######################################################################
##############################################################################
if __name__ == "__main__":
    APP_HOST = os.getenv("HOST", "0.0.0.0")
    APP_DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    APP_PORT = os.getenv("PORT", 10000)

    PROFILE = os.getenv("PROFILE", "False").lower() in ("true", "1", "yes")
    PROF_DIR = os.getenv("PROFILE_DIR", "profile")

    if PROFILE:
        app.server.config["PROFILE"] = True
        app.server.wsgi_app = ProfilerMiddleware(
            app.server.wsgi_app,
            sort_by=["cumtime"],
            restrictions=[50],
            stream=None,
            profile_dir=PROF_DIR,
        )

    app.run(host=APP_HOST, debug=APP_DEBUG, port=APP_PORT)
