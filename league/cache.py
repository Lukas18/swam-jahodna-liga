"""Shared, bounded read cache. Saves and manual refresh invalidate immediately."""
import streamlit as st
from .handicaps import ALGORITHM, recalculate_handicaps
from .statistics import trend_observations


def _load(store):
    data, version = store.load()
    if data.get('handicap_run', {}).get('algorithm') != ALGORITHM:
        data = recalculate_handicaps(data)
    return data, version, trend_observations(data)


@st.cache_data(ttl=10, max_entries=8, show_spinner=False)
def _cached_view(identity, _store):
    return _load(_store)


def load_view_state(store):
    # Test/file adapters without a stable connection identity remain uncached.
    identity = getattr(store, 'cache_key', None)
    return _cached_view(identity, store) if identity is not None else _load(store)


def clear_view_cache():
    _cached_view.clear()
