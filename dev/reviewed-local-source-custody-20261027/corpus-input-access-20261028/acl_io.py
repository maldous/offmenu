"""Linux libacl inode-pinned metadata I/O. Does not read file contents."""
import ctypes as C
import os
import stat

class ACLIOError(RuntimeError):
    pass

class ACLIO:
    DEFAULT = 0x4000
    def __init__(self):
        self.lib = C.CDLL('libacl.so.1', use_errno=True)
        signatures = {
            'acl_get_fd': ([C.c_int], C.c_void_p),
            'acl_get_file': ([C.c_char_p, C.c_int], C.c_void_p),
            'acl_to_any_text': ([C.c_void_p, C.c_char_p, C.c_char, C.c_int], C.c_void_p),
            'acl_free': ([C.c_void_p], C.c_int),
            'acl_from_text': ([C.c_char_p], C.c_void_p),
            'acl_valid': ([C.c_void_p], C.c_int),
            'acl_set_fd': ([C.c_int, C.c_void_p], C.c_int),
            'acl_set_file': ([C.c_char_p, C.c_int, C.c_void_p], C.c_int),
            'acl_delete_def_file': ([C.c_char_p], C.c_int),
        }
        for name, (args, ret) in signatures.items():
            f = getattr(self.lib, name)
            f.argtypes, f.restype = args, ret

    def text(self, acl):
        if not acl:
            raise ACLIOError('ACL read failed')
        p = None
        try:
            p = self.lib.acl_to_any_text(acl, None, b'\n', 0x08)
            if not p:
                raise ACLIOError('ACL serialization failed')
            text = C.string_at(p).decode('ascii')
            return text.rstrip('\n') + '\n' if text else ''
        finally:
            if p:
                self.lib.acl_free(p)
            self.lib.acl_free(acl)

    def get(self, fd, is_dir):
        text = self.text(self.lib.acl_get_fd(fd))
        if is_dir:
            default = self.text(self.lib.acl_get_file(f'/proc/self/fd/{fd}'.encode(), self.DEFAULT))
            text += ''.join('default:' + line + '\n' for line in default.splitlines())
        return text

    def _set(self, fd, text, default=False):
        p = self.lib.acl_from_text(text.encode())
        if not p:
            raise ACLIOError('ACL parse failed')
        try:
            if self.lib.acl_valid(p) != 0:
                raise ACLIOError('ACL validation failed')
            if default:
                r = self.lib.acl_set_file(f'/proc/self/fd/{fd}'.encode(), self.DEFAULT, p)
            else:
                r = self.lib.acl_set_fd(fd, p)
            if r != 0:
                raise ACLIOError('ACL write failed')
        finally:
            self.lib.acl_free(p)

    def put(self, fd, text, is_dir):
        access, default = [], []
        for line in text.splitlines():
            if line.startswith('default:'):
                default.append(line[len('default:'):])
            else:
                access.append(line)
        # Caller has a durable before-record and marks inode touched BEFORE call.
        # Two ACL types necessarily use separate kernel operations.
        self._set(fd, '\n'.join(access) + '\n')
        if default:
            if not is_dir:
                raise ACLIOError('Default ACL on nondirectory')
            self._set(fd, '\n'.join(default) + '\n', default=True)
        elif is_dir and self.lib.acl_delete_def_file(f'/proc/self/fd/{fd}'.encode()) != 0:
            raise ACLIOError('Default ACL removal failed')


def open_inode(path, expected=None):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    s = os.fstat(fd)
    if not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
        os.close(fd)
        raise ACLIOError('Unsupported inode type')
    if expected is not None and (s.st_dev, s.st_ino) != tuple(expected):
        os.close(fd)
        raise ACLIOError('Inode changed')
    return fd, s
