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


def kpi_block(label, value, suffix=""):
    # Detectar tema actual
    theme = st.get_option("theme.base")

    if theme == "dark":
        bg = "#1e1e1e"
        text_color = "#ffffff"
        border = "#333333"
    else:
        bg = "#ffffff"
        text_color = "#000000"
        border = "#dddddd"

    st.markdown(
        f"""
        <div style="
            padding:18px;
            border-radius:12px;
            background-color:{bg};
            color:{text_color};
            border:1px solid {border};
            text-align:center;
            box-shadow:0 2px 4px rgba(0,0,0,0.05);
        ">
            <div style="font-size:14px; opacity:0.7;">{label}</div>
            <div style="font-size:30px; font-weight:700; margin-top:4px;">
                {value}{suffix}
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


def fetch_comidas_bedca():
    try:
        res = supabase.table("comidas_bedca").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al cargar comidas: {e}")
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


@st.cache_data(show_spinner="Cargando base de datos BEDCA…")
def load_bedca():
    try:
        df = pd.read_csv("bedca_alimentos_limpio.csv", sep=",")
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Validación mínima
        if "alimento" not in df.columns:
            st.error("❌ El archivo BEDCA no contiene la columna 'alimento'.")
            return pd.DataFrame()
        
        # Reemplazar NaN por 0 en nutrientes
        df = df.fillna(0)

        return df

    except FileNotFoundError:
        st.error("❌ No se encontró el archivo 'bedca_alimentos_limpio.csv'.")
        return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error cargando BEDCA: {e}")
        return pd.DataFrame()


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
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)

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

    peso = kpis["peso"][0]
    rounds_buenos = kpis["rounds_buenos"][0]
    recuperacion = kpis["recuperacion"][0]
    cardio = kpis["cardio"][0]
    claridad = kpis["claridad"][0]
    consistencia = kpis["consistencia"][0]

    with col1:
        kpi_block("Peso promedio", f"{peso}", " kg")
    with col2:
        kpi_block("% Rounds buenos", f"{rounds_buenos}", "%")
    with col3:
        kpi_block("Recuperación", f"{recuperacion}")

    with col4:
        kpi_block("Cardio competitivo", f"{cardio}")
    with col5:
        kpi_block("Claridad mental", f"{claridad}")
    with col6:
        kpi_block("Consistencia", f"{consistencia}", "/7")

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
    section_title("🏋️‍♂️", "Rutinas de entrenamiento")

    modo = st.radio(
        "¿Qué quieres hacer?",
        ["Crear rutina", "Ejecutar rutina"],
        horizontal=True
    )

    # ---------------------------------------------------------
    # MODO 1: CREAR RUTINA
    # ---------------------------------------------------------
    if modo == "Crear rutina":
        st.markdown("### 🏗️ Crear nueva rutina")

        if "ejercicios" not in st.session_state:
            st.session_state.ejercicios = []

        rutina_nombre = st.text_input("Nombre de la rutina", placeholder="Ej: Full Body A, Torso, Pierna...")

        st.markdown("#### Añadir ejercicio")

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
                if rutina_nombre.strip() == "":
                    st.warning("Pon un nombre a la rutina antes de guardarla")
                else:
                    insert_row("rutina", {
                        "timestamp": timestamp(),
                        "nombre": rutina_nombre,
                        "ejercicios": st.session_state.ejercicios
                    })
                    st.success(f"Rutina '{rutina_nombre}' guardada correctamente")
                    st.session_state.ejercicios = []

    # ---------------------------------------------------------
    # MODO 2: EJECUTAR RUTINA
    # ---------------------------------------------------------
    if modo == "Ejecutar rutina":
        st.markdown("### 🏋️‍♂️ Ejecutar una rutina guardada")

        df_rutinas = fetch_table("rutina")

        if df_rutinas.empty:
            st.info("Todavía no hay rutinas guardadas.")
        else:
            nombres_rutinas = df_rutinas["nombre"].tolist()
            rutina_sel = st.selectbox("Selecciona una rutina", nombres_rutinas)

            rutina = df_rutinas[df_rutinas["nombre"] == rutina_sel].iloc[0]
            ejercicios = rutina["ejercicios"]

            st.markdown(f"### 📘 Rutina: **{rutina_sel}**")

            if "progreso_rutina" not in st.session_state:
                st.session_state.progreso_rutina = {}

            for i, ej in enumerate(ejercicios):
                st.markdown(f"#### {ej['nombre']}")

                check = st.checkbox("Completado", key=f"check_{rutina_sel}_{i}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    peso_real = st.number_input("Peso usado (kg)", min_value=0.0, value=float(ej['peso']), key=f"peso_real_{i}")
                with col2:
                    reps_real = st.number_input("Reps realizadas", min_value=0, value=int(ej['repeticiones']), key=f"reps_real_{i}")
                with col3:
                    rpe_real = st.slider("RPE", 1, 10, ej['rpe'], key=f"rpe_real_{i}")

                st.session_state.progreso_rutina[i] = {
                    "nombre": ej["nombre"],
                    "completado": check,
                    "peso": peso_real,
                    "reps": reps_real,
                    "rpe": rpe_real
                }

            if st.button("Guardar entrenamiento realizado"):
                insert_row("entrenos_realizados", {
                    "timestamp": timestamp(),
                    "rutina": rutina_sel,
                    "ejercicios": st.session_state.progreso_rutina
                })
                st.success("Entrenamiento guardado correctamente")
                st.session_state.progreso_rutina = {}

with tab_alimentacion:
    st.markdown("""
<style>

/* Card bonita */
.food-card {
    background: #f8f9fa;
    padding: 14px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
    margin-bottom: 10px;
}

/* Título de sección */
.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 10px;
}

