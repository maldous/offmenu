"""Offline client tests; no network or secret access."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('jobs_client',Path(__file__).with_name('windmill_foo_jobs.py'))
client=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'paramiko':types.ModuleType('paramiko'),'wmill':types.ModuleType('wmill')}):spec.loader.exec_module(client)

class Channel:
    def __init__(self):self.out=bytearray(b'x'*100000);self.err=bytearray(b'y'*100000)
    def recv_ready(self):return bool(self.out)
    def recv_stderr_ready(self):return bool(self.err)
    def recv(self,n):d=self.out[:n];del self.out[:n];return d
    def recv_stderr(self,n):d=self.err[:n];del self.err[:n];return d
    def exit_status_ready(self):return not self.out and not self.err
    def recv_exit_status(self):return 0

class Tests(unittest.TestCase):
    def test_invalid_inputs_before_network(self):
        for args in ({'action':'shell'},{'job_id':'../x'},{'job_id':'ok','timeout_seconds':True},{'job_id':'ok','timeout_seconds':1801},{'action':'run','job_id':'ok','command':'\x00'}):
            self.assertFalse(client.main(**args)['ok'])
    def test_bounded_streams(self):
        r=client._drain(Channel(),10)
        self.assertEqual(len(r['stdout']),65536);self.assertEqual(len(r['stderr']),65536)
        self.assertTrue(all(r['truncated'].values()))
    def test_deadline(self):
        with patch.object(client.time,'monotonic',side_effect=[0,11]):
            with self.assertRaises(TimeoutError):client._drain(Channel(),10)

if __name__=='__main__':unittest.main()
