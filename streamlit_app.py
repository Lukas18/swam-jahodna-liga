"""Public league results with a single authenticated administrator."""
from copy import deepcopy
from datetime import date
from io import BytesIO
import hashlib
import hmac
import json
import os
import re
import time
import pandas as pd
import altair as alt
import streamlit as streamlit
from league.localization import LocalizedUI, translate
st = LocalizedUI(streamlit, lambda: admin())
from league.domain import (new_id, find, profile, validate_holes, save_player, add_round,
                           tournament_results, league_results, hole_stats, validate_data, resize_holes, whole_number,
                           tournament_entries, register_player, score_grid, save_score_grid, site_settings, home_standings, place_labels)
from league.presentation import category_styles
from league.search import matching_players
from league.handicaps import recalculate_handicaps
from league.statistics import selected_rounds, summary, hole_statistics, hole_heat_styles, scoring_trend, top_trend_players
from league.storage import Store, StorageError, encoded
from league.imports import read_export, preview_import

st.set_page_config(page_title='SWAM Jahodna liga', page_icon='🥏', layout='wide')
st.markdown('''<style>
.block-container {padding-top:2rem;max-width:1250px;}
h1,h2,h3 {letter-spacing:-.025em;}
[class*="st-key-leaderboard_"] {border:2px solid #DCCEAB;border-radius:12px;padding:4px 6px 8px;overflow-x:auto;}
.st-key-placement_points {max-width:240px;padding:4px 6px 8px;border:1px solid rgba(220,206,171,.35);border-radius:8px;}
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table {width:100%;border-collapse:collapse;}
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table td,
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table thead th {
    font-size:17px !important;line-height:1.5 !important;padding:10px 12px !important;
    height:48px !important;vertical-align:middle !important;white-space:normal;
}
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table td *,
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table th * {
    font-size:inherit !important;line-height:inherit !important;font-weight:inherit !important;
}
:is([class*="st-key-leaderboard_"], .st-key-placement_points) [data-testid="stMarkdownContainer"],
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table p {margin:0 !important;}
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table thead th:first-child,
:is([class*="st-key-leaderboard_"], .st-key-placement_points) table tbody th {display:none;}
[data-testid="stMetric"] {background:rgba(127,127,127,.08);border-radius:12px;padding:16px;}
</style>''', unsafe_allow_html=True)


def secrets():
    try:
        return st.secrets.to_dict()
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return {}


CONFIG = secrets()
try:
    from league.database import get_store
    STORE = get_store()
    from league.cache import load_view_state, clear_view_cache
    DATA, VERSION, TREND_OBSERVATIONS = load_view_state(STORE)
except (StorageError, OSError) as exc:
    st.error(str(exc))
    st.stop()


SETTINGS = site_settings(DATA)
# st.set_page_config(page_title=SETTINGS['site_title'])


def admin():
    expires = st.session_state.get('admin_expires', 0)
    return expires > time.time()


def current_theme():
    return 'light' if st.context.theme.type == 'light' else 'dark'


def persist(draft):
    if not admin():
        st.error('Sign in as administrator to save changes.')
        st.stop()
    try:
        STORE.save(draft, VERSION)
        clear_view_cache()
    except (ValueError, KeyError, StorageError, OSError) as exc:
        st.error(str(exc))
        return
    st.session_state['notice'] = 'Changes saved.'
    st.rerun()


def table(rows, key=None, sortable=False):
    if not rows:
        st.info('No results yet.')
        return
    df = pd.DataFrame(rows)
    if 'Place' in df:
        df['Place'] = place_labels(rows)
    hidden = ['player_id', 'Complete']
    cols = [c for c in ['Place', 'Player', 'Category', 'Points', 'Tournaments', 'Rounds'] if c in df]
    cols += [c for c in df if c not in cols + hidden]
    colors = category_styles(DATA['categories'], current_theme())
    display = df[cols].rename(columns=translate)
    styled = display.style.apply(lambda row: [colors.get(row[translate('Category')], 'background-color: #D8DED9; color: #17251F')] * len(row), axis=1)
    styled = styled.format({translate(c): '{:.0f}' for c in ['Points', 'HCP adjusted', 'Handicap', 'Current handicap', 'Stableford'] if c in df}, na_rep='—', escape='html')
    with st.container(key='leaderboard_' + (key or 'results')):
        if sortable:
            st.dataframe(styled, hide_index=True, width='stretch', row_height=48,
                         height=(len(display) + 1) * 48 + 8, key=key, column_config={translate(c): st.column_config.NumberColumn(format='%.0f') for c in ['Handicap', 'Current handicap', 'HCP adjusted', 'Stableford'] if c in df})
        else:
            st.table(styled)
    st.download_button('Download CSV', df[cols].to_csv(index=False).encode('utf-8'),
                       'results.csv', 'text/csv', key=(key or 'results') + '_csv')


def search_players(items, key):
    query = st.text_input('Search players', key=key, placeholder='Name or surname', help='Search ignores accents.')
    return matching_players(items, query, include_username=admin())


def choose(label, items, key, text=lambda x: x['name']):
    if label == 'Player':
        items = search_players(items, key + '_search')
    if not items:
        st.info('No players match this search.' if label == 'Player' else f'No {label.lower()} available yet.')
        return None
    if st.session_state.get(key) not in {x['id'] for x in items}:
        st.session_state.pop(key, None)
    selected = st.selectbox(label, [x['id'] for x in items], format_func=lambda value: text(next(x for x in items if x['id'] == value)), key=key)
    return next(x for x in items if x['id'] == selected)


def category_filter(key, categories=None):
    return st.selectbox('Category', ['All'] + (categories or DATA['categories']), key=key)


def statistics_category(key, categories=None, label='Statistics category'):
    language = st.session_state.get('language', 'sk')
    return st.selectbox(label, ['All'] + (categories or DATA['categories']), key=key,
                        format_func=lambda c: 'Celkovo' if c == 'All' and language == 'sk' else c)


def metric_picker(key, default='to_par'):
    # Keep ranking implementations for later, but currently expose only par-based results.
    st.session_state.pop(key, None)
    return 'to_par'


def navigate(page, selection_key, item_id):
    st.session_state['page'] = page
    st.session_state[selection_key] = item_id


