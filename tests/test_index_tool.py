import unittest

from enstaller.index_tool import parse_requires


class TestUtils(unittest.TestCase):

    def test_parse_requires(self):
        for txt, packages in [
            ('argparse', ['argparse']),
            ('NumPy ==1.0.4', ['NumPy 1.0.4']),
            ('NumPy ==1.0.4\nNumpy >= 1.1.0', ['NumPy 1.0.4']),
            ('Traits[ui]', ['Traits']),
            ('NumPy ==1.0.4\nSciPy', ['NumPy 1.0.4', 'SciPy']),
            ]:
            self.assertEqual(parse_requires(txt), packages)


if __name__ == '__main__':
    unittest.main()
