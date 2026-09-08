"""
dashboard.py — painel Streamlit do comparativo Presidente 2018 x 2022,
gerado por coleta.py. Lê comparativo_presidente_2018_2022.csv (mesma
pasta) e usa a MESMA identidade visual do painel de apuração ao vivo
(app.py deste projeto): masthead navy, tipografia Montserrat, paleta
Eixo (vinho/marinho/amarelo), cards de indicador e tabelas no mesmo
estilo "tse-*".

Rodar: streamlit run dashboard.py
"""

from __future__ import annotations

import html as _html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CSV = Path(__file__).parent / "comparativo_presidente_2018_2022.csv"
LOGO_PATH = "logoeixo.png"

# ── Config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Comparativo TSE · Presidente 2018 → 2022", layout="wide")

# Mesma paleta/identidade visual do painel Eixo de apuração ao vivo.
EIXO = {
    "tinta": "#111111",
    "vinho": "#962E4D",
    "gelo": "#F4F3EF",
    "borda": "#DADAD4",
    "subtexto": "#767672",
    "amarelo": "#E8A600",
    "marinho": "#192D4E",
    "coral": "#B84349",
}
COR_PT = EIXO["vinho"]
COR_BOL = EIXO["marinho"]

NOMES_UF = {
    "SP": "São Paulo", "RJ": "Rio de Janeiro", "DF": "Distrito Federal", "MG": "Minas Gerais",
    "AC": "Acre", "RS": "Rio Grande do Sul", "GO": "Goiás", "SC": "Santa Catarina",
    "PR": "Paraná", "MS": "Mato Grosso do Sul", "ES": "Espírito Santo", "RN": "Rio Grande do Norte",
    "PB": "Paraíba", "RO": "Rondônia", "AM": "Amazonas", "MT": "Mato Grosso", "PE": "Pernambuco",
    "TO": "Tocantins", "PA": "Pará", "PI": "Piauí", "SE": "Sergipe", "BA": "Bahia", "CE": "Ceará",
    "AP": "Amapá", "AL": "Alagoas", "MA": "Maranhão", "RR": "Roraima", "ZZ": "Voto no exterior",
}


def fmt(n: int) -> str:
    """Formata inteiro com ponto de milhar (padrão BR)."""
    return f"{n:,}".replace(",", ".")


def esc(texto: str) -> str:
    return _html.escape(str(texto or ""))


