"""
Monetary Policy & The Inflation Crisis — Interactive Dashboard
==============================================================
CMT218 Data Visualisation · Assessment 2
Cardiff University · MSc Data Science

Run:  python app.py
View: http://localhost:8050
"""

import xlrd
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, callback, ctx, no_update
import dash_bootstrap_components as dbc


# ═════════════════════════════════════════════════════════════════════════════
#  DATA LOADING & PREPROCESSING
# ═════════════════════════════════════════════════════════════════════════════

# Load data 
df = pd.read_csv('data/processed/dashboard_data.csv', parse_dates=['Date'])

# Country order (Japan last, it's the outlier, draws the eye)
COUNTRIES = ['United States', 'United Kingdom', 'Euro Area',
             'Canada', 'Australia', 'Switzerland', 'Japan']

# Colourblind-safe qualitative palette (Brewer 2003)
# Based on ColorBrewer Set1 + Safe qualitative, 7 distinct hues
COUNTRY_COLOURS = {
    'United States'  : '#E41A1C',  # red
    'United Kingdom' : '#377EB8',  # blue
    'Euro Area'      : '#4DAF4A',  # green
    'Canada'         : '#FF7F00',  # orange
    'Australia'      : '#984EA3',  # purple
    'Switzerland'    : '#A65628',  # brown
    'Japan'          : '#999999',  # grey — deliberate: outlier = muted
}

# Year boundaries
YEAR_MIN = 2007
YEAR_MAX = 2030
FORECAST_START = 2025

# Quick check


# Forward fill Japan's missing early policy rate months
df['Policy_Rate'] = df.groupby('Country')['Policy_Rate'].transform(
    lambda x: x.ffill().bfill()
)

# Add year column 
df['Year'] = df['Date'].dt.year

# Add month column 
df['YearMonth'] = df['Date'].dt.to_period('M').astype(str)

# Filter to forecast/non-forecast for chart styling
df_real     = df[df['Is_Forecast'] == False].copy()
df_forecast = df[df['Is_Forecast'] == True].copy()

# Annual aggregation 
df_annual = (
    df.groupby(['Country', 'Year'])
    .agg(
        Inflation    = ('Inflation',    'mean'),
        Policy_Rate  = ('Policy_Rate',  'mean'),
        Unemployment = ('Unemployment', 'mean'),
        GDP_Growth   = ('GDP_Growth',   'first'),
        Is_Forecast  = ('Is_Forecast',  'first')
    )
    .reset_index()
)



# ═════════════════════════════════════════════════════════════════════════════
#  APP INITIALISATION & LAYOUT
# ═════════════════════════════════════════════════════════════════════════════

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title='Monetary Policy & Inflation Dashboard'
)

# Colour helpers 
BG_MAIN    = '#F8F9FA'
BG_CARD    = '#FFFFFF'
TEXT_DARK  = '#2C3E50'
TEXT_MUTED = '#6C757D'
ACCENT     = '#2C7BB6'

# Reusable card wrapper 
def make_card(children, style=None):
    base = {
        'backgroundColor': BG_CARD,
        'borderRadius'   : '10px',
        'padding'        : '16px',
        'boxShadow'      : '0 1px 4px rgba(0,0,0,0.08)',
        'marginBottom'   : '16px'
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)

# KPI card 
def kpi_card(title, value, subtitle, colour):
    return html.Div([
        html.P(title, style={
            'fontSize': '11px', 'fontWeight': '600',
            'color': TEXT_MUTED, 'marginBottom': '4px',
            'textTransform': 'uppercase', 'letterSpacing': '0.5px'
        }),
        html.H4(value, style={
            'fontSize': '22px', 'fontWeight': '700',
            'color': colour, 'marginBottom': '2px'
        }),
        html.P(subtitle, style={
            'fontSize': '11px', 'color': TEXT_MUTED, 'marginBottom': '0'
        })
    ], style={
        'backgroundColor': BG_CARD,
        'borderRadius'   : '10px',
        'padding'        : '16px 20px',
        'borderLeft'     : f'4px solid {colour}',
        'boxShadow'      : '0 1px 4px rgba(0,0,0,0.08)',
    })


# Expand button for chart cards
def expand_btn(chart_id):
    return html.Button(
        '⤢ Expand',
        id={'type': 'expand-btn', 'index': chart_id},
        n_clicks=0,
        style={
            'position': 'absolute', 'top': '12px', 'right': '12px',
            'background': '#F0F4F8', 'border': 'none', 'borderRadius': '6px',
            'padding': '4px 10px', 'fontSize': '11px', 'color': '#6C757D',
            'cursor': 'pointer', 'zIndex': '10', 'fontFamily': 'inherit',
        }
    )


