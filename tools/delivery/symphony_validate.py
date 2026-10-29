#!/usr/bin/env python3
"""Parse a workflow using an installed Symphony bundle, without starting its app.

This invokes only Workflow.load and Config.Schema.parse in a temporary Erlang VM.
It does not call the Symphony CLI, tracker, supervisor, hook or Codex app-server.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, default=Path(__file__).with_name('symphony-workflow.md'))
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    workflow = args.workflow.resolve(strict=True)
    erl = bundle / 'otp/bin/erl'
    archive = bundle / 'libexec/symphony'
    if not erl.is_file() or not archive.is_file():
        parser.error('bundle must contain otp/bin/erl and libexec/symphony')
    with tempfile.TemporaryDirectory(prefix='offmenu-symphony-parse-') as directory:
        root = Path(directory)
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                relative = Path(name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('unsafe bundle archive path')
                if '/ebin/' in name and name.endswith(('.beam', '.app')):
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read(name))
        paths = sorted(str(p) for p in root.glob('*/ebin'))
        # Paths are passed via argv/environment, never interpolated into Erlang source.
        expression = """
application:ensure_all_started(elixir),
Path = unicode:characters_to_binary(os:getenv("OFFMENU_SYMPHONY_VALIDATE_WORKFLOW")),
case 'Elixir.SymphonyElixir.Workflow':load(Path) of
 {ok, Workflow} ->
  case 'Elixir.SymphonyElixir.Config.Schema':parse(maps:get(config, Workflow)) of
   {ok, _} -> io:format("Symphony Workflow.load and Config.Schema.parse: PASS~n"), halt(0);
   _ -> io:format("Symphony schema validation: FAIL (details suppressed)~n"), halt(2)
  end;
 _ -> io:format("Symphony workflow parse: FAIL (details suppressed)~n"), halt(2)
end.
"""
        environment = os.environ.copy()
        environment['OFFMENU_SYMPHONY_VALIDATE_WORKFLOW'] = str(workflow)
        environment['ERL_ROOTDIR'] = str(bundle / 'otp')
        environment['ERL_FLAGS'] = '+S 2:2'
        result = subprocess.run([str(erl), '-noshell', '-pa', *paths, '-eval', expression], env=environment, timeout=30, capture_output=True, text=True)
        # Only emit a fixed summary; never dump configuration or credential values.
        print(json.dumps({'schema_version': 1, 'workflow': str(workflow), 'bundle': str(bundle), 'validation': 'passed' if result.returncode == 0 else 'failed', 'exit_code': result.returncode, 'services_started': False, 'model_calls': False}))
        return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
