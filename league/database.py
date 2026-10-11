import streamlit as st
from supabase import create_client


@st.cache_resource
def get_db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def load_data():
    db = get_db()

    response = (
        db.table("app_data")
        .select("content")
        .eq("id", "main")
        .single()
        .execute()
    )

    return response.data["content"]


def save_data(data):
    db = get_db()

    db.table("app_data").upsert({
        "id": "main",
        "content": data
    }).execute()