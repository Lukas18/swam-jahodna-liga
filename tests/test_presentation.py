import re
import unittest
from league.presentation import category_styles
from league.statistics import hole_heat_styles


def luminance(hex_color):
    channels = [int(hex_color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return sum(a*b for a, b in zip(linear, [.2126, .7152, .0722]))


class PaletteTest(unittest.TestCase):
    def test_theme_palettes_have_readable_text_and_distinct_categories(self):
        for theme in ['light', 'dark']:
            styles = list(category_styles(['MPO', 'FPO', 'MA3', 'FA3', 'MJ18', 'MJ15', 'FJ15'], theme).values())
            self.assertEqual(len(set(styles)), 7)
            styles += [hole_heat_styles({'Average +/− par': d}, theme)[0] for d in [-2, -1, -.5, .5, 1, 2]]
            for style in styles:
                bg, fg = re.findall(r'#[0-9A-Fa-f]{6}', style)
                self.assertGreaterEqual((luminance(bg)+.05)/(luminance(fg)+.05), 4.5)
        self.assertNotEqual(category_styles(['MPO'], 'light'), category_styles(['MPO'], 'dark'))
        self.assertNotEqual(hole_heat_styles({'Average +/− par': 1}, 'light'), hole_heat_styles({'Average +/− par': 1}, 'dark'))
        self.assertEqual(hole_heat_styles({'Average +/− par': 0, 'Par %': 100}, 'light'), ['', ''])
