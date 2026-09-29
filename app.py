import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="CONFORMACIÓN DE CUADRILLAS",
    page_icon="👷",
    layout="wide"
)


# ============================================================
# CONFIGURACIÓN DE HOJAS
# ============================================================

HOJAS_ITEMS = [
    "ITEM_II",
    "ITEM_III",
    "ITEM_IV"
]

HOJA_HISTORICO = "Historico_de_ITEMS"

COLUMNAS = [
    "CENTRO DE COSTOS",
    "PLACA DE VEHICULO",
    "TIPO DE VEHICULO",
    "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO",
    "NOMBRES Y APELLIDOS TECNICO DE APOYO",
    "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA",
    "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO",
    "FECHA INICIO",
    "FECHA FIN",
    "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR",
    "UNIDAD DE NEGOCIO",
    "SERVICIO ELECTRICO",
    "CONTRATO",
    "ITEM",
    "SUPERVISOR DE LA CUADRILLA",
    "NUMERO CELULAR EMPRESA DEL SUPERVISOR",
    "NUMERO CELULAR PERSONAL DEL SUPERVISOR",
    "COORDINADOR GENERAL",
    "OBSERVACION"
]

COLUMNAS_HISTORICO = COLUMNAS + [
    "FECHA_MODIFICACION",
    "USUARIO_MODIFICACION",
    "HOJA_ORIGEN",
    "TIPO_MOVIMIENTO"
]


# ============================================================
# CONEXIÓN GOOGLE SHEETS
# ============================================================

@st.cache_resource
def conectar_google():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)

    spreadsheet_id = st.secrets["SPREADSHEET_ID"]

    spreadsheet = client.open_by_key(spreadsheet_id)

    return spreadsheet


try:

    spreadsheet = conectar_google()

except Exception as e:

    st.error("❌ No se pudo conectar con Google Sheets.")
    st.exception(e)
    st.stop()


# ============================================================
# FUNCIONES
# ============================================================

def obtener_hoja(nombre_hoja):

    try:
        return spreadsheet.worksheet(nombre_hoja)

    except gspread.WorksheetNotFound:

        st.error(
            f"❌ No existe la hoja '{nombre_hoja}' "
            "en el Google Sheets."
        )

        return None


# ------------------------------------------------------------
# OBTENER REGISTROS
# ------------------------------------------------------------

def obtener_registros(nombre_hoja):

    hoja = obtener_hoja(nombre_hoja)

    if hoja is None:
        return pd.DataFrame()

    valores = hoja.get_all_values()

    if not valores:
        return pd.DataFrame(columns=COLUMNAS)

    encabezados = valores[0]
    registros = valores[1:]

    # Si la hoja tiene los 19 campos
    if len(encabezados) >= len(COLUMNAS):

        registros_19 = []

        for fila in registros:

            fila = fila[:len(COLUMNAS)]

            while len(fila) < len(COLUMNAS):
                fila.append("")

            registros_19.append(fila)

        return pd.DataFrame(
            registros_19,
            columns=COLUMNAS
        )

    return pd.DataFrame(columns=COLUMNAS)


# ------------------------------------------------------------
# NORMALIZAR
# ------------------------------------------------------------

def normalizar(valor):

    if valor is None:
        return ""

    return str(valor).strip().upper()


# ------------------------------------------------------------
# VALIDAR REGISTRO
# ------------------------------------------------------------

def validar_registro(datos):

    obligatorios = [
        "CENTRO DE COSTOS",
        "PLACA DE VEHICULO",
        "TIPO DE VEHICULO",
        "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO",
        "UNIDAD DE NEGOCIO",
        "SERVICIO ELECTRICO",
        "CONTRATO",
        "ITEM",
        "SUPERVISOR DE LA CUADRILLA",
        "COORDINADOR GENERAL"
    ]

    faltantes = []

    for campo in obligatorios:

        if not str(datos.get(campo, "")).strip():

            faltantes.append(campo)

    return faltantes


# ------------------------------------------------------------
# AGREGAR AL HISTÓRICO
# ------------------------------------------------------------

