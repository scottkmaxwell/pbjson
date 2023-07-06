from __future__ import absolute_import
import unittest
import sys


class OptionalExtensionTestSuite(unittest.TestSuite):
    def __init__(self, suite, test_no_speedups=False):
        super(OptionalExtensionTestSuite, self).__init__(suite)
        self.test_no_speedups = test_no_speedups

    def run(self, result, test_no_speedups=False):
        import pbjson
        run = unittest.TestSuite.run
        if not self.test_no_speedups:
            run(self, result)
            return result

        if not pbjson._has_encoder_speedups() and not pbjson._has_decoder_speedups():
            print("Testing with missing speedups")
            TestMissingSpeedups().run(result)
        else:
            pbjson._toggle_speedups(False)
            print("Testing without speedups")
            run(self, result)
            pbjson._toggle_speedups(True)
        return result


class TestMissingSpeedups(unittest.TestCase):
    def runTest(self):
        if hasattr(sys, 'pypy_translation_info'):
            "PyPy doesn't need speedups! :)"
        elif hasattr(self, 'skipTest'):
            self.skipTest('_speedups.so is missing!')


# def additional_tests(suite=None):
#     import pbjson
#     import pbjson.encoder
#     import pbjson.decoder
#     if suite is None:
#         suite = unittest.TestSuite()
#     for mod in (pbjson, pbjson.encoder, pbjson.decoder):
#         suite.addTest(doctest.DocTestSuite(mod))
#     suite.addTest(doctest.DocFileSuite('../../index.rst'))
#     return suite


def all_tests_suite(test_no_speedups=False):
    suite = unittest.TestLoader().loadTestsFromNames([
        'pbjson.tests.test_check_circular',
        'pbjson.tests.test_custom',
        # 'pbjson.tests.test_decimal',
        'pbjson.tests.test_decode',
        'pbjson.tests.test_default',
        'pbjson.tests.test_encode',
        'pbjson.tests.test_float',
        'pbjson.tests.test_for_json',
        'pbjson.tests.test_mapping',
        'pbjson.tests.test_pass1',
        'pbjson.tests.test_pass2',
        # 'pbjson.tests.test_recursion',
        'pbjson.tests.test_speedups',
        'pbjson.tests.test_tuple',
    ])
    # suite = additional_tests(suite)
    return OptionalExtensionTestSuite([suite], test_no_speedups=test_no_speedups)


def main():
    runner = unittest.TextTestRunner(verbosity=1 + sys.argv.count('-v'))
    suite = all_tests_suite()
    if not runner.run(suite).wasSuccessful():
        raise SystemExit(1)
    suite = all_tests_suite(True)
    raise SystemExit(not runner.run(suite).wasSuccessful())


if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    main()
