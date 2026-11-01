"""Finite, fixed-route credential transfer. Real CLI use requires separate authority.

No secret diagnostics, subprocesses, service actions or arbitrary filesystem secret reads.
Internal dirfd functions exist only to permit offline synthetic verification.
"""
import hashlib
import hmac
import os
import resource
import select
import signal
import stat
import struct
import sys
import time
import secrets

PARENT = 'offmenu-stokowski-current-credential'
FINAL = 'linear-api-key'
DESTINATION = '/run/' + PARENT + '/' + FINAL
LIMIT = 16384
SECONDS = 15
MAGIC = b'OMSC\x01'
TRAILER = b'\x00END-OMSC\x01'
SOURCE_PARENT = 'offmenu-stokowski-credential-input'
SOURCE_FILE = 'frame'
SOURCE_BASE = '/run/user/1000'
MAX_FRAME = len(MAGIC) + 4 + LIMIT + 32 + len(TRAILER)


class Refused(Exception):
    """A fixed public failure class; never attach input or exception details."""


def pipe_only(fd):
    info = os.fstat(fd)
    if (not stat.S_ISFIFO(info.st_mode)
            or os.readlink('/proc/self/fd/' + str(fd)) != 'pipe:[' + str(info.st_ino) + ']'
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise Refused('pipe_required')


def wait_ready(fd, writing, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Refused('transfer_timeout')
        try:
            ready = select.select([] if writing else [fd],
                                  [fd] if writing else [], [], remaining)
        except InterruptedError:
            continue
        if ready[1 if writing else 0]:
            return
        raise Refused('transfer_timeout')


def write_all(fd, data, deadline, pipe=False):
    view = memoryview(data)
    while view:
        if time.monotonic() >= deadline:
            raise Refused('transfer_timeout')
        if pipe:
            wait_ready(fd, True, deadline)
        try:
            count = os.write(fd, view)
        except (InterruptedError, BlockingIOError):
            continue
        if count <= 0:
            raise Refused('write_failed')
        view = view[count:]


def frame(payload):
    if not payload or len(payload) > LIMIT:
        raise Refused('payload_rejected')
    return MAGIC + struct.pack('!I', len(payload)) + payload + hashlib.sha256(payload).digest() + TRAILER


def read_frame(fd, deadline):
    """Require declared size, digest, trailer AND EOF before filesystem creation."""
    pipe_only(fd)
    os.set_blocking(fd, False)
    data = bytearray()
    maximum = len(MAGIC) + 4 + LIMIT + 32 + len(TRAILER)
    while True:
        wait_ready(fd, False, deadline)
        try:
            part = os.read(fd, min(4096, maximum + 1 - len(data)))
        except (InterruptedError, BlockingIOError):
            continue
        if not part:
            break
        data.extend(part)
        if len(data) > maximum:
            raise Refused('frame_rejected')
        if len(data) >= len(MAGIC) + 4:
            length = struct.unpack('!I', data[len(MAGIC):len(MAGIC) + 4])[0]
            if data[:len(MAGIC)] != MAGIC or not 1 <= length <= LIMIT:
                raise Refused('frame_rejected')
            if len(data) > len(MAGIC) + 4 + length + 32 + len(TRAILER):
                raise Refused('frame_rejected')
    return decode_frame(data)


def decode_frame(data):
    header = len(MAGIC) + 4
    if len(data) < header or data[:len(MAGIC)] != MAGIC:
        raise Refused('frame_rejected')
    length = struct.unpack('!I', data[len(MAGIC):header])[0]
    if not 1 <= length <= LIMIT or len(data) != header + length + 32 + len(TRAILER):
        raise Refused('frame_rejected')
    payload = bytes(data[header:header + length])
    if (data[-len(TRAILER):] != TRAILER or not hmac.compare_digest(
            data[header + length:header + length + 32], hashlib.sha256(payload).digest())):
        raise Refused('frame_rejected')
    return payload


def identity(info):
    return info.st_dev, info.st_ino


def remove_owned(dirfd, name, owned, directory=False):
    """Never remove a replacement, collision or a preexisting object."""
    if owned is None:
        return
    try:
        info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        if identity(info) == owned:
            if directory:
                os.rmdir(name, dir_fd=dirfd)
            else:
                os.unlink(name, dir_fd=dirfd)
    except OSError:
        pass  # Remnants require manual reconciliation; no recursive deletion.


def check_directory(fd, uid, exact_mode=None, *, gid=None):
    gid = uid if gid is None else gid
    info = os.fstat(fd)
    mode = stat.S_IMODE(info.st_mode)
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid
            or info.st_gid != gid or mode & 0o022
            or (exact_mode is not None and mode != exact_mode)):
        raise Refused('directory_rejected')
    return identity(info)


def stage(parentfd, payload, deadline, uid, *, gid=None):
    """Internal ownership pair; omitted gid preserves the fixed CLI uid:uid policy."""
    gid = uid if gid is None else gid
    if not payload or len(payload) > LIMIT:
        raise Refused('payload_rejected')
    check_directory(parentfd, uid, gid=gid)
    directory_id = temporary_id = published_id = None
    directoryfd = filefd = None
    temporary = '.incomplete-' + secrets.token_hex(16)
    try:
        os.mkdir(PARENT, 0o700, dir_fd=parentfd)  # Existing anything is a refusal.
        directory_id = identity(os.stat(PARENT, dir_fd=parentfd, follow_symlinks=False))
        directoryfd = os.open(PARENT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=parentfd)
        if check_directory(directoryfd, uid, 0o700, gid=gid) != directory_id:
            raise Refused('directory_rejected')
        filefd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directoryfd)
        info = os.fstat(filefd)
        temporary_id = identity(info)
        if info.st_uid != uid or info.st_gid != gid or stat.S_IMODE(info.st_mode) != 0o600:
            raise Refused('file_rejected')
        write_all(filefd, payload, deadline)
        os.fsync(filefd)
        os.close(filefd)
        filefd = None
        os.link(temporary, FINAL, src_dir_fd=directoryfd, dst_dir_fd=directoryfd,
                follow_symlinks=False)  # Atomic create, never replace.
        published_id = temporary_id
        os.fsync(directoryfd)
        remove_owned(directoryfd, temporary, temporary_id)
        os.fsync(directoryfd)
        os.fsync(parentfd)
    except BaseException:
        if directoryfd is not None:
            remove_owned(directoryfd, FINAL, published_id)
            remove_owned(directoryfd, temporary, temporary_id)
        remove_owned(parentfd, PARENT, directory_id, directory=True)
        raise
    finally:
        if filefd is not None:
            os.close(filefd)
        if directoryfd is not None:
            os.close(directoryfd)


