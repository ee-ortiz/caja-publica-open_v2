import streamlit as st
import firebase_admin
from firebase_admin import firestore
from datetime import datetime

def main_feedback():
    """
    Crea un formulario de feedback y lo guarda en la base de datos (Firestore).
    """
    st.write("Por favor, déjanos tu feedback para mejorar la aplicación")

    form = st.form(key="feedback_form")
    profesion = form.text_input("Profesión")
    comentarios = form.text_area("Comentarios")
    uso = form.text_area("¿Qué uso le das a la aplicación?")
    nuevas_funcionalides = form.text_area("¿Qué nuevas funcionalidades te gustaría ver?")
    submit = form.form_submit_button("Enviar")

    if submit:
        db = firestore.client()
        doc_ref = db.collection("feedback").document()
        doc_ref.set({
            "profesion": profesion,
            "comentarios": comentarios,
            "uso": uso,
            "nuevas_funcionalides": nuevas_funcionalides,
            "fecha": datetime.now()
        })
        st.success("Feedback enviado")

if __name__ == "__main__":
    main_feedback()