def agregar_historico(
    datos,
    hoja_origen,
    tipo_movimiento
):

    hoja_historico = obtener_hoja(HOJA_HISTORICO)

    if hoja_historico is None:
        return False

    fecha = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    # Usuario de Streamlit.
    # Si posteriormente implementamos login,
    # aquí se colocará el usuario real.
    usuario = st.session_state.get(
        "usuario",
        "STREAMLIT"
    )

    fila = []

    # Los 19 campos originales
    for columna in COLUMNAS:

        fila.append(
            datos.get(columna, "")
        )

    # Campos del histórico
    fila.extend([
        fecha,
        usuario,
        hoja_origen,
        tipo_movimiento
    ])

    hoja_historico.append_row(
        fila,
        value_input_option="USER_ENTERED"
    )

    return True


# ------------------------------------------------------------
# CREAR REGISTRO
# ------------------------------------------------------------

def crear_registro(
    hoja_nombre,
    datos
):

    hoja = obtener_hoja(hoja_nombre)

    if hoja is None:
        return False

    # Agregar primero al ITEM
    fila = [
        datos.get(columna, "")
        for columna in COLUMNAS
    ]

    hoja.append_row(
        fila,
        value_input_option="USER_ENTERED"
    )

    # Después respaldar
    agregar_historico(
        datos,
        hoja_nombre,
        "NUEVO"
    )

    return True


# ------------------------------------------------------------
# ACTUALIZAR REGISTRO
# ------------------------------------------------------------

def actualizar_registro(
    hoja_nombre,
    numero_fila,
    datos
):

    hoja = obtener_hoja(hoja_nombre)

    if hoja is None:
        return False

    fila = [
        datos.get(columna, "")
        for columna in COLUMNAS
    ]

    hoja.update(
        f"A{numero_fila}:S{numero_fila}",
        [fila],
        value_input_option="USER_ENTERED"
    )

    # Guardar la nueva versión en histórico
    agregar_historico(
        datos,
        hoja_nombre,
        "MODIFICADO"
    )

    return True


# ------------------------------------------------------------
# ELIMINAR REGISTRO
# ------------------------------------------------------------

def eliminar_registro(
    hoja_nombre,
    numero_fila,
    datos
):

    hoja = obtener_hoja(hoja_nombre)

    if hoja is None:
        return False

    # Primero respaldar el registro eliminado
    agregar_historico(
        datos,
        hoja_nombre,
        "ELIMINADO"
    )

    # Después eliminarlo del ITEM
    hoja.delete_rows(numero_fila)

    return True


# ============================================================
# INTERFAZ
# ============================================================

st.title("👷 CONFORMACIÓN DE CUADRILLAS")

st.caption(
    "Registro y actualización de cuadrillas "
    "por ITEM"
)


# ============================================================
# SELECCIÓN DE ITEM
# ============================================================

item_seleccionado = st.selectbox(
    "📦 SELECCIONAR ITEM",
    HOJAS_ITEMS
)

hoja_actual = obtener_hoja(item_seleccionado)

if hoja_actual is None:
    st.stop()


# ============================================================
# PESTAÑAS
# ============================================================

tab_nuevo, tab_editar, tab_eliminar = st.tabs([
    "➕ NUEVA CUADRILLA",
    "✏️ EDITAR CUADRILLA",
    "🗑️ ELIMINAR CUADRILLA"
])

# ============================================================
# TAB NUEVO
# ============================================================

