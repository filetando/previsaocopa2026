"""
Dashboard interativo Copa 2026 — Modelo xG Dixon-Coles.
Executar: streamlit run app_streamlit.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Garante que src/ esteja no path independente de onde o app for executado
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.collection.teams import COPA_2026_TEAMS
from src.model.copa2026 import GROUPS
from src.model.matchup import classify_style
from src.model.pipeline import prever_confronto
from src.utils.config import DATA_PROCESSED

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Copa 2026 — Modelo xG",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Constantes visuais
# ---------------------------------------------------------------------------
RADAR_DIMS = [
    ("forca_ofensiva",       "Força Ofensiva"),
    ("solidez_defensiva",    "Solidez Def."),
    ("qualidade_finalizacao","Qualidade xG"),
    ("dominio_territorial",  "Domínio"),
    ("eficiencia_finalizacao","Eficiência"),
    ("volume_ataque",        "Volume Ataque"),
    ("solidez_xg",           "Solidez xG Def."),
]

STYLE_LABEL = {
    "high_press": "Alta Pressão ⚡",
    "possession": "Posse de Bola 🔵",
    "direct":     "Jogo Direto ➡️",
    "low_block":  "Bloco Baixo 🛡️",
}

COLOR_WIN  = "#2ecc71"   # verde
COLOR_LOSE = "#e74c3c"   # vermelho
COLOR_DRAW = "#3498db"   # azul

# ---------------------------------------------------------------------------
# Cache de recursos pesados
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Carregando modelo Dixon-Coles…")
def load_model_cached():
    import pickle
    path = ROOT / "outputs" / "model" / "dixon_coles_v1.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)


@st.cache_data(show_spinner=False)
def load_indices() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "team_profiles" / "indices_v1.parquet")


@st.cache_data(show_spinner=False)
def load_group_matches() -> list[dict]:
    path = ROOT / "outputs" / "predictions" / "copa2026_grupos.json"
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_standings() -> pd.DataFrame:
    path = ROOT / "outputs" / "predictions" / "copa2026_standings.parquet"
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Helpers de previsão
# ---------------------------------------------------------------------------
def predict_matchup(team_a: str, team_b: str) -> dict:
    """Chama o pipeline e devolve dict com probabilidades e placares."""
    return prever_confronto(team_a, team_b, apply_style=True)


def get_index_row(team: str, indices: pd.DataFrame) -> dict:
    """Retorna dict {dim: valor} para um time; NaN vira None."""
    if team not in indices.index:
        return {}
    row = indices.loc[team]
    return {k: (None if (isinstance(v, float) and math.isnan(v)) else round(float(v), 1))
            for k, v in row.items()}


# ---------------------------------------------------------------------------
# Componentes de gráfico
# ---------------------------------------------------------------------------
def bar_result_probs(prob_a: float, prob_draw: float, prob_b: float,
                     label_a: str, label_b: str) -> go.Figure:
    colors = [COLOR_WIN, COLOR_DRAW, COLOR_LOSE]
    if prob_b > prob_a:
        colors = [COLOR_LOSE, COLOR_DRAW, COLOR_WIN]

    fig = go.Figure(go.Bar(
        x=[f"🏆 {label_a}", "🤝 Empate", f"🏆 {label_b}"],
        y=[prob_a * 100, prob_draw * 100, prob_b * 100],
        marker_color=colors,
        text=[f"{prob_a*100:.1f}%", f"{prob_draw*100:.1f}%", f"{prob_b*100:.1f}%"],
        textposition="outside",
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 100], ticksuffix="%"),
        showlegend=False,
        height=320,
        margin=dict(t=20, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def radar_chart(team_a: str, idx_a: dict, team_b: str, idx_b: dict) -> go.Figure:
    labels = [label for _, label in RADAR_DIMS]
    keys   = [key   for key, _   in RADAR_DIMS]

    vals_a = [idx_a.get(k) or 0 for k in keys]
    vals_b = [idx_b.get(k) or 0 for k in keys]

    fig = go.Figure()
    for vals, name, color, fill in [
        (vals_a, team_a, COLOR_WIN,  COLOR_WIN  + "30"),
        (vals_b, team_b, COLOR_LOSE, COLOR_LOSE + "30"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=name,
            line_color=color,
            fillcolor=fill,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10], tickvals=[2, 4, 6, 8, 10])),
        showlegend=True,
        height=380,
        margin=dict(t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def radar_multi(teams: list[str], indices: pd.DataFrame) -> go.Figure:
    labels = [label for _, label in RADAR_DIMS]
    keys   = [key   for key, _   in RADAR_DIMS]
    palette = [COLOR_WIN, COLOR_LOSE, "#f39c12", "#9b59b6"]

    fig = go.Figure()
    for i, team in enumerate(teams):
        idx = get_index_row(team, indices)
        vals = [idx.get(k) or 0 for k in keys]
        color = palette[i % len(palette)]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=team,
            line_color=color,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10])),
        showlegend=True,
        height=420,
        margin=dict(t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Seções do dashboard
# ---------------------------------------------------------------------------
def section_matchup(indices: pd.DataFrame):
    st.header("⚔️ Previsão de Confronto")

    teams_sorted = sorted(COPA_2026_TEAMS)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        team_a = st.selectbox("Time A", teams_sorted, index=teams_sorted.index("Brazil"),
                              key="sel_a")
    with col2:
        team_b = st.selectbox("Time B", teams_sorted, index=teams_sorted.index("France"),
                              key="sel_b")
    with col3:
        st.write("")
        st.write("")
        prever = st.button("⚽ Prever", use_container_width=True, type="primary")

    if not prever:
        st.info("Selecione dois times e clique em **Prever** para ver as probabilidades.")
        return

    if team_a == team_b:
        st.warning("Selecione times diferentes.")
        return

    with st.spinner("Calculando…"):
        result = predict_matchup(team_a, team_b)

    prob_a    = result["prob_vitoria_" + team_a]
    prob_draw = result["prob_empate"]
    prob_b    = result["prob_vitoria_" + team_b]
    xg_a      = result["xg_a"]
    xg_b      = result["xg_b"]
    placar    = result["placar_mais_provavel"]["placar"]
    top5      = result["top5_placares"]
    style_a   = STYLE_LABEL.get(result.get("style_a", "direct"), result.get("style_a", "—"))
    style_b   = STYLE_LABEL.get(result.get("style_b", "direct"), result.get("style_b", "—"))

    idx_a = get_index_row(team_a, indices)
    idx_b = get_index_row(team_b, indices)

    # Favorito para cor de cabeçalho
    cor_a = COLOR_WIN  if prob_a > prob_b else (COLOR_DRAW if prob_a == prob_b else COLOR_LOSE)
    cor_b = COLOR_WIN  if prob_b > prob_a else (COLOR_DRAW if prob_a == prob_b else COLOR_LOSE)

    st.divider()

    # --- Tabela de métricas ---
    c1, c2, c3 = st.columns([1.4, 1, 1.4])

    with c1:
        st.markdown(f"### 🏳️ {team_a}")
    with c2:
        st.markdown("### vs")
    with c3:
        st.markdown(f"### 🏳️ {team_b}")

    metrics = [
        ("Probabilidade de Vitória", f"{prob_a*100:.1f}%", f"{prob_b*100:.1f}%"),
        ("Probabilidade de Empate",  f"{prob_draw*100:.1f}%", ""),
        ("xG Esperado",              f"{xg_a:.2f}", f"{xg_b:.2f}"),
        ("Força Ofensiva (0-10)",    str(idx_a.get("forca_ofensiva") or "—"),
                                     str(idx_b.get("forca_ofensiva") or "—")),
        ("Solidez Defensiva (0-10)", str(idx_a.get("solidez_defensiva") or "—"),
                                     str(idx_b.get("solidez_defensiva") or "—")),
        ("Estilo de Jogo",           style_a, style_b),
        ("Placar Mais Provável",     placar, ""),
    ]

    for label, val_a, val_b in metrics:
        ca, cb, cc = st.columns([1.4, 1, 1.4])
        with ca:
            st.metric(label="" , value=val_a, label_visibility="hidden")
        with cb:
            st.caption(label)
        with cc:
            st.metric(label="", value=val_b, label_visibility="hidden")

    st.divider()

    # --- Gráficos ---
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Probabilidades de Resultado")
        st.plotly_chart(
            bar_result_probs(prob_a, prob_draw, prob_b, team_a, team_b),
            use_container_width=True,
        )

    with g2:
        st.subheader("Perfil Tático (Radar)")
        if idx_a or idx_b:
            st.plotly_chart(
                radar_chart(team_a, idx_a, team_b, idx_b),
                use_container_width=True,
            )
        else:
            st.info("Índices táticos não disponíveis para esses times.")

    # --- Top 5 placares ---
    st.subheader("Top 5 Placares Mais Prováveis")
    df_top5 = pd.DataFrame([
        {"Placar": r["placar"], "Probabilidade": f"{r['probabilidade']*100:.1f}%"}
        for r in top5
    ])
    st.dataframe(df_top5, use_container_width=True, hide_index=True)


def section_groups():
    st.header("🏆 Fase de Grupos — Copa 2026")

    group_matches = load_group_matches()
    standings     = load_standings()

    tabs = st.tabs([f"Grupo {g}" for g in sorted(GROUPS.keys())])

    for tab, group_name in zip(tabs, sorted(GROUPS.keys())):
        with tab:
            # Tabela de classificação
            df_group = (standings[standings["group"] == group_name]
                        .sort_values("rank")
                        .reset_index(drop=True))

            def row_color(rank: int) -> str:
                if rank <= 2:
                    return "background-color: #1a472a; color: white"
                return ""

            st.subheader(f"Classificação — Grupo {group_name}")

            # Monta tabela formatada
            display = df_group[["rank", "team", "pts", "gf", "ga", "gd"]].copy()
            display.columns = ["Pos", "Seleção", "Pts Esp.", "GF", "GA", "Saldo"]
            display["Pts Esp."] = display["Pts Esp."].round(1)
            display["GF"]       = display["GF"].round(1)
            display["GA"]       = display["GA"].round(1)
            display["Saldo"]    = display["Saldo"].round(1)

            def highlight_qualif(row):
                if row["Pos"] == 1:
                    return ["background-color: #1a472a; color: white"] * len(row)
                if row["Pos"] == 2:
                    return ["background-color: #1e5631; color: white"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display.style.apply(highlight_qualif, axis=1),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("🟢 Verde = classificados (1º e 2º lugar)")

            # Jogos do grupo
            with st.expander(f"📋 Ver todos os jogos — Grupo {group_name}"):
                group_games = [m for m in group_matches if m["group"] == group_name]

                for m in group_games:
                    ta, tb = m["team_a"], m["team_b"]
                    pa, pd_, pb = m["prob_win_a"], m["prob_draw"], m["prob_win_b"]
                    xa, xb = m.get("xg_a") or 0, m.get("xg_b") or 0
                    placar = m.get("placar_mais_provavel", "?-?")

                    fav  = ta if pa > pb else (tb if pb > pa else "Empate")
                    diff = abs(pa - pb)
                    conf = "forte" if diff > 0.3 else ("moderada" if diff > 0.1 else "equilibrado")

                    col_a, col_mid, col_b = st.columns([2, 3, 2])
                    with col_a:
                        st.markdown(f"**{ta}**")
                        st.caption(f"P(vitória): {pa*100:.0f}% | xG: {xa:.2f}")
                    with col_mid:
                        st.markdown(
                            f"<div style='text-align:center'>"
                            f"<b>{pa*100:.0f}%</b> — {pd_*100:.0f}% — <b>{pb*100:.0f}%</b><br>"
                            f"<small>Placar: <b>{placar}</b> | {conf}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_b:
                        st.markdown(f"**{tb}**", )
                        st.caption(f"P(vitória): {pb*100:.0f}% | xG: {xb:.2f}")

                    st.divider()


def section_comparison(indices: pd.DataFrame):
    st.header("📊 Comparação de Times")

    teams_sorted = sorted(COPA_2026_TEAMS)
    selected = st.multiselect(
        "Selecione até 4 seleções para comparar",
        teams_sorted,
        default=["Brazil", "France", "Argentina", "Spain"],
        max_selections=4,
    )

    if len(selected) < 2:
        st.info("Selecione pelo menos 2 times.")
        return

    # Radar comparativo
    st.subheader("Radar Tático Comparativo")
    st.plotly_chart(radar_multi(selected, indices), use_container_width=True)

    # Tabela de índices
    st.subheader("Índices Táticos")
    rows = []
    for team in selected:
        idx = get_index_row(team, indices)
        rows.append({
            "Seleção":             team,
            "Força Ofensiva":      idx.get("forca_ofensiva"),
            "Solidez Def.":        idx.get("solidez_defensiva"),
            "Qualidade xG":        idx.get("qualidade_finalizacao"),
            "Domínio":             idx.get("dominio_territorial"),
            "Eficiência":          idx.get("eficiencia_finalizacao"),
            "Volume Ataque":       idx.get("volume_ataque"),
            "Solidez xG Def.":     idx.get("solidez_xg"),
            "Índice Geral":        idx.get("indice_geral"),
        })

    df_comp = pd.DataFrame(rows).set_index("Seleção")
    st.dataframe(
        df_comp.style.format("{:.1f}", na_rep="—")
                     .background_gradient(cmap="RdYlGn", axis=0, vmin=0, vmax=10),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------
def main():
    st.title("⚽ Copa do Mundo 2026 — Modelo Preditivo xG")
    st.caption(
        "Modelo Dixon-Coles treinado com 2.152 partidas (2023–2026) | "
        "Brier Score validado: 0.1995 (referência aleatória: 0.333)"
    )

    # Carrega recursos
    load_model_cached()   # aquece o cache do modelo
    indices = load_indices()

    # Navegação por abas
    tab1, tab2, tab3 = st.tabs([
        "⚔️ Prever Confronto",
        "🏆 Fase de Grupos",
        "📊 Comparar Times",
    ])

    with tab1:
        section_matchup(indices)

    with tab2:
        section_groups()

    with tab3:
        section_comparison(indices)


if __name__ == "__main__":
    main()
