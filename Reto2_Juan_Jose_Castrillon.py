# -*- coding: utf-8 -*-
"""
Created on 2025

@author: jj012
"""

#primero importo las librerias que necesito 
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

#configuracion inicial de la pag
st.set_page_config(page_title="Tablero Contable QuimQuinAgro", page_icon="📊", layout="wide")


#direccion del archivo
DB_PATH = r"C:\Users\jj012\Downloads\contabilidad (1).db"

#pruebo que la conexion a la base de datos sea exitosa
conn = sqlite3.connect(DB_PATH)
print("conexion exitosa")
conn.close()

#creo funciones auxiliares
#primero una para abrir la base de datos, ejecutar la consulta SQL y devolver los resultados
def ejecutar_sql(consulta: str, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(consulta, conn, params=params)

def descargar_csv(df: pd.DataFrame, nombre: str):
    if df is None or df.empty:
        return
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="Descargar",
        data=csv,
        file_name=f"{nombre}.csv",
        mime="text/csv"
    )
    
# identificar columnas de entrada/salida por año
def expr_entrada_salida(tabla):

    cols_df = ejecutar_sql(f"PRAGMA table_info({tabla});")
    columnas = cols_df['name'].tolist() if not cols_df.empty else []

    if "entrada" in columnas and "salida" in columnas:
        entrada_expr = "entrada"
        salida_expr = "salida"
    elif "abono" in columnas and "prestamo" in columnas:
        entrada_expr = "abono"
        salida_expr = "prestamo"
    else:
        raise Exception(f"No se encontraron columnas válidas en {tabla}.")
    
    return entrada_expr, salida_expr

#menu de navegacion sin texto libre
st.title("Tablero Contable QuimQuinAgro 📊")
consulta = st.sidebar.radio(
    "Selecciona una consulta:",
    [
        "Consulta 1 - Flujo mensual y saldo",
        "Consulta 2 - Días críticos de egreso",
        "Consulta 3 - Concentración de flujo por categorías", 
        "Consulta 4 - Caja mensual (básico)",
        "Consulta 5 - Top 10 egresos",
        "Consulta 6 - Ingresos por socio"
    ]
)

#permito al usuario elegir entre los diferentes años
AÑOS_DISPONIBLES = [2020, 2022, 2023, 2024]
año = st.sidebar.selectbox("Año de datos", AÑOS_DISPONIBLES, index=1)
tabla_caja = f"caja{año}"
tabla_cxc  = f"cxc{año}"


#verifico la existencia para el año seleccionado 
def existe_tabla(nombre_tabla: str) -> bool:
    df_chk = ejecutar_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
        (nombre_tabla,)
    )
    return not df_chk.empty

# consulta 1 
# resultado neto por mes (entrada - salida)
# saldo acumulado mes a mes
if consulta == "Consulta 1 - Flujo mensual y saldo":
    st.header("📈 Flujo neto mensual y saldo acumulado")

    if not existe_tabla(tabla_caja):
        st.warning(f"No existe la tabla {tabla_caja} para el año {año}.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q1_ini")
        with c2:
            fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q1_fin")

        if fecha_ini > fecha_fin:
            st.warning("La fecha inicial no puede ser mayor a la final.")
        else:
            #hago mensual el flujo neto y calculamos saldo acumulado
            sql_q1 = f"""
            WITH mensual AS (
                SELECT strftime('%Y-%m', fecha) AS mes,
                       SUM(entrada - salida)    AS flujo_neto
                FROM {tabla_caja}
                WHERE fecha BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', fecha)
            )
            SELECT mes,
                   flujo_neto,
                   SUM(flujo_neto) OVER (ORDER BY mes) AS saldo_acumulado
            FROM mensual
            ORDER BY mes;
            """
            df_q1 = ejecutar_sql(sql_q1, (fecha_ini, fecha_fin))

            if df_q1.empty:
                st.info("No se encontraron movimientos en ese rango.")
            else:
                st.subheader("Tabla de resultados")
                st.dataframe(df_q1, use_container_width=True)

                #grafico barras: flujo neto mensual
                fig_barras = px.bar(
                    df_q1, x="mes", y="flujo_neto",
                    title=f"Flujo neto mensual · {año}",
                    text_auto=True
                )
                st.plotly_chart(fig_barras, use_container_width=True)

                #grafico línea: saldo acumulado
                fig_linea = px.line(
                    df_q1, x="mes", y="saldo_acumulado",
                    markers=True,
                    title=f"Saldo acumulado · {año}"
                )
                st.plotly_chart(fig_linea, use_container_width=True)

                descargar_csv(df_q1, f"flujo_mensual_y_saldo_{año}")
                
                if año == 2020:
                    st.markdown(
                        "**Conclusión:** No se registran movimientos durante este año, por lo que no hay flujo de caja para analizar."
                        )

                elif año == 2022:
                    st.markdown(
                        "**Conclusión:** El flujo de caja fue inestable, hubo una recuperación en mayo, pero los egresos del último trimestre provocaron un cierre negativo."
                        )

                elif año == 2023:
                    st.markdown(
                        "**Conclusión:** El año inició con una salida fuerte en enero, tuvo una buena recuperación en marzo y cerró casi equilibrado."
                        )

                elif año == 2024:
                    st.markdown(
                        "**Conclusión:** Comenzó con pérdidas importantes en el primer semestre, pero gracias al aumento de ingresos en el último trimestre el año cerró con saldo positivo."
                        )

                else:
                    st.markdown(
                        "**Conclusión:** No hay datos disponibles o no se pudo generar un resumen para este año."
                        )
 