# Chart card with expand button
def chart_card(title, subtitle, graph_id, height='300px'):
    return make_card([
        html.Div(style={'position': 'relative'}, children=[
            expand_btn(graph_id),
            html.H6(title,
                     style={'color': TEXT_DARK, 'fontWeight': '600',
                            'marginBottom': '4px'}),
            html.P(subtitle,
                    style={'color': TEXT_MUTED, 'fontSize': '12px',
                           'marginBottom': '12px'}),
            dcc.Graph(id=graph_id, style={'height': height})
        ])
    ])


# Layout 
app.layout = html.Div(style={'backgroundColor': BG_MAIN, 'minHeight': '100vh',
                              'fontFamily': 'Inter, Segoe UI, sans-serif'}, children=[

    # Header 
    html.Div(style={
        'background'   : 'linear-gradient(135deg, #1a3a5c 0%, #2C7BB6 100%)',
        'padding'      : '28px 40px 20px',
        'marginBottom' : '24px'
    }, children=[
        html.H1('Monetary Policy & The Inflation Crisis',
                style={'color': '#FFFFFF', 'fontWeight': '700',
                       'fontSize': '26px', 'marginBottom': '6px'}),
        html.P('How major central banks used interest rates to fight the 2021–2023 '
               'inflation crisis — and what happened to growth and unemployment.',
               style={'color': 'rgba(255,255,255,0.8)', 'fontSize': '14px',
                      'marginBottom': '20px'}),

        # Filters row 
        html.Div(style={'display': 'flex', 'gap': '32px',
                        'alignItems': 'flex-start', 'flexWrap': 'wrap'}, children=[

            # Country checklist
            html.Div([
                html.Label('Countries', style={
                    'color': 'rgba(255,255,255,0.7)', 'fontSize': '11px',
                    'fontWeight': '600', 'textTransform': 'uppercase',
                    'letterSpacing': '0.5px', 'marginBottom': '8px',
                    'display': 'block'
                }),
                dcc.Checklist(
                    id='country-filter',
                    options=[{'label': f'  {c}', 'value': c} for c in COUNTRIES],
                    value=COUNTRIES,
                    inline=True,
                    inputStyle={'marginRight': '4px', 'accentColor': '#F0C040'},
                    labelStyle={
                        'color': '#FFFFFF', 'fontSize': '13px',
                        'marginRight': '16px', 'cursor': 'pointer'
                    }
                )
            ]),

            # Year range slider
            html.Div(style={'minWidth': '280px'}, children=[
                html.Label('Year range', style={
                    'color': 'rgba(255,255,255,0.7)', 'fontSize': '11px',
                    'fontWeight': '600', 'textTransform': 'uppercase',
                    'letterSpacing': '0.5px', 'marginBottom': '8px',
                    'display': 'block'
                }),
                dcc.RangeSlider(
                    id='year-filter',
                    min=YEAR_MIN, max=YEAR_MAX,
                    value=[YEAR_MIN, YEAR_MAX],
                    marks={y: {'label': str(y),
                               'style': {'color': 'rgba(255,255,255,0.7)',
                                         'fontSize': '11px'}}
                           for y in range(2007, 2031, 3)},
                    step=1,
                    tooltip={'placement': 'bottom', 'always_visible': False}
                )
            ])
        ])
    ]),

    # Main content
    html.Div(style={'padding': '0 32px 32px'}, children=[

        # KPI row 
        html.Div(style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(4, 1fr)',
            'gap': '16px', 'marginBottom': '16px'
        }, children=[
            kpi_card('Peak Inflation',    '11.1%',  'United Kingdom · Oct 2022', '#E41A1C'),
            kpi_card('Peak Policy Rate',  '5.50%',  'United States · 2023',      '#377EB8'),
            kpi_card('Japan Outlier',     '0.10%',  'Rate held near-zero · 2023','#999999'),
            kpi_card('Fastest Hike Cycle','425 bps','Canada · Mar–Jan 2023',     '#FF7F00'),
        ]),
        
        # ── Narrative text box ────────────────────────────────────────────────
        html.Div(style={
            'backgroundColor' : '#EBF4FB',
            'borderLeft'      : '4px solid #2C7BB6',
            'borderRadius'    : '8px',
            'padding'         : '14px 20px',
            'marginBottom'    : '16px',
        }, children=[
            html.P(
                'Between 2021 and 2023, inflation across major economies surged '
                'to levels unseen since the 1980s, driven by post-COVID supply '
                'chain disruptions and unprecedented fiscal stimulus. Central banks '
                'responded with the fastest interest rate hiking cycle in four '
                'decades — yet outcomes diverged sharply. Japan, facing deflationary '
                'pressures rather than inflation, held rates near zero throughout, '
                'exposing how the same global shock produced radically different '
                'policy responses. Use the filters above to explore each economy\'s '
                'trajectory.',
                style={
                    'fontSize'    : '13px',
                    'color'       : '#1a3a5c',
                    'lineHeight'  : '1.7',
                    'marginBottom': '0'
                }
            )
        ]),

        # Section 2: Core story 
        chart_card('Inflation Rate vs Policy Rate (2007–2026)',
                   'Solid lines = inflation · Dashed lines = policy rate · '
                   'Shaded region = IMF forecast (2025–2030)',
                   'line-chart-main', height='420px'),

        # Section 3: Country deep-dive 
        html.Div(style={
            'display': 'grid',
            'gridTemplateColumns': '1fr 1fr',
            'gap': '16px', 'marginBottom': '0'
        }, children=[
            chart_card('Inflation Intensity Heatmap',
                       'Average annual inflation by country and year',
                       'heatmap-chart'),
            chart_card('Policy Rate Hike Speed',
                       'Policy rate at pre-hike baseline, peak, and current level per country',
                       'slope-chart'),
        ]),

        # Section 4: Economic impact 
        html.Div(style={
            'display': 'grid',
            'gridTemplateColumns': '1fr 1fr',
            'gap': '16px', 'marginBottom': '0'
        }, children=[
            chart_card('GDP Growth Rate (2007–2030)',
                       'Real data (solid) · IMF forecast 2025–2030 (dashed)',
                       'gdp-chart'),
            chart_card('Unemployment Rate (2007–2026)',
                       'Unemployment rate: pre-COVID (2019) vs post-hike (2022) vs latest (2024)',
                       'unemployment-chart'),
        ]),

        # Section 5: Scatter 
        chart_card('Inflation vs Policy Rate — Annual Scatter',
                   'Each point = one country in one year · '
                   'Size = unemployment rate · Colour = country',
                   'scatter-chart', height='380px'),

        # Footer 
        html.P([
            'Designed for policy analysts, financial journalists, and economics graduates. · ',
            'Sources: BIS (Policy Rates & CPI, 2026) · Our World in Data (Unemployment) · ',
            'IMF World Economic Outlook (GDP Growth, 2025) · ',
            'Forecasts shown as dashed lines · Colour-blind safe palette (Brewer, 2003)'
        ],
        style={
            'color'      : TEXT_MUTED,
            'fontSize'   : '11px',
            'textAlign'  : 'center',
            'marginTop'  : '8px',
            'borderTop'  : '1px solid #DEE2E6',
            'paddingTop' : '16px'
        }
        )
    ]),

    # ── Fullscreen expand modal ──
    dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle(id='modal-title'),
            close_button=True
        ),
        dbc.ModalBody(
            dcc.Graph(id='modal-chart', style={'height': '80vh'})
        ),
    ], id='chart-modal', size='xl', is_open=False),

    # Hidden store to track which chart is expanded
    dcc.Store(id='expanded-chart-id', data=''),
])



