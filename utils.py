import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import spacy
from dotenv import load_dotenv
load_dotenv()
import os
import numpy as np

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
    print("Loading engine...")

    # POSTGRESQL CONFIG:
    host = os.environ["AWS_DATABASE_URL"]
    port = 5432
    user = os.environ["AWS_DATABASE_USER"]
    password = os.environ["AWS_DATABASE_PASSWORD"]

    # Create engine with fast_executemany=True
    engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/secop')

    print(engine)

    return engine

engine = load_engine()

@st.cache_data
def query_postgres(sql_query: str) -> pd.DataFrame:

    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = result.fetchall()

    # Get the column names
    column_names = [item[0] for item in result.context.cursor.description]

    # Create a dictionary with column names as keys and corresponding values from data rows
    parsed_data = [dict(zip(column_names, row)) for row in rows]

    # Convert to Pandas DataFrame
    parsed_data = pd.DataFrame(parsed_data)

    # Return the parsed data
    return parsed_data

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