# consulta 2
# días con mayor salida (egreso) en el rango
# % que representan sobre el egreso total del período
elif consulta == "Consulta 2 - Días críticos de egreso":
    st.header("💸 Días críticos de egreso")

    if not existe_tabla(tabla_caja):
        st.warning(f"No existe la tabla {tabla_caja} para el año {año}.")
    else:
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q2_ini")
        with c2:
            fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q2_fin")
        with c3:
            top_n = st.slider("Top N días", min_value=5, max_value=20, value=10, step=1)

        if fecha_ini > fecha_fin:
            st.warning("La fecha inicial no puede ser mayor a la final.")
        else:
            sql_top = f"""
            SELECT fecha, SUM(salida) AS egreso_dia
            FROM {tabla_caja}
            WHERE fecha BETWEEN ? AND ?
            GROUP BY fecha
            ORDER BY egreso_dia DESC
            LIMIT ?;
            """
            df_top = ejecutar_sql(sql_top, (fecha_ini, fecha_fin, top_n))

        
            sql_total = f"""
            SELECT SUM(salida) AS egreso_total
            FROM {tabla_caja}
            WHERE fecha BETWEEN ? AND ?;
            """
            df_total = ejecutar_sql(sql_total, (fecha_ini, fecha_fin))
            egreso_total = float(df_total.iloc[0, 0]) if not df_total.empty and df_total.iloc[0, 0] is not None else 0.0

            if df_top.empty or egreso_total == 0:
                st.info("No hay egresos en el rango seleccionado.")
            else:
                df_top["porc_del_total"] = (df_top["egreso_dia"] / egreso_total * 100).round(2)

                st.subheader(f"Top {top_n} días con mayor egreso")
                st.dataframe(df_top, use_container_width=True)

                #grafico barras horizontales 
                fig = px.bar(
                    df_top.sort_values("egreso_dia", ascending=True),
                    x="egreso_dia", y="fecha", orientation="h",
                    title=f"Días críticos de egreso · {año}",
                    text="egreso_dia"
                )
                st.plotly_chart(fig, use_container_width=True)

                # Métrica del peso del Top N en el total
                st.metric(
                    label="Participación del Top N en el egreso total",
                    value=f"{df_top['egreso_dia'].sum() / egreso_total * 100:.2f}%"
                )

                descargar_csv(df_top, f"dias_criticos_egreso_{año}")
                
             
                if año == 2022:
                    st.markdown(
                        "**Conclusión:** Los egresos se concentraron en pocos días, especialmente en noviembre y septiembre, mostrando picos de gasto al cierre del año."
                        )

                elif año == 2023:
                    st.markdown(
                        "**Conclusión:** Un solo día concentró más del 60 % del egreso total, reflejando una salida extraordinaria de fondos."
                        )

                elif año == 2024:
                    st.markdown(
                        "**Conclusión:** La distribución de egresos fue más equilibrada, aunque julio y septiembre destacan con montos altos."
                        )

                else:
                    st.markdown(
                        "**Conclusión:** No hay datos disponibles o no se pudo generar un resumen para este año."
                        )


