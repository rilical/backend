import sys
import unittest

# Pull in each provider's test suite
from apps.providers.westernunion.tests import TestWesternUnionProviderRealAPI
from apps.providers.ria.tests import TestRIAProviderRealAPI
from apps.providers.wise.tests import TestWiseProviderRealAPI
from apps.providers.pangea.tests import TestPangeaProviderRealAPI

def main():
    suite = unittest.TestSuite()
    
    # Add provider tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWesternUnionProviderRealAPI))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRIAProviderRealAPI))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWiseProviderRealAPI))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPangeaProviderRealAPI))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main()