# ═════════════════════════════════════════════════════════════════════════════
#  CHART BUILDER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

# Shared layout defaults (applied to every chart) 
def base_layout(title=None):
    layout = dict(
        paper_bgcolor = 'rgba(0,0,0,0)',
        plot_bgcolor  = 'rgba(0,0,0,0)',
        font          = dict(family='Inter, Segoe UI, sans-serif',
                             color=TEXT_DARK, size=12),
        margin        = dict(l=48, r=24, t=36, b=48),
        legend        = dict(
            orientation = 'h',
            yanchor     = 'bottom',
            y           = 1.02,
            xanchor     = 'left',
            x           = 0,
            font        = dict(size=11),
            bgcolor     = 'rgba(0,0,0,0)'
        ),
        hoverlabel = dict(
            bgcolor    = '#2C3E50',
            font_color = '#FFFFFF',
            font_size  = 12,
            bordercolor= '#2C3E50'
        ),
        xaxis = dict(
            showgrid    = True,
            gridcolor   = '#EEEEEE',
            gridwidth   = 0.5,
            zeroline    = False,
            showline    = True,
            linecolor   = '#DDDDDD',
            tickfont    = dict(size=11)
        ),
        yaxis = dict(
            showgrid    = True,
            gridcolor   = '#EEEEEE',
            gridwidth   = 0.5,
            zeroline    = True,
            zerolinecolor = '#CCCCCC',
            zerolinewidth = 0.8,
            showline    = False,
            tickfont    = dict(size=11)
        ),
    )
    if title:
        layout['title'] = dict(text=title, font=dict(size=13), x=0, xanchor='left')
    return layout