def home():
    st.title('🥏 ' + SETTINGS['site_title'])
    st.caption('Fall Discgolf League SWAM Jahodna 2026')
    if SETTINGS['active_league_id']:
        st.subheader('Overall standings')
        metric = metric_picker('home_metric')
        standings = home_standings(DATA, SETTINGS['active_league_id'], metric)
        medals = {1: '🥇 ', 2: '🥈 ', 3: '🥉 '}
        for category in DATA['categories']:

            rows = [r for r in standings if r['Category'] == category]
            # print(rows)
            if rows:
                st.subheader(category)
                frame = pd.DataFrame([{'Place': label, 'Name': medals.get(r['Place'], '') + r['Player'],
                                       'Total points': r['Points'], 'Tournaments attended': r['Tournaments'], 'Current handicap': r['Current handicap']} for r, label in zip(rows, place_labels(rows))])
                frame = frame.rename(columns=translate)
                styled = frame.style.set_properties(**{'color': '#3B2119'}).hide(axis="index")
                styled = styled.apply(lambda row: [
                    'background-color: #DED9C7' if row.name % 2 == 0 else 'background-color: #EAE4D0'
                ] * len(row), axis=1)
                styled = styled.set_properties(subset=[translate(c) for c in ['Place', 'Name', 'Total points', 'Tournaments attended']], **{'color': '#16492F', 'font-weight': 'bold'})
                with st.container(key='leaderboard_home_' + category):
                    st.table(styled.format({translate('Current handicap'): '{:.0f}'}, na_rep='—', escape='html'))
        if not standings:
            st.info('Standings will appear after the first recorded round.')
    st.subheader('Recent tournaments')
    if DATA['tournaments']:
        for t in sorted(DATA['tournaments'], key=lambda x: x['date'], reverse=True)[:8]:
            layout = find(DATA, 'layouts', t['layout_id'])
            course = find(DATA, 'courses', layout['course_id'])
            with st.container(border=True):
                st.button(t['name'], key='home_tournament_' + t['id'], width='stretch',
                          on_click=navigate, args=('Tournaments', 'tournament_select', t['id']))
                st.caption(f"{t['date']} · {course['name']} / {layout['name']} · {t['num_rounds']} round(s)")
                results = tournament_results(DATA, t['id'], complete_only=True)
                st.write(f"{len(results)} players with complete scores")

    else:
        st.info('The admin can create the first league and tournament.')
    st.subheader('Leagues')
    for league in DATA['leagues']:
        with st.container(border=True):
            st.button(league['name'], key='home_league_' + league['id'], width='stretch',
                      on_click=navigate, args=('Leagues', 'league_select', league['id']))
            count = sum(t['league_id'] == league['id'] for t in DATA['tournaments'])
            st.caption(f'{count} tournament(s)')


def league_editor(league=None):
    key = league['id'] if league else 'new'
    with st.expander('Edit league & points' if league else 'Create league'):
        places = st.number_input('Number of places awarded points', min_value=1, max_value=100,
                                 value=len(league['points']) if league else 10, key=f'places_{key}')
        initial = [whole_number(p) for p in league['points']] if league else [25, 20, 16, 13, 11, 10, 9, 8, 7, 6]
        with st.form(f'league_{key}'):
            name = st.text_input('League name', value=league['name'] if league else '')
            scope = st.selectbox('Award tournament points', ['Within each category', 'Across all players'],
                                  index=1 if league and league['points_scope'] == 'overall' else 0)
            ties = st.selectbox('Ties', ['Share occupied-place points', 'Same points for the tied place'],
                                index=1 if league and league['tie_mode'] == 'same' else 0)
            points = st.data_editor(pd.DataFrame({'Place': range(1, places+1),
                                                 'Points': [initial[i] if i < len(initial) else 0 for i in range(places)]}),
                                    disabled=['Place'], hide_index=True, width='stretch', key=f'points_{key}_{places}',
                                    column_config={'Points': st.column_config.NumberColumn(min_value=0, step=1, format='%d', required=True)})
            st.caption('Unlisted places receive zero points. Only completed tournaments award points. Editing rules recalculates standings.')
            if st.form_submit_button('Save league'):
                if not name.strip() or points['Points'].isna().any() or any(float(v) != int(v) for v in points['Points'].dropna()):
                    st.error('Enter a name and a whole-number points value for every place.')
                else:
                    draft = deepcopy(DATA)
                    obj = {'id': key if league else new_id(), 'name': name.strip(), 'points': points['Points'].astype(int).tolist(),
                           'points_scope': 'category' if scope.startswith('Within') else 'overall',
                           'tie_mode': 'shared' if ties.startswith('Share') else 'same'}
                    draft['leagues'] = [x for x in draft['leagues'] if x['id'] != obj['id']] + [obj]
                    persist(draft)


def leagues():
    st.title('League leaderboard')
    league = choose('League', DATA['leagues'], 'league_select')
    if not league:
        return
    cat = category_filter('league_cat')
    metric = metric_picker('league_rank')
    table(league_results(DATA, league['id'], cat, metric), 'league_table', sortable=True)
    st.caption('Placement points')
    points = pd.DataFrame({translate('Place'): list(range(1, len(league['points']) + 1)),
                           translate('Points'): [whole_number(p) for p in league['points']]})
    with st.container(key='placement_points'):
        st.table(points)
    st.subheader('League tournaments')
    ts = [t for t in DATA['tournaments'] if t['league_id'] == league['id']]
    for t in sorted(ts, key=lambda x: x['date']):
        st.button(f"{t['date']} · {t['name']} · {t['num_rounds']} round(s)",
                  key='league_tournament_' + t['id'], width='stretch',
                  on_click=navigate, args=('Tournaments', 'tournament_select', t['id']))