with tab_nuevo:

    st.subheader(
        f"➕ Nueva cuadrilla - {item_seleccionado}"
    )

    with st.form("form_nueva_cuadrilla"):

        # ====================================================
        # FILA 1
        # ====================================================

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            centro_costos = st.text_input(
                "CENTRO DE COSTOS"
            )

        with col2:

            placa = st.text_input(
                "PLACA DE VEHICULO"
            )

        with col3:

            tipo_vehiculo = st.text_input(
                "TIPO DE VEHICULO"
            )

        with col4:

            licencia = st.text_input(
                "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR"
            )

        with col5:

            tecnico_calificado = st.text_input(
                "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO"
            )


        # ====================================================
        # FILA 2
        # ====================================================

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            tecnico_apoyo = st.text_input(
                "NOMBRES Y APELLIDOS TECNICO DE APOYO"
            )

        with col2:

            celular_empresa_tecnico = st.text_input(
                "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA"
            )

        with col3:

            celular_personal_tecnico = st.text_input(
                "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO"
            )

        with col4:

            contrato = st.text_input(
                "CONTRATO"
            )

        with col5:

            item = st.text_input(
                "ITEM",
                value=item_seleccionado.replace("ITEM_", "")
            )


        # ====================================================
        # FILA 3
        # ====================================================

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            unidad_negocio = st.text_input(
                "UNIDAD DE NEGOCIO"
            )

        with col2:

            servicio_electrico = st.text_input(
                "SERVICIO ELECTRICO"
            )

        with col3:

            supervisor = st.text_input(
                "SUPERVISOR DE LA CUADRILLA"
            )

        with col4:

            celular_empresa_supervisor = st.text_input(
                "NUMERO CELULAR EMPRESA DEL SUPERVISOR"
            )

        with col5:

            celular_personal_supervisor = st.text_input(
                "NUMERO CELULAR PERSONAL DEL SUPERVISOR"
            )


        # ====================================================
        # FILA 4
        # ====================================================

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            coordinador = st.text_input(
                "COORDINADOR GENERAL"
            )

        with col2:

            fecha_inicio = st.date_input(
                "FECHA INICIO",
                value=None
            )

        with col3:

            fecha_fin = st.date_input(
                "FECHA FIN",
                value=None
            )

        with col4:

            observacion = st.text_area(
                "OBSERVACION"
            )

        with col5:

            # Se deja vacío para conservar
            # exactamente la distribución solicitada.
            st.empty()


        # ====================================================
        # BOTÓN
        # ====================================================

        guardar_nuevo = st.form_submit_button(
            "💾 GUARDAR CUADRILLA",
            use_container_width=True
        )


    # ========================================================
    # GUARDAR
    # ========================================================

    if guardar_nuevo:

        datos = {

            "CENTRO DE COSTOS":
                centro_costos,

            "PLACA DE VEHICULO":
                placa,

            "TIPO DE VEHICULO":
                tipo_vehiculo,

            "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO":
                tecnico_calificado,

            "NOMBRES Y APELLIDOS TECNICO DE APOYO":
                tecnico_apoyo,

            "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA":
                celular_empresa_tecnico,

            "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO":
                celular_personal_tecnico,

            "FECHA INICIO":
                fecha_inicio.strftime("%d/%m/%Y")
                if fecha_inicio else "",

            "FECHA FIN":
                fecha_fin.strftime("%d/%m/%Y")
                if fecha_fin else "",

            "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR":
                licencia,

            "UNIDAD DE NEGOCIO":
                unidad_negocio,

            "SERVICIO ELECTRICO":
                servicio_electrico,

            "CONTRATO":
                contrato,

            "ITEM":
                item,

            "SUPERVISOR DE LA CUADRILLA":
                supervisor,

            "NUMERO CELULAR EMPRESA DEL SUPERVISOR":
                celular_empresa_supervisor,

            "NUMERO CELULAR PERSONAL DEL SUPERVISOR":
                celular_personal_supervisor,

            "COORDINADOR GENERAL":
                coordinador,

            "OBSERVACION":
                observacion
        }

        faltantes = validar_registro(datos)

        if faltantes:

            st.warning(
                "⚠️ Completa los campos obligatorios:\n\n"
                + "\n".join(
                    f"- {campo}"
                    for campo in faltantes
                )
            )

        else:

            try:

                crear_registro(
                    item_seleccionado,
                    datos
                )

                st.success(
                    "✅ Cuadrilla registrada correctamente "
                    "y respaldada en Historico_de_ITEMS."
                )

            except Exception as e:

                st.error(
                    "❌ Ocurrió un error al guardar."
                )

                st.exception(e)
# ============================================================
# TAB EDITAR
# ============================================================

