import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Registro Deportivo",
    layout="wide",
    page_icon="📘"
)

st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CONEXIÓN A SUPABASE
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------
def kpi_block(label, value_tuple, suffix=""):
    value, arrow, color = value_tuple
    display = f"{value}{suffix}" if value is not None else "—"

    # Detectar tema actual
    theme = st.get_option("theme.base")

    # Colores adaptativos
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


def fetch_table(table: str, limit: int = 500):
    """Obtiene datos de una tabla de Supabase como DataFrame."""
    try:
        res = supabase.table(table).select("*").order("timestamp", desc=True).limit(limit).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()


def get_last_week(df):
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    return df[df["timestamp"] >= one_week_ago]


def insert_row(table: str, data: dict):
    """Inserta una fila en Supabase con manejo de errores."""
    try:
        supabase.table(table).insert(data).execute()
        st.success("Datos guardados correctamente")
    except Exception as e:
        st.error("❌ Error al guardar datos")
        st.code(str(e))


def section_title(icon, title):
    st.markdown(f"## {icon} {title}")


def timestamp():
    return datetime.utcnow().isoformat()


def compute_weekly_kpis(df_metrics, df_bjj):
    kpis = {}

    # Semana actual y anterior
    m_this = get_week(df_metrics, 0)
    m_prev = get_week(df_metrics, 1)

    b_this = get_week(df_bjj, 0)
    b_prev = get_week(df_bjj, 1)

    # Helper seguro
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

    # Peso promedio
    peso_this = safe_mean(m_this, "peso")
    peso_prev = safe_mean(m_prev, "peso")
    kpis["peso"] = (peso_this, *compare(peso_this, peso_prev))

    # % rounds buenos
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

    # Cardio competitivo
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


def get_week(df, weeks_ago=0):
    """
    weeks_ago = 0 → esta semana
    weeks_ago = 1 → semana anterior
    """
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    today = datetime.utcnow()

    start = today - timedelta(days=7 * (weeks_ago + 1))
    end = today - timedelta(days=7 * weeks_ago)

    return df[(df["timestamp"] >= start) & (df["timestamp"] < end)]




# ---------------------------------------------------------
# TÍTULO PRINCIPAL
# ---------------------------------------------------------
st.title("📘 Registro Deportivo Personal")
st.write("Controla tus métricas, entrenos y sesiones de BJJ de forma sencilla y profesional.")

tab_metrics, tab_entrenos, tab_alimentacion = st.tabs(["📊 Métricas", "🏋️ Ejericios", "🥗 Alimentacion"])

with tab_metrics:
    st.markdown("---")
    st.subheader("📈 KPIs Semanales (con comparación)")

    df_metrics = fetch_table("metrics")
    df_bjj = fetch_table("bjj")

    kpis = compute_weekly_kpis(df_metrics, df_bjj)

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        kpi_block("Peso promedio", kpis["peso"], " kg")
    with col2:
        kpi_block("% Rounds buenos", kpis["rounds_buenos"], "%")
    with col3:
        kpi_block("Recuperación", kpis["recuperacion"])

    with col4:
        kpi_block("Cardio competitivo", kpis["cardio"])
    with col5:
        kpi_block("Claridad mental", kpis["claridad"])
    with col6:
        kpi_block("Consistencia", kpis["consistencia"], "/7")

    st.markdown("---")

    # ---------------------------------------------------------
    # MÉTRICAS DIARIAS
    # ---------------------------------------------------------
    section_title("📊", "Métricas diarias")

    with st.form("metrics_form"):
        col1, col2 = st.columns(2)
        with col1:
            peso = st.number_input("Peso (kg)", value=70.0, step=0.1)
            sueno = st.number_input("Horas de sueño", value=8.0, step=0.1)
            energia = st.slider("Energía", 1, 5, 3)
        with col2:
            calidad_sueno = st.slider("Calidad del sueño", 1, 5, 3)
            fatiga = st.slider("Fatiga", 1, 5, 3)
            pulso_reposo = st.number_input("Pulso en reposo (ppm)", value=70, step=1)

        if st.form_submit_button("Guardar métricas"):
            insert_row("metrics", {
                "timestamp": timestamp(),
                "peso": peso,
                "sueno": sueno,
                "calidad_sueno": calidad_sueno,
                "energia": energia,
                "fatiga": fatiga,
                "pulso_reposo": pulso_reposo
            })


    # ---------------------------------------------------------
    # ENTRENOS
    # ---------------------------------------------------------
    section_title("🏋️", "Registro de entrenos")

    with st.form("entrenos_form"):
        tipo_entreno = st.selectbox("Tipo de entreno", ["Cardio", "Fuerza", "Potencia"])
        duracion = st.number_input("Duración (min)", value=30, min_value=1)
        rpe = st.slider("RPE", 1, 10, 5)
        explosividad = st.slider("Explosividad", 1, 5, 3)
        cardio = st.slider("Cardio", 1, 5, 3)
        claridad_mental = st.slider("Claridad mental", 1, 5, 3)
        calidad_ultimo_round = st.slider("Último round", 1, 5, 3)
        notas = st.text_area("Notas")

        if st.form_submit_button("Guardar entreno"):
            insert_row("entrenos", {
                "timestamp": timestamp(),
                "tipo_entreno": tipo_entreno,
                "duracion": duracion,
                "rpe": rpe,
                "explosividad": explosividad,
                "cardio": cardio,
                "claridad_mental": claridad_mental,
                "calidad_ultimo_round": calidad_ultimo_round,
                "notas": notas
            })


    # ---------------------------------------------------------
    # BJJ
    # ---------------------------------------------------------
    section_title("🥋", "Registro BJJ")

    with st.form("bjj_form"):
        col1, col2 = st.columns(2)
        with col1:
            rounds_totales = st.number_input("Rounds totales", value=5, min_value=0)
            rounds_buenos = st.number_input("Rounds buenos", value=3, min_value=0)
            cardio_bjj = st.slider("Cardio BJJ", 1, 5, 3)
            claridad_mental_bjj = st.slider("Claridad mental", 1, 5, 3)
        with col2:
            juego_propio = st.slider("Juego propio", 1, 5, 3)
            intensidad_bjj = st.slider("Intensidad", 1, 5, 3)
            recuperacion_rounds = st.slider("Recuperación", 1, 5, 3)

        st.markdown("### Técnicas trabajadas")
        tecnicas = {
            "raspado": st.checkbox("Raspado"),
            "sumision": st.checkbox("Sumisión"),
            "escapes": st.checkbox("Escapes"),
            "derribo": st.checkbox("Derribo"),
            "pase_guardia": st.checkbox("Pase de guardia"),
            "cien_kilos": st.checkbox("Cien kilos"),
            "montada": st.checkbox("Montada"),
            "guardia": st.checkbox("Guardia")
        }

        notas_bjj = st.text_area("Notas adicionales")

        if st.form_submit_button("Guardar BJJ"):
            insert_row("bjj", {
                "timestamp": timestamp(),
                "rounds_totales": rounds_totales,
                "rounds_buenos": rounds_buenos,
                "cardio_bjj": cardio_bjj,
                "claridad_mental_bjj": claridad_mental_bjj,
                "juego_propio": juego_propio,
                "intensidad_bjj": intensidad_bjj,
                "recuperacion_rounds": recuperacion_rounds,
                **tecnicas,
                "notas_bjj": notas_bjj
            })