def players():
    st.title('Players')
    matches = search_players(DATA['players'], 'admin_player_search')
    rows = []
    for p in sorted(matches, key=lambda p: (p['last_name'], p['first_name'])):
        row = {'Player': f"{p['first_name']} {p['last_name']}", 'Category': p['category'], 'Current handicap': None if p.get('handicap_pending') else p['handicap']}
        if admin():
            row['uDisc username'] = p['udisc']
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch', column_config={'Current handicap': st.column_config.NumberColumn(format='%.0f')})
    if not admin():
        return
    options = ['new'] + [p['id'] for p in matches]
    pid = st.selectbox('Edit player', options, format_func=lambda x: 'Add new player' if x == 'new' else
                       f"{find(DATA, 'players', x)['first_name']} {find(DATA, 'players', x)['last_name']}")
    p = find(DATA, 'players', pid) if pid != 'new' else None
    with st.form(f'player_{pid}'):
        c1, c2 = st.columns(2)
        first = c1.text_input('First name', value=p['first_name'] if p else '')
        last = c2.text_input('Last name', value=p['last_name'] if p else '', help='Optional for players using a single name.')
        cat = st.selectbox('Default category', DATA['categories'], index=DATA['categories'].index(p['category']) if p else 0)
        hcp = st.number_input('Current handicap', value=int(p['handicap']) if p else 0, step=1, disabled=True)
        udisc = st.text_input('uDisc username', value=p['udisc'] if p else '', help='Used to match imported results. Matching ignores case and surrounding spaces.')
        st.caption('Handicaps are calculated automatically from the last 10 completed tournaments.')
        if st.form_submit_button('Save player'):
            draft = deepcopy(DATA)
            try:
                save_player(draft, p['id'] if p else None, first, last, cat, hcp, udisc)
                persist(draft)
            except ValueError as exc:
                st.error(str(exc))
    if p:
        used = any(r['player_id'] == p['id'] for r in DATA['rounds']) or any(e['player_id'] == p['id'] for e in DATA.get('registrations', []))
        if st.button('Delete player', disabled=used, help='Players registered in tournaments or with scores cannot be deleted.'):
            draft = deepcopy(DATA)
            draft['players'] = [x for x in draft['players'] if x['id'] != p['id']]
            persist(draft)


def layout_editor(course, layout=None):
    key = layout['id'] if layout else 'new_' + course['id']
    with st.expander('Edit layout & category holes' if layout else 'Create layout'):
        selected = st.selectbox('Hole configuration', ['default'] + DATA['categories'],
                                format_func=lambda x: 'Default — all categories unless overridden' if x == 'default' else x,
                                key=f'profile_{key}')
        initial = profile(layout, selected) if layout else [{'number': i, 'par': 3, 'length': 0} for i in range(1, 19)]
        count = st.number_input('Number of holes', min_value=1, max_value=99, value=len(initial),
                                key=f'hole_count_{key}_{selected}')
        initial = resize_holes(initial, count)
        st.caption('Choose the hole count first, then edit pars and lengths. Each category can have its own count. Lengths are in metres; 0 means unknown.')
        with st.form(f'layout_{key}_{selected}'):
            name = st.text_input('Layout name', value=layout['name'] if layout else '')
            holes = st.data_editor(pd.DataFrame(initial), num_rows='fixed', hide_index=True, width='stretch',
                                   key=f'holes_{key}_{selected}_{count}', column_config={
                                       'number': st.column_config.NumberColumn('Hole', min_value=1, max_value=99, step=1, required=True),
                                       'par': st.column_config.NumberColumn('Par', min_value=1, max_value=10, step=1, required=True),
                                       'length': st.column_config.NumberColumn('Length (m)', min_value=0, step=1, format='%.0f', required=True)})
            if st.form_submit_button('Save hole configuration'):
                try:
                    clean = validate_holes(holes.to_dict('records'))
                    if not name.strip():
                        raise ValueError('Layout name is required.')
                    draft = deepcopy(DATA)
                    obj = deepcopy(layout) if layout else {'id': new_id(), 'course_id': course['id'], 'profiles': {
                        'default': deepcopy(clean) if selected == 'default' else [{'number': i, 'par': 3, 'length': 0} for i in range(1, 19)]}}
                    obj['name'] = name.strip()
                    obj['profiles'][selected] = clean
                    draft['layouts'] = [x for x in draft['layouts'] if x['id'] != obj['id']] + [obj]
                    persist(draft)
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
        if layout and selected != 'default' and selected in layout['profiles']:
            if st.button('Remove override and use default holes', key=f'delete_profile_{key}_{selected}'):
                draft = deepcopy(DATA)
                del find(draft, 'layouts', layout['id'])['profiles'][selected]
                persist(draft)


def courses():
    st.title('Courses → Layouts')
    if admin():
        with st.expander('Create course'):
            with st.form('new_course'):
                name = st.text_input('Course name')
                desc = st.text_area('Description')
                if st.form_submit_button('Create course'):
                    if name.strip():
                        draft = deepcopy(DATA)
                        draft['courses'].append({'id': new_id(), 'name': name.strip(), 'description': desc})
                        persist(draft)
                    else:
                        st.error('Enter a course name.')
    course = choose('Course', DATA['courses'], 'course_select')
    if not course:
        return
    st.write(course['description'])
    if admin():
        with st.expander('Edit course'):
            with st.form('course_edit_' + course['id']):
                name = st.text_input('Course name', value=course['name'])
                desc = st.text_area('Description', value=course['description'])
                if st.form_submit_button('Save course'):
                    if name.strip():
                        draft = deepcopy(DATA)
                        find(draft, 'courses', course['id']).update(name=name.strip(), description=desc)
                        persist(draft)
                    else:
                        st.error('Enter a course name.')
        layout_editor(course)
    layouts = [x for x in DATA['layouts'] if x['course_id'] == course['id']]
    layout = choose('Layout', layouts, 'layout_select_' + course['id'])
    if not layout:
        return
    cat = statistics_category('layout_cat_' + layout['id'], label='Category')
    holes = profile(layout, cat)
    c1, c2, c3 = st.columns(3)
    c1.metric('Holes', len(holes))
    c2.metric('Par', sum(h['par'] for h in holes))
    c3.metric('Length (m)', f"{sum(h['length'] for h in holes):.0f}")
    st.dataframe(pd.DataFrame(holes).rename(columns={'number': 'Hole', 'par': 'Par', 'length': 'Length (m)'}), hide_index=True, width='stretch',
                 column_config={'Length (m)': st.column_config.NumberColumn(format='%.0f')})
    st.subheader('Layout statistics')
    rounds = selected_rounds(DATA, layout_id=layout['id'], category=cat)
    if rounds:
        c1, c2, c3 = st.columns(3)
        c1.metric('Recorded rounds', len(rounds))
        c2.metric('Average throws', f"{sum(r['total'] for r in rounds)/len(rounds):.2f}")
        c3.metric('Average +/− par', f"{sum(r['total']-r['par'] for r in rounds)/len(rounds):+.2f}")
    stats = hole_statistics(DATA, rounds, combine_categories=cat == 'All')
    if stats:
        frame = statistics_frame(stats)
        st.dataframe(frame.style.apply(hole_heat_styles, axis=1, theme=current_theme()), hide_index=True, width='stretch', column_config={
            **{c: st.column_config.NumberColumn(format='%.2f') for c in frame if c.startswith('Average')},
            **{c: st.column_config.NumberColumn(format='%.0f') for c in frame if c.endswith(' %')},
            'Par': st.column_config.NumberColumn(format='%.0f'),
            'Length (m)': st.column_config.NumberColumn(format='%.0f')})
        st.download_button('Download hole statistics', frame.to_csv(index=False), 'hole_statistics.csv', 'text/csv')
    else:
        st.info('No hole-by-hole scores recorded for this layout and category yet.')
    if admin():
        layout_editor(course, layout)


