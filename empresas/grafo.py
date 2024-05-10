import psycopg2
import streamlit as st
from utils import query_postgres
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

    # Group by id_origen and id_destino and sum total_contratos_millones
    # df = df.groupby(["id_origen", "id_destino"]).agg({"total_contratos_millones": "sum"}).reset_index()

        # If tipo_origen is "j" then keep first 9 digits of id_origen
    df["id_origen"] = df.apply(lambda x: str(x["id_origen"])[:9] if x["tipo_origen"] == "j" else x["id_origen"], axis=1)

    # If tipo_destino is "j" then keep first 9 digits of id_destino
    df["id_destino"] = df.apply(lambda x: str(x["id_destino"])[:9] if x["tipo_destino"] == "j" else x["id_destino"], axis=1)

    nodes_origines = df[["id_origen", "nombre_origen", "tipo_origen"]].drop_duplicates()
    nodes_destinos = df[["id_destino", "nombre_destino", "tipo_destino"]].drop_duplicates()

    # Number of characters for nombre_origen
    nodes_origines["nombre_origen_len"] = nodes_origines["nombre_origen"].apply(lambda x: len(x))

    # Number of characters for nombre_destino
    nodes_destinos["nombre_destino_len"] = nodes_destinos["nombre_destino"].apply(lambda x: len(x))

    # Identify the index of rows with the highest score for each company_id
    idx_to_keep_origenes = nodes_origines.groupby('id_origen')['nombre_origen_len'].idxmax()
    # Create a new DataFrame with only the rows to keep
    nodes_origines = nodes_origines.loc[idx_to_keep_origenes]

    # Identify the index of rows with the highest score for each company_id
    idx_to_keep_destinos = nodes_destinos.groupby('id_destino')['nombre_destino_len'].idxmax()
    # Create a new DataFrame with only the rows to keep
    nodes_destinos = nodes_destinos.loc[idx_to_keep_destinos]

    # Drop
    nodes_origines = nodes_origines.drop(columns=["nombre_origen_len"])
    nodes_destinos = nodes_destinos.drop(columns=["nombre_destino_len"])

    nodes_origines.columns = ["id", "name", "tipo"]
    nodes_destinos.columns = ["id", "name", "tipo"]
    nodes = pd.concat([nodes_origines, nodes_destinos], ignore_index=True)

    nodes = nodes[nodes["id"] != "No Definido"]
    nodes = nodes[nodes["id"] != "No Defini"]

    # Parse nodes as int
    nodes["id"] = nodes["id"].astype(int)

    nodes["color"] = nodes["tipo"].apply(lambda x: color_map[x])

    # st.dataframe(nodes)


    df_edges = df[["id_origen", "id_destino", "total_contratos_millones"]]

    df_edges = df_edges[["id_origen", "id_destino", "total_contratos_millones"]]

    df_edges = df_edges[df_edges["id_origen"] != "No Definido"]
    df_edges = df_edges[df_edges["id_destino"] != "No Definido"]

    df_edges = df_edges[df_edges["id_origen"] != "No Defini"]
    df_edges = df_edges[df_edges["id_destino"] != "No Defini"]

    df_edges["id_origen"] = df_edges["id_origen"].astype(int)
    df_edges["id_destino"] = df_edges["id_destino"].astype(int)
    # df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones_n"].astype(int)

    # st.title("Before:")
    # st.dataframe(df_edges)

    # Group by id_origen and id_destino and sum total_contratos_millones
    # Also VERY important: reorganize so -1 values stay at the bottom. This is because pyvis will not show edges with value -1.
    # If repeated, we want to show edges with actual values
    df_edges = df_edges.groupby(["id_origen", "id_destino"]).agg({"total_contratos_millones": "sum"}).reset_index().sort_values(by="total_contratos_millones", ascending=False)

    # st.title("After:")
    # st.dataframe(df_edges)

    if df_edges.shape[0] == 1:
        df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"]
    else:
        min_edges = df_edges[df_edges["total_contratos_millones"] > 0]["total_contratos_millones"].min()
        max_edges = df_edges["total_contratos_millones"].max()
        max_minus_min = max_edges - min_edges
        min_edges, max_edges

        # normalize total_contratos_millones between 1 and 100
        df_edges["total_contratos_millones_n"] = df_edges["total_contratos_millones"].apply(lambda x: (x - min_edges) / max_minus_min * 100)



    # st.dataframe(df_edges)

    return nodes, df_edges


def create_graph(nodes: pd.DataFrame, df_edges: pd.DataFrame):

    list_of_tuples = [tuple(row[1]) for row in df_edges.iterrows()]

    net = Network(notebook=True, cdn_resources='remote', height="800px", width="980")

    nodes_list = nodes["id"].values.tolist()
    titles_list = nodes["name"].values.tolist()

    titles_list = [x.title() for x in titles_list]

    net.add_nodes(
        nodes_list,
        title=titles_list,
        color=nodes["color"].values.tolist()
    )

    for t in list_of_tuples:
        net.add_edge(int(t[0]), int(t[1]), value=int(t[2]), title=t[3])

    # Iterate through nodes and update label visibility
    connections = net.get_adj_list()
    for i, node in enumerate(net.nodes):
        node_identifier = node["id"]
        node_connections = connections[node_identifier]
        number_of_node_connections = len(node_connections)
        if number_of_node_connections > 3:
            print(number_of_node_connections)
            print(node)
            # Assign title to label in node
            net.nodes[i]["label"] = node["title"]
        else:
            net.nodes[i]["label"] = None
            pass

    # net.show("streamlit_edges.html") # this will save the graph as file as an html document
    st.header("Grafo")
    with st.expander("¿Qué significa cada color?"):
        st.markdown("""
        - <span style="color:#00bfff">Azul</span>: Empresa
        - <span style="color:#808080">Gris</span>: Consorcio
        - <span style="color:#ffc0cb">Rosado</span>: Humano
        - <span style="color:#ff0000">Rojo</span>: Entidad del estado
        """, unsafe_allow_html=True)
    pv_static(net)
    
        

