import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from supabase import create_client, Client

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Registro Deportivo",
    layout="wide",
    page_icon="📘"
)

# ---------------------------------------------------------
# CONEXIÓN A SUPABASE
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_table(table: str, limit: int = 500):
    try:
        res = supabase.table(table).select("*").order("timestamp", desc=True).limit(limit).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error cargando {table}: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# CSS OPTIMIZACIÓN MÓVIL
# ---------------------------------------------------------
st.markdown("""
<style>

.block-container {
    padding-left: 0.8rem;
    padding-right: 0.8rem;
    max-width: 100%;
}

@media (max-width: 600px) {
    .block-container {
        padding-left: 0.4rem;
        padding-right: 0.4rem;
    }
}

.kpi-container {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 10px;
    padding-top: 5px;
}
.kpi-container > div {
    min-width: 180px;
    flex-shrink: 0;
}

button[kind="primary"] {
    width: 100%;
    border-radius: 8px;
    padding: 12px 0;
    font-size: 18px;
}

.top-menu {
    display: flex;
    justify-content: space-around;
    background-color: #11111111;
    padding: 10px 0;
    border-radius: 10px;
    margin-bottom: 15px;
}
.top-menu a {
    text-decoration: none;
    font-size: 18px;
    font-weight: 600;
    opacity: 0.8;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="top-menu">
    <a href="#kpis">📊 KPIs</a>
    <a href="#metricas">📝 Métricas</a>
    <a href="#bjj">🥋 BJJ</a>
    <a href="#entrenos">💪 Entrenos</a>
    <a href="#dashboard">📈 Dashboard</a>
</div>
""", unsafe_allow_html=True)

def get_week(df, weeks_ago=0):
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    today = datetime.utcnow()
    start = today - timedelta(days=7 * (weeks_ago + 1))
    end = today - timedelta(days=7 * weeks_ago)
    return df[(df["timestamp"] >= start) & (df["timestamp"] < end)]


def compute_weekly_kpis(df_metrics, df_bjj):
    kpis = {}

    m_this = get_week(df_metrics, 0)
    m_prev = get_week(df_metrics, 1)
    b_this = get_week(df_bjj, 0)
    b_prev = get_week(df_bjj, 1)

    def safe_mean(df, col):
        return round(df[col].mean(), 2) if not df.empty and col in df.columns else None

    def safe_sum(df, col):
        return df[col].sum() if not df.empty and col in df.columns else 0

    def compare(current, previous):
        if current is None or previous is None:
            return "→", "gray"
        if current > previous:
            return "↑", "green"
        if current < previous:
            return "↓", "red"
        return "→", "gray"

    # Peso
    peso_this = safe_mean(m_this, "peso")
    peso_prev = safe_mean(m_prev, "peso")
    kpis["peso"] = (peso_this, *compare(peso_this, peso_prev))

    # Rounds buenos
    total_this = safe_sum(b_this, "rounds_totales")
    buenos_this = safe_sum(b_this, "rounds_buenos")
    pct_this = round((buenos_this / total_this) * 100, 1) if total_this > 0 else None

    total_prev = safe_sum(b_prev, "rounds_totales")
    buenos_prev = safe_sum(b_prev, "rounds_buenos")
    pct_prev = round((buenos_prev / total_prev) * 100, 1) if total_prev > 0 else None

    kpis["rounds_buenos"] = (pct_this, *compare(pct_this, pct_prev))

    # Recuperación
    rec_this = safe_mean(b_this, "recuperacion_rounds")
    rec_prev = safe_mean(b_prev, "recuperacion_rounds")
    kpis["recuperacion"] = (rec_this, *compare(rec_this, rec_prev))

    # Cardio
    cardio_this = safe_mean(b_this, "cardio_bjj")
    cardio_prev = safe_mean(b_prev, "cardio_bjj")
    kpis["cardio"] = (cardio_this, *compare(cardio_this, cardio_prev))

    # Claridad mental
    clar_this = safe_mean(m_this, "energia")
    clar_prev = safe_mean(m_prev, "energia")
    kpis["claridad"] = (clar_this, *compare(clar_this, clar_prev))

    # Consistencia
    cons_this = m_this["timestamp"].dt.date.nunique() if not m_this.empty else None
    cons_prev = m_prev["timestamp"].dt.date.nunique() if not m_prev.empty else None
    kpis["consistencia"] = (cons_this, *compare(cons_this, cons_prev))

    return kpis

