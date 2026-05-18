import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Registro Deportivo",
    layout="centered",
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


# ---------------------------------------------------------
# TÍTULO PRINCIPAL
# ---------------------------------------------------------
st.title("📘 Registro Deportivo Personal")
st.write("Controla tus métricas, entrenos y sesiones de BJJ de forma sencilla y profesional.")


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


# ---------------------------------------------------------
# ÚLTIMOS REGISTROS
# ---------------------------------------------------------
st.markdown("---")
section_title("📈", "Últimos registros")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Ver métricas"):
        df = pd.DataFrame(supabase.table("metrics").select("*").order("timestamp", desc=True).limit(10).execute().data)
        st.dataframe(df)

with col2:
    if st.button("Ver entrenos"):
        df = pd.DataFrame(supabase.table("entrenos").select("*").order("timestamp", desc=True).limit(10).execute().data)
        st.dataframe(df)

with col3:
    if st.button("Ver BJJ"):
        df = pd.DataFrame(supabase.table("bjj").select("*").order("timestamp", desc=True).limit(10).execute().data)
        st.dataframe(df)