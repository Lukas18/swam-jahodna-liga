"""Compatibility helpers routed through the versioned authoritative Store."""
import os
import hashlib
import json
import streamlit as st
from .storage import Store


@st.cache_resource(show_spinner=False)
def _cached_store(identity, _config):
    return Store(supabase=_config)


def get_store():
    try:
        cfg = st.secrets.to_dict()
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        cfg = {}
    config = {
        **cfg.get('supabase', {}),
        'url': os.environ.get('SUPABASE_URL') or cfg.get('SUPABASE_URL') or cfg.get('supabase', {}).get('url'),
        'key': os.environ.get('SUPABASE_KEY') or cfg.get('SUPABASE_KEY') or cfg.get('supabase', {}).get('key'),
        'model': os.environ.get('DISCGOLF_STORAGE_MODEL') or cfg.get('DISCGOLF_STORAGE_MODEL') or cfg.get('supabase', {}).get('model', 'json'),
    }
    config['document_id'] = os.environ.get('DISCGOLF_DOCUMENT_ID', config.get('document_id', 'main'))
    identity = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return _cached_store(identity, config)


def get_db():
    return get_store().db


def load_data():
    return get_store().load()[0]


def save_data(data, expected_version):
    """The caller must pass the version it loaded; blind upserts are prohibited."""
    get_store().save(data, expected_version)
    from .cache import clear_view_cache
    clear_view_cache()
