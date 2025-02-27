import psycopg2
import streamlit as st
from utils import *
import pyvis
from pyvis.network import Network
import pandas as pd
from stvis import pv_static

color_map = {
    "j": "#00bfff",
    "c": "#808080",
    "n": "#ffc0cb",
    "e": "#ff0000"
}

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    # Si tipo_origen es "j", nos quedamos con 9 dígitos de id_origen
    df["id_origen"] = df.apply(lambda x: str(x["id_origen"])[:9] if x["tipo_origen"] == "j" else x["id_origen"], axis=1)
    # Si tipo_destino es "j", idem para id_destino
    df["id_destino"] = df.apply(lambda x: str(x["id_destino"])[:9] if x["tipo_destino"] == "j" else x["id_destino"], axis=1)

    nodes_origines = df[["id_origen", "nombre_origen", "tipo_origen"]].drop_duplicates()
    nodes_destinos = df[["id_destino", "nombre_destino", "tipo_destino"]].drop_duplicates()

    # Rellenamos valores nulos en nombres
    nodes_origines["nombre_origen"] = nodes_origines["nombre_origen"].fillna("")
    nodes_destinos["nombre_destino"] = nodes_destinos["nombre_destino"].fillna("")

    # Calculamos la longitud de los nombres para elegir el más largo
    nodes_origines["nombre_origen_len"] = nodes_origines["nombre_origen"].apply(lambda x: len(x))
    nodes_destinos["nombre_destino_len"] = nodes_destinos["nombre_destino"].apply(lambda x: len(x))

    idx_to_keep_origenes = nodes_origines.groupby('id_origen')['nombre_origen_len'].idxmax()
    idx_to_keep_destinos = nodes_destinos.groupby('id_destino')['nombre_destino_len'].idxmax()

    nodes_origines = nodes_origines.loc[idx_to_keep_origenes].drop(columns=["nombre_origen_len"])
    nodes_destinos = nodes_destinos.loc[idx_to_keep_destinos].drop(columns=["nombre_destino_len"])

    # Renombramos columnas para unificarlas
    nodes_origines.columns = ["id", "name", "tipo"]
    nodes_destinos.columns = ["id", "name", "tipo"]
    nodes = pd.concat([nodes_origines, nodes_destinos], ignore_index=True)

    # Excluimos valores no válidos
    nodes = nodes[nodes["id"] != "No Definido"]
    nodes = nodes[nodes["id"] != "No Defini"]

    # --- MODIFICACIÓN: Extraer solo los dígitos y convertir a int ---
    nodes["id"] = nodes["id"].astype(str).str.extract(r'(\d+)')[0].astype(int)

    nodes["color"] = nodes["tipo"].apply(lambda x: color_map[x])

    df_edges = df[["id_origen", "id_destino", "total_contratos_millones"]]

    # Filtramos edges no válidos
    df_edges = df_edges[df_edges["id_origen"] != "No Definido"]
    df_edges = df_edges[df_edges["id_destino"] != "No Definido"]
    df_edges = df_edges[df_edges["id_origen"] != "No Defini"]
    df_edges = df_edges[df_edges["id_destino"] != "No Defini"]

    # --- MODIFICACIÓN: Extraer dígitos para edges y convertir a int ---
    df_edges["id_origen"] = df_edges["id_origen"].astype(str).str.extract(r'(\d+)')[0].astype(int)
    df_edges["id_destino"] = df_edges["id_destino"].astype(str).str.extract(r'(\d+)')[0].astype(int)

    # Agrupamos por (id_origen, id_destino) y sumamos total_contratos_millones
    df_edges = df_edges.groupby(["id_origen", "id_destino"]).agg({"total_contratos_millones": "sum"}).reset_index().sort_values(by="total_contratos_millones", ascending=False)

    # Normalizamos la columna total_contratos_millones en [1, 100]
    if df_edges.shape[0] == 1:
        df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"]
    else:
        min_edges = df_edges[df_edges["total_contratos_millones"] > 0]["total_contratos_millones"].min()
        max_edges = df_edges["total_contratos_millones"].max()
        max_minus_min = max_edges - min_edges

        df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"].apply(lambda x: (x - min_edges) / max_minus_min * 100 if max_minus_min != 0 else 50)

    return nodes, df_edges

def create_graph(nodes: pd.DataFrame, df_edges: pd.DataFrame):
    list_of_tuples = [tuple(row[1]) for row in df_edges.iterrows()]

    net = Network(notebook=True, cdn_resources='remote', height="800px", width="980")

    nodes_list = nodes["id"].values.tolist()
    titles_list = [name.title() for name in nodes["name"].values.tolist()]
    colors_list = nodes["color"].values.tolist()

    net.add_nodes(nodes_list, title=titles_list, color=colors_list)

    for t in list_of_tuples:
        # t = (id_origen, id_destino, total_contratos_millones, total_contratos_millones_n)
        net.add_edge(int(t[0]), int(t[1]), value=int(t[2]), title=t[3])

    # Ajustamos los labels según el número de conexiones
    number_of_nodes = len(net.nodes)
    if number_of_nodes < 5:
        for i, node in enumerate(net.nodes):
            net.nodes[i]["label"] = node["title"]
    else:
        connections = net.get_adj_list()
        for i, node in enumerate(net.nodes):
            node_identifier = node["id"]
            node_connections = connections[node_identifier]
            if len(node_connections) > 3:
                net.nodes[i]["label"] = node["title"]
            else:
                net.nodes[i]["label"] = None

    st.header("Grafo")
    with st.expander("¿Qué significa cada color?"):
        st.markdown("""
        - <span style="color:#00bfff">Azul</span>: Empresa  
        - <span style="color:#808080">Gris</span>: Consorcio  
        - <span style="color:#ffc0cb">Rosado</span>: Humano  
        - <span style="color:#ff0000">Rojo</span>: Entidad del estado  
        """, unsafe_allow_html=True)
    pv_static(net)

