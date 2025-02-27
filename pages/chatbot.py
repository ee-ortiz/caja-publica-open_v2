import streamlit as st
import pandas as pd
import boto3
import json
import re
from utils import query_athena  # Función para conectar con Athena

##############################################
# Función para invocar Amazon Nova (AWS Bedrock)
##############################################
def call_bedrock(prompt: str) -> str:
    """
    Invoca Amazon Nova (modelo amazon.nova-lite-v1:0) para generar una respuesta.
    El payload se construye según el formato requerido.
    """
    client = boto3.client("bedrock-runtime", region_name="us-east-1")  # Ajusta la región si es necesario

    payload = {
        "inferenceConfig": {
            "max_new_tokens": 1000
        },
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        body=json.dumps(payload).encode("utf-8"),
        contentType="application/json",
        accept="application/json"
    )
    # Se utiliza response["body"] en minúsculas
    response_body = response["body"].read().decode("utf-8")
    result_json = json.loads(response_body)
    generated_text = (
        result_json.get("output", {})
                   .get("message", {})
                   .get("content", [{}])[0]
                   .get("text", "")
                   .strip()
    )
    return generated_text

##############################################
# Funciones auxiliares para el contexto
##############################################
def extraer_nit_de_texto(texto: str) -> str:
    """
    Intenta extraer un NIT (secuencia de dígitos) del texto.
    """
    match = re.search(r'\d{8,}', texto)
    return match.group(0) if match else ""

def obtener_contexto(pregunta: str, limite_general: int = 50, limite_especifico: int = 200) -> str:
    """
    Dependiendo de si la pregunta está enfocada a **empresa**, **entidad** o **persona**,
    se consulta la tabla correspondiente:
      - **Empresa:** se consulta la tabla personas_juridicas.
      - **Entidad:** se consulta la tabla personas_naturales filtrando por datos de entidad (nombre_entidad).
      - **Persona:** se consulta la tabla personas_naturales.
    Además, si el usuario encierra entre comillas un término específico, se usa ese valor para hacer la consulta.
    """
    pregunta_lower = pregunta.lower()
    contexto_list = []
    
    # Detecta términos entre comillas
    terminos_especificos = re.findall(r'"([^"]+)"', pregunta)
    
    if "empresa" in pregunta_lower or "nit" in pregunta_lower:
        # Caso para empresas
        if terminos_especificos:
            termino = terminos_especificos[0].strip()
            if termino.isdigit():
                query = f"SELECT * FROM personas_juridicas WHERE nit_empresa = '{termino}' LIMIT {limite_especifico}"
                df = query_athena(query)
                if not df.empty:
                    resumen = f"Resumen de la empresa (NIT: {termino}):\n" + df.head(20).to_string(index=False)
                    contexto_list.append(resumen)
            else:
                query = f"SELECT * FROM personas_juridicas WHERE lower(nombre_empresa) LIKE '%{termino.lower()}%' LIMIT {limite_especifico}"
                df = query_athena(query)
                if not df.empty:
                    resumen = f"Resumen de la empresa (nombre similar a: \"{termino}\"):\n" + df.head(20).to_string(index=False)
                    contexto_list.append(resumen)
        else:
            # Si no se especifica entre comillas, intenta extraer un NIT
            nit_extraido = extraer_nit_de_texto(pregunta)
            if nit_extraido:
                query = f"SELECT * FROM personas_juridicas WHERE nit_empresa = '{nit_extraido}' LIMIT {limite_especifico}"
                df = query_athena(query)
                if not df.empty:
                    resumen = f"Resumen de la empresa (NIT: {nit_extraido}):\n" + df.head(20).to_string(index=False)
                    contexto_list.append(resumen)
            else:
                palabras = [pal for pal in pregunta_lower.split() if len(pal) > 3]
                if palabras:
                    filtro = " OR ".join([f"lower(nombre_empresa) LIKE '%{pal}%'" for pal in palabras])
                    query = f"SELECT * FROM personas_juridicas WHERE {filtro} LIMIT {limite_especifico}"
                    df = query_athena(query)
                    if not df.empty:
                        resumen = f"Resumen de empresas que coinciden con la consulta:\n" + df.head(20).to_string(index=False)
                        contexto_list.append(resumen)
                        
    elif "entidad" in pregunta_lower:
        # Caso para entidades
        if terminos_especificos:
            termino = terminos_especificos[0].strip()
            query = f"SELECT * FROM personas_naturales WHERE lower(nombre_entidad) LIKE '%{termino.lower()}%' LIMIT {limite_especifico}"
            df = query_athena(query)
            if not df.empty:
                resumen = f"Resumen de la entidad (nombre similar a: \"{termino}\"):\n" + df.head(20).to_string(index=False)
                contexto_list.append(resumen)
        else:
            query = f"SELECT * FROM personas_naturales WHERE nit_entidad IS NOT NULL LIMIT {limite_especifico}"
            df = query_athena(query)
            if not df.empty:
                resumen = "Resumen de entidades (datos de personas naturales con entidad):\n" + df.head(20).to_string(index=False)
                contexto_list.append(resumen)
                
    elif "persona" in pregunta_lower:
        # Caso para personas
        if terminos_especificos:
            termino = terminos_especificos[0].strip()
            if termino.isdigit():
                query = f"SELECT * FROM personas_naturales WHERE documento_persona = '{termino}' LIMIT {limite_especifico}"
                df = query_athena(query)
                if not df.empty:
                    resumen = f"Resumen de la persona (documento: {termino}):\n" + df.head(20).to_string(index=False)
                    contexto_list.append(resumen)
            else:
                query = f"SELECT * FROM personas_naturales WHERE lower(nombre_persona) LIKE '%{termino.lower()}%' LIMIT {limite_especifico}"
                df = query_athena(query)
                if not df.empty:
                    resumen = f"Resumen de la persona (nombre similar a: \"{termino}\"):\n" + df.head(20).to_string(index=False)
                    contexto_list.append(resumen)
        else:
            query = f"SELECT * FROM personas_naturales LIMIT {limite_general}"
            df = query_athena(query)
            if not df.empty:
                resumen = "Resumen de datos generales de personas naturales:\n" + df.head(20).to_string(index=False)
                contexto_list.append(resumen)
    else:
        # Si no se especifica, se asume una consulta general de personas naturales
        query = f"SELECT * FROM personas_naturales LIMIT {limite_general}"
        df = query_athena(query)
        if not df.empty:
            resumen = "Resumen de datos generales de personas naturales:\n" + df.head(20).to_string(index=False)
            contexto_list.append(resumen)
    
    # Información adicional: datos de grupos (opcional)
    query_grupos = f"SELECT * FROM grupos LIMIT {limite_general}"
    df_grupos = query_athena(query_grupos)
    if not df_grupos.empty:
        resumen_grupos = "Resumen de datos generales de grupos:\n" + df_grupos.head(10).to_string(index=False)
        contexto_list.append(resumen_grupos)
    
    return "\n\n".join(contexto_list)

