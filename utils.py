import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import spacy
from dotenv import load_dotenv
load_dotenv()
import os
import numpy as np
from urllib.parse import quote_plus 

tipos_contratos = [
    "Todos",
    "Prestación de Servicios",
    "Suministro",
    "Otro Tipo de Contrato",
    "Compraventa",
    "Obra",
    "Arrendamiento",
    "Consultoría",
    "Decreto 092 de 2017",
    "Interventoría",
    "Comodato",
    "Arrendamiento de inmuebles",
    "Concesión",
    "Seguros",
    "Crédito",
    "Acuerdo Marco",
    "No Especificado",
    "Fiducia",
    "Acuerdo Marco de Precios",
    "No Definido",
    "Arrendamiento de muebles",
    "Servicios financieros",
    "Asociación Público Privada",
    "Operaciones de Crédito Público",
    "Agregación de Demanda",
    "Venta muebles",
    "Comisión",
    "Negocio fiduciario",
    "Venta inmuebles",
    "Acuerdo de cooperación",

]

@st.cache_resource
def load_engine():
    print("Loading Athena engine...")

    # Configuración de Athena
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    region = os.environ["AWS_REGION"]
    s3_staging_dir = quote_plus(os.environ["AWS_S3_STAGING_DIR"])  # Ej: s3://tu-bucket/athena-results/
    database = "secop"

    # Crear cadena de conexión para Athena
    connection_str = (
        f"awsathena+rest://{aws_access_key}:{aws_secret_key}@athena.{region}.amazonaws.com:443/"
        f"{database}?s3_staging_dir={s3_staging_dir}"
    )

    engine = create_engine(connection_str)
    return engine

engine = load_engine()

@st.cache_data
def query_athena(sql_query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        # Obtener nombres de columnas directamente desde el resultado
        column_names = result.keys()
        rows = result.fetchall()

    return pd.DataFrame(rows, columns=column_names)

@st.cache_resource
def load_nlp():

    print("Loading Spanish language model...")
    # Load the Spanish language model
    # IN TERMINAL: python -m spacy download es_core_news_sm
    nlp = spacy.load('es_core_news_sm')

    return nlp

# Load nlp
nlp = load_nlp()

def get_keywords(original_df: pd.DataFrame) -> list:

    # Input Spanish text
    input_text = " ".join(set([x.lower() if x else "" for x in original_df['objeto_contratar'].values.tolist()]))
    # Process the input text
    doc = nlp(input_text)

    # Extract keywords (lemmatized tokens)
    keywords = [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
    # Keep only keywords that appear more than once
    keywords = [keyword for keyword in keywords if keywords.count(keyword) > 1]

    # Remove duplicates
    keywords = list(set(keywords))

    # Keep only up until 20 keywords
    keywords = keywords[:20]

    return keywords


def preprocess_data(original_df: pd.DataFrame) -> pd.DataFrame:
        
    # Replace empty by NaN in valor_contrato and pago_por_mes

    original_df['valor_contrato_millones'] = original_df['valor_contrato_millones'].replace('', np.nan)
    original_df['pago_por_mes'] = original_df['pago_por_mes'].replace('', np.nan)

    # Convert valor_contrato and pago_por_mes to float
    original_df['valor_contrato_millones'] = original_df['valor_contrato_millones'].astype(float)
    original_df['pago_por_mes'] = original_df['pago_por_mes'].astype(float)

    return original_df