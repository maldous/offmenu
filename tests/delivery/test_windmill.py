"""Worker adapter contract without network or a live Windmill installation."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

from test_engine import DeliveryFixture
from offmenu.delivery.engine import Engine, writer, DeliveryError

MODULE = Path(__file__).resolve().parents[2] / 'tools/delivery/windmill_entrypoint.py'
spec = importlib.util.spec_from_file_location('windmill_entrypoint', MODULE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class WindmillTests(DeliveryFixture):
    def prepare(self):
        state = self.root / '.delivery'
        state.mkdir(exist_ok=True)
        path = state / 'task.json'
        path.write_text(json.dumps(self.task))
        return '.delivery/task.json'

    def test_reviewed_task_runs_and_status_returns_recorded_acceptance(self):
        task_path = self.prepare()
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            self.assertEqual(adapter.main(task_path, 'run')['status'], 'accepted')
            self.assertEqual(adapter.main(task_path)['status'], 'accepted')

    def test_status_rejects_conflicting_task_binding(self):
        task_path = self.prepare()
        with writer(self.root) as state:
            Engine(self.root, state, self.task)
        self.task['owner'] = 'another-owner'
        (self.root / task_path).write_text(json.dumps(self.task))
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            with self.assertRaisesRegex(DeliveryError, 'binding mismatch'):
                adapter.main(task_path)

    def test_rejects_outside_task_path(self):
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            with self.assertRaisesRegex(ValueError, 'reviewed delivery'):
                adapter.main('../outside.json')
