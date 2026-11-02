"""Real isolated Git acquisition; no network, provider, Pool or live control."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_project_source as source
from symphony_capacity import AdmissionError


class ProjectSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.repository = self.root/'project'
        self.repository.mkdir()
        self.git('init','-b','develop')
        (self.repository/'file.txt').write_text('accepted\n')
        self.commit('accepted')
        self.accepted = self.git('rev-parse','HEAD')
        self.tree = self.git('rev-parse','HEAD^{tree}')
        (self.repository/'file.txt').write_text('unaccepted tip\n')
        self.commit('later unaccepted tip')
        self.later = self.git('rev-parse','HEAD')
        self.git('checkout','-b','bugfix/controller')
        (self.repository/'file.txt').write_text('different control revision\n')
        self.commit('controller')
        self.control = self.git('rev-parse','HEAD')

    def git(self,*arguments):
        return subprocess.check_output(['git','-C',str(self.repository),
            '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
            '-c','commit.gpgsign=false',*arguments],text=True,stderr=subprocess.PIPE).strip()

    def commit(self,message):
        self.git('add','file.txt');self.git('commit','-m',message)

    def test_exact_accepted_revision_with_different_control_and_later_tip(self):
        destination = self.root/'private'/'checkout'
        before = self.git('show-ref')
        source.materialize_accepted_project_source(self.repository,destination,head=self.accepted,tree=self.tree,
                            branch='bugfix/source-uif138')
        self.assertEqual((destination/'file.txt').read_text(),'accepted\n')
        self.assertEqual(source._git(destination,'branch','--show-current'),'bugfix/source-uif138')
        self.assertEqual(destination.stat().st_mode & 0o777,0o700)
        self.assertFalse((destination/'.git/objects/info/alternates').exists())
        self.assertEqual(self.git('rev-parse','HEAD'),self.control)
        self.assertEqual(self.git('show-ref'),before)
        source.materialize_accepted_project_source(self.repository,destination,head=self.accepted,tree=self.tree,
                            branch='bugfix/source-uif138')
        (destination/'file.txt').write_text('retained change\n')
        with self.assertRaisesRegex(AdmissionError,'reconciliation'):
            source.materialize_accepted_project_source(self.repository,destination,head=self.accepted,tree=self.tree,
                                branch='bugfix/source-uif138')
        self.assertEqual((destination/'file.txt').read_text(),'retained change\n')


if __name__ == '__main__':
    unittest.main()
