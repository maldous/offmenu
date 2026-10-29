"""Explicit named non-sensitive development output only; no shell or global hooks."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
SAVED_LOGS = {
    'ai-reuse-r1': (Path('/home/user/src/offmenu-ai-reuse-candidate-20261028/tests.log'), 'e67c5eefcd3cb3fc739ae3dbe4fe24da4b2b70fd839349a51a3c42358a1af60d'),
    'ai-reuse-r2': (Path('/home/user/src/offmenu-ai-reuse-candidate-20261028-r2/tests.log'), 'dc5516274b9daacdcb9886743d029b004694ad4998c15feeb2f107e3b5f60e83'),
}
# Changes to named commands/inputs require source review. No arbitrary argv/stdin.
COMMANDS = {'filter-tests': (sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT), '-p', 'test_terminal_filter.py', '-v')}
CLASSIFY_LIMIT = 1048576


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))+'\n').encode('ascii')


def private_directory(directory):
    directory = Path(directory)
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('artifact directory must be an owned private non-symlink directory')
    return directory


def new_artifact(directory):
    directory = private_directory(directory)
    path = directory/(uuid.uuid4().hex+'.bin')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return path, os.fdopen(fd, 'wb')


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def finalize(path, *, profile, returncode, cancelled, elapsed, command=None, cancellation_signal=None):
    size, sha = fingerprint(path)
    os.chmod(path, 0o400)
    metadata = {'profile': profile, 'original_artifact': str(path.resolve()),
                'original_bytes': size, 'original_sha256': sha,
                'process_returncode': returncode, 'cancelled': cancelled,
                'cancellation_signal': cancellation_signal,
                'capture_elapsed_seconds': elapsed, 'command_argv': command,
                'stream': 'observed combined stdout/stderr bytes' if command else 'saved named log bytes'}
    receipt = path.with_suffix('.json')
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encoded(metadata))
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(receipt, 0o400)
    metadata['capture_receipt'] = str(receipt.resolve())
    return metadata


def save_named_log(profile, directory):
    started = time.monotonic()
    source, expected = SAVED_LOGS[profile]
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('named input must be a regular file')
        data = stream.read(CLASSIFY_LIMIT+1)
    if len(data) > CLASSIFY_LIMIT or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('named input changed; review its classification/hash before capture')
    path, stream = new_artifact(directory)
    with stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return finalize(path, profile=profile, returncode=None, cancelled=False,
                    elapsed=time.monotonic()-started)


def stop_group(process, initial_signal=signal.SIGINT):
    # No shell, retries of the command, or indefinite cleanup waits.
    for sig, grace in ((initial_signal, .5), (signal.SIGTERM, .5), (signal.SIGKILL, 1.0)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=grace)
            # The leader can exit before its descendants; kill the remaining group.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return
        except subprocess.TimeoutExpired:
            continue
    raise RuntimeError('cleanup unconfirmed; capture must not be treated as finalized')


class CaptureCancelled(BaseException):
    def __init__(self, signum):
        self.signum = signum


def capture_command(command, directory, *, profile, cwd):
    """Internal runner; CLI accepts only COMMANDS names, never caller-supplied argv."""
    started = time.monotonic()
    path, stream = new_artifact(directory)
    process = None
    cancelled = False
    cancellation_signal = None
    def terminate(signum, frame):
        raise CaptureCancelled(signum)
    prior_term = signal.signal(signal.SIGTERM, terminate)
    try:
        with stream:
            process = subprocess.Popen(command, cwd=cwd, shell=False,
                                       stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True, stdin=subprocess.DEVNULL)
            try:
                process.wait()
                stop_group(process)
            except (KeyboardInterrupt, CaptureCancelled) as interruption:
                cancelled = True
                cancellation_signal = interruption.signum if isinstance(interruption, CaptureCancelled) else signal.SIGINT
                stop_group(process, cancellation_signal)
            finally:
                if process.poll() is None:
                    stop_group(process)
            stream.flush()
            os.fsync(stream.fileno())
    except (KeyboardInterrupt, CaptureCancelled) as interruption:
        cancelled = True
        cancellation_signal = interruption.signum if isinstance(interruption, CaptureCancelled) else signal.SIGINT
        if process is not None:
            stop_group(process, cancellation_signal)
    except BaseException:
        if process is not None and process.poll() is None:
            stop_group(process)
        # Leave partial bytes private; never forge a finalized hash/status receipt.
        raise
    finally:
        signal.signal(signal.SIGTERM, prior_term)
    return finalize(path, profile=profile, returncode=process.returncode if process else None,
                    cancelled=cancelled, elapsed=time.monotonic()-started,
                    command=list(command), cancellation_signal=cancellation_signal)


def classify_unittest_ok(data):
    """Only the complete known unittest verbose-success grammar is compressible."""
    try:
        records = data.decode('ascii').splitlines(keepends=True)
    except UnicodeDecodeError:
        return None
    tests = 0
    retained = []
    phase = 'tests'
    for raw in records:
        line = raw.rstrip('\r\n')
        if phase == 'tests' and re.fullmatch(r'test[A-Za-z0-9_]+ \([A-Za-z0-9_.]+\) \.\.\. ok', line):
            tests += 1
        elif not line or (phase == 'tests' and re.fullmatch('-{10,}', line)):
            continue
        elif phase == 'tests' and (match := re.fullmatch(r'Ran (\d+) tests? in [0-9.]+s', line)):
            if int(match[1]) != tests:
                return None
            retained.append(raw)
            phase = 'trailer'
        elif phase == 'trailer' and line == 'OK':
            retained.append(raw)
            phase = 'done'
        else:
            return None
    if phase != 'done' or not tests:
        return None
    kept = ''.join(retained).encode('ascii')
    return {'recognized_test_records': tests, 'retained_text': kept.decode('ascii'),
            'omitted_bytes': len(data)-len(kept), 'omitted_records': len(records)-len(retained)}


def summarize(metadata, max_bytes=1536):
    if type(max_bytes) is not int or not 1024 <= max_bytes <= 16384:
        raise ValueError('summary budget must be 1024..16384 bytes')
    path = Path(metadata['original_artifact'])
    size, sha = fingerprint(path)
    if (size, sha) != (metadata['original_bytes'], metadata['original_sha256']):
        raise ValueError('original changed; refusing a misleading summary')
    summary = {k: metadata[k] for k in ('profile', 'original_artifact', 'original_bytes',
                                      'original_sha256', 'process_returncode', 'cancelled', 'capture_receipt')}
    summary.update(summary_is_full_evidence=False,
                   notice='Summary is not full evidence. Diagnostics and exact bytes remain in original_artifact.',
                   execution_outcome='cancelled' if metadata['cancelled'] else
                       'not_observed' if metadata['process_returncode'] is None else
                       'exited_zero' if metadata['process_returncode'] == 0 else 'exited_nonzero')
    with path.open('rb') as stream:
        data = stream.read(CLASSIFY_LIMIT+1)
    classified = classify_unittest_ok(data) if size <= CLASSIFY_LIMIT else None
    if classified and metadata['process_returncode'] in (None, 0) and not metadata['cancelled']:
        summary.update(mode='strict_unittest_ok', diagnostics='none_in_recognized_grammar', **classified)
        result = encoded(summary)
        if len(result) <= max_bytes:
            return result
        # Metadata/known content also cannot bypass the output budget.
        for key in classified:
            summary.pop(key, None)
    summary.update(mode='bounded_raw_chunks', classification='uncertain_or_failure',
                   diagnostics='full_original_only_when_chunks_omit_bytes')
    # No unknown record is classified as harmless. Base64 handles binary, Unicode,
    # long lines and terminal escapes without lossy decoding or terminal effects.
    for sample_size in range(min(max_bytes, size), -1, -1):
        with path.open('rb') as stream:
            head = stream.read((sample_size+1)//2)
            tail_offset = max(len(head), size-sample_size//2)
            stream.seek(tail_offset)
            tail = stream.read()
        chunks = [{'offset': 0, 'bytes': len(head), 'base64': base64.b64encode(head).decode('ascii')}]
        if tail:
            chunks.append({'offset': tail_offset, 'bytes': len(tail), 'base64': base64.b64encode(tail).decode('ascii')})
        summary.update(raw_chunks=chunks, omitted_bytes=size-len(head)-len(tail),
                       diagnostic_omission_possible=(size > len(head)+len(tail)))
        result = encoded(summary)
        if len(result) <= max_bytes:
            return result
    raise ValueError('metadata alone exceeds summary budget; use the full receipt/artifact')


def shell_status(metadata):
    if metadata['cancelled']:
        return 128+int(metadata.get('cancellation_signal') or signal.SIGINT)
    code = metadata['process_returncode']
    return 0 if code is None else code if code >= 0 else 128-code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('saved', 'run'))
    parser.add_argument('profile')
    parser.add_argument('--max-bytes', type=int, default=1536)
    args = parser.parse_args(argv)
    choices = SAVED_LOGS if args.mode == 'saved' else COMMANDS
    if args.profile not in choices:
        parser.error('profile must be an explicitly reviewed named non-sensitive output')
    if not 1024 <= args.max_bytes <= 16384:
        parser.error('--max-bytes must be 1024..16384')
    metadata = None
    try:
        if args.mode == 'saved':
            metadata = save_named_log(args.profile, ROOT/'artifacts')
        else:
            metadata = capture_command(COMMANDS[args.profile], ROOT/'artifacts', profile=args.profile, cwd=ROOT)
        sys.stdout.buffer.write(summarize(metadata, args.max_bytes))
        return shell_status(metadata)
    except Exception as error:
        # Avoid arbitrary exception text/traceback; this is not a redaction claim.
        print(json.dumps({'tool_status': 'failed_closed', 'error_type': type(error).__name__,
                          'notice': 'No success claim. Inspect private artifacts/receipts if created.',
                          'process_returncode': metadata['process_returncode'] if metadata else None}), file=sys.stderr)
        return shell_status(metadata) if metadata and shell_status(metadata) != 0 else 125


if __name__ == '__main__':
    sys.exit(main())
