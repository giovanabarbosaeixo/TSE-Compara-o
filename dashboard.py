"""
dashboard.py — painel Streamlit do comparativo Presidente 2018 x 2022 gerado
por coleta.py. Lê comparativo_presidente_2018_2022.csv (mesma pasta) e
reproduz os gráficos do relatório: cards de resumo nacional, barra
divergente da variação de margem por UF e dumbbell (2018 -> 2022).

Rodar: streamlit run dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CSV = Path(__file__).parent / "comparativo_presidente_2018_2022.csv"

# mesma paleta do relatório: vermelho = PT, azul = Bolsonaro
COR_PT = "#e34948"
COR_BOL = "#2a78d6"
COR_NEUTRA = "#898781"

NOMES_UF = {
    "SP": "São Paulo", "RJ": "Rio de Janeiro", "DF": "Distrito Federal", "MG": "Minas Gerais",
    "AC": "Acre", "RS": "Rio Grande do Sul", "GO": "Goiás", "SC": "Santa Catarina",
    "PR": "Paraná", "MS": "Mato Grosso do Sul", "ES": "Espírito Santo", "RN": "Rio Grande do Norte",
    "PB": "Paraíba", "RO": "Rondônia", "AM": "Amazonas", "MT": "Mato Grosso", "PE": "Pernambuco",
    "TO": "Tocantins", "PA": "Pará", "PI": "Piauí", "SE": "Sergipe", "BA": "Bahia", "CE": "Ceará",
    "AP": "Amapá", "AL": "Alagoas", "MA": "Maranhão", "RR": "Roraima", "ZZ": "Voto no exterior",
}


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    df["nome"] = df["uf"].map(NOMES_UF).fillna(df["uf"])
    return df.sort_values("variacao_margem_pt", ascending=False)


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
        height=28 * len(df) + 80,
        margin=dict(l=10, r=60, t=10, b=30),
        xaxis_title="variação da margem do PT (pontos percentuais)",
        yaxis=dict(autorange="reversed", title=None),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.25,
    )
    fig.add_vline(x=0, line_width=1, line_color=COR_NEUTRA)
    return fig


def grafico_dumbbell(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, row in df.iterrows():
        cor22 = COR_PT if row["margem_pt_2022"] >= 0 else COR_BOL
        fig.add_trace(
            go.Scatter(
                x=[row["margem_pt_2018"], row["margem_pt_2022"]],
                y=[row["uf"], row["uf"]],
                mode="lines",
                line=dict(color=COR_NEUTRA, width=1.5),
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
                marker=dict(
                    size=9,
                    color="white",
                    line=dict(color=COR_PT if row["margem_pt_2018"] >= 0 else COR_BOL, width=2),
                ),
                name="2018",
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
                name="2022",
                showlegend=False,
                hovertemplate=f"<b>{row['nome']}</b> — 2022<br>Margem: {row['margem_pt_2022']:+.2f} p.p.<extra></extra>",
            )
        )
    fig.update_layout(
        height=28 * len(df) + 80,
        margin=dict(l=10, r=20, t=10, b=30),
        xaxis_title="margem do PT (pontos percentuais)",
        yaxis=dict(autorange="reversed", title=None),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.add_vline(x=0, line_width=1, line_color=COR_NEUTRA)
    return fig


def main():
    st.set_page_config(page_title="Presidente 2018 → 2022", layout="wide")
    df = carregar_dados()

    st.title("Presidente 2018 → 2022: como cada estado mudou")
    st.caption(
        "Comparação do 2º turno (Haddad/Lula × Bolsonaro) por UF, com base nos dados oficiais "
        "e permanentes do TSE (votação por candidato/município/zona)."
    )

    tot18_pt = df["pt_votos_2018"].sum()
    tot18_bol = df["bolsonaro_votos_2018"].sum()
    tot22_pt = df["pt_votos_2022"].sum()
    tot22_bol = df["bolsonaro_votos_2022"].sum()
    margem18 = tot18_pt / (tot18_pt + tot18_bol) * 100 - tot18_bol / (tot18_pt + tot18_bol) * 100
    margem22 = tot22_pt / (tot22_pt + tot22_bol) * 100 - tot22_bol / (tot22_pt + tot22_bol) * 100
    viraram = df[df["virou_a_favor_do_pt"]]

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Margem nacional · 2018",
        f"Bolsonaro +{abs(margem18):.1f} p.p.",
        help=f"PT {tot18_pt/(tot18_pt+tot18_bol)*100:.2f}% × Bolsonaro {tot18_bol/(tot18_pt+tot18_bol)*100:.2f}%",
    )
    c2.metric(
        "Margem nacional · 2022",
        f"PT +{margem22:.1f} p.p.",
        help=f"PT {tot22_pt/(tot22_pt+tot22_bol)*100:.2f}% × Bolsonaro {tot22_bol/(tot22_pt+tot22_bol)*100:.2f}%",
    )
    c3.metric(
        "Estados que viraram para o PT",
        len(viraram),
        help=", ".join(viraram["nome"]) if len(viraram) else "nenhum",
    )

    st.subheader("Variação da margem do PT por UF")
    st.caption("2018 → 2022, em pontos percentuais. Vermelho = avanço do PT, azul = avanço do Bolsonaro.")
    st.plotly_chart(grafico_variacao(df), use_container_width=True)

    st.subheader("Margem PT × Bolsonaro: 2018 comparado a 2022")
    st.caption("Ponto claro = 2018, ponto cheio = 2022. Cruzar a linha do zero é virar de lado.")
    st.plotly_chart(grafico_dumbbell(df), use_container_width=True)

    with st.expander("Ver tabela com todos os números"):
        colunas = [
            "nome", "pt_votos_2018", "bolsonaro_votos_2018", "pt_pct_2018",
            "pt_votos_2022", "bolsonaro_votos_2022", "pt_pct_2022",
            "margem_pt_2018", "margem_pt_2022", "variacao_margem_pt", "virou_a_favor_do_pt",
        ]
        st.dataframe(df[colunas], use_container_width=True, hide_index=True)

    st.caption(
        "Fonte: Portal de Dados Abertos do TSE (dadosabertos.tse.jus.br), dataset "
        "votacao_candidato_munzona — 2º turno de Presidente, 2018 e 2022. "
        "\"ZZ\" é o voto de eleitores no exterior."
    )


if __name__ == "__main__":
    main()