# consulta 3
# comparo ingresos vs egresos por 'detalle' y calculo balance neto
# ordena por mayor impacto absoluto y limita a las 15 categorías top
elif consulta == "Consulta 3 - Concentración de flujo por categorías":
    st.header("🏷️ Concentración de flujo por categorías (ingresos y egresos)")

    if not existe_tabla(tabla_caja):
        st.warning(f"No existe la tabla {tabla_caja} para el año {año}.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q3_ini")
        with c2:
            fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q3_fin")

        if fecha_ini > fecha_fin:
            st.warning("La fecha inicial no puede ser mayor a la final.")
        else:
            
            sql_q3 = f"""
            SELECT 
                detalle,
                SUM(entrada) AS total_ingresos,
                SUM(salida)  AS total_egresos,
                SUM(entrada - salida) AS balance_neto
            FROM {tabla_caja}
            WHERE fecha BETWEEN ? AND ?
            GROUP BY detalle
            HAVING total_ingresos IS NOT NULL OR total_egresos IS NOT NULL
            ORDER BY ABS(balance_neto) DESC
            LIMIT 15;
            """
            df_q3 = ejecutar_sql(sql_q3, (fecha_ini, fecha_fin))

            if df_q3.empty:
                st.info("No se encontraron movimientos en ese rango.")
            else:
                st.subheader("Tabla de resultados")
                st.dataframe(df_q3, use_container_width=True)

                # grafico sdarras agrupadas: ingresos vs egresos por categoría
                df_melt = df_q3.melt(
                    id_vars="detalle", 
                    value_vars=["total_ingresos", "total_egresos"],
                    var_name="tipo", value_name="valor"
                )
                fig1 = px.bar(
                    df_melt, x="detalle", y="valor", color="tipo",
                    barmode="group",
                    title=f"Ingresos vs Egresos por categoría · {año}",
                    text_auto=True
                )
                fig1.update_layout(xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig1, use_container_width=True)

                # Balance neto (positivo/negativo)
                df_q3["signo"] = df_q3["balance_neto"].apply(lambda x: "Positivo" if x >= 0 else "Negativo")
                fig2 = px.bar(
                    df_q3.sort_values("balance_neto"),
                    x="balance_neto", y="detalle", orientation="h",
                    color="signo",
                    title="Balance neto por categoría (positivo/negativo)",
                    text="balance_neto"
                )
                st.plotly_chart(fig2, use_container_width=True)

                descargar_csv(df_q3, f"flujo_por_categoria_{año}")
                
             
                if año == 2022:
                    st.markdown(
                        "**Conclusión:** Los mayores ingresos provinieron de intereses y ventas específicas, mientras que los egresos estuvieron repartidos, mostrando un flujo relativamente balanceado entre categorías."
                        )

                elif año == 2023:
                    st.markdown(
                        "**Conclusión:** Hubo alta concentración en dos categorías principales (ventas y pago de intereses), reflejando una fuerte dependencia de pocos rubros para los movimientos del año."
                        )

                elif año == 2024:
                    st.markdown(
                        "**Conclusión:** Los ingresos se concentraron en abonos de deuda e inversiones, mientras que las demás categorías tuvieron menor participación, mostrando una gestión más enfocada."
                        )

                else:
                    st.markdown(
                        "**Conclusión:** No hay datos disponibles o no se pudo generar un resumen para este año."
                        )