with tab_editar:

    st.subheader(
        f"✏️ Editar cuadrilla - {item_seleccionado}"
    )

    df = obtener_registros(
        item_seleccionado
    )

    if df.empty:

        st.info(
            "No existen cuadrillas registradas."
        )

    else:

        opciones = []

        for indice, fila in df.iterrows():

            descripcion = (
                f"{indice + 2} | "
                f"{fila['CENTRO DE COSTOS']} | "
                f"{fila['PLACA DE VEHICULO']} | "
                f"{fila['NOMBRES Y APELLIDOS DE TECNICO CALIFICADO']}"
            )

            opciones.append(descripcion)

        seleccion = st.selectbox(
            "Seleccionar cuadrilla",
            opciones
        )

        indice_df = opciones.index(
            seleccion
        )

        numero_fila = indice_df + 2

        registro = df.iloc[indice_df].to_dict()

        st.divider()

        # ====================================================
        # FORMULARIO EDITAR
        # MISMO ORDEN QUE NUEVA CUADRILLA
        # ====================================================

        with st.form("form_editar_cuadrilla"):

            # =================================================
            # FILA 1
            # =================================================

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                centro_costos_e = st.text_input(
                    "CENTRO DE COSTOS",
                    value=str(
                        registro["CENTRO DE COSTOS"]
                    )
                )

            with col2:

                placa_e = st.text_input(
                    "PLACA DE VEHICULO",
                    value=str(
                        registro["PLACA DE VEHICULO"]
                    )
                )

            with col3:

                tipo_vehiculo_e = st.text_input(
                    "TIPO DE VEHICULO",
                    value=str(
                        registro["TIPO DE VEHICULO"]
                    )
                )

            with col4:

                licencia_e = st.text_input(
                    "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR",
                    value=str(
                        registro[
                            "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR"
                        ]
                    )
                )

            with col5:

                tecnico_calificado_e = st.text_input(
                    "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO",
                    value=str(
                        registro[
                            "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO"
                        ]
                    )
                )


            # =================================================
            # FILA 2
            # =================================================

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                tecnico_apoyo_e = st.text_input(
                    "NOMBRES Y APELLIDOS TECNICO DE APOYO",
                    value=str(
                        registro[
                            "NOMBRES Y APELLIDOS TECNICO DE APOYO"
                        ]
                    )
                )

            with col2:

                celular_empresa_tecnico_e = st.text_input(
                    "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA",
                    value=str(
                        registro[
                            "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA"
                        ]
                    )
                )

            with col3:

                celular_personal_tecnico_e = st.text_input(
                    "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO",
                    value=str(
                        registro[
                            "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO"
                        ]
                    )
                )

            with col4:

                contrato_e = st.text_input(
                    "CONTRATO",
                    value=str(
                        registro["CONTRATO"]
                    )
                )

            with col5:

                item_e = st.text_input(
                    "ITEM",
                    value=str(
                        registro["ITEM"]
                    )
                )


            # =================================================
            # FILA 3
            # =================================================

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                unidad_negocio_e = st.text_input(
                    "UNIDAD DE NEGOCIO",
                    value=str(
                        registro["UNIDAD DE NEGOCIO"]
                    )
                )

            with col2:

                servicio_electrico_e = st.text_input(
                    "SERVICIO ELECTRICO",
                    value=str(
                        registro["SERVICIO ELECTRICO"]
                    )
                )

            with col3:

                supervisor_e = st.text_input(
                    "SUPERVISOR DE LA CUADRILLA",
                    value=str(
                        registro[
                            "SUPERVISOR DE LA CUADRILLA"
                        ]
                    )
                )

            with col4:

                celular_empresa_supervisor_e = st.text_input(
                    "NUMERO CELULAR EMPRESA DEL SUPERVISOR",
                    value=str(
                        registro[
                            "NUMERO CELULAR EMPRESA DEL SUPERVISOR"
                        ]
                    )
                )

            with col5:

                celular_personal_supervisor_e = st.text_input(
                    "NUMERO CELULAR PERSONAL DEL SUPERVISOR",
                    value=str(
                        registro[
                            "NUMERO CELULAR PERSONAL DEL SUPERVISOR"
                        ]
                    )
                )


            # =================================================
            # FILA 4
            # =================================================

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                coordinador_e = st.text_input(
                    "COORDINADOR GENERAL",
                    value=str(
                        registro["COORDINADOR GENERAL"]
                    )
                )

            with col2:

                fecha_inicio_e = st.text_input(
                    "FECHA INICIO",
                    value=str(
                        registro["FECHA INICIO"]
                    )
                )

            with col3:

                fecha_fin_e = st.text_input(
                    "FECHA FIN",
                    value=str(
                        registro["FECHA FIN"]
                    )
                )

            with col4:

                observacion_e = st.text_area(
                    "OBSERVACION",
                    value=str(
                        registro["OBSERVACION"]
                    )
                )

            with col5:

                st.empty()


            # =================================================
            # BOTÓN
            # =================================================

            guardar_edicion = st.form_submit_button(
                "💾 GUARDAR MODIFICACIÓN",
                use_container_width=True
            )


        # ====================================================
        # GUARDAR CAMBIOS
        # ====================================================

        if guardar_edicion:

            datos_editados = {

                "CENTRO DE COSTOS":
                    centro_costos_e,

                "PLACA DE VEHICULO":
                    placa_e,

                "TIPO DE VEHICULO":
                    tipo_vehiculo_e,

                "NOMBRES Y APELLIDOS DE TECNICO CALIFICADO":
                    tecnico_calificado_e,

                "NOMBRES Y APELLIDOS TECNICO DE APOYO":
                    tecnico_apoyo_e,

                "NUMERO CELULAR TECNICO CALIFICADO DE LA EMPRESA":
                    celular_empresa_tecnico_e,

                "NUMERO CELULAR PERSONAL DEL TECNICO CALIFICADO":
                    celular_personal_tecnico_e,

                "FECHA INICIO":
                    fecha_inicio_e,

                "FECHA FIN":
                    fecha_fin_e,

                "CATEGORIA DE LICENCIA DE CONDUCIR DEL CONDUCTOR":
                    licencia_e,

                "UNIDAD DE NEGOCIO":
                    unidad_negocio_e,

                "SERVICIO ELECTRICO":
                    servicio_electrico_e,

                "CONTRATO":
                    contrato_e,

                "ITEM":
                    item_e,

                "SUPERVISOR DE LA CUADRILLA":
                    supervisor_e,

                "NUMERO CELULAR EMPRESA DEL SUPERVISOR":
                    celular_empresa_supervisor_e,

                "NUMERO CELULAR PERSONAL DEL SUPERVISOR":
                    celular_personal_supervisor_e,

                "COORDINADOR GENERAL":
                    coordinador_e,

                "OBSERVACION":
                    observacion_e
            }

            faltantes = validar_registro(
                datos_editados
            )

            if faltantes:

                st.warning(
                    "⚠️ Completa los campos obligatorios:\n\n"
                    + "\n".join(
                        f"- {campo}"
                        for campo in faltantes
                    )
                )

            else:

                try:

                    actualizar_registro(
                        item_seleccionado,
                        numero_fila,
                        datos_editados
                    )

                    st.success(
                        "✅ Registro modificado correctamente "
                        "y respaldado en Historico_de_ITEMS."
                    )

                except Exception as e:

                    st.error(
                        "❌ Ocurrió un error al modificar."
                    )

                    st.exception(e)