with tab_entrenos:
    section_title("🏋️‍♂️", "Rutina de ejercicios")
    st.markdown("Registra los ejercicios específicos realizados en tu sesión de fuerza o técnica.")

    if "ejercicios" not in st.session_state:
        st.session_state.ejercicios = []

    st.markdown("### 🏗️ Añadir ejercicio")

    with st.form("add_exercise_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Ejercicio", placeholder="Press banca, sentadilla, remo...")
            series = st.number_input("Series", min_value=1, value=3)
            repeticiones = st.number_input("Repeticiones", min_value=1, value=8)
        with col2:
            peso = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=0.5)
            rpe_ej = st.slider("RPE (opcional)", 1, 10, 7)

        if st.form_submit_button("Añadir ejercicio"):
            st.session_state.ejercicios.append({
                "nombre": nombre,
                "series": series,
                "repeticiones": repeticiones,
                "peso": peso,
                "rpe": rpe_ej
            })
            st.success(f"Ejercicio añadido: {nombre}")

    if st.session_state.ejercicios:
        st.markdown("### 📋 Ejercicios añadidos")
        for i, ej in enumerate(st.session_state.ejercicios):
            st.write(f"**{i+1}. {ej['nombre']}** — {ej['series']}×{ej['repeticiones']} — {ej['peso']} kg — RPE {ej['rpe']}")

        if st.button("Guardar rutina completa"):
            insert_row("rutina", {
                "timestamp": timestamp(),
                "ejercicios": st.session_state.ejercicios
            })
            st.session_state.ejercicios = []


with tab_alimentacion:
    section_title("🥗", "Registro de alimentación")
    st.markdown("Registra tus comidas del día para llevar un control nutricional más preciso.")

    with st.form("food_form"):
        col1, col2 = st.columns(2)

        with col1:
            tipo_comida = st.selectbox(
                "Tipo de comida",
                ["Desayuno", "Comida", "Cena", "Snack"],
                help="Selecciona el momento del día."
            )
            nombre_plato = st.text_input(
                "Nombre del plato",
                placeholder="Ej: Tortilla de 3 huevos, arroz con pollo..."
            )
            calorias = st.number_input(
                "Calorías (kcal)",
                min_value=0,
                value=0,
                help="Calorías aproximadas del plato."
            )

        with col2:
            proteinas = st.number_input("Proteínas (g)", min_value=0, value=0)
            carbohidratos = st.number_input("Carbohidratos (g)", min_value=0, value=0)
            grasas = st.number_input("Grasas (g)", min_value=0, value=0)

        notas_comida = st.text_area("Notas adicionales", placeholder="Ej: Me sentó pesado, lo comí después de entrenar...")

        if st.form_submit_button("Guardar comida"):
            insert_row("alimentacion", {
                "timestamp": timestamp(),
                "tipo_comida": tipo_comida,
                "nombre_plato": nombre_plato,
                "calorias": calorias,
                "proteinas": proteinas,
                "carbohidratos": carbohidratos,
                "grasas": grasas,
                "notas": notas_comida
            })