# consulta 4 
# Caja mensual (básico): Ingresos vs Egresos por mes
elif consulta == "Consulta 4 - Caja mensual (básico)":
    st.header("📊 Caja mensual: Ingresos vs Egresos")

    c1, c2 = st.columns(2)
    with c1:
        fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q4_ini")
    with c2:
        fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q4_fin")

    try:
        e_expr, s_expr = expr_entrada_salida(tabla_caja)
    except Exception as err:
        st.warning(str(err))
    else:
        sql_q4 = f"""
        SELECT 
            strftime('%Y-%m', fecha) AS mes,
            SUM({e_expr}) AS ingresos,
            SUM({s_expr}) AS egresos
        FROM {tabla_caja}
        WHERE fecha BETWEEN ? AND ?
        GROUP BY mes
        ORDER BY mes;
        """
        df_q4 = ejecutar_sql(sql_q4, (fecha_ini, fecha_fin))

        if df_q4.empty:
            st.info("No se encontraron movimientos en ese rango.")
        else:
            st.dataframe(df_q4, use_container_width=True)
            fig_q4 = px.bar(df_q4, x="mes", y=["ingresos", "egresos"],
                            barmode="group", title=f"Ingresos vs Egresos por mes · {año}")
            st.plotly_chart(fig_q4, use_container_width=True)
            descargar_csv(df_q4, f"caja_mensual_{año}")
            
            if año == 2022:
                st.markdown(
                    "**Conclusión:** Durante 2022 los flujos fueron variables, con meses de alto egreso en enero, abril y noviembre, y picos de ingreso en mayo y julio. El año mostró movimientos irregulares y varios meses con predominio de salidas sobre entradas."
                    )

            elif año == 2023:
                st.markdown(
                    "**Conclusión:** En 2023 los movimientos se concentraron en pocos meses, especialmente febrero y marzo. Aunque hubo ingresos elevados, también se registraron egresos importantes, reflejando operaciones puntuales de alto valor más que un flujo continuo."
                    )

            elif año == 2024:
                st.markdown(
                    "**Conclusión:** En 2024 se observa un flujo más equilibrado, con ingresos y egresos distribuidos de forma más constante. El comportamiento mensual muestra estabilidad y mejor control frente a los años anteriores."
                    )

            else:
                st.markdown(
                    "**Conclusión:** No hay datos disponibles o no se pudo generar un resumen para este año."
                    )

# consulta 5        
# Top 10 egresos por detalle (Caja)
elif consulta == "Consulta 5 - Top 10 egresos":
    st.header("💸 Top 10 egresos por detalle")

    c1, c2 = st.columns(2)
    with c1:
        fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q5_ini")
    with c2:
        fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q5_fin")

    try:
        _, s_expr = expr_entrada_salida(tabla_caja)
    except Exception as err:
        st.warning(str(err))
    else:
        sql_q5 = f"""
        SELECT detalle, SUM({s_expr}) AS total_egreso
        FROM {tabla_caja}
        WHERE fecha BETWEEN ? AND ?
        GROUP BY detalle
        ORDER BY total_egreso DESC
        LIMIT 10;
        """
        df_q5 = ejecutar_sql(sql_q5, (fecha_ini, fecha_fin))

        if df_q5.empty:
            st.info("No hay egresos en ese período.")
        else:
            st.dataframe(df_q5, use_container_width=True)
            fig_q5 = px.bar(df_q5, x="detalle", y="total_egreso", text_auto=True,
                            title=f"Top 10 conceptos de egreso · {año}")
            fig_q5.update_layout(xaxis={'categoryorder':'total descending'},
                                 xaxis_title="Detalle", yaxis_title="Egreso total")
            st.plotly_chart(fig_q5, use_container_width=True)
            descargar_csv(df_q5, f"top10_egresos_{año}")
            
            if año == 2022:
                st.markdown(
                    "**Conclusión:** En 2022 los egresos estuvieron dominados por pagos a proveedores y entidades como Agroquimbaya y Homecenter. El gasto se concentró en pocos conceptos, reflejando compras operativas y de mantenimiento como principales salidas de efectivo."
                    )

            elif año == 2023:
                st.markdown(
                    "**Conclusión:** En 2023 los egresos se concentraron en el pago de intereses y obligaciones financieras, destacando un único concepto que supera ampliamente al resto. Esto evidencia una fuerte dependencia de compromisos financieros durante el año."
                )
            
            elif año == 2024:
                st.markdown(
                    "**Conclusión:** En 2024 se observa una distribución más amplia, aunque los pagos de deuda e impuestos siguen siendo los mayores egresos. Predominan los abonos relacionados con obligaciones financieras y gastos administrativos, mostrando una gestión más ordenada."
                )
            
            else:
                st.markdown(
                    "**Conclusión:** No hay datos disponibles o no se pudo generar un resumen para este año."
                )
            

