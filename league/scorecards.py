"""Read-only, player-by-hole tournament round tables."""
from html import escape

from .domain import place_labels, rank_rows


SORT_SCRIPT = '''<script>
(() => {
  const root = document.currentScript?.getRootNode() || document;
  root.querySelectorAll('.round-scorecard:not([data-sort-ready])').forEach(card => {
    card.dataset.sortReady = 'true';
    const table = card.querySelector('table');
    const body = table.tBodies[0];
    const headers = Array.from(table.tHead.rows[0].cells);
    Array.from(body.rows).forEach((row, index) => { row.dataset.originalOrder = index; });
    headers.forEach((header, column) => {
      header.tabIndex = 0;
      header.setAttribute('aria-sort', 'none');
      const sort = () => {
        const ascending = header.getAttribute('aria-sort') !== 'ascending';
        headers.forEach(item => item.setAttribute('aria-sort', 'none'));
        header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        const textColumn = header.classList.contains('name') || header.classList.contains('category');
        const value = row => row.cells[column].textContent.trim();
        const number = text => Number(text.replace(/^T(?=\\d)/i, ''));
        const rows = Array.from(body.rows);
        rows.sort((left, right) => {
          const a = value(left), b = value(right);
          const aMissing = !a || a === '—', bMissing = !b || b === '—';
          if (aMissing !== bMissing) return aMissing ? 1 : -1;
          const comparison = textColumn
            ? a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'})
            : number(a) - number(b);
          return (ascending ? comparison : -comparison)
            || Number(left.dataset.originalOrder) - Number(right.dataset.originalOrder);
        });
        rows.forEach(row => body.appendChild(row));
      };
      header.addEventListener('click', sort);
      header.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          sort();
        }
      });
    });
  });
})();
</script>'''


def round_scorecard_html(data, records, labels):
    """Render one round's recorded scores, using each scorecard's saved hole par."""
    players = {player['id']: player for player in data['players']}
    category_order = {category: index for index, category in enumerate(data['categories'])}
    rows = []
    for record in records:
        player = players[record['player_id']]
        rows.append({'record': record, 'player_id': player['id'],
                     'Player': f"{player['first_name']} {player['last_name']}".strip(),
                     'Category': record['category'], 'Relative': record['total'] - record['par']})
    rows.sort(key=lambda row: (category_order.get(row['Category'], len(category_order)),
                               row['Relative'], row['Player'].casefold(), row['player_id']))
    rank_rows(rows, 'Relative')
    places = place_labels(rows)
    show_category = len({row['Category'] for row in rows}) > 1
    holes = sorted({hole['number'] for record in records for hole in record['holes']})

    def header(label, css=''):
        return f'<th scope="col" class="{css}">{escape(label)}</th>'

    head = [header(labels['#'], 'position'), header(labels['Name'], 'name')]
    if show_category:
        head.append(header(labels['Category'], 'category'))
    head.append(header(labels['Total'], 'total'))
    for number in holes:
        snapshots = [hole for record in records for hole in record['holes'] if hole['number'] == number]
        pars = {hole['par'] for hole in snapshots}
        lengths = {hole['length'] for hole in snapshots}
        # Only shared snapshot metadata belongs in a column heading. Each score
        # always carries its own recorded par and length in the cell tooltip.
        par = f'<small>{escape(labels["Par"])} {next(iter(pars))}</small>' if len(pars) == 1 else ''
        length = f'<small>{next(iter(lengths)):.0f} m</small>' if len(lengths) == 1 and next(iter(lengths)) > 0 else ''
        head.append(f'<th scope="col" class="hole"><span>{number}</span>{length}{par}</th>')
    round_pars = {record['par'] for record in records}
    round_par = f'<small>{escape(labels["Par"])} {next(iter(round_pars))}</small>' if len(round_pars) == 1 else ''
    round_lengths = [sum(hole['length'] for hole in record['holes']) for record in records
                     if record['holes'] and all(hole['length'] > 0 for hole in record['holes'])]
    round_length = (f'<small>{round_lengths[0]:.0f} m</small>'
                    if len(round_lengths) == len(records) and len(set(round_lengths)) == 1 else '')
    head.append(f'<th scope="col" class="round-total"><span>{escape(labels["Round"])}</span>'
                f'{round_length}{round_par}</th>')

    body = []
    for row, place in zip(rows, places):
        record = row['record']
        name = escape(row['Player'])
        if not record['holes']:
            name += f'<small class="totals-only">{escape(labels["Totals only"])}</small>'
        cells = [f'<td class="position">{escape(place)}</td>', f'<th scope="row" class="name">{name}</th>']
        if show_category:
            cells.append(f'<td class="category">{escape(row["Category"])}</td>')
        cells.append(f'<td class="total">{row["Relative"]:+d}</td>')
        by_number = {hole['number']: hole for hole in record['holes']}
        for number in holes:
            hole = by_number.get(number)
            if hole is None:
                cells.append('<td class="hole empty">—</td>')
                continue
            difference = hole['throws'] - hole['par']
            if hole['throws'] == 1:
                score_class = 'ace'
            elif difference < 0:
                score_class = 'under'
            elif difference == 0:
                score_class = 'par'
            else:
                score_class = 'over' if difference == 1 else f'over over-{min(difference, 4)}'
            tooltip = f'{labels["Hole"]} {number} · {labels["Par"]} {hole["par"]}'
            if hole['length'] > 0:
                tooltip += f' · {hole["length"]:.0f} m'
            cells.append(f'<td class="hole" title="{escape(tooltip, quote=True)}">'
                         f'<span class="score {score_class}">{hole["throws"]}</span></td>')
        cells.append(f'<td class="round-total">{record["total"]}</td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')
    round_label = escape(f'{labels["Round"]} {records[0]["round_number"]}', quote=True)
    return (f'<div class="round-scorecard" role="region" aria-label="{round_label}" tabindex="0">'
            '<table><thead><tr>' + ''.join(head) + '</tr></thead><tbody>'
            + ''.join(body) + '</tbody></table></div>' + SORT_SCRIPT)