def get_graph(cedula: str):
    query = """
    WITH rlmc AS (
        SELECT 
            documento_empresa AS id_origen, 
            nombre_empresa AS nombre_origen, 
            codigo_grupo AS id_destino, 
            nombre_grupo AS nombre_destino, 
            'empresa_consorcio' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'j' AS tipo_origen, 
            'c' AS tipo_destino
        FROM representantes_miembros_consorcio
        WHERE documento_persona = '{documento_persona}'
        GROUP BY documento_empresa, nombre_empresa, codigo_grupo, nombre_grupo
    ),
    filtro AS (
        SELECT 
            documento_persona, 
            nombre_persona, 
            nit_empresa, 
            nombre_empresa, 
            nit_entidad, 
            nombre_entidad, 
            tipo_relacion, 
            id_unico, 
            valor_contrato_millones
        FROM personas_naturales
        WHERE documento_persona = '{documento_persona}'
    ),
    miembro AS (
        SELECT
            documento_persona AS id_origen,
            nombre_persona AS nombre_origen,
            nit_empresa AS id_destino,
            nombre_empresa AS nombre_destino,
            'persona_consorcio' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'n' AS tipo_origen,
            'c' AS tipo_destino
        FROM filtro
        WHERE tipo_relacion = 'Miembro de consorcio'
        GROUP BY documento_persona, nombre_persona, nit_empresa, nombre_empresa
    ),
    rte_legal_temp AS (
        SELECT
            documento_persona AS id_origen,
            nit_empresa AS id_destino,
            'rte_empresa' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'n' AS tipo_origen,
            'j' AS tipo_destino
        FROM filtro
        WHERE tipo_relacion = 'Representante legal'
        GROUP BY documento_persona, nit_empresa
    ),
    rte_legal AS (
        SELECT
            t.id_origen,
            m.nombre_persona AS nombre_origen,
            t.id_destino,
            r.nombre_empresa AS nombre_destino,
            t.relacion,
            t.total_contratos_millones,
            t.numero_de_contratos,
            t.tipo_origen,
            t.tipo_destino
        FROM rte_legal_temp t
        LEFT JOIN ids_nombres m ON t.id_origen = m.documento_persona
        LEFT JOIN representantes_legales r ON t.id_destino = r.doc_empresa
    ),
    ops AS (
        SELECT
            documento_persona AS id_origen,
            nombre_persona AS nombre_origen,
            nit_entidad AS id_destino,
            nombre_entidad AS nombre_destino,
            'persona_entidad' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'n' AS tipo_origen,
            'e' AS tipo_destino
        FROM filtro
        WHERE tipo_relacion = 'Contratista'
        GROUP BY documento_persona, nombre_persona, nit_entidad, nombre_entidad
    ),
    grupos_search AS (
        SELECT DISTINCT id_destino AS codigo_grupo FROM rlmc
        UNION ALL
        SELECT DISTINCT id_destino AS codigo_grupo FROM miembro
    ),
    miembros_grupo AS (
        SELECT
            codigo_grupo AS id_origen,
            nombre_grupo AS nombre_origen,
            nit_participante AS id_destino,
            nombre_participante AS nombre_destino,
            'consorcio_empresa' AS relacion,
            -1.0 AS total_contratos_millones,
            CAST(-1 AS BIGINT) AS numero_de_contratos,
            'c' AS tipo_origen,
            'j' AS tipo_destino
        FROM grupos
        WHERE codigo_grupo IN ( SELECT codigo_grupo FROM grupos_search )
    ),
    representantes_miembros AS (
        SELECT
            doc_empresa AS id_origen,
            nombre_empresa AS nombre_origen,
            doc_representante_legal AS id_destino,
            nombre_representante_legal AS nombre_destino,
            'empresa_rte' AS relacion,
            -1.0 AS total_contratos_millones,
            CAST(-1 AS BIGINT) AS numero_de_contratos,
            'j' AS tipo_origen,
            'n' AS tipo_destino
        FROM representantes_legales_final
        WHERE doc_empresa IN ( SELECT id_destino FROM miembros_grupo )
    )
    SELECT * FROM rlmc
    UNION ALL
    SELECT * FROM miembro
    UNION ALL
    SELECT * FROM rte_legal
    UNION ALL
    SELECT * FROM ops
    UNION ALL
    SELECT * FROM miembros_grupo
    UNION ALL
    SELECT * FROM representantes_miembros;
    """.format(documento_persona=cedula)

    response_df = query_athena(query)
    response_df["total_contratos_millones"] = response_df["total_contratos_millones"].astype(float)
    nodes, df_edges = preprocess_data(response_df)
    create_graph(nodes, df_edges)