# ── CSS (mesmas classes tse-* do app.py) ────────────────────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
* {{ box-sizing: border-box; }}
[data-testid="stAppViewContainer"] {{ background: {EIXO["gelo"]} !important; }}
.block-container {{ max-width: 1180px !important; padding: 0 2rem 3rem !important; background: {EIXO["gelo"]}; }}
[data-testid="stHeader"] {{ display: none; }}
[data-testid="stDecoration"] {{ display: none; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
body, p, span, div, label, input, select {{ font-family: 'Montserrat', sans-serif !important; }}

[data-testid="stSidebar"] {{ background: {EIXO["gelo"]} !important; border-right: 1px solid {EIXO["borda"]} !important; }}
[data-testid="stSidebar"] * {{ font-family: 'Montserrat', sans-serif !important; font-size: 13px !important; }}

.tse-masthead {{
    background: {EIXO["marinho"]};
    color: #fff;
    padding: 40px 48px;
    margin: 0 -2rem 24px -2rem;
    width: calc(100% + 4rem);
    display: flex; align-items: center; justify-content: space-between;
}}
.tse-masthead-title {{ font-size: 38px; font-weight: 800; color: #fff; line-height: 1.1; }}
.tse-masthead-meta {{
    font-size: 12px; color: rgba(255,255,255,0.65); letter-spacing: 0.05em;
    margin-top: 6px; display: block;
}}
.tse-masthead-mark {{
    width: 52px; height: 52px; border: 2px solid rgba(255,255,255,0.55);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 24px; flex-shrink: 0;
}}
.tse-page-title {{
    font-size: 24px; font-weight: 700; letter-spacing: 0.06em;
    text-transform: uppercase; color: {EIXO["tinta"]};
    border-bottom: 1px solid {EIXO["borda"]}; padding-bottom: 14px;
    margin: 20px 0 20px;
}}

[data-testid="stTabs"] [role="tablist"] {{ border-bottom: 1px solid {EIXO["borda"]} !important; gap: 0 !important; }}
[data-testid="stTabs"] [role="tab"] {{
    font-size: 11px !important; font-weight: 500 !important; letter-spacing: 0.12em !important;
    text-transform: uppercase !important; color: {EIXO["subtexto"]} !important;
    padding: 10px 20px 9px !important; border-bottom: 2px solid transparent !important;
    background: transparent !important; border-radius: 0 !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {EIXO["marinho"]} !important; border-bottom-color: {EIXO["marinho"]} !important;
}}

.tse-stat-wrap {{ display: flex; background: #fff; border: 1px solid {EIXO["borda"]}; margin-top: 10px; }}
.tse-stat {{ flex: 1; padding: 14px 16px; border-left: 1px solid {EIXO["borda"]}; }}
.tse-stat:first-child {{ border-left: none; }}
.tse-stat-label {{
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: {EIXO["subtexto"]}; margin-bottom: 4px;
}}
.tse-stat-value {{ font-size: 20px; font-weight: 800; color: {EIXO["tinta"]}; line-height: 1; }}
.tse-stat-sub {{ font-size: 10.5px; color: {EIXO["subtexto"]}; margin-top: 4px; }}

.tse-snap-wrap {{ width: 100%; background: #fff; border: 1px solid {EIXO["borda"]}; overflow: hidden; margin-top: 10px; }}
.tse-snap-table {{ width: 100%; border-collapse: collapse; }}
.tse-snap-table thead th {{
    background: {EIXO["marinho"]}; color: #fff;
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 11px 16px; text-align: left;
}}
.tse-snap-table thead th.tse-num {{ text-align: right; }}
.tse-snap-table tbody tr {{ border-bottom: 1px solid {EIXO["borda"]}; }}
.tse-snap-table tbody tr:last-child {{ border-bottom: none; }}
.tse-snap-table tbody tr:hover {{ background: {EIXO["gelo"]}; }}
.tse-snap-table tbody td {{ padding: 11px 16px; font-size: 12.5px; color: {EIXO["tinta"]}; vertical-align: middle; }}
.tse-snap-table tbody td.tse-num {{ text-align: right; font-weight: 700; }}
.tse-snap-cand {{ font-weight: 700; color: {EIXO["marinho"]}; }}
.tse-badge {{
    display: inline-block; font-size: 9px; font-weight: 700; letter-spacing: 0.06em;
    text-transform: uppercase; padding: 2px 7px; border-radius: 2px; margin-left: 6px; vertical-align: middle;
}}
.tse-badge-eleito {{ background: #d4edda; color: #1a5c2e; }}
.tse-badge-naoeleito {{ background: {EIXO["borda"]}; color: {EIXO["subtexto"]}; }}

.tse-pos-intro {{
    font-size: 12.5px; color: {EIXO["subtexto"]}; line-height: 1.6;
    background: #fff; border: 1px solid {EIXO["borda"]}; border-left: 4px solid {EIXO["amarelo"]};
    padding: 14px 18px; margin: 4px 0 18px;
}}
.tse-pos-cat {{
    font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    color: #fff; background: {EIXO["marinho"]}; padding: 9px 16px; margin-top: 18px;
}}
</style>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="tse-masthead">
  <div>
    <div class="tse-masthead-title">Comparativo TSE</div>
    <span class="tse-masthead-meta">dados oficiais e permanentes · 2º turno 2018 e 2022</span>
  </div>
  <div class="tse-masthead-mark">🗳️</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    try:
        st.image(LOGO_PATH, width="stretch")
    except Exception:
        st.caption("Logo não encontrada.")
    st.markdown(
        f'<div style="border-left:3px solid {EIXO["vinho"]};padding:10px 12px;'
        f'margin:0 0 10px 0;background:#fff;border-radius:0 6px 6px 0;">'
        f'<p style="font-size:12.5px;color:{EIXO["tinta"]};line-height:1.65;margin:0;">'
        f'Compara o 2º turno de Presidente de 2018 e 2022 por UF, a partir do dataset '
        f'permanente <strong>votacao_candidato_munzona</strong> do TSE (não o site de '
        f'apuração ao vivo, que só mantém pleitos recentes).</p></div>',
        unsafe_allow_html=True,
    )
    st.caption("Coleta e comparação em coleta.py.")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    df["nome"] = df["uf"].map(NOMES_UF).fillna(df["uf"])
    return df.sort_values("variacao_margem_pt", ascending=False)


df = carregar_dados()

st.markdown('<div class="tse-page-title">Presidente · 2018 vs 2022</div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="tse-pos-intro">
  ⚠️ Cada UF é comparada pelo NÚMERO do candidato na urna, não pelo nome — o
  número de um dos lados muda entre os dois anos (Bolsonaro era 17 em 2018 e
  22 em 2022), então a coluna "pt"/"bolsonaro" é quem garante a comparação
  correta entre os ciclos.
</div>""",
    unsafe_allow_html=True,
)

tot18_pt = int(df["pt_votos_2018"].sum())
tot18_bol = int(df["bolsonaro_votos_2018"].sum())
tot22_pt = int(df["pt_votos_2022"].sum())
tot22_bol = int(df["bolsonaro_votos_2022"].sum())
pct18_pt = tot18_pt / (tot18_pt + tot18_bol) * 100
pct18_bol = tot18_bol / (tot18_pt + tot18_bol) * 100
pct22_pt = tot22_pt / (tot22_pt + tot22_bol) * 100
pct22_bol = tot22_bol / (tot22_pt + tot22_bol) * 100
margem18 = pct18_pt - pct18_bol
margem22 = pct22_pt - pct22_bol
viraram = df[df["virou_a_favor_do_pt"]]

st.markdown(
    f"""
<div class="tse-stat-wrap">
  <div class="tse-stat">
    <div class="tse-stat-label">Margem nacional · 2018</div>
    <div class="tse-stat-value" style="color:{COR_BOL};">Bolsonaro +{abs(margem18):.1f} p.p.</div>
    <div class="tse-stat-sub">PT {pct18_pt:.2f}% × Bolsonaro {pct18_bol:.2f}%</div>
  </div>
  <div class="tse-stat">
    <div class="tse-stat-label">Margem nacional · 2022</div>
    <div class="tse-stat-value" style="color:{COR_PT};">PT +{margem22:.1f} p.p.</div>
    <div class="tse-stat-sub">PT {pct22_pt:.2f}% × Bolsonaro {pct22_bol:.2f}%</div>
  </div>
  <div class="tse-stat">
    <div class="tse-stat-label">Estados que viraram para o PT</div>
    <div class="tse-stat-value">{len(viraram)}</div>
    <div class="tse-stat-sub">{esc(", ".join(viraram["nome"]) if len(viraram) else "nenhum")}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

legenda_cores = (
    f'<span style="display:inline-flex;align-items:center;margin-right:16px;">'
    f'<span style="width:10px;height:10px;border-radius:2px;background:{COR_PT};'
    f'display:inline-block;margin-right:6px;"></span>PT à frente / avançou</span>'
    f'<span style="display:inline-flex;align-items:center;margin-right:16px;">'
    f'<span style="width:10px;height:10px;border-radius:2px;background:{COR_BOL};'
    f'display:inline-block;margin-right:6px;"></span>Bolsonaro à frente / avançou</span>'
)
st.markdown(
    f'<div style="font-size:11.5px;color:{EIXO["subtexto"]};margin:14px 0 4px;">{legenda_cores}</div>',
    unsafe_allow_html=True,
)


def grafico_variacao(df: pd.DataFrame) -> go.Figure:
    cores = [COR_PT if v >= 0 else COR_BOL for v in df["variacao_margem_pt"]]
    fig = go.Figure(
        go.Bar(
            x=df["variacao_margem_pt"],
            y=df["uf"],
            orientation="h",
            marker_color=cores,
            text=[f"{v:+.2f} p.p." for v in df["variacao_margem_pt"]],
            textposition="outside",
            textfont={"family": "Montserrat", "color": EIXO["tinta"]},
            customdata=df[["nome", "margem_pt_2018", "margem_pt_2022"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Margem 2018: %{customdata[1]:+.2f} p.p.<br>"
                "Margem 2022: %{customdata[2]:+.2f} p.p.<br>"
                "Variação: %{x:+.2f} p.p.<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=28 * len(df) + 60,
        margin=dict(l=10, r=70, t=10, b=40),
        xaxis_title="variação da margem do PT (pontos percentuais)",
        yaxis=dict(autorange="reversed", title=None),
        plot_bgcolor=EIXO["gelo"],
        paper_bgcolor=EIXO["gelo"],
        font={"family": "Montserrat", "size": 11, "color": EIXO["tinta"]},
        bargap=0.25,
    )
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(gridcolor=EIXO["borda"], zeroline=False)
    fig.add_vline(x=0, line_width=1, line_color=EIXO["subtexto"])
    return fig


def grafico_dumbbell(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, row in df.iterrows():
        cor22 = COR_PT if row["margem_pt_2022"] >= 0 else COR_BOL
        cor18 = COR_PT if row["margem_pt_2018"] >= 0 else COR_BOL
        fig.add_trace(
            go.Scatter(
                x=[row["margem_pt_2018"], row["margem_pt_2022"]],
                y=[row["uf"], row["uf"]],
                mode="lines",
                line=dict(color=EIXO["subtexto"], width=1.5),
                opacity=0.5,
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[row["margem_pt_2018"]],
                y=[row["uf"]],
                mode="markers",
                marker=dict(size=9, color="white", line=dict(color=cor18, width=2)),
                showlegend=False,
                hovertemplate=f"<b>{row['nome']}</b> — 2018<br>Margem: {row['margem_pt_2018']:+.2f} p.p.<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[row["margem_pt_2022"]],
                y=[row["uf"]],
                mode="markers",
                marker=dict(size=10, color=cor22),
                showlegend=False,
                hovertemplate=f"<b>{row['nome']}</b> — 2022<br>Margem: {row['margem_pt_2022']:+.2f} p.p.<extra></extra>",
            )
        )
    fig.update_layout(
        height=28 * len(df) + 60,
        margin=dict(l=10, r=20, t=10, b=40),
        xaxis_title="margem do PT (pontos percentuais) — claro = 2018, cheio = 2022",
        yaxis=dict(autorange="reversed", title=None),
        plot_bgcolor=EIXO["gelo"],
        paper_bgcolor=EIXO["gelo"],
        font={"family": "Montserrat", "size": 11, "color": EIXO["tinta"]},
    )
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(gridcolor=EIXO["borda"], zeroline=False)
    fig.add_vline(x=0, line_width=1, line_color=EIXO["subtexto"])
    return fig


tab_variacao, tab_antes_depois, tab_tabela = st.tabs(
    ["Variação por UF", "2018 x 2022 (antes/depois)", "Tabela completa"]
)

with tab_variacao:
    st.caption(
        "2018 → 2022, em pontos percentuais. Ordenado do maior avanço do PT "
        "(topo) para o maior avanço do Bolsonaro (base)."
    )
    st.plotly_chart(grafico_variacao(df), width="stretch", theme=None, config={"displayModeBar": False})

with tab_antes_depois:
    st.caption(
        "Ponto claro = 2018, ponto cheio = 2022 — a linha mostra o trajeto. "
        "Cruzar a linha do zero é virar de lado."
    )
    st.plotly_chart(grafico_dumbbell(df), width="stretch", theme=None, config={"displayModeBar": False})

with tab_tabela:
    linhas_html = "".join(
        f"""
<tr>
  <td class="tse-snap-cand">{esc(r.nome)} ({esc(r.uf)})</td>
  <td class="tse-num">{fmt(r.pt_votos_2018)}</td>
  <td class="tse-num">{fmt(r.bolsonaro_votos_2018)}</td>
  <td class="tse-num">{r.margem_pt_2018:+.2f} p.p.</td>
  <td class="tse-num">{fmt(r.pt_votos_2022)}</td>
  <td class="tse-num">{fmt(r.bolsonaro_votos_2022)}</td>
  <td class="tse-num">{r.margem_pt_2022:+.2f} p.p.</td>
  <td class="tse-num">{r.variacao_margem_pt:+.2f} p.p.
    {'<span class="tse-badge tse-badge-eleito">virou</span>' if r.virou_a_favor_do_pt else ''}
  </td>
</tr>"""
        for r in df.itertuples()
    )
    st.markdown(
        f"""
<div class="tse-snap-wrap">
  <table class="tse-snap-table">
    <thead>
      <tr>
        <th>UF</th><th class="tse-num">PT 2018</th><th class="tse-num">Bols. 2018</th>
        <th class="tse-num">Margem 2018</th><th class="tse-num">PT 2022</th>
        <th class="tse-num">Bols. 2022</th><th class="tse-num">Margem 2022</th>
        <th class="tse-num">Variação</th>
      </tr>
    </thead>
    <tbody>{linhas_html}</tbody>
  </table>
</div>""",
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
<p style="font-size:11.5px;color:{EIXO["subtexto"]};line-height:1.6;margin-top:18px;">
Fonte: Portal de Dados Abertos do TSE (dadosabertos.tse.jus.br), dataset
votacao_candidato_munzona — 2º turno de Presidente, 2018 e 2022. "ZZ" é o
voto de eleitores no exterior.
</p>""",
    unsafe_allow_html=True,
)
