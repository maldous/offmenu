"""Only the fixed export test reporter; no live machine observations."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tested_export_reporter',ROOT/'scripts/check-local-source-export-tests.py')
reporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(reporter)

class ExportDiagnostic(unittest.TestCase):
    def capture(self, text, code=1):
        return {'error_code':'none','child_exit_code':code,'capture_status':'completed','stdout':b'private ignored value','stderr':text.encode()}
    def test_failure_exposes_only_fixed_id_exception_and_counts(self):
        identity=sorted(reporter.BASE.EXPECTED_TEST_IDS)[0]
        method=identity.rsplit('.',1)[1]
        text='F\nFAIL: '+method+' ('+identity+')\nTraceback private /home/user/private\nAssertionError: private-token-value\n\nRan 39 tests in 0.1s\n\nFAILED (failures=1)\n'
        value=reporter.project(self.capture(text))
        self.assertEqual(value['failed_test_ids'],[identity]);self.assertEqual(value['exceptionClasses'],['AssertionError'])
        self.assertNotIn('private',json.dumps(value));self.assertEqual(value['tests_run'],39)
    def test_missing_module_name_is_identifier_only(self):
        text="ModuleNotFoundError: No module named 'example.module'\nRan 1 test in 0.1s\nFAILED (errors=1)\n"
        value=reporter.project(self.capture(text));self.assertEqual(value['missingModuleIdentifiers'],['example.module'])
        value=reporter.project(self.capture(text.replace('example.module','/home/private/token')))
        self.assertEqual(value['missingModuleIdentifiers'],[])
    def test_unknown_exception_and_test_text_not_published(self):
        text='ERROR: private (not_a_known_test.private)\nPrivateSecretClass: private body\nRan 39 tests in 0.1s\nFAILED (errors=1)\n'
        value=reporter.project(self.capture(text));self.assertEqual(value['error_code'],'unknown_test_id')
        self.assertNotIn('private',json.dumps(value));self.assertEqual(value['exceptionClasses'],[])
    def test_command_uses_exact_existing_cli_and_suite_pin(self):
        self.assertTrue(reporter.BASE.verify_suite_identity())
        self.assertEqual(reporter.BASE.fixed_command()[1:],['-I','-B','-m','unittest','discover','-s','tests','-p','test_local_source_export.py'])
        self.assertEqual(reporter.BASE.EXPECTED_COUNT,39)

if __name__=='__main__': unittest.main()