def tournament_editor(t=None):
    key = t['id'] if t else 'new'
    if not DATA['leagues'] or not DATA['layouts']:
        st.info('Create a league and a course layout before creating a tournament.')
        return
    locked = bool(t and tournament_entries(DATA, t['id']))
    with st.expander('Edit tournament' if t else 'Create tournament'):
        with st.form('tournament_' + key):
            name = st.text_input('Tournament name', value=t['name'] if t else '')
            day = st.date_input('Date', value=date.fromisoformat(t['date']) if t else date.today())
            event_order = st.number_input('Order on the same date', min_value=0, value=int(t.get('event_order', 0)) if t else 0, step=1, help='Use different order numbers when a player plays two tournaments on the same date.')
            league_ids = [x['id'] for x in DATA['leagues']]
            lid = st.selectbox('League', league_ids, index=league_ids.index(t['league_id']) if t else 0,
                               format_func=lambda x: find(DATA, 'leagues', x)['name'])
            layout_ids = [x['id'] for x in DATA['layouts']]
            layout_id = st.selectbox('Course / layout', layout_ids, index=layout_ids.index(t['layout_id']) if t else 0,
                                     format_func=lambda x: f"{find(DATA, 'courses', find(DATA, 'layouts', x)['course_id'])['name']} / {find(DATA, 'layouts', x)['name']}", disabled=locked)
            rounds = st.number_input('Rounds', min_value=1, max_value=20, value=t['num_rounds'] if t else 1, disabled=locked)
            cats = st.multiselect('Categories', DATA['categories'], default=t['categories'] if t else DATA['categories'], disabled=locked)
            if locked:
                st.caption('Layout, rounds and categories are locked while this tournament has registered players or scores.')
            if st.form_submit_button('Save tournament'):
                if not name.strip() or not cats:
                    st.error('Enter a name and select at least one category.')
                else:
                    draft = deepcopy(DATA)
                    obj = {'id': t['id'] if t else new_id(), 'name': name.strip(), 'date': day.isoformat(),
                           'league_id': lid, 'layout_id': layout_id, 'num_rounds': rounds, 'categories': cats, 'event_order': event_order}
                    draft['tournaments'] = [x for x in draft['tournaments'] if x['id'] != obj['id']] + [obj]
                    persist(draft)


def tournament_registration(t):
    st.subheader('Tournament players')
    entries = tournament_entries(DATA, t['id'])
    rows = []
    for e in entries:
        p = find(DATA, 'players', e['player_id'])
        rows.append({'Player': f"{p['first_name']} {p['last_name']}", 'Category': e['category'], 'Handicap': None if e.get('handicap_pending') else e['handicap']})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch', column_config={'Handicap': st.column_config.NumberColumn(format='%.0f')})
    enrolled = {e['player_id'] for e in entries}
    available = [p for p in DATA['players'] if p['id'] not in enrolled]
    if available:
        matches = search_players(available, 'register_player_search_' + t['id'])
        selected_ids = set(st.session_state.get('register_players_' + t['id'], []))
        available = [p for p in available if p in matches or p['id'] in selected_ids]
        selected = st.multiselect('Players to add', [p['id'] for p in available],
                                 format_func=lambda pid: f"{find(DATA, 'players', pid)['first_name']} {find(DATA, 'players', pid)['last_name']}",
                                 key='register_players_' + t['id'])
        category = st.selectbox('Registration category', ['Player default'] + t['categories'], key='register_category_' + t['id'])
        st.caption('Use each player’s default category and handicap, or choose a category override for this selection.')
        if st.button('Add selected players', disabled=not selected, key='register_' + t['id']):
            draft = deepcopy(DATA)
            try:
                for pid in selected:
                    register_player(draft, t['id'], pid, None if category == 'Player default' else category)
                persist(draft)
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.caption('All players are registered. Add more players under Admin → Players.')
    if entries:
        with st.expander('Edit or remove a tournament registration'):
            candidates = [find(DATA, 'players', e['player_id']) for e in entries]
            player = choose('Player', candidates, 'edit_registration_' + t['id'], lambda p: f"{p['first_name']} {p['last_name']}")
            if not player:
                return
            pid = player['id']
            entry = next(e for e in entries if e['player_id'] == pid)
            scored = any(r['tournament_id'] == t['id'] and r['player_id'] == pid for r in DATA['rounds'])
            with st.form('registration_edit_' + t['id'] + '_' + pid):
                cat = st.selectbox('Tournament category', t['categories'], index=t['categories'].index(entry['category']), disabled=scored)
                hcp = st.number_input('Tournament handicap', value=int(entry['handicap']), step=1, disabled=True)
                if st.form_submit_button('Save registration', disabled=scored):
                    draft = deepcopy(DATA)
                    register_player(draft, t['id'], pid, cat, hcp)
                    persist(draft)
            if st.button('Remove registration', disabled=scored, key='remove_registration_' + t['id']):
                draft = deepcopy(DATA)
                draft['registrations'] = [e for e in draft.get('registrations', []) if not (e['tournament_id'] == t['id'] and e['player_id'] == pid)]
                persist(draft)
            st.caption('Players with scores retain their registration. Remove their recorded rounds first to change category, handicap or registration.')


