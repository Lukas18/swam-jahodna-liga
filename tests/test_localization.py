import unittest
from league.localization import translate


class LocalizationTest(unittest.TestCase):
    def test_dynamic_validation_errors_and_golf_terms(self):
        self.assertEqual(translate('Row 2: Duplicate player and round in this file.', 'sk'),
                         'Riadok 2: Duplicitný hráč a kolo v tomto súbore.')
        self.assertEqual(translate('Alice Player: First and last name are required.', 'sk'),
                         'Alice Player: Meno a priezvisko sú povinné.')
        self.assertEqual(translate('Hole 2 is listed twice.', 'sk'), 'Jamka 2 je uvedená dvakrát.')
        self.assertEqual(translate('Round must be a whole number from 1 to 2.', 'sk'), 'Kolo musí byť celé číslo od 1 do 2.')
        self.assertEqual(translate('2 round(s)', 'sk'), '2 kolá')
        self.assertEqual(translate('Birdie %', 'sk'), 'Birdie %')
        self.assertEqual(translate('MPO', 'sk'), 'MPO')
        self.assertEqual(translate('Score relative to par', 'en'), 'Score relative to par')
