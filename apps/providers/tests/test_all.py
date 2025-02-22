import sys
import unittest

# Pull in each provider's test suite
from apps.providers.moneygram.tests import TestMoneyGramProvider
from apps.providers.westernunion.tests import TestWesternUnionProvider
from apps.providers.ria.tests import TestRiaProvider

def main():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMoneyGramProvider))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWesternUnionProvider))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRiaProvider))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main()