def manual_scores(t):
    st.subheader('Enter scores')
    if not tournament_entries(DATA, t['id']):
        st.info('Add players to this tournament before entering scores.')
        return
    number = st.number_input('Round number', min_value=1, max_value=t['num_rounds'], value=1, key='score_round_' + t['id'])
    st.caption('Players are rows; holes are columns. Tick Save for rows to record. Unplayed scores stay blank. Saving a recorded row replaces that round. Tables are separated by category so junior hole counts stay correct.')
    for cat in t['categories']:
        rows, snapshots = score_grid(DATA, t['id'], number, cat)
        if not rows:
            continue
        st.markdown(f'**{cat}**')
        frame = pd.DataFrame(rows)
        hole_cols = sorted({c for c in frame if re.fullmatch(r'H[0-9]+', c)}, key=lambda c: int(c[1:]))
        for c in hole_cols:
            frame[c] = pd.array(frame[c], dtype='Int64')
        frame = frame[['player_id', 'Save', 'Player', 'Handicap', 'Status'] + hole_cols]
        signature = hashlib.sha256(json.dumps(snapshots, sort_keys=True).encode()).hexdigest()[:12]
        configs = {'player_id': None, 'Save': st.column_config.CheckboxColumn('Save', default=False),
                   'Player': st.column_config.TextColumn('Player', pinned=True)}
        configs.update({c: st.column_config.NumberColumn(c, min_value=1, max_value=100, step=1, format='%d') for c in hole_cols})
        with st.form(f"score_grid_{t['id']}_{number}_{cat}"):
            scores = st.data_editor(frame, hide_index=True, width='stretch',
                                    disabled=['player_id', 'Player', 'Handicap', 'Status'],
                                    column_config=configs, key=f"grid_{t['id']}_{number}_{cat}_{signature}")
            if st.form_submit_button(f'Save {cat} scores'):
                try:
                    persist(save_score_grid(DATA, t['id'], number, cat, scores.to_dict('records')))
                except ValueError as exc:
                    st.error(str(exc))
        pars = {tuple((h['number'], h['par']) for h in hs) for hs in snapshots.values()}
        for par_list in sorted(pars):
            st.caption('Par: ' + ' · '.join(f'H{n}: {par}' for n, par in par_list))
    recorded = [r for r in DATA['rounds'] if r['tournament_id'] == t['id'] and r['round_number'] == number]
    if recorded:
        with st.expander('Remove a recorded round'):
            rid = st.selectbox('Round to remove', [r['id'] for r in recorded],
                               format_func=lambda rid: f"{find(DATA, 'players', next(r['player_id'] for r in recorded if r['id'] == rid))['first_name']} {find(DATA, 'players', next(r['player_id'] for r in recorded if r['id'] == rid))['last_name']}",
                               key='delete_round_' + t['id'])
            confirmed = st.checkbox('Confirm removal of this round', key='delete_confirm_' + rid)
            if st.button('Remove recorded round', disabled=not confirmed):
                draft = deepcopy(DATA)
                draft['rounds'] = [r for r in draft['rounds'] if r['id'] != rid]
                persist(draft)


def import_scores(t):
    st.subheader('Import uDisc results')
    st.caption('Excel .xlsx or CSV: one player per row, optionally with a round column. Match by uDisc username, never by display name. Add unknown usernames in Players first.')
    uploaded = st.file_uploader('uDisc export', type=['xlsx', 'csv'], key='upload_' + t['id'])
    if not uploaded:
        return
    try:
        sheet = 0
        if uploaded.name.lower().endswith('.xlsx'):
            names = pd.ExcelFile(BytesIO(uploaded.getvalue()), engine='openpyxl').sheet_names
            sheet = st.selectbox('Worksheet', names)
        header_row = st.number_input('Header row (1-based)', min_value=1, max_value=100, value=1)
        frame = read_export(uploaded.getvalue(), uploaded.name, sheet, header_row)
    except Exception as exc:
        st.error(f'Could not read export: {exc}')
        return
    st.dataframe(frame.head(20), hide_index=True, width='stretch')
    if frame.empty:
        st.info('No rows in this worksheet.')
        return
    cols = list(frame.columns)
    prefix = f"map_{t['id']}_{hashlib.sha256(uploaded.getvalue()).hexdigest()[:8]}_{sheet}_{header_row}"
    layout_id = st.selectbox('Layout used for these results', [None] + [l['id'] for l in DATA['layouts']],
                            format_func=lambda lid: 'Choose a layout' if lid is None else
                            f"{find(DATA, 'courses', find(DATA, 'layouts', lid)['course_id'])['name']} / {find(DATA, 'layouts', lid)['name']}",
                            key=prefix + 'layout')
    st.caption('Scores relative to par are calculated from the selected layout and its category holes. Spreadsheet relative scores are ignored. The layout is saved with the tournament when you confirm the import.')
    if layout_id is None:
        st.info('Choose a layout to preview the import.')
        return
    layout = find(DATA, 'layouts', layout_id)
    if layout_id != t['layout_id'] and any(r['tournament_id'] == t['id'] for r in DATA['rounds']):
        st.error('A tournament with recorded scores must keep its existing layout.')
        return
    def column(label, required=False, aliases=()):
        options = cols if required else ['(not mapped)'] + cols
        matches = [i for i, x in enumerate(options) if x.casefold() in aliases]
        value = st.selectbox(label, options, index=matches[0] if matches else 0, key=prefix + label)
        return None if value == '(not mapped)' else value
    mapping = {'username': column('uDisc username column', True, ('username', 'udisc username', 'udisc', 'user name')),
               'category': column('Category column', aliases=('category', 'division')),
               'handicap': column('Handicap column', aliases=('handicap', 'hcp')),
               'round': column('Round column', aliases=('round', 'round number'))}
    default_cat = st.selectbox('Category when not mapped', ['Player default'] + t['categories'], key=prefix + 'fallback')
    round_no = st.number_input('Round when not mapped', min_value=1, max_value=t['num_rounds'], value=1)
    mode = st.radio('Import detail', ['Hole-by-hole scores', 'Totals only'], horizontal=True)
    mapping['total'] = column('Absolute total throws column', required=mode == 'Totals only', aliases=('round_total_score', 'total throws', 'throws', 'total strokes', 'total'))
    st.caption('Map actual throw counts, not scores relative to par. Optional total checks that hole scores add up. Totals-only imports do not generate hole statistics.')
    if mode == 'Hole-by-hole scores':
        numbers = sorted({h['number'] for cat in t['categories'] for h in profile(layout, cat)})
        mapping['holes'] = {}
        with st.expander('Map hole score columns', expanded=True):
            for n in numbers:
                mapping['holes'][n] = column(f'Hole {n}', aliases=(f'hole_{n}', str(n), f'h{n}', f'hole {n}', f'hole{n}', f'hole {n} score'))
        mapped = [v for v in mapping['holes'].values() if v]
        if len(mapped) != len(set(mapped)):
            st.error('Each hole needs a different score column.')
            return
    draft, preview, errors = preview_import(DATA, t['id'], frame, mapping, round_no,
                                            None if default_cat == 'Player default' else default_cat, layout_id=layout_id)
    st.subheader('Import preview')
    if preview:
        st.dataframe(pd.DataFrame(preview), hide_index=True, width='stretch')
    for message in errors:
        st.error(message)
    replacements = any(row['Action'] == 'Replace' for row in preview)
    replace_ok = st.checkbox('Allow replacement of the existing rounds shown above', key=prefix + 'replace') if replacements else True
    if st.button('Confirm import', disabled=bool(errors) or not preview or not replace_ok, type='primary'):
        persist(draft)


