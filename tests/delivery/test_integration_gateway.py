"""Run connector mutation-contract regressions inside the delivery profile."""
import os
from pathlib import Path
import subprocess
import unittest


class IntegrationGatewayTests(unittest.TestCase):
    def test_connector_action_and_reconciliation_contract(self):
        root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env.pop('NODE_TEST_CONTEXT',None)
        result = subprocess.run(['node','--test','tests/delivery/test-integration-gateway.mjs'],
                                cwd=root,env=env,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('fail 0',result.stdout)


if __name__ == '__main__':
    unittest.main()
