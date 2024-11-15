import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import plotly.express as px

# =====================================
# Configuración de la Página
# =====================================
st.set_page_config(
    page_title="Dashboard de Clientes y Unidades",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# =====================================
# Estilo CSS Personalizado
# =====================================
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
        background-color: #0e1117;
        color: #fafafa;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        margin: 5px;
        color: #fafafa;
    }
    .metric-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #fafafa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 24px;
        background-color: #262730;
        border-radius: 5px;
        color: #fafafa;
    }
    div[data-testid="stDataFrame"] > div {
        background-color: #262730;
        padding: 10px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Clientes y Unidades")

# =====================================
# Funciones Auxiliares
# =====================================

def cargar_datos(db_file, costos_file):
    """Carga y valida los datos desde la base de datos y el archivo de costos."""
    datos = {}
    
    # Cargar base de datos
    if db_file:
        temp_path = Path("temp_db.db")
        try:
            with open(temp_path, "wb") as f:
                f.write(db_file.read())  # Corregido: usar read() en lugar de getvalue()
            conn = sqlite3.connect(temp_path)
            datos['conn'] = conn
            datos['temp_path'] = temp_path
            st.success("✅ Base de datos cargada correctamente")
        except Exception as e:
            st.error(f"❌ Error al cargar la base de datos: {str(e)}")
            datos['conn'] = None
            datos['temp_path'] = None
    else:
        datos['conn'] = None
        datos['temp_path'] = None
    
    # Cargar archivo de costos
    if costos_file:
        try:
            # Cargar el archivo Excel
            df_costos = pd.read_excel(costos_file)
            
            # Limpiar nombres de columnas
            df_costos.columns = [str(col).strip() for col in df_costos.columns]
            
            columnas_requeridas = ['Cuenta', 'Usuario', 'Nombre Comercial', 'Costo', 'Tipo', 'Observaciones']
            if not all(col in df_costos.columns for col in columnas_requeridas):
                st.error("❌ El archivo de costos no tiene el formato esperado. Debe contener las columnas: " + ", ".join(columnas_requeridas))
                datos['df_costos'] = None
            else:
                # Asegurar que la columna Costo sea numérica
                try:
                    # Convertir la columna Costo a string primero para manejar cualquier tipo de dato
                    df_costos['Costo'] = df_costos['Costo'].astype(str)
                    
                    # Limpiar la columna de caracteres especiales
                    df_costos['Costo'] = df_costos['Costo'].str.replace('$', '', regex=False)
                    df_costos['Costo'] = df_costos['Costo'].str.replace(',', '', regex=False)
                    df_costos['Costo'] = df_costos['Costo'].str.strip()
                    
                    # Convertir a numérico
                    df_costos['Costo'] = pd.to_numeric(df_costos['Costo'], errors='coerce')
                    
                    # Limpiar otros campos
                    df_costos['Cuenta'] = df_costos['Cuenta'].astype(str).str.strip()
                    df_costos['Tipo'] = df_costos['Tipo'].fillna('Mensual')
                    
                    # Eliminar filas donde el costo es nulo o negativo
                    df_costos = df_costos[df_costos['Costo'].notna() & (df_costos['Costo'] >= 0)]
                    
                    datos['df_costos'] = df_costos
                    st.success("✅ Archivo de costos cargado correctamente")
                    
                    # Mostrar información de las columnas para depuración
                    st.write("Información de las columnas cargadas:")
                    for col in df_costos.columns:
                        st.write(f"- {col}: {df_costos[col].dtype}")
                        if col == 'Costo':
                            st.write(f"  Rango de valores: {df_costos[col].min()} a {df_costos[col].max()}")
                    
                except Exception as e:
                    st.error(f"❌ Error al procesar la columna de costos: {str(e)}")
                    st.write("Muestra de los datos problemáticos:")
                    st.write(df_costos[['Cuenta', 'Costo']].head())
                    datos['df_costos'] = None
        except Exception as e:
            st.error(f"❌ Error al cargar el archivo de costos: {str(e)}")
            datos['df_costos'] = None
    else:
        datos['df_costos'] = None
    
    return datos

def obtener_tablas(conn):
    """Obtiene la lista de tablas de la base de datos."""
    tablas_query = "SELECT name FROM sqlite_master WHERE type='table'"
    tablas = pd.read_sql_query(tablas_query, conn)['name'].tolist()
    return tablas

def cargar_datos_tabla(conn, tabla):
    """Carga los datos de una tabla específica y filtra filas vacías."""
    columnas_query = f"PRAGMA table_info({tabla})"
    columnas = pd.read_sql_query(columnas_query, conn)
    columnas_disponibles = columnas['name'].tolist()
    
    columnas_requeridas = ['Cliente_Cuenta', 'Nombre', 'Fecha_de_Desactivacion', 'Origen']
    if all(col in columnas_disponibles for col in columnas_requeridas):
        try:
            df = pd.read_sql_query(f"""
                SELECT Cliente_Cuenta, Nombre, Fecha_de_Desactivacion, Origen
                FROM {tabla}
                WHERE Cliente_Cuenta IS NOT NULL 
                AND Cliente_Cuenta != ''
                AND Nombre IS NOT NULL 
                AND Nombre != ''
            """, conn)
            
            # Asegurarse de que las columnas son de tipo string antes de aplicar str.strip()
            df['Cliente_Cuenta'] = df['Cliente_Cuenta'].astype(str)
            df['Nombre'] = df['Nombre'].astype(str)
            
            # Eliminar filas con valores vacíos o nulos en columnas críticas
            df = df.dropna(subset=['Cliente_Cuenta', 'Nombre'])
            
            # Limpiar espacios en blanco
            df['Cliente_Cuenta'] = df['Cliente_Cuenta'].str.strip()
            df['Nombre'] = df['Nombre'].str.strip()
            
            # Verificar si hay datos después de la limpieza
            if df.empty:
                st.error("❌ No hay datos válidos después de filtrar filas vacías.")
                return None
                
            return df
        except Exception as e:
            st.error(f"❌ Error al cargar los datos de la tabla: {str(e)}")
            return None
    else:
        st.error("❌ La tabla seleccionada no contiene las columnas necesarias para el análisis: " + ", ".join(columnas_requeridas))
        return None

def validar_registros(df):
    """Valida los registros basados en Cliente_Cuenta."""
    df['Es_Valido'] = df['Cliente_Cuenta'].notna() & (df['Cliente_Cuenta'] != '') & (df['Cliente_Cuenta'] != '0')
    df_validos = df[df['Es_Valido']].copy()
    df_validos['Estado'] = df_validos['Fecha_de_Desactivacion'].isna().map({True: 'Activada', False: 'Desactivada'})
    return df_validos

def integrar_costos(df_validos, df_costos):
    """Integra la información de costos al DataFrame de registros válidos."""
    try:
        # Verificar que df_costos no sea None
        if df_costos is None:
            st.warning("No hay datos de costos disponibles para integrar.")
            return df_validos
            
        # Verificar que las columnas necesarias existan
        columnas_requeridas = ['Cuenta', 'Costo', 'Tipo']
        if not all(col in df_costos.columns for col in columnas_requeridas):
            st.error(f"❌ Error: Columnas faltantes en df_costos. Columnas requeridas: {columnas_requeridas}")
            st.write("Columnas disponibles en df_costos:")
            st.write(list(df_costos.columns))
            return df_validos
            
        # Realizar la fusión con manejo de errores
        df_validos = df_validos.merge(
            df_costos[columnas_requeridas],
            left_on='Cliente_Cuenta',
            right_on='Cuenta',
            how='left'
        )
        
        # Validar y limpiar datos de costo
        df_validos['Costo'] = pd.to_numeric(df_validos['Costo'], errors='coerce')
        df_validos.loc[df_validos['Costo'] < 0, 'Costo'] = None
        
        # Calcular costo mensual con manejo de casos inválidos
        def normalizar_costo_mensual(row):
            if pd.isna(row['Tipo']) or pd.isna(row['Costo']):
                return row['Costo']
            tipo = row['Tipo'].lower() if isinstance(row['Tipo'], str) else ''
            if tipo == 'semestral':
                return row['Costo'] / 6
            elif tipo == 'anual':
                return row['Costo'] / 12
            elif tipo == 'mensual':
                return row['Costo']
            else:
                return None  # Tipo de facturación inválido
        
        df_validos['Costo_Mensual'] = df_validos.apply(normalizar_costo_mensual, axis=1)
        df_validos['Ciclo_Facturacion'] = df_validos['Tipo'].fillna('No especificado')
        
        # Calcular métricas adicionales
        df_validos['Perdida_Por_Desactivacion'] = df_validos.apply(
            lambda x: x['Costo_Mensual'] if x['Estado'] == 'Desactivada' else 0, 
            axis=1
        )
        
        return df_validos
        
    except Exception as e:
        st.error(f"❌ Error al procesar los datos: '{str(e)}'")
        st.write("Verificando datos de costos:")
        st.write("Columnas en df_costos:")
        st.write(list(df_costos.columns))
        st.write("Muestra de los datos de costos:")
        st.write(df_costos.head())
        return df_validos

def mostrar_metricas_validacion(df, df_validos):
    """Muestra las métricas de validación de registros."""
    total_registros = len(df)
    registros_validos = len(df_validos)
    registros_invalidos = total_registros - registros_validos
    
    st.markdown("### 🔍 Validación de Registros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Total Registros",
            f"{total_registros:,}",
            help="Número total de registros en la base de datos"
        )
    
    with col2:
        porcentaje_validos = (registros_validos / total_registros * 100) if total_registros > 0 else 0
        st.metric(
            "✅ Registros Válidos",
            f"{registros_validos:,}",
            f"{porcentaje_validos:.1f}%",
            help="Registros con Cliente_Cuenta válido"
        )
    
    with col3:
        porcentaje_invalidos = (registros_invalidos / total_registros * 100) if total_registros > 0 else 0
        st.metric(
            "❌ Registros Inválidos",
            f"{registros_invalidos:,}",
            f"{porcentaje_invalidos:.1f}%",
            help="Registros sin Cliente_Cuenta válido"
        )
    
    if registros_invalidos > 0:
        with st.expander("📋 Ver Registros Inválidos"):
            st.dataframe(
                df[~df['Es_Valido']],
                column_config={
                    "Cliente_Cuenta": "ID Cliente",
                    "Nombre": "Nombre",
                    "Origen": "Plataforma",
                    "Fecha_de_Desactivacion": "Fecha Desactivación"
                },
                hide_index=True
            )
    
    st.markdown("---")

def resumen_unidades_por_plataforma(df_validos, unique_suffix=""):
    """Crea y muestra un resumen de unidades por plataforma."""
    st.markdown("#### 📊 Resumen de Unidades por Plataforma")
    
    plataformas = sorted(df_validos['Origen'].unique())
    resumen_plataformas = []

    for plataforma in plataformas:
        df_plat = df_validos[df_validos['Origen'] == plataforma]
        activas = df_plat[df_plat['Estado'] == 'Activada'].shape[0]
        desactivadas = df_plat[df_plat['Estado'] == 'Desactivada'].shape[0]
        total = len(df_plat)
        
        resumen_plataformas.append({
            'Plataforma': plataforma,
            'Unidades Activas': activas,
            'Unidades Desactivadas': desactivadas,
            'Total Unidades': total,
            '% Activas': (activas / total * 100) if total > 0 else 0,
            'Clientes Únicos': df_plat['Cliente_Cuenta'].nunique()
        })
    
    df_resumen = pd.DataFrame(resumen_plataformas)
    
    # Agregar fila de totales
    totales = {
        'Plataforma': 'TOTAL',
        'Unidades Activas': df_resumen['Unidades Activas'].sum(),
        'Unidades Desactivadas': df_resumen['Unidades Desactivadas'].sum(),
        'Total Unidades': df_resumen['Total Unidades'].sum(),
        '% Activas': (df_resumen['Unidades Activas'].sum() / df_resumen['Total Unidades'].sum() * 100) if df_resumen['Total Unidades'].sum() > 0 else 0,
        'Clientes Únicos': df_validos['Cliente_Cuenta'].nunique()
    }
    df_resumen = pd.concat([df_resumen, pd.DataFrame([totales])], ignore_index=True)
    
    # Mostrar tabla de resumen
    st.dataframe(
        df_resumen,
        column_config={
            "Plataforma": st.column_config.TextColumn(
                "Plataforma",
                width="medium",
                help="Plataforma de origen"
            ),
            "Unidades Activas": st.column_config.NumberColumn(
                "Unidades Activas",
                format="%d",
                help="Número de unidades activas"
            ),
            "Unidades Desactivadas": st.column_config.NumberColumn(
                "Unidades Desactivadas",
                format="%d",
                help="Número de unidades desactivadas"
            ),
            "Total Unidades": st.column_config.NumberColumn(
                "Total Unidades",
                format="%d",
                help="Total de unidades en la plataforma"
            ),
            "% Activas": st.column_config.ProgressColumn(
                "% Activas",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                help="Porcentaje de unidades activas"
            ),
            "Clientes Únicos": st.column_config.NumberColumn(
                "Clientes Únicos",
                format="%d",
                help="Número de clientes únicos"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras apiladas
        fig_barras = px.bar(
            df_resumen[df_resumen['Plataforma'] != 'TOTAL'],
            x='Plataforma',
            y=['Unidades Activas', 'Unidades Desactivadas'],
            title='Distribución de Unidades por Plataforma',
            labels={'value': 'Número de Unidades', 'variable': 'Estado'},
            color_discrete_map={
                'Unidades Activas': '#00CC96',
                'Unidades Desactivadas': '#EF553B'
            }
        )
        fig_barras.update_layout(barmode='stack')
        # Clave única utilizando el sufijo
        st.plotly_chart(fig_barras, use_container_width=True, key=f"barras_apiladas_resumen_{unique_suffix}")
    
    with col2:
        # Gráfico de pastel
        fig_pie = px.pie(
            df_resumen[df_resumen['Plataforma'] != 'TOTAL'],
            values='Total Unidades',
            names='Plataforma',
            title='Proporción de Unidades por Plataforma'
        )
        st.plotly_chart(fig_pie, use_container_width=True, key=f"pastel_distribucion_resumen_{unique_suffix}")
    
    st.markdown("---")
    return plataformas

def detalles_por_plataforma(df_validos, plataformas, df_costos):
    """Muestra detalles detallados por plataforma."""
    st.markdown("##### 📑 Detalles por Plataforma (Solo Registros Válidos)")
    
    for plataforma in plataformas:
        with st.expander(f"📱 {plataforma} - Análisis Detallado"):
            df_plat = df_validos[df_validos['Origen'] == plataforma]
            
            # Columnas para métricas y gráficos
            col1, col2, col3 = st.columns([1, 1, 1])
            
            # Métricas Generales
            with col1:
                total_plat = len(df_plat)
                activas_plat = df_plat[df_plat['Estado'] == 'Activada'].shape[0]
                desactivadas_plat = df_plat[df_plat['Estado'] == 'Desactivada'].shape[0]
                clientes_unicos = df_plat['Cliente_Cuenta'].nunique()
                promedio_unidades_cliente = (total_plat / clientes_unicos) if clientes_unicos > 0 else 0
                
                st.markdown("**📊 Métricas Generales:**")
                st.markdown(f"""
                - 📦 Total Unidades: **{total_plat:,}**
                - ✅ Unidades Activas: **{activas_plat:,}** ({(activas_plat/total_plat*100):.1f}%)
                - ❌ Unidades Desactivadas: **{desactivadas_plat:,}** ({(desactivadas_plat/total_plat*100):.1f}%)
                - 👥 Clientes Únicos: **{clientes_unicos:,}**
                - 📈 Promedio Unidades/Cliente: **{promedio_unidades_cliente:.2f}**
                """)
                
                # Métricas de Facturación
                if 'Costo_Mensual' in df_plat.columns:
                    df_activas = df_plat[df_plat['Estado'] == 'Activada']
                    facturacion_mensual = df_activas['Costo_Mensual'].sum()
                    promedio_costo = df_activas['Costo_Mensual'].mean()
                    
                    st.markdown("**💰 Métricas de Facturación:**")
                    st.markdown(f"""
                    - 💵 Facturación Mensual Total: **${facturacion_mensual:,.2f}**
                    - 📊 Costo Promedio por Unidad: **${promedio_costo:,.2f}**
                    """)
                    
                    # Ciclos de Facturación
                    ciclos = df_plat['Ciclo_Facturacion'].value_counts()
                    st.markdown("**🔄 Ciclos de Facturación:**")
                    for ciclo, cantidad in ciclos.items():
                        st.markdown(f"- {ciclo}: **{cantidad:,}** unidades")
            
            # Gráfico de Distribución de Estados
            with col2:
                fig_estados = px.pie(
                    df_plat,
                    names='Estado',
                    title=f'Estados en {plataforma}',
                    color='Estado',
                    color_discrete_map={'Activada': '#00CC96', 'Desactivada': '#EF553B'},
                    hole=0.4
                )
                fig_estados.update_layout(showlegend=True)
                st.plotly_chart(fig_estados, use_container_width=True, key=f"estados_pie_{plataforma}")
            
            # Tendencia de Desactivaciones
            with col3:
                if 'Fecha_de_Desactivacion' in df_plat.columns:
                    df_temporal = df_plat[df_plat['Fecha_de_Desactivacion'].notna()].copy()
                    if not df_temporal.empty:
                        df_temporal['Fecha_de_Desactivacion'] = pd.to_datetime(df_temporal['Fecha_de_Desactivacion'], errors='coerce')
                        df_temporal['Mes'] = df_temporal['Fecha_de_Desactivacion'].dt.to_period('M')
                        desactivaciones = df_temporal.groupby('Mes').size().reset_index(name='Cantidad')
                        desactivaciones['Mes'] = desactivaciones['Mes'].astype(str)
                        
                        fig_trend = px.line(
                            desactivaciones,
                            x='Mes',
                            y='Cantidad',
                            title=f'Desactivaciones por Mes en {plataforma}',
                            markers=True
                        )
                        fig_trend.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig_trend, use_container_width=True, key=f"tendencia_line_{plataforma}")
            
            # Análisis de Clientes
            st.markdown("**👥 Análisis de Clientes**")
            col1, col2 = st.columns([1, 1])
            
            # Top 10 Clientes por Total de Unidades
            with col1:
                top_clientes = df_plat.groupby('Cliente_Cuenta').agg({
                    'Nombre': 'count',
                    'Estado': lambda x: (x == 'Activada').sum()
                }).reset_index()
                
                top_clientes.columns = ['Cliente', 'Total Unidades', 'Unidades Activas']
                top_clientes['% Activas'] = (top_clientes['Unidades Activas'] / top_clientes['Total Unidades'] * 100).round(1)
                top_clientes = top_clientes.sort_values('Total Unidades', ascending=False).head(10)
                
                st.markdown("**📈 Top 10 Clientes por Total de Unidades:**")
                st.dataframe(
                    top_clientes,
                    column_config={
                        "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                        "Total Unidades": st.column_config.NumberColumn("Total Unidades", format="%d"),
                        "Unidades Activas": st.column_config.NumberColumn("Unidades Activas", format="%d"),
                        "% Activas": st.column_config.ProgressColumn("% Activas", format="%.1f%%", min_value=0, max_value=100)
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            # Top 10 Clientes por % de Unidades Activas
            with col2:
                top_activos = df_plat.groupby('Cliente_Cuenta').agg({
                    'Nombre': 'count',
                    'Estado': lambda x: (x == 'Activada').sum()
                }).reset_index()
                
                top_activos.columns = ['Cliente', 'Total Unidades', 'Unidades Activas']
                top_activos['% Activas'] = (top_activos['Unidades Activas'] / top_activos['Total Unidades'] * 100).round(1)
                top_activos = top_activos[top_activos['Total Unidades'] >= 5]
                top_activos = top_activos.sort_values(['% Activas', 'Total Unidades'], ascending=[False, False]).head(10)
                
                st.markdown("**🏆 Top 10 Clientes por % de Unidades Activas (mín. 5 unidades):**")
                st.dataframe(
                    top_activos,
                    column_config={
                        "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                        "Total Unidades": st.column_config.NumberColumn("Total Unidades", format="%d"),
                        "Unidades Activas": st.column_config.NumberColumn("Unidades Activas", format="%d"),
                        "% Activas": st.column_config.ProgressColumn("% Activas", format="%.1f%%", min_value=0, max_value=100)
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            # Distribución de Clientes por Tamaño
            st.markdown("**📊 Distribución de Clientes por Tamaño**")
            
            def categorizar_cliente(total):
                if total >= 100:
                    return 'Grande (100+ unidades)'
                elif total >= 50:
                    return 'Mediano (50-99 unidades)'
                elif total >= 10:
                    return 'Pequeño (10-49 unidades)'
                else:
                    return 'Micro (1-9 unidades)'
            
            distribucion_clientes = df_plat.groupby('Cliente_Cuenta').size().reset_index(name='Total')
            distribucion_clientes['Categoría'] = distribucion_clientes['Total'].apply(categorizar_cliente)
            resumen_categorias = distribucion_clientes['Categoría'].value_counts().reset_index()
            resumen_categorias.columns = ['Categoría', 'Cantidad de Clientes']
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_dist = px.bar(
                    resumen_categorias,
                    x='Categoría',
                    y='Cantidad de Clientes',
                    title='Distribución de Clientes por Tamaño',
                    color='Categoría',
                    text='Cantidad de Clientes'
                )
                fig_dist.update_traces(textposition='outside')
                st.plotly_chart(fig_dist, use_container_width=True, key=f"distribucion_clientes_{plataforma}")
            
            with col2:
                st.dataframe(
                    resumen_categorias,
                    column_config={
                        "Categoría": st.column_config.TextColumn("Categoría", width="medium"),
                        "Cantidad de Clientes": st.column_config.NumberColumn("Cantidad de Clientes", format="%d")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            st.markdown("---")

def analisis_de_costos(df_validos):
    """Crea y muestra el análisis de costos por cliente."""
    st.markdown("#### 📊 Análisis de Costos por Cliente")
    
    # Verificar si los datos de costos están integrados
    if 'Costo_Mensual' not in df_validos.columns or 'Costo' not in df_validos.columns:
        st.warning("⚠️ No hay datos de costos disponibles para realizar el análisis.")
        return
    
    # Agrupar por Cliente
    df_costos_cliente = df_validos.groupby('Cliente_Cuenta').agg(
        Unidades_Activadas=('Estado', lambda x: (x == 'Activada').sum()),
        Unidades_Desactivadas=('Estado', lambda x: (x == 'Desactivada').sum()),
        Total_Unidades=('Estado', 'count'),
        Costo_Unitario=('Costo_Mensual', 'mean')
    ).reset_index()
    
    # Calcular Costo Total Impactado por Unidades Activas
    df_costos_cliente['Costo_Total_Impactado'] = df_costos_cliente['Unidades_Activadas'] * df_costos_cliente['Costo_Unitario']
    
    # Redondear los costos a dos decimales
    df_costos_cliente['Costo_Unitario'] = df_costos_cliente['Costo_Unitario'].round(2)
    df_costos_cliente['Costo_Total_Impactado'] = df_costos_cliente['Costo_Total_Impactado'].round(2)
    
    # Ordenar por Costo Total Impactado Descendente
    df_costos_cliente = df_costos_cliente.sort_values('Costo_Total_Impactado', ascending=False)
    
    # Mostrar la tabla
    st.dataframe(
        df_costos_cliente,
        column_config={
            "Cliente_Cuenta": st.column_config.TextColumn("Cliente", width="medium"),
            "Unidades_Activadas": st.column_config.NumberColumn("Unidades Activas", format="%d"),
            "Unidades_Desactivadas": st.column_config.NumberColumn("Unidades Desactivadas", format="%d"),
            "Total_Unidades": st.column_config.NumberColumn("Total Unidades", format="%d"),
            "Costo_Unitario": st.column_config.NumberColumn("Costo Unitario", format="$%.2f"),
            "Costo_Total_Impactado": st.column_config.NumberColumn("Costo Total Impactado", format="$%.2f")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Opcional: Agregar gráficos para una mejor visualización
    st.markdown("##### 📈 Distribución del Costo Total Impactado")
    fig = px.bar(
        df_costos_cliente.head(20),  # Mostrar los 20 principales para mayor claridad
        x='Cliente_Cuenta',
        y='Costo_Total_Impactado',
        title='Top 20 Clientes por Costo Total Impactado',
        labels={'Costo_Total_Impactado': 'Costo Total Impactado (USD)', 'Cliente_Cuenta': 'Cliente'},
        color='Costo_Total_Impactado',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True, key="costo_total_impactado_bar_chart")

def crear_tabs(df_validos, df_costos):
    """Crea las diferentes pestañas del dashboard."""
    # Obtener plataformas únicas para dividir los datos
    plataformas = sorted(df_validos['Origen'].unique())
    
    # Dividir el dataframe validado en dataframes separados por plataforma
    df_plataformas = {plataforma: df_validos[df_validos['Origen'] == plataforma].copy() for plataforma in plataformas}
    
    # Crear una lista de etiquetas para las pestañas
    etiquetas_tabs = [
        "📈 Gráficos", 
        "🔍 Búsqueda de Clientes", 
        "💰 Análisis por Plataforma", 
        "📋 Datos Completos",
        "💵 Análisis de Costos",
        "📂 Datos por Plataforma"  # Nueva pestaña añadida
    ]
    
    # Crear las pestañas y asignarlas a una lista
    tabs = st.tabs(etiquetas_tabs)
    
    with tabs[0]:
        st.markdown("### 📈 Gráficos")
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras apiladas para top N clientes
            top_n = st.slider("Seleccionar número de clientes", 5, 20, 10, key="top_n_slider")
            top_clients = df_validos.groupby(['Cliente_Cuenta', 'Estado']).agg({
                'Nombre': 'count'
            }).reset_index()
            top_clients = top_clients.pivot_table(
                index='Cliente_Cuenta',
                columns='Estado',
                values='Nombre',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            if 'Activada' not in top_clients.columns:
                top_clients['Activada'] = 0
            if 'Desactivada' not in top_clients.columns:
                top_clients['Desactivada'] = 0
            
            top_clients['Total'] = top_clients['Activada'] + top_clients['Desactivada']
            top_clients = top_clients.sort_values(['Total'], ascending=[False]).head(top_n)
            
            fig1 = px.bar(
                top_clients,
                x='Cliente_Cuenta',
                y=['Activada', 'Desactivada'],
                title=f'Top {top_n} Clientes por Total de Unidades',
                labels={'value': 'Cantidad de Unidades', 'Cliente_Cuenta': 'Cliente'},
                color_discrete_sequence=['#00CC96', '#EF553B']
            )
            fig1.update_layout(
                xaxis_tickangle=-45,
                legend_title_text='Estado',
                barmode='stack'
            )
            # Clave única basada en top_n
            st.plotly_chart(fig1, use_container_width=True, key=f"top_clientes_barras_{top_n}")
        
        with col2:
            # Gráfico de pastel para distribución general de estados
            fig2 = px.pie(
                values=[
                    df_validos[df_validos['Estado'] == 'Activada'].shape[0],
                    df_validos[df_validos['Estado'] == 'Desactivada'].shape[0]
                ],
                names=['Activadas', 'Desactivadas'],
                title='Distribución de Estados',
                color_discrete_sequence=['#00CC96', '#EF553B'],
                hole=0.4
            )
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True, key="distribucion_estados_pie_tab1")
        
        # Análisis Temporal de Desactivaciones
        if 'Fecha_de_Desactivacion' in df_validos.columns:
            st.markdown("#### 📅 Análisis Temporal")
            df_temporal = df_validos[df_validos['Fecha_de_Desactivacion'].notna()].copy()
            df_temporal['Fecha_de_Desactivacion'] = pd.to_datetime(df_temporal['Fecha_de_Desactivacion'], errors='coerce')
            df_temporal['Mes'] = df_temporal['Fecha_de_Desactivacion'].dt.to_period('M')
            desactivaciones_por_mes = df_temporal.groupby('Mes').size().reset_index(name='Cantidad')
            desactivaciones_por_mes['Mes'] = desactivaciones_por_mes['Mes'].astype(str)
            
            fig3 = px.line(
                desactivaciones_por_mes,
                x='Mes',
                y='Cantidad',
                title='Tendencia de Desactivaciones por Mes',
                labels={'Cantidad': 'Cantidad de Desactivaciones', 'Mes': 'Mes'},
                markers=True
            )
            fig3.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig3, use_container_width=True, key="tendencia_desactivaciones_line_tab1")
    
    with tabs[1]:
        st.markdown("### 🔍 Búsqueda y Análisis de Cliente")
        
        # Selector de Cliente
        col1, col2 = st.columns([1, 2])
        with col1:
            clientes_unicos = sorted(df_validos['Cliente_Cuenta'].unique())
            buscar_cliente = st.selectbox(
                "Seleccionar Cliente:",
                options=clientes_unicos,
                key="busqueda_cliente_selectbox"
            )
        
        if buscar_cliente:
            clientes_filtrados = df_validos[df_validos['Cliente_Cuenta'] == buscar_cliente].copy()
            
            if not clientes_filtrados.empty:
                # Resumen del Cliente
                st.markdown("#### 📊 Resumen del Cliente")
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    estados_cliente = clientes_filtrados['Estado'].value_counts()
                    fig = px.pie(
                        values=estados_cliente.values,
                        names=estados_cliente.index,
                        title=f'Distribución de Unidades',
                        color_discrete_sequence=['#00CC96', '#EF553B'],
                        hole=0.4
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, key=f"resumen_cliente_pie_{buscar_cliente}")
                
                with col2:
                    total_unidades_cliente = len(clientes_filtrados)
                    unidades_activas = clientes_filtrados[clientes_filtrados['Estado'] == 'Activada']
                    unidades_activas_cliente = len(unidades_activas)
                    
                    st.markdown("**📈 Métricas Generales:**")
                    st.markdown(f"""
                    - 📱 Total Unidades: **{total_unidades_cliente:,}**
                    - ✅ Unidades Activas: **{unidades_activas_cliente:,}**
                    - ❌ Unidades Desactivadas: **{total_unidades_cliente - unidades_activas_cliente:,}**
                    """)
                    
                    if 'Costo_Mensual' in clientes_filtrados.columns:
                        costo_total = unidades_activas['Costo_Mensual'].sum()
                        costo_promedio = unidades_activas['Costo_Mensual'].mean()
                        
                        st.markdown("**💰 Información de Costos:**")
                        st.markdown(f"""
                        - 💵 Facturación Mensual: **${costo_total:,.2f}**
                        - 📊 Costo Promedio por Unidad: **${costo_promedio:,.2f}**
                        """)
                
                # Detalle de Unidades y Costos
                st.markdown("#### 📋 Detalle de Unidades y Costos")
                
                if 'Costo_Mensual' in clientes_filtrados.columns:
                    detalle_unidades = clientes_filtrados[['Estado', 'Origen', 'Ciclo_Facturacion', 'Costo_Mensual']].copy()
                    detalle_unidades['Costo_Mensual'] = detalle_unidades['Costo_Mensual'].fillna(0)
                    detalle_unidades['Costo_Efectivo'] = detalle_unidades.apply(
                        lambda x: x['Costo_Mensual'] if x['Estado'] == 'Activada' else 0,
                        axis=1
                    )
                    
                    st.dataframe(
                        detalle_unidades,
                        column_config={
                            "Estado": st.column_config.TextColumn("Estado", width="medium"),
                            "Origen": st.column_config.TextColumn("Plataforma", width="medium"),
                            "Ciclo_Facturacion": st.column_config.TextColumn("Ciclo", width="medium"),
                            "Costo_Mensual": st.column_config.NumberColumn(
                                "Costo Base",
                                format="$%.2f",
                                width="medium"
                            ),
                            "Costo_Efectivo": st.column_config.NumberColumn(
                                "Costo Efectivo",
                                format="$%.2f",
                                width="medium",
                                help="Costo real considerando solo unidades activas"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Resumen por Plataforma
                    st.markdown("#### 📊 Resumen por Plataforma")
                    resumen_plataforma = clientes_filtrados[clientes_filtrados['Estado'] == 'Activada'].groupby('Origen').agg({
                        'Estado': 'count',
                        'Costo_Mensual': 'sum'
                    }).reset_index()
                    
                    resumen_plataforma.columns = ['Plataforma', 'Unidades Activas', 'Facturación Mensual']
                    
                    st.dataframe(
                        resumen_plataforma,
                        column_config={
                            "Plataforma": st.column_config.TextColumn("Plataforma", width="medium"),
                            "Unidades Activas": st.column_config.NumberColumn("Unidades Activas", format="%d"),
                            "Facturación Mensual": st.column_config.NumberColumn(
                                "Facturación Mensual",
                                format="$%.2f"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Gráfico de Facturación por Plataforma
                    fig_facturacion = px.bar(
                        resumen_plataforma,
                        x='Plataforma',
                        y='Facturación Mensual',
                        title='Facturación Mensual por Plataforma',
                        text='Unidades Activas',
                        labels={'Facturación Mensual': 'Facturación (USD)', 'Unidades Activas': 'Unidades Activas'}
                    )
                    fig_facturacion.update_traces(
                        texttemplate='%{text} unidades',
                        textposition='outside'
                    )
                    st.plotly_chart(fig_facturacion, use_container_width=True, key=f"facturacion_plataforma_{buscar_cliente}")
                
                else:
                    st.warning("⚠️ No hay información de costos disponible para este cliente")
            else:
                st.warning("⚠️ No se encontraron registros para el cliente seleccionado")

    with tabs[2]:
        st.markdown("### 💰 Análisis por Plataforma")
        
        # Reutilizar el resumen de unidades por plataforma con un sufijo único
        plataformas_resumen = resumen_unidades_por_plataforma(df_validos, unique_suffix="tab3")
        detalles_por_plataforma(df_validos, plataformas_resumen, df_costos)

    with tabs[3]:
        st.markdown("### 📋 Datos Completos")
        
        # Filtrado de Datos
        col1, col2 = st.columns(2)
        with col1:
            estado_filtro = st.multiselect(
                "Filtrar por Estado",
                options=['Activada', 'Desactivada'],
                default=['Activada', 'Desactivada'],
                key="estado_filtro_multiselect_tab4"
            )
        
        df_filtrado = df_validos[df_validos['Estado'].isin(estado_filtro)]
        
        # Paginación
        registros_por_pagina = 50
        num_paginas = len(df_filtrado) // registros_por_pagina + (1 if len(df_filtrado) % registros_por_pagina > 0 else 0)
        if num_paginas > 0:
            pagina = st.slider('Página', 1, num_paginas, 1, key="pagina_slider_tab4")
            inicio = (pagina - 1) * registros_por_pagina
            fin = min(inicio + registros_por_pagina, len(df_filtrado))
            
            st.dataframe(
                df_filtrado.iloc[inicio:fin][['Cliente_Cuenta', 'Nombre', 'Estado', 'Fecha_de_Desactivacion']],
                use_container_width=True
            )
            
            st.markdown(f"Mostrando registros {inicio + 1} a {fin} de {len(df_filtrado)}")
        else:
            st.warning("No hay datos para mostrar con los filtros seleccionados")

    with tabs[4]:
        st.markdown("### 💵 Análisis de Costos")
        analisis_de_costos(df_validos)
    
    with tabs[5]:
        st.markdown("### 📂 Datos por Plataforma")
        mostrar_tablas_por_plataforma(df_plataformas)

def mostrar_tablas_por_plataforma(df_plataformas):
    """Muestra tres tablas separadas, una para cada plataforma."""
    st.markdown("#### 📂 Datos por Plataforma")
    
    for plataforma, df_plat in df_plataformas.items():
        st.markdown(f"##### 📱 Plataforma: {plataforma}")
        if df_plat.empty:
            st.warning(f"No hay datos disponibles para la plataforma **{plataforma}**.")
            continue
        
        # Agrupar por Cliente para obtener las métricas requeridas
        df_costos_cliente = df_plat.groupby('Cliente_Cuenta').agg(
            Unidades_Activadas=('Estado', lambda x: (x == 'Activada').sum()),
            Unidades_Desactivadas=('Estado', lambda x: (x == 'Desactivada').sum()),
            Total_Unidades=('Estado', 'count'),
            Costo_Unitario=('Costo_Mensual', 'mean')
        ).reset_index()
        
        # Calcular Costo Total Impactado por Unidades Activas
        df_costos_cliente['Costo_Total_Impactado'] = df_costos_cliente['Unidades_Activadas'] * df_costos_cliente['Costo_Unitario']
        
        # Redondear los costos a dos decimales
        df_costos_cliente['Costo_Unitario'] = df_costos_cliente['Costo_Unitario'].round(2)
        df_costos_cliente['Costo_Total_Impactado'] = df_costos_cliente['Costo_Total_Impactado'].round(2)
        
        # Ordenar por Costo Total Impactado Descendente
        df_costos_cliente = df_costos_cliente.sort_values('Costo_Total_Impactado', ascending=False)
        
        # Mostrar la tabla
        st.dataframe(
            df_costos_cliente,
            column_config={
                "Cliente_Cuenta": st.column_config.TextColumn("Cliente", width="medium"),
                "Unidades_Activadas": st.column_config.NumberColumn("Unidades Activas", format="%d"),
                "Unidades_Desactivadas": st.column_config.NumberColumn("Unidades Desactivadas", format="%d"),
                "Total_Unidades": st.column_config.NumberColumn("Total Unidades", format="%d"),
                "Costo_Unitario": st.column_config.NumberColumn("Costo Unitario", format="$%.2f"),
                "Costo_Total_Impactado": st.column_config.NumberColumn("Costo Total Impactado", format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Opcional: Agregar gráficos para una mejor visualización
        st.markdown(f"##### 📈 Distribución del Costo Total Impactado en {plataforma}")
        fig = px.bar(
            df_costos_cliente.head(20),  # Mostrar los 20 principales para mayor claridad
            x='Cliente_Cuenta',
            y='Costo_Total_Impactado',
            title=f'Top 20 Clientes por Costo Total Impactado en {plataforma}',
            labels={'Costo_Total_Impactado': 'Costo Total Impactado (USD)', 'Cliente_Cuenta': 'Cliente'},
            color='Costo_Total_Impactado',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True, key=f"costo_total_impactado_bar_chart_{plataforma}")

# =====================================
# Sidebar: Carga y Configuración
# =====================================
with st.sidebar:
    st.header("Configuración")
    st.markdown("---")
    
    # Cargar base de datos
    st.subheader("📁 Base de Datos Principal")
    db_file = st.file_uploader("Cargar base de datos SQLite", type=['db'], key="db_file_uploader")
    
    # Cargar archivo de costos
    st.markdown("---")
    st.subheader("💰 Costos y Ciclos de Facturación")
    costos_file = st.file_uploader("Cargar archivo de costos", type=['xlsx', 'xls'], key="costos_file_uploader")
    
    if db_file:
        st.success("✅ Base de datos cargada correctamente")
        st.markdown("---")
        st.markdown("""
        ### 📌 Guía Rápida
        1. Seleccione una tabla de la base de datos
        2. Explore las métricas generales
        3. Analice los gráficos interactivos
        4. Busque clientes específicos
        """)
    else:
        st.info("👆 Seleccione un archivo de base de datos SQLite para comenzar el análisis.")

# =====================================
# Lógica Principal
# =====================================
datos = cargar_datos(db_file, costos_file)

if datos['conn'] is not None:
    try:
        tablas = obtener_tablas(datos['conn'])
        
        if not tablas:
            st.error("❌ No se encontraron tablas en la base de datos.")
        else:
            # Asumir que la tabla principal se llama 'main', si no, seleccionar la primera tabla
            with st.sidebar:
                if 'main' in tablas:
                    tabla_seleccionada = 'main'
                else:
                    tabla_seleccionada = tablas[0]
                st.info(f"📂 Tabla seleccionada: **{tabla_seleccionada}**")
        
            # Cargar datos de la tabla seleccionada
            df = cargar_datos_tabla(datos['conn'], tabla_seleccionada)
            
            if df is not None:
                # Validar registros
                df_validos = validar_registros(df)
                
                if df_validos.empty:
                    st.warning("⚠️ No hay registros válidos para mostrar.")
                else:
                    # Integrar costos si están disponibles
                    if datos['df_costos'] is not None:
                        df_validos = integrar_costos(df_validos, datos['df_costos'])
                    
                    # Mostrar métricas de validación
                    mostrar_metricas_validacion(df, df_validos)
                    
                    # Crear Tabs para diferentes vistas
                    crear_tabs(df_validos, df_costos=datos.get('df_costos'))
    
    except Exception as e:
        st.error(f"❌ Error al procesar los datos: {str(e)}")
    
    finally:
        # Cerrar conexión y limpiar archivos temporales
        datos['conn'].close()
        if datos['temp_path']:
            datos['temp_path'].unlink()
else:
    st.info("👆 Seleccione un archivo de base de datos SQLite para comenzar el análisis.")