def tournaments():
    st.title('Tournaments')
    t = choose('Tournament', sorted(DATA['tournaments'], key=lambda x: x['date'], reverse=True), 'tournament_select',
                lambda x: f"{x['date']} · {x['name']}")
    if not t:
        return
    layout = find(DATA, 'layouts', t['layout_id'])
    st.caption(f"{find(DATA, 'leagues', t['league_id'])['name']} · {find(DATA, 'courses', layout['course_id'])['name']} / {layout['name']}")
    cat = category_filter('tournament_cat', t['categories'])
    metric = metric_picker('tournament_metric')
    st.caption(f"{len(tournament_entries(DATA, t['id']))} registered players")
    complete = st.checkbox('Completed players only', value=True)
    table(tournament_results(DATA, t['id'], cat, metric, complete), 'tournament_table')
    with st.expander('Round scorecards'):
        records = sorted([r for r in DATA['rounds'] if r['tournament_id'] == t['id'] and (cat == 'All' or r['category'] == cat)],
                         key=lambda r: (r['player_id'], r['round_number']))
        for r in records:
            p = find(DATA, 'players', r['player_id'])
            st.markdown(f"**{p['first_name']} {p['last_name']} · {r['category']} · Round {r['round_number']} · {r['total']} throws ({r['total']-r['par']:+} par)**")
            if r['holes']:
                st.dataframe(pd.DataFrame(r['holes']).rename(columns={'number': 'Hole', 'par': 'Par', 'length': 'Length (m)', 'throws': 'Throws'}), hide_index=True, width='stretch',
                             column_config={'Length (m)': st.column_config.NumberColumn(format='%.0f')})
            else:
                st.caption('Totals-only result — hole scores unavailable.')

    st.subheader('Tournament statistics')
    stats_cat = statistics_category('tournament_stats_category_' + t['id'], t['categories'])
    show_statistics(selected_rounds(DATA, tournament_id=t['id'], layout_id=t['layout_id'], category=stats_cat), 'tournament_stats', stats_cat == 'All')


def statistics_frame(rows):
    """Keep full outcome calculations, but show only the requested statistics."""
    frame = pd.DataFrame(rows).drop(columns=['Course', 'Ace %', 'Albatross or better %'], errors='ignore')
    if 'Par' in frame:
        frame['Par'] = frame['Par'].map(whole_number).astype(int)
    for column in frame:
        if column.startswith('Average'):
            frame[column] = frame[column].round(2)
        elif column.endswith(' %'):
            frame[column] = frame[column].map(whole_number).astype(int)
    if 'Category' in frame and st.session_state.get('language', 'sk') == 'sk':
        frame['Category'] = frame['Category'].replace({'All': 'Celkovo'})
    return frame


def show_statistics(rounds, key, combine_categories=False):
    totals = summary(rounds)
    cols = st.columns(4)
    for col, label in zip(cols, ['Recorded rounds', 'Players', 'Tournaments', 'Hole scores']):
        col.metric(label, totals[label])
    if not rounds:
        st.info('No recorded results match these filters.')
        return
    c1, c2 = st.columns(2)
    c1.metric('Average throws per round', f"{totals['Average throws']:.2f}")
    c2.metric('Average +/− par per round', f"{totals['Average +/− par']:+.2f}")
    st.subheader('Hole statistics')
    stats = hole_statistics(DATA, rounds, combine_categories=combine_categories)
    if stats:
        frame = statistics_frame(stats)
        st.dataframe(frame.style.apply(hole_heat_styles, axis=1, theme=current_theme()), hide_index=True, width='stretch', key=key + '_holes', column_config={
            **{c: st.column_config.NumberColumn(format='%.2f') for c in frame if c.startswith('Average')},
            **{c: st.column_config.NumberColumn(format='%.0f') for c in frame if c.endswith(' %')},
            'Par': st.column_config.NumberColumn(format='%.0f'),
            'Length (m)': st.column_config.NumberColumn(format='%.0f')})
        st.download_button('Download hole statistics', frame.to_csv(index=False), 'hole_statistics.csv', 'text/csv', key=key + '_holes_csv')
    else:
        st.info('These results have totals only. Import or enter hole scores to see hole averages and outcome percentages.')