def kpi_block(label, value_tuple, suffix=""):
    value, arrow, color = value_tuple
    display = f"{value}{suffix}" if value is not None else "—"

    theme = st.get_option("theme.base")

    if theme == "dark":
        bg = "#1e1e1e"
        text_color = "#ffffff"
        border = "#333333"
    else:
        bg = "#f7f7f7"
        text_color = "#000000"
        border = "#dddddd"

    st.markdown(
        f"""
        <div style="
            padding:12px;
            border-radius:10px;
            background-color:{bg};
            color:{text_color};
            border:1px solid {border};
            text-align:center;
            min-width:180px;
        ">
            <div style="font-size:14px; opacity:0.8;">{label}</div>
            <div style="font-size:26px; font-weight:600;">
                {display}
                <span style="color:{color}; font-weight:700;">{arrow}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

df_metrics = fetch_table("metrics")
df_bjj = fetch_table("bjj")

st.markdown('<h2 id="kpis">📊 KPIs Semanales</h2>', unsafe_allow_html=True)
st.markdown('<div class="kpi-container">', unsafe_allow_html=True)

kpis = compute_weekly_kpis(df_metrics, df_bjj)

kpi_block("Peso promedio", kpis["peso"], " kg")
kpi_block("% Rounds buenos", kpis["rounds_buenos"], "%")
kpi_block("Recuperación", kpis["recuperacion"])
kpi_block("Cardio competitivo", kpis["cardio"])
kpi_block("Claridad mental", kpis["claridad"])
kpi_block("Consistencia", kpis["consistencia"], "/7")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<h2 id="metricas">📝 Registrar métricas</h2>', unsafe_allow_html=True)

with st.form("metricas_form"):
    peso = st.number_input("Peso (kg)", step=0.1)
    energia = st.slider("Energía / claridad mental", 1, 10)
    sueno = st.slider("Horas de sueño", 0, 12)
    enviado = st.form_submit_button("Guardar métricas")

    if enviado:
        supabase.table("metrics").insert({
            "peso": peso,
            "energia": energia,
            "sueno": sueno,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        st.success("Métricas guardadas")

st.markdown('<h2 id="bjj">🥋 Registrar BJJ</h2>', unsafe_allow_html=True)

with st.form("bjj_form"):
    rounds_totales = st.number_input("Rounds totales", 0, 20)
    rounds_buenos = st.number_input("Rounds buenos", 0, 20)
    cardio = st.slider("Cardio BJJ", 1, 10)
    recuperacion = st.slider("Recuperación entre rounds", 1, 10)
    enviado = st.form_submit_button("Guardar BJJ")

    if enviado:
        supabase.table("bjj").insert({
            "rounds_totales": rounds_totales,
            "rounds_buenos": rounds_buenos,
            "cardio_bjj": cardio,
            "recuperacion_rounds": recuperacion,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        st.success("Entrenamiento BJJ guardado")


st.markdown('<h2 id="entrenos">💪 Registrar entreno</h2>', unsafe_allow_html=True)

with st.form("entrenos_form"):
    tipo = st.selectbox("Tipo de entreno", ["Fuerza", "Cardio", "Movilidad"])
    duracion = st.number_input("Duración (min)", 0, 300)
    rpe = st.slider("RPE", 1, 10)
    enviado = st.form_submit_button("Guardar entreno")

    if enviado:
        supabase.table("entrenos").insert({
            "tipo": tipo,
            "duracion": duracion,
            "rpe": rpe,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        st.success("Entreno guardado")


st.markdown('<h2 id="dashboard">📈 Dashboard</h2>', unsafe_allow_html=True)

if not df_metrics.empty:
    df_metrics["timestamp"] = pd.to_datetime(df_metrics["timestamp"])

    st.subheader("📉 Evolución del peso")
    chart_peso = alt.Chart(df_metrics).mark_line(point=True).encode(
        x="timestamp:T",
        y="peso:Q"
    )
    st.altair_chart(chart_peso, use_container_width=True)

    st.subheader("🧠 Claridad mental")
    chart_energia = alt.Chart(df_metrics).mark_line(point=True).encode(
        x="timestamp:T",
        y="energia:Q"
    )
    st.altair_chart(chart_energia, use_container_width=True)

if not df_bjj.empty:
    df_bjj["timestamp"] = pd.to_datetime(df_bjj["timestamp"])
    df_bjj["pct_buenos"] = (df_bjj["rounds_buenos"] / df_bjj["rounds_totales"]) * 100

    st.subheader("🔥 Cardio BJJ")
    chart_cardio = alt.Chart(df_bjj).mark_line(point=True).encode(
        x="timestamp:T",
        y="cardio_bjj:Q"
    )
    st.altair_chart(chart_cardio, use_container_width=True)

    st.subheader("🥋 % Rounds buenos")
    chart_rounds = alt.Chart(df_bjj).mark_line(point=True).encode(
        x="timestamp:T",
        y="pct_buenos:Q"
    )
    st.altair_chart(chart_rounds, use_container_width=True)