# consulta 6
# Ingresos por socio (CXC)
# 'Todos' -> barras por socio
# un socio -> serie temporal
elif consulta == "Consulta 6 - Ingresos por socio":
    st.header("🤝 Ingresos por socio (CXC)")

    c1, c2 = st.columns(2)
    with c1:
        fecha_ini = st.date_input("📅 Fecha inicial", pd.Timestamp(f"{año}-01-01"), key="q6_ini_v3")
    with c2:
        fecha_fin = st.date_input("📅 Fecha final", pd.Timestamp(f"{año}-12-31"), key="q6_fin_v3")

    tabla_cxc = f"cxc{año}"

   
    existe = ejecutar_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
        (tabla_cxc,)
    )
    if existe.empty:
        st.warning(f"No hay datos disponibles para {año} (no existe la tabla {tabla_cxc}).")
        st.stop()

 
    pragma = ejecutar_sql(f"PRAGMA table_info({tabla_cxc});")
    if pragma.empty:
        st.warning(f"No se pudieron leer las columnas de {tabla_cxc}.")
        st.stop()

    cols = set(pragma["name"].str.lower())

 
    cand_ingreso = [c for c in ["entrada", "ingreso", "abono"] if c in cols]
    col_ing = cand_ingreso[0] if cand_ingreso else None

    # socio
    cand_socio = [c for c in ["socio", "cliente"] if c in cols]
    col_soc = cand_socio[0] if cand_socio else None

    # fecha
    cand_fecha = [c for c in ["fecha", "date"] if c in cols]
    col_fec = cand_fecha[0] if cand_fecha else None

    if not col_ing or not col_soc or not col_fec:
        st.warning(
            f"La tabla {tabla_cxc} no tiene las columnas requeridas. "
            f"Se requieren: ingreso→({', '.join(['entrada','ingreso','abono'])}), "
            f"socio→(socio/cliente), fecha→(fecha/date)."
        )
        st.stop()

  
    socios_df = ejecutar_sql(
        f"SELECT DISTINCT {col_soc} AS socio FROM {tabla_cxc} "
        f"WHERE {col_fec} BETWEEN ? AND ? AND {col_soc} IS NOT NULL "
        f"ORDER BY socio;",
        (fecha_ini, fecha_fin)
    )
    socios = ["Todos"] + socios_df["socio"].dropna().astype(str).tolist()
    socio_sel = st.selectbox("Socio", socios, key="q6_socio_v3")

    if socio_sel == "Todos":
  
        sql_all = (
            f"SELECT {col_soc} AS socio, "
            f"SUM({col_ing}) AS ingresos "
            f"FROM {tabla_cxc} "
            f"WHERE {col_fec} BETWEEN ? AND ? "
            f"GROUP BY {col_soc} "
            f"ORDER BY ingresos DESC;"
        )
        df_q6 = ejecutar_sql(sql_all, (fecha_ini, fecha_fin))

        if df_q6.empty:
            st.info("No se encontraron ingresos en el rango seleccionado.")
            st.stop()

        st.dataframe(df_q6, use_container_width=True)
        fig_q6 = px.bar(df_q6, x="socio", y="ingresos", text_auto=True,
                        title=f"Ingresos totales por socio · {año}")
        fig_q6.update_layout(xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig_q6, use_container_width=True)
        descargar_csv(df_q6, f"ingresos_por_socio_{año}")

    else:
   
        sql_one = (
            f"SELECT {col_fec} AS fecha, SUM({col_ing}) AS ingresos "
            f"FROM {tabla_cxc} "
            f"WHERE {col_fec} BETWEEN ? AND ? AND {col_soc} = ? "
            f"GROUP BY {col_fec} "
            f"ORDER BY {col_fec};"
        )
        df_q6 = ejecutar_sql(sql_one, (fecha_ini, fecha_fin, socio_sel))

        if df_q6.empty:
            st.info("No se encontraron ingresos para ese socio en el rango.")
            st.stop()

        st.dataframe(df_q6, use_container_width=True)
        fig_q6 = px.line(df_q6, x="fecha", y="ingresos", markers=True,
                         title=f"Ingresos diarios de {socio_sel} · {año}")
        st.plotly_chart(fig_q6, use_container_width=True)
        descargar_csv(df_q6, f"ingresos_{socio_sel}_{año}")

    # --- Conclusión corta (opcional, edítala si quieres por año) ---
    if año == 2022:
        st.markdown("**Conclusión:** Sin datos suficientes para este año.")
    elif año == 2023:
        st.markdown("**Conclusión:** Sin datos suficientes para este año.")
    elif año == 2024:
        st.markdown("**Conclusión:** En 2024 los ingresos se concentraron en un solo socio principal, mostrando alta dependencia, aunque con resultados financieros sólidos.")
    else:
        st.markdown("**Conclusión:** Sin datos suficientes para este año.")

                    