# Key event annotations (reused across charts)
def key_annotations():
    # events = [
    #     ('2008-09-01', 'GFC',             '#888888', 1.01),
    #     ('2020-03-01', 'COVID',           '#888888', 1.08),
    #     ('2022-01-01', 'Inflation peak',  '#E41A1C', 1.01),
    #     ('2024-06-01', 'Rate cuts begin', '#377EB8', 1.08),
    # ]
    # shapes = []
    # annotations = []
    # for date, label, colour, y_pos in events:
    #     shapes.append(dict(
    #         type    = 'line',
    #         x0=date, x1=date, y0=0, y1=1,
    #         yref    = 'paper',
    #         line    = dict(color=colour, width=1, dash='dot'),
    #         opacity = 0.4
    #     ))
    #     annotations.append(dict(
    #         x        = date,
    #         y        = y_pos,
    #         yref     = 'paper',
    #         text     = label,
    #         showarrow= False,
    #         font     = dict(size=9, color=colour),
    #         xanchor  = 'left',
    #         opacity  = 0.85,
    #         bgcolor  = 'rgba(255,255,255,0.7)',
    #         borderpad= 2
    #     ))
    # return shapes, annotations
    return [], []
    


# Forecast shading helper
def forecast_shape():
    return dict(
        type      = 'rect',
        x0        = f'{FORECAST_START}-01-01',
        x1        = '2030-12-31',
        y0        = 0, y1 = 1,
        yref      = 'paper',
        fillcolor = '#F0F0F0',
        opacity   = 0.4,
        line      = dict(width=0)
    )