# ============================================================
# TAB ELIMINAR
# ============================================================

with tab_eliminar:

    st.subheader(
        f"🗑️ Eliminar cuadrilla - {item_seleccionado}"
    )

    df = obtener_registros(
        item_seleccionado
    )

    if df.empty:

        st.info(
            "No existen cuadrillas registradas."
        )

    else:

        opciones = []

        for indice, fila in df.iterrows():

            descripcion = (
                f"{indice + 2} | "
                f"{fila['CENTRO DE COSTOS']} | "
                f"{fila['PLACA DE VEHICULO']} | "
                f"{fila['NOMBRES Y APELLIDOS DE TECNICO CALIFICADO']}"
            )

            opciones.append(descripcion)

        seleccion_eliminar = st.selectbox(
            "Seleccionar cuadrilla a eliminar",
            opciones,
            key="seleccion_eliminar"
        )

        indice_eliminar = opciones.index(
            seleccion_eliminar
        )

        numero_fila_eliminar = (
            indice_eliminar + 2
        )

        registro_eliminar = (
            df.iloc[indice_eliminar].to_dict()
        )

        st.warning(
            "⚠️ Esta acción eliminará la cuadrilla "
            "de la hoja del ITEM seleccionado."
        )

        st.info(
            "El registro NO será eliminado de "
            "Historico_de_ITEMS. Se conservará como "
            "ELIMINADO."
        )

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar esta cuadrilla"
        )

        if st.button(
            "🗑️ ELIMINAR CUADRILLA",
            type="primary",
            use_container_width=True
        ):

            if not confirmar:

                st.warning(
                    "⚠️ Debes confirmar la eliminación."
                )

            else:

                try:

                    eliminar_registro(
                        item_seleccionado,
                        numero_fila_eliminar,
                        registro_eliminar
                    )

                    st.success(
                        "✅ Cuadrilla eliminada de "
                        f"{item_seleccionado}.\n\n"
                        "El respaldo permanece en "
                        "Historico_de_ITEMS."
                    )

                except Exception as e:

                    st.error(
                        "❌ Ocurrió un error al eliminar."
                    )

                    st.exception(e)


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.divider()

st.caption(
    "Sistema de Conformación de Cuadrillas"
)
