"""Readable solid fills for category rows in light and dark/custom themes."""
CATEGORY_COLORS = {
    'light': ['#D0EBDD', '#EDCCE7', '#D2E6F7', '#F3E1B3', '#E0D8F4', '#F0D2C3', '#CDECEF'],
    'dark': ['#82B99D', '#CF9BC5', '#92BDE4', '#E0C27A', '#B3A8DC', '#DBA994', '#91C5CD'],
}


def category_styles(categories, theme='dark'):
    palette = CATEGORY_COLORS['light' if theme == 'light' else 'dark']
    return {category: f'background-color: {palette[i % len(palette)]}; color: #17251F'
            for i, category in enumerate(categories)}


def percentage_value(value):
    """Keep rare outcomes numeric; ordinary rates use whole percentages."""
    from .domain import whole_number
    return value if 0 < value < 1 else whole_number(value)


def percentage_label(value):
    return f'{value:.2f}' if 0 < value < 1 else f'{int(value):d}'