# ── Helper: hex colour → rgba string ─────────────────────────────────────────
def hex_to_rgba(hex_colour, alpha=0.1):
    hex_colour = hex_colour.lstrip('#')
    r, g, b = int(hex_colour[0:2], 16), int(hex_colour[2:4], 16), int(hex_colour[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'

# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Dual-axis line chart: Inflation vs Policy Rate
# ─────────────────────────────────────────────────────────────────────────────
def build_line_chart(selected_countries, year_range):
    dff = df[
        (df['Country'].isin(selected_countries)) &
        (df['Year'] >= year_range[0]) &
        (df['Year'] <= year_range[1])
    ].copy()

    fig = make_subplots(specs=[[{'secondary_y': True}]])

    for country in selected_countries:
        c = dff[dff['Country'] == country]
        colour = COUNTRY_COLOURS[country]

        # Real data — inflation (solid, primary axis)
        c_real = c[c['Is_Forecast'] == False]
        fig.add_trace(go.Scatter(
            x    = c_real['Date'],
            y    = c_real['Inflation'],
            name = f'{country} · Inflation',
            mode = 'lines',
            line = dict(color=colour, width=1.8),
            hovertemplate = (
                f'<b>{country}</b><br>'
                'Inflation: %{y:.1f}%<br>'
                '%{x|%b %Y}<extra></extra>'
            )
        ), secondary_y=False)

        # Real data — policy rate (dashed, secondary axis)
        fig.add_trace(go.Scatter(
            x    = c_real['Date'],
            y    = c_real['Policy_Rate'],
            name = f'{country} · Rate',
            mode = 'lines',
            line = dict(color=colour, width=1.8, dash='dash'),
            hovertemplate = (
                f'<b>{country}</b><br>'
                'Policy rate: %{y:.2f}%<br>'
                '%{x|%b %Y}<extra></extra>'
            )
        ), secondary_y=True)

        # Forecast — policy rate (dotted)
        c_fore = c[c['Is_Forecast'] == True]
        if not c_fore.empty:
            fig.add_trace(go.Scatter(
                x    = c_fore['Date'],
                y    = c_fore['GDP_Growth'],
                name = f'{country} · Forecast',
                mode = 'lines',
                line = dict(color=colour, width=1.2, dash='dot'),
                opacity  = 0.5,
                showlegend = False,
                hovertemplate = (
                    f'<b>{country}</b><br>'
                    'GDP forecast: %{y:.1f}%<br>'
                    '%{x|%b %Y}<extra></extra>'
                )
            ), secondary_y=True)

    # Annotations + forecast shading
    shapes, annots = key_annotations()
    shapes.append(forecast_shape())

    # Forecast label
    annots.append(dict(
        x='2025-06-01', y=0.95, yref='paper',
        text='← IMF Forecast →',
        showarrow=False,
        font=dict(size=10, color='#999999'),
        xanchor='center'
    ))
    
    # Add 2% inflation target reference line
    shapes.append(dict(
        type      = 'line',
        x0        = '2007-01-01',
        x1        = '2030-12-31',
        y0        = 2, y1 = 2,
        yref      = 'y',
        line      = dict(color='#2CA02C', width=1.2, dash='dot'),
        opacity   = 0.7
    ))
    annots.append(dict(
        x         = '2007-06-01',
        y         = 2,
        yref      = 'y',
        text      = '2% target',
        showarrow = False,
        font      = dict(size=10, color='#2CA02C'),
        xanchor   = 'left',
        yanchor   = 'bottom',
        bgcolor   = 'rgba(255,255,255,0.7)',
        borderpad = 2,
        opacity   = 0.9
    ))

    layout = base_layout()
    layout.update(dict(
        shapes      = shapes,
        annotations = annots,
        yaxis       = dict(
            title     = 'Inflation rate (%)',
            showgrid  = True,
            gridcolor = '#EEEEEE',
            zeroline  = True,
            zerolinecolor = '#CCCCCC',
            ticksuffix = '%',
            tickfont  = dict(size=11)
        ),
        yaxis2      = dict(
            title     = 'Policy rate (%)',
            showgrid  = False,
            zeroline  = False,
            ticksuffix = '%',
            tickfont  = dict(size=11)
        ),
        hovermode   = 'x unified',
        legend      = dict(
            orientation = 'h',
            y=-0.18, x=0,
            font=dict(size=10),
            bgcolor='rgba(0,0,0,0)'
        )
    ))
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Inflation heatmap (country × year)
# ─────────────────────────────────────────────────────────────────────────────
def build_heatmap(selected_countries, year_range):
    dff = df_annual[
        (df_annual['Country'].isin(selected_countries)) &
        (df_annual['Year'] >= year_range[0]) &
        (df_annual['Year'] <= year_range[1]) &
        (df_annual['Is_Forecast'] == False)
    ].copy()

    pivot = dff.pivot(index='Country', columns='Year', values='Inflation')
    pivot = pivot.reindex([c for c in COUNTRIES if c in selected_countries])

    fig = go.Figure(go.Heatmap(
        z             = pivot.values,
        x             = pivot.columns.astype(str),
        y             = pivot.index.tolist(),
        colorscale    = [
            [0.0,  '#2166AC'],   # deep blue  — deflation / very low
            [0.2,  '#92C5DE'],   # light blue — low inflation
            [0.4,  '#F7F7F7'],   # white      — ~2% target
            [0.65, '#FDDBC7'],   # light red  — elevated
            [0.85, '#D6604D'],   # red        — high
            [1.0,  '#B2182B'],   # dark red   — crisis level
        ],
        zmid          = 2,       # centre the scale at the 2% target
        zmin          = -2,
        zmax          = 12,
        colorbar      = dict(
            title      = dict(text='Inflation %', side='right',
                              font=dict(size=11)),
            thickness  = 12,
            len        = 0.8,
            ticksuffix = '%',
            tickfont   = dict(size=10)
        ),
        hovertemplate = (
            '<b>%{y}</b><br>'
            'Year: %{x}<br>'
            'Inflation: %{z:.1f}%<extra></extra>'
        ),
        text          = [[f'{v:.1f}' if not np.isnan(v) else ''
                          for v in row] for row in pivot.values],
        texttemplate  = '%{text}',
        textfont      = dict(size=9, color='#333333')
    ))

    layout = base_layout()
    layout.update(dict(
        xaxis  = dict(tickfont=dict(size=10), showgrid=False),
        yaxis  = dict(tickfont=dict(size=11), showgrid=False,
                      autorange='reversed'),
        margin = dict(l=120, r=60, t=20, b=40)
    ))
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Grouped bar: Rate at baseline vs peak vs current (replaces slope)
# ─────────────────────────────────────────────────────────────────────────────
def build_slope_chart(selected_countries, year_range):
    # Pull annual averages for three key years
    key_years  = [2021, 2023, 2024]
    dff = df_annual[
        (df_annual['Country'].isin(selected_countries)) &
        (df_annual['Year'].isin(key_years)) &
        (df_annual['Is_Forecast'] == False)
    ].copy()

    labels = {2021: 'Pre-hike (2021)', 2023: 'Peak (2023)', 2024: 'Current (2024)'}
    bar_colours = ['#A8C8E8', '#E41A1C', '#4DAF4A']  # soft blue, red, green

    fig = go.Figure()

    for i, year in enumerate(key_years):
        dy = dff[dff['Year'] == year]
        # Maintain country order
        dy = dy.set_index('Country').reindex(
            [c for c in selected_countries if c in dy['Country'].values]
        ).reset_index()

        fig.add_trace(go.Bar(
            name        = labels[year],
            x           = dy['Country'],
            y           = dy['Policy_Rate'],
            marker_color= bar_colours[i],
            text        = dy['Policy_Rate'].apply(lambda v: f'{v:.2f}%'
                                                  if pd.notna(v) else ''),
            textposition= 'outside',
            textfont    = dict(size=10),
            hovertemplate = (
                '<b>%{x}</b><br>'
                f'{labels[year]}<br>'
                'Policy rate: %{y:.2f}%<extra></extra>'
            )
        ))

    layout = base_layout()
    layout.update(dict(
        barmode  = 'group',
        bargap   = 0.2,
        bargroupgap = 0.05,
        yaxis    = dict(
            title      = 'Policy rate (%)',
            ticksuffix = '%',
            showgrid   = True,
            gridcolor  = '#EEEEEE',
            zeroline   = True,
            zerolinecolor = '#CCCCCC',
            tickfont   = dict(size=11)
        ),
        xaxis    = dict(
            tickfont = dict(size=11),
            showgrid = False
        ),
        legend   = dict(
            orientation = 'h',
            y=1.12, x=0,
            font=dict(size=11),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin   = dict(l=48, r=24, t=60, b=80)
    ))
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — GDP growth line chart (real + forecast)
# ─────────────────────────────────────────────────────────────────────────────
def build_gdp_chart(selected_countries, year_range):
    dff = df_annual[
        (df_annual['Country'].isin(selected_countries)) &
        (df_annual['Year'] >= year_range[0]) &
        (df_annual['Year'] <= year_range[1])
    ].copy()

    fig = go.Figure()

    for country in selected_countries:
        c      = dff[dff['Country'] == country]
        colour = COUNTRY_COLOURS[country]
        c_real = c[c['Is_Forecast'] == False]
        c_fore = c[c['Is_Forecast'] == True]

        fig.add_trace(go.Scatter(
            x    = c_real['Year'],
            y    = c_real['GDP_Growth'],
            name = country,
            mode = 'lines',
            line = dict(color=colour, width=2),
            hovertemplate = (
                f'<b>{country}</b><br>'
                'GDP growth: %{y:.1f}%<br>'
                'Year: %{x}<extra></extra>'
            )
        ))

        if not c_fore.empty:
            join = pd.concat([c_real.iloc[[-1]], c_fore])
            fig.add_trace(go.Scatter(
                x    = join['Year'],
                y    = join['GDP_Growth'],
                mode = 'lines',
                line = dict(color=colour, width=1.5, dash='dash'),
                opacity    = 0.6,
                showlegend = False,
                hovertemplate = (
                    f'<b>{country}</b><br>'
                    'GDP forecast: %{y:.1f}%<br>'
                    'Year: %{x}<extra></extra>'
                )
            ))

    # Zero reference line
    fig.add_hline(y=0, line_color='#AAAAAA', line_width=0.8, line_dash='dot')

    shapes, annots = key_annotations()
    shapes.append(forecast_shape())

    layout = base_layout()
    layout.update(dict(
        shapes      = shapes,
        annotations = annots,
        yaxis       = dict(
            title      = 'GDP growth (%)',
            ticksuffix = '%',
            showgrid   = True,
            gridcolor  = '#EEEEEE',
            zeroline   = True,
            zerolinecolor = '#CCCCCC',
            tickfont   = dict(size=11)
        ),
        hovermode = 'x unified'
    ))
    fig.update_layout(**layout)
    return fig



# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — Lollipop dot plot: Unemployment 2019 vs 2022 vs 2024 (replaces area)
# ─────────────────────────────────────────────────────────────────────────────
def build_unemployment_chart(selected_countries, year_range):
    key_years   = [2019, 2022, 2024]
    dot_colours = {
        2019: '#A8C8E8',  # soft blue  — pre-COVID baseline
        2022: '#E41A1C',  # red        — post-hike stress
        2024: '#4DAF4A',  # green      — recovery
    }
    labels = {2019: 'Pre-COVID (2019)', 2022: 'Post-hike (2022)', 2024: 'Latest (2024)'}

    dff = df_annual[
        (df_annual['Country'].isin(selected_countries)) &
        (df_annual['Year'].isin(key_years)) &
        (df_annual['Is_Forecast'] == False)
    ].copy()

    # Order countries consistently
    ordered = [c for c in COUNTRIES if c in selected_countries]

    fig = go.Figure()

    # Draw connector lines between 2019 and 2024 per country (lollipop stem)
    for country in ordered:
        c = dff[dff['Country'] == country]
        vals = {}
        for _, row in c.iterrows():
            vals[row['Year']] = row['Unemployment']

        if 2019 in vals and 2024 in vals:
            fig.add_trace(go.Scatter(
                x         = [vals[2019], vals[2024]],
                y         = [country, country],
                mode      = 'lines',
                line      = dict(color='#CCCCCC', width=2),
                showlegend= False,
                hoverinfo = 'skip'
            ))

    # Draw dots for each year
    for year in key_years:
        dy = dff[dff['Year'] == year].copy()
        dy = dy.set_index('Country').reindex(ordered).reset_index()

        fig.add_trace(go.Scatter(
            x    = dy['Unemployment'],
            y    = dy['Country'],
            mode = 'markers',
            name = labels[year],
            marker = dict(
                color  = dot_colours[year],
                size   = 14,
                line   = dict(color='white', width=1.5)
            ),
            hovertemplate = (
                '<b>%{y}</b><br>'
                f'{labels[year]}<br>'
                'Unemployment: %{x:.1f}%<extra></extra>'
            )
        ))

    layout = base_layout()
    layout.update(dict(
        xaxis = dict(
            title      = 'Unemployment rate (%)',
            ticksuffix = '%',
            showgrid   = True,
            gridcolor  = '#EEEEEE',
            zeroline   = False,
            tickfont   = dict(size=11)
        ),
        yaxis = dict(
            showgrid    = False,
            tickfont    = dict(size=11),
            autorange   = 'reversed',
            categoryorder = 'array',
            categoryarray = list(reversed(ordered))
        ),
        legend = dict(
            orientation = 'h',
            y=1.12, x=0,
            font=dict(size=11),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin = dict(l=130, r=24, t=60, b=48),
        hovermode = 'closest'
    ))
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — Animated scatter: Inflation vs Policy Rate
# ─────────────────────────────────────────────────────────────────────────────
def build_scatter_chart(selected_countries, year_range):
    dff = df_annual[
        (df_annual['Country'].isin(selected_countries)) &
        (df_annual['Year'] >= year_range[0]) &
        (df_annual['Year'] <= year_range[1]) &
        (df_annual['Is_Forecast'] == False) &
        (df_annual['Inflation'].notna()) &
        (df_annual['Policy_Rate'].notna())
    ].copy()

    fig = px.scatter(
        dff,
        x           = 'Policy_Rate',
        y           = 'Inflation',
        color       = 'Country',
        size        = 'Unemployment',
        animation_frame = 'Year',
        hover_name  = 'Country',
        hover_data  = {
            'Policy_Rate'  : ':.2f',
            'Inflation'    : ':.1f',
            'Unemployment' : ':.1f',
            'Year'         : True,
            'Country'      : False
        },
        color_discrete_map = COUNTRY_COLOURS,
        size_max    = 28,
        labels      = {
            'Policy_Rate'  : 'Policy rate (%)',
            'Inflation'    : 'Inflation rate (%)',
            'Unemployment' : 'Unemployment (%)'
        }
    )

    # 45-degree reference line (rate = inflation → real rate = 0)
    max_val = max(dff['Policy_Rate'].max(), dff['Inflation'].max()) + 1
    fig.add_trace(go.Scatter(
        x    = [0, max_val],
        y    = [0, max_val],
        mode = 'lines',
        line = dict(color='#CCCCCC', width=1, dash='dot'),
        showlegend    = False,
        hoverinfo     = 'skip'
    ))

    # Annotation on reference line
    fig.add_annotation(
        x=max_val * 0.8, y=max_val * 0.8,
        text='Rate = Inflation<br>(real rate = 0)',
        showarrow=False,
        font=dict(size=9, color='#AAAAAA'),
        xanchor='left'
    )

    layout = base_layout()
    layout.update(dict(
        xaxis = dict(
            title      = 'Policy rate (%)',
            ticksuffix = '%',
            showgrid   = True,
            gridcolor  = '#EEEEEE',
            zeroline   = True,
            zerolinecolor = '#CCCCCC',
            tickfont   = dict(size=11)
        ),
        yaxis = dict(
            title      = 'Inflation rate (%)',
            ticksuffix = '%',
            showgrid   = True,
            gridcolor  = '#EEEEEE',
            zeroline   = True,
            zerolinecolor = '#CCCCCC',
            tickfont   = dict(size=11)
        ),
        legend = dict(
            orientation = 'v',
            x=1.02, y=1,
            font=dict(size=11)
        )
    ))
    fig.update_layout(**layout)

    # Style animation buttons
    fig.update_layout(
        updatemenus=[dict(
            type       = 'buttons',
            showactive = False,
            y          = -0.9,
            x          = 0.5,
            xanchor    = 'center',
            yanchor    = 'top',
            pad        = dict(t=10),
            buttons    = [
                dict(label='▶  Play',
                     method='animate',
                     args=[None, dict(
                         frame=dict(duration=600, redraw=True),
                         fromcurrent=True
                     )]),
                dict(label='⏸  Pause',
                     method='animate',
                     args=[[None], dict(
                         frame=dict(duration=0, redraw=False),
                         mode='immediate'
                     )])
            ]
        )],
            sliders=[{
                'currentvalue': {
                    'prefix'   : 'Year: ',
                    'visible'  : True,
                    'xanchor'  : 'center',
                    'font'     : {'size': 12, 'color': TEXT_MUTED}
                },
                'pad'        : {'t': 50, 'b': 10},
                'x'          : 0.1,
                'len'        : 0.8,
                'xanchor'    : 'left',
            }]
        )
    
    return fig




# ═════════════════════════════════════════════════════════════════════════════
#  CALLBACK
# ═════════════════════════════════════════════════════════════════════════════

@callback(
    Output('line-chart-main',    'figure'),
    Output('heatmap-chart',      'figure'),
    Output('slope-chart',        'figure'),
    Output('gdp-chart',          'figure'),
    Output('unemployment-chart', 'figure'),
    Output('scatter-chart',      'figure'),
    Input('country-filter',      'value'),
    Input('year-filter',         'value'),
)
def update_all_charts(selected_countries, year_range):
    # Fallback — if user deselects everything, show all
    if not selected_countries:
        selected_countries = COUNTRIES

    return (
        build_line_chart(selected_countries, year_range),
        build_heatmap(selected_countries, year_range),
        build_slope_chart(selected_countries, year_range),
        build_gdp_chart(selected_countries, year_range),
        build_unemployment_chart(selected_countries, year_range),
        build_scatter_chart(selected_countries, year_range),
    )



# ═════════════════════════════════════════════════════════════════════════════
#  EXPAND MODAL CALLBACK
# ═════════════════════════════════════════════════════════════════════════════

# Chart ID → (title, builder function)
from dash import ALL

CHART_REGISTRY = {
    'line-chart-main':   ('Inflation Rate vs Policy Rate',        build_line_chart),
    'heatmap-chart':     ('Inflation Intensity Heatmap',          build_heatmap),
    'slope-chart':       ('Policy Rate: Baseline vs Peak vs Current', build_slope_chart),
    'gdp-chart':         ('GDP Growth Rate (2007–2030)',          build_gdp_chart),
    'unemployment-chart':('Unemployment: Before & After Rate Hikes', build_unemployment_chart),
    'scatter-chart':     ('Inflation vs Policy Rate — Animated Scatter', build_scatter_chart),
}


@callback(
    Output('chart-modal',    'is_open'),
    Output('modal-title',    'children'),
    Output('modal-chart',    'figure'),
    Input({'type': 'expand-btn', 'index': ALL}, 'n_clicks'),
    State('country-filter',  'value'),
    State('year-filter',     'value'),
    prevent_initial_call=True
)
def toggle_expand_modal(n_clicks_list, selected_countries, year_range):
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    # Find which button was clicked
    triggered = ctx.triggered_id
    if triggered is None:
        return no_update, no_update, no_update

    chart_id = triggered['index']

    if chart_id not in CHART_REGISTRY:
        return no_update, no_update, no_update

    if not selected_countries:
        selected_countries = COUNTRIES

    title, builder = CHART_REGISTRY[chart_id]
    fig = builder(selected_countries, year_range)

    return True, title, fig


# ═════════════════════════════════════════════════════════════════════════════
#  RUN SERVER
# ═════════════════════════════════════════════════════════════════════════════

# http://127.0.0.1:8050
if __name__ == '__main__':
    app.run(debug=True, port=8050)