def receive(fd, parentfd, deadline, uid, *, gid=None):
    stage(parentfd, read_frame(fd, deadline), deadline, uid, gid=gid)


def send(fd, environment, deadline):
    # Only selected exported value is captured; aliases and files are never read.
    value = environment.get('LINEAR_API_KEY')
    environment.clear()
    if not value:
        raise Refused('export_missing_or_empty')
    pipe_only(fd)
    payload = value.encode('utf-8')
    del value
    encoded = frame(payload)
    os.set_blocking(fd, False)
    write_all(fd, encoded, deadline, pipe=True)


def snapshot(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def same_path(parentfd, name, fd):
    if snapshot(os.stat(name, dir_fd=parentfd, follow_symlinks=False)) != snapshot(os.fstat(fd)):
        raise Refused('source_changed')


def check_source(info, uid):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not len(MAGIC) + 4 + 1 + 32 + len(TRAILER) <= info.st_size <= MAX_FRAME):
        raise Refused('source_rejected')


def capture(environment):
    value = environment.get('LINEAR_API_KEY')
    environment.clear()
    if not value:
        raise Refused('export_missing_or_empty')
    return frame(value.encode('utf-8'))


def send_file(basefd, environment, deadline, uid, *, gid=None):
    """Fixed names, exclusive creation. Successful secret source stays for cleanup."""
    gid = uid if gid is None else gid
    encoded = capture(environment)
    check_directory(basefd, uid, 0o700, gid=gid)
    directoryfd = filefd = None
    directory_id = file_id = None
    try:
        os.mkdir(SOURCE_PARENT, 0o700, dir_fd=basefd)
        directory_id = identity(os.stat(SOURCE_PARENT, dir_fd=basefd, follow_symlinks=False))
        directoryfd = os.open(SOURCE_PARENT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=basefd)
        if check_directory(directoryfd, uid, 0o700, gid=gid) != directory_id:
            raise Refused('source_changed')
        filefd = os.open(SOURCE_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directoryfd)
        file_id = identity(os.fstat(filefd))
        write_all(filefd, encoded, deadline)
        check_source(os.fstat(filefd), uid)
        os.fsync(filefd)
        same_path(directoryfd, SOURCE_FILE, filefd)
        same_path(basefd, SOURCE_PARENT, directoryfd)
        os.fsync(directoryfd)
        os.fsync(basefd)
        return directory_id, file_id
    except BaseException:
        if directoryfd is not None:
            remove_owned(directoryfd, SOURCE_FILE, file_id)
        remove_owned(basefd, SOURCE_PARENT, directory_id, directory=True)
        raise
    finally:
        if filefd is not None:
            os.close(filefd)
        if directoryfd is not None:
            os.close(directoryfd)