##############################################
# Construcción del prompt
##############################################
def construir_prompt(contexto: str, pregunta: str) -> str:
    """
    Construye el prompt para el modelo generativo. Se le indica al modelo:
      - Que utilice solo el contexto extraído.
      - Que genere un análisis transversal de los contratos, resaltando patrones clave, 
        tendencias y aspectos generales más relevantes.
      - Que extraiga información específica si es útil, pero evitando listar contratos de forma repetitiva.
      - Que omita frases genéricas y se enfoque en hallazgos concretos.
    """
    prompt = (
        "Utiliza la siguiente información extraída de la base de datos Athena para generar un análisis detallado y transversal "
        "sobre la empresa mencionada en la pregunta. En lugar de listar contratos individuales, identifica patrones, tendencias y "
        "aspectos generales más relevantes. Si es necesario, menciona datos específicos, pero solo si aportan valor al análisis general.\n\n"
        "Evita frases de cierre innecesarias y prioriza información relevante. Si no hay datos suficientes, responde 'No se encontró información relevante'.\n\n"
        
        f"Contexto:\n{contexto}\n\n"
        f"Pregunta: {pregunta}\n\n"
        "Análisis:"
    )
    return prompt

##############################################
# Chatbot en Streamlit
##############################################
def chatbot():
    
    col1, col2 = st.columns([1, 3])  # Primera columna más pequeña, segunda más grande

    with col1:
        st.image("assets/logo.png", width=175)
    
    st.title("Chatbot Inteligente: Consulta sobre los contratos")
    
    st.markdown(
        """
        **Reglas para las consultas:**
        - Especifica en tu pregunta el enfoque: **persona**, **empresa** o **entidad**.
        - Para consultas específicas, encierra el término exacto entre comillas.
            - Ejemplo para empresa: *"Consorcio XYZ"* o NIT: 12345678
            - Ejemplo para persona: *"Juan Pérez"* o documento: 10234567
            - Ejemplo para entidad: *"Ministerio de Salud"*
        - Describe tu consulta de forma clara.
        """
    )
    
    pregunta = st.text_input("Escribe tu pregunta sobre los datos:")
    
    if pregunta:
        st.write("Obteniendo contexto de Athena...")
        contexto = obtener_contexto(pregunta, limite_general=50, limite_especifico=75)
        # st.text_area("Contexto extraído (para depuración)", value=contexto, height=300)
        
        prompt = construir_prompt(contexto, pregunta)
        st.write("Generando respuesta ...")
        respuesta = call_bedrock(prompt)
        
        st.markdown("**Resumen de respuesta:**")
        st.write(respuesta)

if __name__ == "__main__":
    chatbot()
