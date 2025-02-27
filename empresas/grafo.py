import streamlit as st
import pandas as pd
from pyvis.network import Network
from stvis import pv_static
from utils import query_athena

color_map = {
    "j": "#00bfff",   # Empresa
    "c": "#808080",   # Consorcio
    "n": "#ffc0cb",   # Humano
    "e": "#ff0000"    # Entidad del estado
}

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara los datos para PyVis:
    - Ajusta ID de orígenes/destinos a sólo 9 dígitos si son 'j'.
    - Crea un DataFrame de nodos y de edges.
    """
    # Si tipo_origen es "j", nos quedamos con 9 dígitos:
    df["id_origen"] = df.apply(
        lambda x: str(x["id_origen"])[:9] if x["tipo_origen"] == "j" else x["id_origen"], axis=1
    )
    # Si tipo_destino es "j", idem:
    df["id_destino"] = df.apply(
        lambda x: str(x["id_destino"])[:9] if x["tipo_destino"] == "j" else x["id_destino"], axis=1
    )

    # Creación del DF de nodos (orígenes y destinos)
    nodes_origines = df[["id_origen", "nombre_origen", "tipo_origen"]].drop_duplicates()
    nodes_destinos = df[["id_destino", "nombre_destino", "tipo_destino"]].drop_duplicates()
    nodes_origines["nombre_origen"] = nodes_origines["nombre_origen"].fillna("")
    nodes_destinos["nombre_destino"] = nodes_destinos["nombre_destino"].fillna("")

    # Para escoger el nombre más largo (en caso de repeticiones)
    nodes_origines["nombre_origen_len"] = nodes_origines["nombre_origen"].apply(len)
    nodes_destinos["nombre_destino_len"] = nodes_destinos["nombre_destino"].apply(len)

    idx_to_keep_origenes = nodes_origines.groupby('id_origen')['nombre_origen_len'].idxmax()
    idx_to_keep_destinos = nodes_destinos.groupby('id_destino')['nombre_destino_len'].idxmax()

    nodes_origines = nodes_origines.loc[idx_to_keep_origenes].drop(columns=["nombre_origen_len"])
    nodes_destinos = nodes_destinos.loc[idx_to_keep_destinos].drop(columns=["nombre_destino_len"])

    # Renombramos columnas para unificarlas
    nodes_origines.columns = ["id", "name", "tipo"]
    nodes_destinos.columns = ["id", "name", "tipo"]
    nodes = pd.concat([nodes_origines, nodes_destinos], ignore_index=True)

    # Excluimos "No Definido" / "No Defini"
    nodes = nodes[~nodes["id"].isin(["No Definido", "No Defini"])]

    # --- CORRECCIÓN: Extraer solo dígitos y convertir a int ---
    nodes["id"] = nodes["id"].astype(str).str.extract(r'(\d+)')[0].astype(int)

    # Color de nodo según su tipo
    nodes["color"] = nodes["tipo"].map(color_map)

    # Edges
    df_edges = df[["id_origen", "id_destino", "total_contratos_millones"]].copy()

    # Removemos "No Definido"
    df_edges = df_edges[~df_edges["id_origen"].isin(["No Definido", "No Defini"])]
    df_edges = df_edges[~df_edges["id_destino"].isin(["No Definido", "No Defini"])]

    # --- CORRECCIÓN: Extraer solo dígitos y convertir a int para los edges ---
    df_edges["id_origen"] = df_edges["id_origen"].astype(str).str.extract(r'(\d+)')[0].astype(int)
    df_edges["id_destino"] = df_edges["id_destino"].astype(str).str.extract(r'(\d+)')[0].astype(int)

    # Agrupamos por (origen, destino) y sumamos total_contratos_millones
    df_edges = (
        df_edges.groupby(["id_origen", "id_destino"])
        .agg({"total_contratos_millones": "sum"})
        .reset_index()
        .sort_values(by="total_contratos_millones", ascending=False)
    )

    # Normalizamos la columna total_contratos_millones en [1, 100]
    if df_edges.shape[0] == 1:
        df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"]
    else:
        positive_vals = df_edges[df_edges["total_contratos_millones"] > 0]["total_contratos_millones"]
        if len(positive_vals) > 0:
            min_edges = positive_vals.min()
            max_edges = df_edges["total_contratos_millones"].max()
            max_minus_min = max_edges - min_edges

            df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"].apply(
                lambda x: (x - min_edges) / max_minus_min * 100 if max_minus_min != 0 else 50
            )
        else:
            df_edges["total_contratos_millones_n"] = 1

    return nodes, df_edges

def create_graph(nodes: pd.DataFrame, df_edges: pd.DataFrame):
    """
    Usa PyVis para crear el grafo y renderizarlo en Streamlit.
    """
    list_of_tuples = [tuple(row[1]) for row in df_edges.iterrows()]
    net = Network(notebook=True, cdn_resources='remote', height="800px", width="980")

    nodes_list = nodes["id"].values.tolist()
    titles_list = [name.title() for name in nodes["name"].values.tolist()]
    colors_list = nodes["color"].values.tolist()

    net.add_nodes(nodes_list, title=titles_list, color=colors_list)

    for t in list_of_tuples:
        id_origen, id_destino, val_millones, val_millones_n = t
        net.add_edge(
            int(id_origen),
            int(id_destino),
            value=int(val_millones),
            title=str(val_millones_n)
        )

    connections = net.get_adj_list()
    for i, node in enumerate(net.nodes):
        node_identifier = node["id"]
        node_connections = connections[node_identifier]
        number_of_node_connections = len(node_connections)
        if number_of_node_connections > 3:
            net.nodes[i]["label"] = node["title"]
        else:
            net.nodes[i]["label"] = None

    st.header("Grafo")
    with st.expander("¿Qué significa cada color?"):
        st.markdown(
            """
            - <span style="color:#00bfff">Azul</span>: Empresa  
            - <span style="color:#808080">Gris</span>: Consorcio  
            - <span style="color:#ffc0cb">Rosado</span>: Humano  
            - <span style="color:#ff0000">Rojo</span>: Entidad del estado  
            """,
            unsafe_allow_html=True,
        )
    pv_static(net)

def get_graph(nit_empresa: str):
    """
    Genera el grafo de conexiones para una empresa dada por nit_empresa.
    Combina varias CTEs con UNION ALL para mostrar:
      - Entidades con las que ha tenido contratos
      - Consorcios en los que ha participado
      - Compañeros en consorcio
      - Representantes legales, etc.
    """
    query = f"""
    WITH contratos_con_entidades_que_ha_tenido AS (
        SELECT
            nit_empresa AS id_origen,
            nombre_empresa AS nombre_origen,
            nit_entidad AS id_destino,
            nombre_entidad AS nombre_destino,
            'empresa_entidad' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'j' AS tipo_origen,
            'e' AS tipo_destino
        FROM personas_juridicas
        WHERE nit_empresa = '{nit_empresa}'
          AND tipo_relacion = 'Contratista'
        GROUP BY nit_empresa, nombre_empresa, nit_entidad, nombre_entidad
    ),
    grupos_donde_ha_participado AS (
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
        WHERE documento_empresa = '{nit_empresa}'
        GROUP BY documento_empresa, nombre_empresa, codigo_grupo, nombre_grupo
    ),
    entidades_con_las_que_los_grupos_han_contratado AS (
        SELECT
            codigo_grupo AS id_origen,
            nombre_grupo AS nombre_origen,
            nit_entidad AS id_destino,
            nombre_entidad AS nombre_destino,
            'consorcio_entidad' AS relacion,
            SUM(CAST(valor_contrato_millones AS DOUBLE)) AS total_contratos_millones,
            COUNT(id_unico) AS numero_de_contratos,
            'c' AS tipo_origen,
            'e' AS tipo_destino
        FROM representantes_miembros_consorcio
        WHERE codigo_grupo IN (
            SELECT DISTINCT id_destino
            FROM grupos_donde_ha_participado
        )
        GROUP BY codigo_grupo, nombre_grupo, nit_entidad, nombre_entidad
    ),
    companeros AS (
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
        WHERE codigo_grupo IN (
            SELECT DISTINCT id_destino FROM grupos_donde_ha_participado
        )
    ),
    representantes_de_companeros AS (
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
        WHERE doc_empresa IN (
            SELECT id_destino FROM companeros
        )
    ),
    representantes_de_esta_empresa AS (
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
        WHERE doc_empresa = '{nit_empresa}'
    ),
    contratos_de_representantes_de_esta_empresa AS (
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
        FROM personas_naturales
        WHERE tipo_relacion = 'Contratista'
          AND documento_persona IN (
              SELECT DISTINCT id_destino
              FROM representantes_de_esta_empresa
          )
        GROUP BY documento_persona, nombre_persona, nit_entidad, nombre_entidad
    )
    SELECT * FROM contratos_con_entidades_que_ha_tenido
    UNION ALL
    SELECT * FROM grupos_donde_ha_participado
    UNION ALL
    SELECT * FROM entidades_con_las_que_los_grupos_han_contratado
    UNION ALL
    SELECT * FROM companeros
    UNION ALL
    SELECT * FROM representantes_de_companeros
    UNION ALL
    SELECT * FROM representantes_de_esta_empresa
    UNION ALL
    SELECT * FROM contratos_de_representantes_de_esta_empresa
    """

    response_df = query_athena(query)

    response_df["total_contratos_millones"] = response_df["total_contratos_millones"].astype(float)

    nodes, df_edges = preprocess_data(response_df)
    create_graph(nodes, df_edges)