def draw_scoring_trend(rows, key):
    if not rows:
        st.info('No recorded results match these filters.')
        return
    frame = pd.DataFrame(rows)
    frame['Date'] = pd.to_datetime(frame['Date'])
    # A trend needs distinct dates. Multiple events on the same day contribute
    # their mean to the fit, without changing event statistics or rankings.
    frame = frame.groupby('Date', as_index=False)['Average +/− par'].mean()
    if len(frame) < 2:
        st.info('At least two tournament dates are needed to show a trend.')
        return
    base = alt.Chart(frame).transform_calculate(Time='toNumber(toDate(datum.Date))')
    if len(frame) < 5:
        fit = base.transform_regression('Time', 'Average +/− par', as_=['Time', 'Trend'])
    else:
        fit = base.transform_loess('Time', 'Average +/− par', bandwidth=0.6, as_=['Time', 'Trend'])
    line = fit.mark_line(
        color='#DCCEAB' if current_theme() == 'dark' else '#245E42',
        strokeWidth=3, interpolate='basis'
    ).encode(
        x=alt.X('Time:T', title=translate('Date'), axis=alt.Axis(format='%d.%m.%Y', tickCount=6, labelFlush=True, labelOverlap='greedy')),
        y=alt.Y('Trend:Q', title=translate('Average +/− par per round'), scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip('Time:T', title=translate('Date'), format='%d.%m.%Y'),
                 alt.Tooltip('Trend:Q', title=translate('Estimated score relative to par'), format='+.2f')])
    zero = alt.Chart(pd.DataFrame({'Par': [0]})).mark_rule(color='#888888', strokeDash=[4,4]).encode(y='Par:Q')
    # Reserve space inside the responsive chart for titles and edge tick labels.
    chart = (zero + line).properties(
        height=350, padding={'left': 18, 'right': 28, 'top': 16, 'bottom': 24},
        autosize=alt.AutoSizeParams(type='fit', contains='padding', resize=True)
    ).configure_axis(labelPadding=8, titlePadding=14, titleLimit=0)
    st.altair_chart(chart, use_container_width=True, key=key)


def trend_controls(rounds, layout, tournament_id=None, category='All'):
    st.subheader('Scoring trend')
    course = find(DATA, 'courses', layout['course_id'])
    trend_scope = st.radio('Trend scope', ['Selected layout', 'Whole course'], horizontal=True, key='trend_scope')
    if 'trend_category' not in st.session_state:
        st.session_state['trend_category'] = category
    category = statistics_category('trend_category', label='Trend category')
    rounds = selected_rounds({**DATA, 'rounds': TREND_OBSERVATIONS},
        tournament_id=tournament_id, course_id=course['id'],
        layout_id=None if trend_scope == 'Whole course' else layout['id'], category=category)
    context = course['name'] if trend_scope == 'Whole course' else f"{course['name']} / {layout['name']}"
    st.write(context + ' · ' + translate(category))
    mode = st.radio('Players in trend', ['All players', 'Specific player', 'Top 3', 'Top 5'], horizontal=True, key='trend_mode', help='Top players have the lowest average score relative to par in the selected filters. The same players are used throughout the trend.')
    player_ids = None
    if mode == 'Specific player':
        ids = {r['player_id'] for r in rounds}
        choices = sorted([p for p in DATA['players'] if p['id'] in ids], key=lambda p: (p['last_name'], p['first_name']))
        player = choose('Player', choices, 'trend_player', lambda p: f"{p['first_name']} {p['last_name']}".strip())
        if not player:
            return
        player_ids = [player['id']]
    elif mode in ['Top 3', 'Top 5']:
        player_ids = top_trend_players(DATA, rounds, 3 if mode == 'Top 3' else 5)
        names = [f"{find(DATA, 'players', pid)['first_name']} {find(DATA, 'players', pid)['last_name']}".strip() for pid in player_ids]
        st.write(translate('Players included') + ': ' + ', '.join(names))
    draw_scoring_trend(scoring_trend(DATA, rounds, player_ids), 'scoring_trend')


def statistics_page():
    st.title('Statistics')
    scope = st.radio('Results scope', ['All time', 'Tournament'], horizontal=True, key='stats_scope')
    tournament_id = None
    if scope == 'Tournament':
        t = choose('Tournament', sorted(DATA['tournaments'], key=lambda x: x['date'], reverse=True), 'stats_tournament',
                   lambda x: f"{x['date']} · {x['name']}")
        if not t:
            return
        tournament_id = t['id']
    layouts = [l for l in DATA['layouts'] if tournament_id is None or l['id'] == t['layout_id']]
    courses = [c for c in DATA['courses'] if any(l['course_id'] == c['id'] for l in layouts)]
    if len(courses) > 1:
        course = choose('Course', courses, 'stats_course')
        if not course:
            return
        layouts = [l for l in layouts if l['course_id'] == course['id']]
    layout = choose('Layout', layouts, 'stats_layout_' + (tournament_id or 'alltime'))
    if not layout:
        return
    category = statistics_category('stats_category')
    st.subheader('All-time statistics' if scope == 'All time' else 'Tournament statistics')
    rounds = selected_rounds(DATA, tournament_id, None,
                             layout['id'], category)
    show_statistics(rounds, 'public_stats', category == 'All')
    trend_controls(rounds, layout, tournament_id, category)