/* Inputs más compactos */
input, select, textarea {
    border-radius: 6px !important;
}

/* Tablas más limpias */
.dataframe tbody tr th {
    font-size: 13px;
}
.dataframe tbody td {
    font-size: 13px;
}

/* Métricas más elegantes */
.metric-card {
    padding: 12px;
    border-radius: 10px;
    background: #ffffff;
    border: 1px solid #e0e0e0;
    text-align: center;
}

.metric-value {
    font-size: 24px;
    font-weight: 700;
}

.metric-label {
    font-size: 13px;
    opacity: 0.7;
}

</style>
""", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🥗 Constructor de Comidas (BEDCA)</div>', unsafe_allow_html=True)

    df_bedca = load_bedca()

    nutrientes = [
        c for c in df_bedca.columns
        if c not in ["food_id", "alimento"] and df_bedca[c].dtype != "object"
    ]

    st.header("🥕 Selecciona alimentos")

    selected_foods = st.multiselect(
        "Alimentos",
        sorted(df_bedca["alimento"].unique())
    )

    if selected_foods:

        st.markdown('<div class="section-title">📋 Cantidades por alimento</div>', unsafe_allow_html=True)

        meal_data = []

        for food in selected_foods:
            with st.container():
                st.markdown(food, unsafe_allow_html=True)

                grams = st.number_input(
                    f"Cantidad en gramos",
                    min_value=0.0,
                    value=100.0,
                    step=10.0,
                    key=f"grams_{food}"
                )

                row = df_bedca[df_bedca["alimento"] == food].iloc[0]

                food_entry = {"alimento": food, "gramos": grams}

                for n in nutrientes:
                    food_entry[n] = row[n] * grams / 100

                meal_data.append(food_entry)

                st.markdown("</div>", unsafe_allow_html=True)

        meal_df = pd.DataFrame(meal_data)

        macro_cols = ["energia_kcal", "proteina_total", "carbohidratos", "grasa_total"]
        other_cols = [c for c in meal_df.columns if c not in macro_cols + ["alimento", "gramos"]]

        meal_df = meal_df[["alimento", "gramos"] + macro_cols + other_cols]

        # ---------------------------
        # NUTRIENTES POR ALIMENTO (vista compacta)
        # ---------------------------
        st.markdown('<div class="section-title">🥗 Nutrientes por alimento</div>', unsafe_allow_html=True)

        for _, row in meal_df.iterrows():
            with st.expander(f"{row['alimento']} — {row['energia_kcal']:.0f} kcal"):

                # MACROS DEL ALIMENTO
                c1, c2, c3, c4 = st.columns(4)
                with c1: kpi_block("Kcal", f"{row['energia_kcal']:.0f}")
                with c2: kpi_block("Proteína", f"{row['proteina_total']:.1f}", " g")
                with c3: kpi_block("Carbs", f"{row['carbohidratos']:.1f}", " g")
                with c4: kpi_block("Grasas", f"{row['grasa_total']:.1f}", " g")

                # MICRONUTRIENTES DEL ALIMENTO
                micro = row.drop(labels=["alimento", "gramos"] + macro_cols).to_frame().reset_index()
                micro.columns = ["Nutriente", "Valor"]
                micro["Valor"] = micro["Valor"].round(3)

                with st.expander("Micronutrientes"):
                    st.dataframe(micro, use_container_width=True, hide_index=True)

        # ---------------------------
        # TOTALES DE LA COMIDA
        # ---------------------------
        st.markdown('<div class="section-title">📊 Totales de la comida</div>', unsafe_allow_html=True)

        totals = meal_df[nutrientes].sum().reset_index()
        totals.columns = ["Nutriente", "Total"]
        totals["Total"] = totals["Total"].round(2)

        # Extraer macros
        kcal = totals.loc[totals["Nutriente"] == "energia_kcal", "Total"].values[0]
        prot = totals.loc[totals["Nutriente"] == "proteina_total", "Total"].values[0]
        carb = totals.loc[totals["Nutriente"] == "carbohidratos", "Total"].values[0]
        gras = totals.loc[totals["Nutriente"] == "grasa_total", "Total"].values[0]

        # MACROS DESTACADOS
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_block("Kcal", f"{kcal:.0f}")
        with c2: kpi_block("Proteína", f"{prot:.1f}", " g")
        with c3: kpi_block("Carbohidratos", f"{carb:.1f}", " g")
        with c4: kpi_block("Grasas", f"{gras:.1f}", " g")

        # MICRONUTRIENTES DE LA COMIDA
        st.markdown("### 🧪 Micronutrientes totales")

        with st.expander("Ver micronutrientes"):
            micro_tot = totals[
                ~totals["Nutriente"].isin([
                    "energia_kcal", "proteina_total", "carbohidratos", "grasa_total"
                ])
            ].copy()

            st.dataframe(micro_tot, use_container_width=True, hide_index=True)
        # ---------------------------
        # GUARDAR EN SUPABASE
        # ---------------------------
        st.markdown('<div class="section-title">💾 Guardar comida</div>', unsafe_allow_html=True)

        meal_name = st.text_input("Nombre de la comida", placeholder="Ej: Desayuno 9 abril")
        notas = st.text_area("Notas (opcional)")

        if st.button("Guardar comida en Supabase"):
            if meal_name.strip() == "":
                st.warning("Pon un nombre a la comida antes de guardarla")
            else:
                insert_row("comidas_bedca", {
                    "timestamp": timestamp(),
                    "nombre": meal_name,
                    "alimentos": meal_df.fillna(0).to_dict(orient="records"),
                    "totales": totals.fillna(0).to_dict(orient="records"),
                    "notas": notas
                })
    else:
        st.info("Selecciona al menos un alimento desde la barra lateral.")



    st.markdown('<div class="section-title">📚 Historial de comidas</div>', unsafe_allow_html=True)

    df_comidas = fetch_comidas_bedca()

    if df_comidas.empty:
        st.info("Todavía no has registrado ninguna comida.")
    else:
        # Ordenar por fecha descendente
        df_comidas = df_comidas.sort_values("timestamp", ascending=False)

        for _, comida in df_comidas.iterrows():

            # Extraer totales principales
            tot = pd.DataFrame(comida["totales"])
            kcal = tot.loc[tot["Nutriente"] == "energia_kcal", "Total"].values[0]
            prot = tot.loc[tot["Nutriente"] == "proteina_total", "Total"].values[0]
            carb = tot.loc[tot["Nutriente"] == "carbohidratos", "Total"].values[0]
            gras = tot.loc[tot["Nutriente"] == "grasa_total", "Total"].values[0]

            with st.expander(f"🍽️ {comida['nombre']} — {kcal:.0f} kcal"):

                st.caption(f"📅 {comida['timestamp']}")

                # ---------------------------
                # MACROS DESTACADOS (KPI BLOCK)
                # ---------------------------
                st.markdown("### 📦 Macronutrientes")

                c1, c2, c3, c4 = st.columns(4)

                with c1: 
                    kpi_block("Kcal", f"{kcal:.0f}")
                with c2: 
                    kpi_block("Proteína", f"{prot:.1f}", " g")
                with c3: 
                    kpi_block("Carbohidratos", f"{carb:.1f}", " g")
                with c4: 
                    kpi_block("Grasas", f"{gras:.1f}", " g")

                # ---------------------------
                # ALIMENTOS
                # ---------------------------
                st.markdown("### 🥗 Alimentos")
                alimentos_df = pd.DataFrame(comida["alimentos"])
                st.dataframe(alimentos_df, use_container_width=True, hide_index=True)

                # ---------------------------
                # MICRONUTRIENTES EN EXPANDER
                # ---------------------------
                st.markdown("### 🧪 Micronutrientes")

                with st.expander("Ver micronutrientes"):
                    micro_df = tot[
                        ~tot["Nutriente"].isin([
                            "energia_kcal", "proteina_total", "carbohidratos", "grasa_total"
                        ])
                    ].copy()

                    micro_df["Total"] = micro_df["Total"].round(3)

                    st.dataframe(
                        micro_df,
                        use_container_width=True,
                        hide_index=True
                    )


    st.markdown('<div class="section-title">📅 Totales del día</div>', unsafe_allow_html=True)

    df_comidas["fecha"] = pd.to_datetime(df_comidas["timestamp"]).dt.date

    fecha_sel = st.date_input("Selecciona una fecha")

    df_dia = df_comidas[df_comidas["fecha"] == fecha_sel]

    if df_dia.empty:
        st.info("No hay comidas registradas en esa fecha.")
    else:
        # Sumar totales
        lista_totales = [pd.DataFrame(row["totales"]) for _, row in df_dia.iterrows()]
        df_sum = pd.concat(lista_totales).groupby("Nutriente")["Total"].sum().reset_index()

        # Extraer macros
        kcal = df_sum.loc[df_sum["Nutriente"] == "energia_kcal", "Total"].values[0]
        prot = df_sum.loc[df_sum["Nutriente"] == "proteina_total", "Total"].values[0]
        carb = df_sum.loc[df_sum["Nutriente"] == "carbohidratos", "Total"].values[0]
        gras = df_sum.loc[df_sum["Nutriente"] == "grasa_total", "Total"].values[0]

        st.markdown("### 📦 Resumen del día")

        # Extraer macros
        kcal = df_sum.loc[df_sum["Nutriente"] == "energia_kcal", "Total"].values[0]
        prot = df_sum.loc[df_sum["Nutriente"] == "proteina_total", "Total"].values[0]
        carb = df_sum.loc[df_sum["Nutriente"] == "carbohidratos", "Total"].values[0]
        gras = df_sum.loc[df_sum["Nutriente"] == "grasa_total", "Total"].values[0]

        # Tarjetas grandes para macros
        c1, c2, c3, c4 = st.columns(4)

        with c1: kpi_block("Kcal", f"{kcal:.0f}")
        with c2: kpi_block("Proteína", f"{prot:.1f}", " g")
        with c3: kpi_block("Carbohidratos", f"{carb:.1f}", " g")
        with c4: kpi_block("Grasas", f"{gras:.1f}", " g")

        # Micronutrientes en expander
        st.markdown("### 🧪 Micronutrientes")

        with st.expander("Ver micronutrientes"):
            micro_df = df_sum[
                ~df_sum["Nutriente"].isin([
                    "energia_kcal", "proteina_total", "carbohidratos", "grasa_total"
                ])
            ].copy()

            micro_df["Total"] = micro_df["Total"].round(3)

            st.dataframe(
                micro_df,
                use_container_width=True,
                hide_index=True
            )