def read_source(basefd, deadline, uid, *, gid=None):
    gid = uid if gid is None else gid
    check_directory(basefd, uid, 0o700, gid=gid)
    directoryfd = os.open(SOURCE_PARENT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                          dir_fd=basefd)
    try:
        check_directory(directoryfd, uid, 0o700, gid=gid)
        before_dir = snapshot(os.fstat(directoryfd))
        same_path(basefd, SOURCE_PARENT, directoryfd)
        fd = os.open(SOURCE_FILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directoryfd)
        try:
            before = os.fstat(fd)
            check_source(before, uid)
            same_path(directoryfd, SOURCE_FILE, fd)
            data = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise Refused('transfer_timeout')
                try:
                    part = os.read(fd, min(4096, MAX_FRAME + 1 - len(data)))
                except InterruptedError:
                    continue
                if not part:
                    break
                data.extend(part)
                if len(data) > MAX_FRAME:
                    raise Refused('source_rejected')
            if snapshot(os.fstat(fd)) != snapshot(before) or len(data) != before.st_size:
                raise Refused('source_changed')
            same_path(directoryfd, SOURCE_FILE, fd)
            same_path(basefd, SOURCE_PARENT, directoryfd)
            if snapshot(os.fstat(directoryfd)) != before_dir:
                raise Refused('source_changed')
            return decode_frame(data)
        finally:
            os.close(fd)
    finally:
        os.close(directoryfd)


def check_volatile(basefd):
    # Exact mount point only; unknown/escaped/alternate filesystems fail closed.
    with open('/proc/self/mountinfo', encoding='ascii') as mountinfo:
        matches = [line.split() for line in mountinfo if line.split()[4] == SOURCE_BASE]
    device = os.fstat(basefd).st_dev
    if (len(matches) != 1 or matches[0][3] != '/'
            or matches[0][2] != str(os.major(device)) + ':' + str(os.minor(device))
            or matches[0][matches[0].index('-') + 1] != 'tmpfs'
            or 'rw' not in matches[0][5].split(',')):
        raise Refused('volatile_storage_required')


def file_route(mode, deadline):
    """Open every fixed component nofollow; recheck the chain before publication."""
    fds = [os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)]
    names = ('run', 'user', '1000')
    try:
        check_directory(fds[0], 0)
        for name in names:
            fds.append(os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=fds[-1]))
        check_directory(fds[1], 0)
        check_directory(fds[2], 0)
        check_directory(fds[3], 1000, 0o700)
        check_volatile(fds[3])
        if mode == 'send-file':
            result = send_file(fds[3], os.environ, deadline, 1000)
        else:
            result = read_source(fds[3], deadline, 1000)
        for index, name in enumerate(names):
            same_path(fds[index], name, fds[index + 1])
        check_volatile(fds[3])
        if mode == 'receive-file':
            stage(fds[1], result, deadline, 0)
        else:
            # Nonsecret identities needed for attributable operator cleanup.
            print('status=source_ready directory_dev_inode=%d:%d file_dev_inode=%d:%d'
                  % (*result[0], *result[1]), flush=True)
    finally:
        for fd in reversed(fds):
            os.close(fd)


def expired(signum, current_frame):
    raise Refused('transfer_timeout')


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else None
    # Receive never examines inherited values. Send clears after selected capture.
    if mode not in ('send', 'send-file'):
        os.environ.clear()
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        signal.signal(signal.SIGALRM, expired)
        signal.alarm(SECONDS)
        deadline = time.monotonic() + SECONDS
        if not sys.flags.isolated:
            raise Refused('isolated_python_required')
        if mode in ('send', 'send-file'):
            if os.getuid() != 1000 or os.geteuid() != 1000:
                raise Refused('sender_role_required')
            if mode == 'send-file':
                file_route(mode, deadline)
            else:
                send(1, os.environ, deadline)
        elif mode in ('receive', 'receive-file'):
            if os.getuid() != 0 or os.geteuid() != 0 or os.getegid() != 0:
                raise Refused('root_receiver_required')
            os.umask(0o077)
            if mode == 'receive-file':
                file_route(mode, deadline)
                print('status=staged id=linear-api-key path=' + DESTINATION, flush=True)
                return 0
            rootfd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                check_directory(rootfd, 0)
                parentfd = os.open('run', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                   dir_fd=rootfd)
                try:
                    receive(0, parentfd, deadline, 0)
                finally:
                    os.close(parentfd)
            finally:
                os.close(rootfd)
            print('status=staged id=linear-api-key path=' + DESTINATION, flush=True)
        else:
            raise Refused('mode_rejected')
        return 0
    except Refused as error:
        # All Refused instances are constructed solely with fixed literals above.
        print('status=' + str(error), file=sys.stderr)
        return 1
    except BaseException:
        print('status=operation_failed', file=sys.stderr)
        return 1
    finally:
        os.environ.clear()
        signal.alarm(0)


if __name__ == '__main__':
    sys.exit(main())