def get_graph(nit_empresa: str):

    query = """
    WITH contratos_con_entidades_que_ha_tenido AS (

        select 
            nit_empresa as id_origen, 
            nombre_empresa as nombre_origen, 
            nit_entidad  as id_destino, 
            nombre_entidad as nombre_destino,
            'empresa_entidad' as relacion,
            sum(valor_contrato_millones) as total_contratos_millones,
            count(id_unico) as numero_de_contratos,
            'j' as tipo_origen, 
            'e' as tipo_destino
            
        from personas_juridicas
        where nit_empresa = '{nit_empresa}'
        and tipo_relacion = 'Contratista'
        group by nit_empresa, nombre_empresa, nit_entidad, nombre_entidad
        
    ),


    grupos_donde_ha_participado AS (

        select 
            documento_empresa as id_origen, 
            nombre_empresa as nombre_origen, 
            codigo_grupo as id_destino, 
            nombre_grupo as nombre_destino, 
            'empresa_consorcio' as relacion,
            sum(valor_contrato_millones) as total_contratos_millones,
            count(id_unico) as numero_de_contratos,
            'j' as tipo_origen, 
            'c' as tipo_destino
        
        from representates_miembros_consorcio
        where documento_empresa = '{nit_empresa}'
        group by documento_empresa, nombre_empresa, codigo_grupo, nombre_grupo

    ),

    entidades_con_las_que_los_grupos_han_contratado AS (

        select 
            codigo_grupo as id_origen,
            nombre_grupo as nombre_origen,
            nit_entidad as id_destino,
            nombre_entidad as nombre_destino,
            'consorcio_entidad' as relacion,
            sum(valor_contrato_millones) as total_contratos_millones,
            count(id_unico) as numero_de_contratos,
            'c' as tipo_origen, 
            'e' as tipo_destino
            
        from representates_miembros_consorcio
        where codigo_grupo IN (select distinct id_destino from grupos_donde_ha_participado)
        group by codigo_grupo, nombre_grupo, nit_entidad, nombre_entidad
    ),

    companeros AS (

        SELECT
            codigo_grupo AS id_origen,
            nombre_grupo AS nombre_origen,
            nit_participante as id_destino,
            nombre_participante as nombre_destino,
            'consorcio_empresa' as relacion,
            -1.0 as total_contratos_millones,
            -1 as numero_de_contratos,
            'c' as tipo_origen, 
            'j' as tipo_destino
        FROM "grupos"
        WHERE codigo_grupo IN (SELECT DISTINCT id_destino FROM grupos_donde_ha_participado) -- id_destino hace referencia al codigo_grupo
    ),

    representantes_de_companeros AS (

        SELECT
            doc_empresa as id_origen, 
            nombre_empresa as nombre_origen, 
            doc_representante_legal as id_destino, 
            nombre_representante_legal as nombre_destino,
            'empresa_rte' as relacion,
            -1.0 as total_contratos_millones,
            -1 as numero_de_contratos,
            'j' as tipo_origen, 
            'n' as tipo_destino
        from representantes_legales_final
        where doc_empresa in (
            select id_destino from companeros -- nit_participante
        )

    ),

    -- aqui solo va a salir uno, pero puede que historicamente haya varios registrados...
    representantes_de_esta_empresa AS (


        SELECT
            doc_empresa as id_origen, 
            nombre_empresa as nombre_origen, 
            doc_representante_legal as id_destino, 
            nombre_representante_legal as nombre_destino,
            'empresa_rte' as relacion,
            -1.0 as total_contratos_millones,
            -1 as numero_de_contratos,
            'j' as tipo_origen, 
            'n' as tipo_destino
        from representantes_legales_final
        where doc_empresa = '{nit_empresa}'
        
    ),

    -- solo contratos OPS, directos entre la persona y la entidad
    contratos_de_representantes_de_esta_empresa AS (
        
        SELECT
            documento_persona as id_origen, 
            nombre_persona as nombre_origen, 
            nit_entidad as id_destino, 
            nombre_entidad as nombre_destino,
            'persona_entidad' as relacion,
            --SUM(CAST(valor_contrato_millones AS FLOAT)) as total_contratos_millones,
            SUM(valor_contrato_millones) as total_contratos_millones,
            count(id_unico) as numero_de_contratos,
            'n' as tipo_origen, 
            'e' as tipo_destino
        from personas_naturales
        where tipo_relacion = 'Contratista'
        and documento_persona IN (select distinct id_destino from representantes_de_esta_empresa)
        group by documento_persona, nombre_persona, nit_entidad, nombre_entidad
    )

    SELECT * FROM contratos_con_entidades_que_ha_tenido UNION all
    SELECT * FROM grupos_donde_ha_participado UNION all
    SELECT * FROM entidades_con_las_que_los_grupos_han_contratado UNION all
    SELECT * FROM companeros UNION all
    SELECT * FROM representantes_de_companeros UNION all
    SELECT * FROM representantes_de_esta_empresa UNION all
    SELECT * FROM contratos_de_representantes_de_esta_empresa


    """.format(nit_empresa=nit_empresa)


    response_df = query_postgres(query)

    # Parse total_contratos_millones as float
    response_df["total_contratos_millones"] = response_df["total_contratos_millones"].astype(float)

    # st.dataframe(response_df)

    nodes, df_edges = preprocess_data(response_df)

    # st.dataframe(df_edges)

    create_graph(nodes, df_edges)