def admin_page():
    st.title('Administration')
    if not admin():
        expected = os.environ.get('DISCGOLF_ADMIN_PASSWORD') or CONFIG.get('admin_password', '')
        if not expected:
            st.info('Admin editing is disabled until an admin password is configured in Streamlit secrets or DISCGOLF_ADMIN_PASSWORD.')
            return
        blocked = st.session_state.get('login_blocked_until', 0) > time.time()
        if blocked:
            st.warning('Too many attempts. Try again in a minute.')
        with st.form('login'):
            value = st.text_input('Admin password', type='password')
            if st.form_submit_button('Sign in', disabled=blocked):
                if hmac.compare_digest(hashlib.sha256(value.encode()).digest(), hashlib.sha256(str(expected).encode()).digest()):
                    st.session_state['admin_expires'] = time.time() + 8*3600
                    st.session_state['login_attempts'] = 0
                    st.rerun()
                else:
                    st.session_state['login_attempts'] = st.session_state.get('login_attempts', 0) + 1
                    if st.session_state['login_attempts'] >= 5:
                        st.session_state['login_blocked_until'] = time.time() + 60
                        st.session_state['login_attempts'] = 0
                    st.error('Incorrect password.')
        return
    st.success('Signed in. Manage all league data here.')
    # if not STORE.github:
    #     st.info('Local JSON storage is active. Before cloud deployment, configure GitHub storage to preserve edits through restarts.')
    # else:
    #     st.caption('Persistent GitHub JSON storage is active.')
    section = st.radio('Manage', ['Players', 'Courses & layouts', 'Leagues', 'Tournaments & scores', 'Categories', 'Settings', 'Backup & restore'],
                       key='admin_section')
    if section == 'Players':
        players()
    elif section == 'Courses & layouts':
        courses()
    elif section == 'Leagues':
        league_editor()
        league = choose('League to edit', DATA['leagues'], 'admin_league_select')
        if league:
            league_editor(league)
    elif section == 'Tournaments & scores':
        tournament_editor()
        t = choose('Tournament to manage', sorted(DATA['tournaments'], key=lambda x: x['date'], reverse=True), 'admin_tournament_select',
                   lambda x: f"{x['date']} · {x['name']}")
        if t:
            tournament_editor(t)
            tournament_registration(t)
            action = st.radio('Manage scores', ['Manual entry', 'uDisc import'], horizontal=True)
            if action == 'Manual entry':
                manual_scores(t)
            else:
                import_scores(t)
    elif section == 'Settings':
        application_settings()
    elif section == 'Categories':
        category_settings()
    else:
        backup_settings()


def handicap_history_page():
    st.title('Handicap history')
    selector, current = st.columns([3, 1])
    with selector:
        options = sorted(DATA['players'], key=lambda p: (p['last_name'], p['first_name']))
        player = choose('Player', options, 'handicap_player', lambda p: f"{p['first_name']} {p['last_name']}".strip())
    if not player:
        return
    current.metric('Current handicap', '—' if player.get('handicap_pending') else str(player['handicap']))
    tournaments = {t['id']: t for t in DATA['tournaments']}
    rows = [{'Date': h['date'], 'Tournament': tournaments[h['tournament_id']]['name'],
             'Score relative to par': float(h['event_score']), 'Handicap': h['handicap_used'],
             'Next handicap': h['handicap_after'], 'Tournaments in average': h['sample_count']}
            for h in sorted(DATA.get('handicap_history', []), key=lambda h: (h['date'], h.get('event_order', 0)), reverse=True) if h['player_id'] == player['id']]
    if not rows:
        st.info('No completed tournaments yet.')
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch', column_config={
        'Score relative to par': st.column_config.NumberColumn(format='%.2f'),
        **{c: st.column_config.NumberColumn(format='%.0f') for c in ['Handicap', 'Next handicap', 'Tournaments in average']}})
    st.download_button('Download CSV', pd.DataFrame(rows).to_csv(index=False), 'handicap_history.csv', 'text/csv')


def application_settings():
    st.subheader('Application settings')
    with st.form('application_settings'):
        title = st.text_input('Application title', value=SETTINGS['site_title'], max_chars=100)
        choices = [x['id'] for x in DATA['leagues']]
        active = st.selectbox('Active league', choices or [None],
                              index=choices.index(SETTINGS['active_league_id']) if choices else 0,
                              format_func=lambda x: find(DATA, 'leagues', x)['name'] if x else 'No leagues yet')
        st.caption('Home shows standings for this league. Only one league is active at a time.')
        if st.form_submit_button('Save settings'):
            if not title.strip():
                st.error('Enter an application title.')
            else:
                draft = deepcopy(DATA)
                draft['settings'] = {'site_title': title.strip(), 'active_league_id': active}
                persist(draft)


def category_settings():
    st.subheader('Categories')
    st.write(', '.join(DATA['categories']))
    with st.form('add_category'):
        value = st.text_input('New category code', placeholder='MJ15')
        if st.form_submit_button('Add category'):
            value = value.strip().upper()
            if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{0,19}', value):
                st.error('Use a category code of up to 20 letters, numbers, underscores or hyphens.')
            elif value in DATA['categories']:
                st.error('Category already exists.')
            else:
                draft = deepcopy(DATA)
                draft['categories'].append(value)
                persist(draft)
    cat = st.selectbox('Category to remove', DATA['categories'])
    used = (any(p['category'] == cat for p in DATA['players']) or any(cat in t['categories'] for t in DATA['tournaments']) or
            any(cat in layout['profiles'] for layout in DATA['layouts']))
    st.caption('A category can be removed once it is no longer used by players, tournaments or layout overrides.')
    if st.button('Remove category', disabled=used or len(DATA['categories']) == 1):
        draft = deepcopy(DATA)
        draft['categories'].remove(cat)
        persist(draft)


def backup_settings():
    st.subheader('Backup & restore')
    st.download_button('Download full JSON backup', encoded(DATA), 'league.json', 'application/json')
    backup = st.file_uploader('Restore JSON backup', type=['json'])
    confirmed = st.checkbox('Replace all current data with this backup')
    if st.button('Restore backup', disabled=not backup or not confirmed):
        try:
            draft = validate_data(json.loads(backup.getvalue()))
            draft['revision'] = DATA.get('revision', 0)
            persist(draft)
        except (ValueError, KeyError, TypeError) as exc:
            st.error(f'Invalid backup: {exc}')


if not admin():
    st.markdown('''<style>button[aria-label="Download as CSV"] {display:none !important;}</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.selectbox('Language', ['sk', 'en'], format_func=lambda code: {'sk': 'Slovenčina', 'en': 'English'}[code], key='language')
    st.title('🥏 ' + SETTINGS['site_title'])
    page = st.radio('Explore', ['Home', 'Leagues', 'Tournaments', 'Statistics', 'Handicap history', 'Admin'], key='page')
    if admin():
        st.caption('Administrator · session expires after 8 hours')
        if st.button('Sign out'):
            st.session_state.pop('admin_expires', None)
            st.rerun()
    if st.button('Refresh results'):
        clear_view_cache()
        st.rerun()
if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))
{'Home': home, 'Leagues': leagues, 'Tournaments': tournaments, 'Statistics': statistics_page, 'Handicap history': handicap_history_page, 'Admin': admin_page}[page]()
