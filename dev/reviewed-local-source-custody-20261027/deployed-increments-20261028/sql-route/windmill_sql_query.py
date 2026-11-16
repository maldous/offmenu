#requirements:
#paramiko==5.1.0
#wmill==1.850.0
"""Trusted public installer receipt pinned 2026-10-27; private draft client.
No secret material is accepted as an argument or intentionally emitted. Commands must
remain within the user's authorized checkout scope; output may contain command data.
"""
import base64
import io
import json
import time

import paramiko
import wmill

HOST = "192.168.1.3"
PORT = 22
USER = "offmenu-wm"
# Fixed values copied from the user-supplied trusted public installer receipt.
SECRET_PATH = "u/admin/foo_ssh_key_20261027"
HOST_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAgv17VNww/UZBfIohmz0jg0Xmim5s8FJuPyi4L9qZ0H"  # OpenSSH public key: algorithm base64 [comment]
DEFAULT_COMMAND = "id; pwd; if command -v git >/dev/null 2>&1; then printf 'git_present=true\\n'; else printf 'git_present=false\\n'; fi"
MAX_REQUEST_BYTES = 65536
MAX_OUTPUT_BYTES = 65536  # per stream; excess is drained and discarded
EXECUTION_SECONDS = 60


def _pin(client):
    fields = HOST_PUBLIC_KEY.split()
    key_types = {"ssh-ed25519": paramiko.Ed25519Key,
                 "ssh-rsa": paramiko.RSAKey,
                 "ecdsa-sha2-nistp256": paramiko.ECDSAKey,
                 "ecdsa-sha2-nistp384": paramiko.ECDSAKey,
                 "ecdsa-sha2-nistp521": paramiko.ECDSAKey}
    if len(fields) < 2 or fields[0] not in key_types:
        raise ValueError("Missing trusted host key")
    key = key_types[fields[0]](data=base64.b64decode(fields[1], validate=True))
    if key.get_name() != fields[0]:
        raise ValueError("Host key type mismatch")
    # Do not load system/user known_hosts; trust only the receipt's exact host key.
    client.get_host_keys().add(HOST, key.get_name(), key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())


def _drain(channel):
    stdout, stderr = bytearray(), bytearray()
    truncated = {"stdout": False, "stderr": False}
    deadline = time.monotonic() + EXECUTION_SECONDS
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Command deadline")
        progress = False
        # One chunk per stream each pass prevents either stream starving the other.
        for label, ready, receive, target in (
            ("stdout", channel.recv_ready, channel.recv, stdout),
            ("stderr", channel.recv_stderr_ready, channel.recv_stderr, stderr),
        ):
            if ready():
                chunk = receive(16384)
                available = MAX_OUTPUT_BYTES - len(target)
                target.extend(chunk[:available])
                truncated[label] |= len(chunk) > available
                progress = True
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            return {"stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "exit_code": channel.recv_exit_status(),
                    "truncated": truncated}
        if not progress:
            time.sleep(0.01)


def _confined_exec(command: str = DEFAULT_COMMAND):
    client = None
    channel = None
    secret = None
    private_key = None
    try:
        if not SECRET_PATH or not HOST_PUBLIC_KEY:
            return {"ok": False, "error_class": "UnconfiguredTrustedReceipt"}
        if not isinstance(command, str) or not command or "\x00" in command:
            return {"ok": False, "error_class": "InvalidCommand"}
        payload = json.dumps({"command": command}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            return {"ok": False, "error_class": "RequestTooLarge"}
        client = paramiko.SSHClient()
        _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as key_stream:
            private_key = paramiko.Ed25519Key.from_private_key(key_stream)
        secret = None
        client.connect(HOST, port=PORT, username=USER, pkey=private_key,
                       allow_agent=False, look_for_keys=False,
                       timeout=5, banner_timeout=5, auth_timeout=5,
                       channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise ConnectionError("Unauthenticated transport")
        channel = transport.open_session(timeout=5)
        channel.settimeout(5)
        # No PTY, shell, SFTP, forwarding, or remote command interpolation.
        channel.exec_command("offmenu-exec-v1")
        channel.sendall(payload)
        channel.shutdown_write()
        result = _drain(channel)
        result["ok"] = result["exit_code"] == 0
        return result
    except Exception as error:
        # No error messages, tracebacks, credential objects, or payload logging.
        return {"ok": False, "error_class": type(error).__name__[:64]}
    finally:
        secret = None
        private_key = None
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


_QUERY_SOURCE_B64 = 'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiJSZXZpZXdlZCBTRUxFQ1Qgb3ZlciBhIGZpbmFsaXplZCBsb2NhbCBQYXJxdWV0IGlucHV0LCB3aXRoIGxvY2FsLW9ubHkgb3V0cHV0LgoKVXNlIHRocm91Z2ggdGhlIGV4aXN0aW5nIGNhcGFjaXR5LWFkbWl0dGVkIEZvbyBydW5uZXIsIG5vdCBhcyBhbiBTUUwgc2VjdXJpdHkKc2FuZGJveC4gSW5wdXRzL1NRTCBhcmUgdHJ1c3RlZCBhbmQgZXhwbGljaXRseSBzZWxlY3RlZCBieSB0aGUgb3duZXIuIFRoZSBlbmdpbmUKdXNlcyBhbiBpbmRlcGVuZGVudCBpbi1tZW1vcnkgY29ubmVjdGlvbiBhbmQgbmV2ZXIgb3BlbnMgdGhlIGxpdmUgU1FMaXRlIERCLgoiIiIKZnJvbSBfX2Z1dHVyZV9fIGltcG9ydCBhbm5vdGF0aW9ucwoKaW1wb3J0IGFyZ3BhcnNlCmltcG9ydCBoYXNobGliCmltcG9ydCBpbXBvcnRsaWIKaW1wb3J0IGpzb24KaW1wb3J0IG1hdGgKaW1wb3J0IG9zCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aAppbXBvcnQgcmUKaW1wb3J0IHJlc291cmNlCmltcG9ydCBzdGF0CmltcG9ydCBzeXMKaW1wb3J0IHRocmVhZGluZwppbXBvcnQgdGltZQoKR0lCID0gMTAyNCoqMwpST09UID0gUGF0aCgnL29mZm1lbnUvZGF0YS8ub2ZmbWVudS1wbGF0Zm9ybScpClJVTlRJTUUgPSBST09UIC8gJ2R1Y2tkYi8xLjUuNi1iYzk2MTllZDdkNGYnCk9VVFBVVF9ST09UID0gUk9PVCAvICdzcWxfcXVlcmllcycKSk9CID0gcmUuY29tcGlsZShyJ1tBLVphLXowLTldW0EtWmEtejAtOV8uLV17MCw3OX1cWicpClZFUlNJT04gPSAnMS41LjYnCk1BWF9TUUwgPSAzMjAwMAoKCmRlZiBlbmNvZGUodmFsdWUpOgogICAgcmV0dXJuIChqc29uLmR1bXBzKHZhbHVlLCBzb3J0X2tleXM9VHJ1ZSwgc2VwYXJhdG9ycz0oJywnLCAnOicpLCBhbGxvd19uYW49RmFsc2UpICsgJ1xuJykuZW5jb2RlKCkKCgpkZWYgc2hhKGRhdGEpOgogICAgcmV0dXJuIGhhc2hsaWIuc2hhMjU2KGRhdGEpLmhleGRpZ2VzdCgpCgoKZGVmIGNhbm9uaWNhbF9wYXRoKHZhbHVlLCAqLCBleGlzdGluZz1GYWxzZSk6CiAgICBwYXRoID0gUGF0aCh2YWx1ZSkKICAgIGlmIG5vdCBwYXRoLmlzX2Fic29sdXRlKCkgb3Igc3RyKHBhdGgpICE9IHN0cih2YWx1ZSkgb3IgJy4uJyBpbiBwYXRoLnBhcnRzOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1BBVEhfQ0FOT05JQ0FMX1JFUVVJUkVEJykKICAgIGlmIGFueShwLmlzX3N5bWxpbmsoKSBmb3IgcCBpbiAocGF0aCwgKnBhdGgucGFyZW50cykpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1NZTUxJTktfUkVGVVNFRCcpCiAgICBpZiBleGlzdGluZyBhbmQgbm90IHBhdGguaXNfZmlsZSgpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JFR1VMQVJfSU5QVVRfUkVRVUlSRUQnKQogICAgcmV0dXJuIHBhdGgKCgpkZWYgc2VsZWN0ZWRfZmlsZShwYXRoLCBsaW1pdD1Ob25lKToKICAgIHBhdGggPSBjYW5vbmljYWxfcGF0aChwYXRoLCBleGlzdGluZz1UcnVlKQogICAgZmQgPSBvcy5vcGVuKHBhdGgsIG9zLk9fUkRPTkxZIHwgb3MuT19OT0ZPTExPVyB8IG9zLk9fTk9OQkxPQ0spCiAgICB3aXRoIG9zLmZkb3BlbihmZCwgJ3JiJykgYXMgc3RyZWFtOgogICAgICAgIGJlZm9yZSA9IG9zLmZzdGF0KHN0cmVhbS5maWxlbm8oKSkKICAgICAgICBpZiBub3Qgc3RhdC5TX0lTUkVHKGJlZm9yZS5zdF9tb2RlKToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUkVHVUxBUl9JTlBVVF9SRVFVSVJFRCcpCiAgICAgICAgaWYgbGltaXQgaXMgTm9uZToKICAgICAgICAgICAgcmV0dXJuIGlkZW50aXR5KGJlZm9yZSkKICAgICAgICB2YWx1ZSA9IHN0cmVhbS5yZWFkKGxpbWl0ICsgMSkKICAgICAgICBpZiBsZW4odmFsdWUpID4gbGltaXQgb3IgaWRlbnRpdHkoYmVmb3JlKSAhPSBpZGVudGl0eShvcy5mc3RhdChzdHJlYW0uZmlsZW5vKCkpKToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSU5QVVRfU0laRV9PUl9DSEFOR0UnKQogICAgICAgIHJldHVybiB2YWx1ZQoKCmRlZiBpZGVudGl0eShzdCk6CiAgICByZXR1cm4geydkZXZpY2UnOiBzdC5zdF9kZXYsICdpbm9kZSc6IHN0LnN0X2lubywgJ2J5dGVzJzogc3Quc3Rfc2l6ZSwKICAgICAgICAgICAgJ210aW1lX25zJzogc3Quc3RfbXRpbWVfbnMsICdjdGltZV9ucyc6IHN0LnN0X2N0aW1lX25zfQoKCmRlZiBtYWtlX3BsYW4oam9iX2lkLCBpbnB1dF9wYXRoLCBzcWxfcGF0aCwgKiwgdGhyZWFkcz00LCBtZW1vcnlfZ2liPTgsCiAgICAgICAgICAgICAgc3BpbGxfZ2liPTIwLCByZXN1bHRfZ2liPTIpOgogICAgIiIiT25lIHByb2Nlc3MsIG1hbnkgZW5naW5lIHRocmVhZHM7IHJlc2VydmUgQ1BVL1JBTS9kaXNrIG9uY2UgcGVyIHF1ZXJ5LgoKICAgIDI3IENQVSAvIDU0IEdpQiAvIDY0IEdpQiBhcmUgdGhlIGN1cnJlbnQgYWRtaXR0ZWQgcGVyLWpvYiBsaW1pdHMsIG5vdCBhbgogICAgb3B0aW11bSBvciBhIHJlcXVlc3QgdG8gY29uc3VtZSBhbGwgY2FwYWNpdHkuIEFkbWlzc2lvbiBpcyBhdXRob3JpdGF0aXZlLgogICAgIiIiCiAgICBpZiBub3QgaXNpbnN0YW5jZShqb2JfaWQsIHN0cikgb3Igbm90IEpPQi5mdWxsbWF0Y2goam9iX2lkKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdKT0JfSURfSU5WQUxJRCcpCiAgICByYW5nZXMgPSB7J3RocmVhZHMnOiAodGhyZWFkcywgMSwgMjcpLCAnbWVtb3J5X2dpYic6IChtZW1vcnlfZ2liLCAxLCA0MyksCiAgICAgICAgICAgICAgJ3NwaWxsX2dpYic6IChzcGlsbF9naWIsIDEsIDYyKSwgJ3Jlc3VsdF9naWInOiAocmVzdWx0X2dpYiwgMSwgNjIpfQogICAgZm9yIHZhbHVlLCBsb3csIGhpZ2ggaW4gcmFuZ2VzLnZhbHVlcygpOgogICAgICAgIGlmIHR5cGUodmFsdWUpIGlzIG5vdCBpbnQgb3Igbm90IGxvdyA8PSB2YWx1ZSA8PSBoaWdoOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdRVUVSWV9CVURHRVRfSU5WQUxJRCcpCiAgICAjIEJ1ZmZlciBsaW1pdHMgYXJlIG5vdCBwcm9jZXNzLVJTUyBsaW1pdHM6IHJlc2VydmUgYXQgbGVhc3QgMjUlIHBsdXMgMSBHaUIuCiAgICBwcm9jZXNzX21lbW9yeSA9IG1hdGguY2VpbChtZW1vcnlfZ2liICogMS4yNSkgKiBHSUIgKyBHSUIKICAgIG91dHB1dF9ieXRlcyA9IChzcGlsbF9naWIgKyByZXN1bHRfZ2liKSAqIEdJQiArIDEwMjQqKjIKICAgIGlmIHByb2Nlc3NfbWVtb3J5ID4gNTQgKiBHSUIgb3Igb3V0cHV0X2J5dGVzID4gNjQgKiBHSUI6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUVVFUllfQlVER0VUX0VYQ0VFRFNfQURNSVNTSU9OJykKICAgIHNvdXJjZSwgc3FsID0gY2Fub25pY2FsX3BhdGgoaW5wdXRfcGF0aCksIGNhbm9uaWNhbF9wYXRoKHNxbF9wYXRoKQogICAgZm9yIHBhdGggaW4gKHNvdXJjZSwgc3FsKToKICAgICAgICBpZiBub3QgcGF0aC5pc19yZWxhdGl2ZV90bygnL29mZm1lbnUnKToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSU5QVVRfT1VUU0lERV9BUFBST1ZFRF9DSEVDS09VVCcpCiAgICBpZiBzb3VyY2Uuc3VmZml4Lmxvd2VyKCkgIT0gJy5wYXJxdWV0JzoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdGSU5BTElaRURfUEFSUVVFVF9SRVFVSVJFRCcpCiAgICBvdXRwdXQgPSBPVVRQVVRfUk9PVCAvIGpvYl9pZAogICAgaWYgc291cmNlLmlzX3JlbGF0aXZlX3RvKG91dHB1dCkgb3Igc3FsLmlzX3JlbGF0aXZlX3RvKG91dHB1dCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSU5QVVRfT1VUUFVUX09WRVJMQVAnKQogICAgcmV0dXJuIHsnZm9ybWF0JzogJ29mZm1lbnUtZHVja2RiLXF1ZXJ5LXBsYW4tdjEnLCAnam9iX2lkJzogam9iX2lkLAogICAgICAgICAgICAnaW5wdXRfcGF0aCc6IHN0cihzb3VyY2UpLCAnc3FsX3BhdGgnOiBzdHIoc3FsKSwgJ291dHB1dF9kaXInOiBzdHIob3V0cHV0KSwKICAgICAgICAgICAgJ2VuZ2luZSc6IHsndmVyc2lvbic6IFZFUlNJT04sICd0aHJlYWRzJzogdGhyZWFkcywKICAgICAgICAgICAgICAgICAgICAgICAnbWVtb3J5X2dpYic6IG1lbW9yeV9naWIsICdzcGlsbF9naWInOiBzcGlsbF9naWJ9LAogICAgICAgICAgICAncmVzdWx0X21heF9ieXRlcyc6IHJlc3VsdF9naWIgKiBHSUIsCiAgICAgICAgICAgICdyZXNvdXJjZXMnOiB7J3dvcmtlcnMnOiAxLCAnb3ZlcmhlYWRfcHJvY2Vzc2VzJzogMiwKICAgICAgICAgICAgICAgICAgICAgICAgICAnY3B1X21pbGxpcyc6IHRocmVhZHMgKiAxMDAwLCAnbWVtb3J5X2J5dGVzJzogcHJvY2Vzc19tZW1vcnksCiAgICAgICAgICAgICAgICAgICAgICAgICAgJ291dHB1dF9ieXRlcyc6IG91dHB1dF9ieXRlcywKICAgICAgICAgICAgICAgICAgICAgICAgICAncmVhZF9yb290cyc6IHNvcnRlZCh7c3RyKHNvdXJjZS5wYXJlbnQpLCBzdHIoc3FsLnBhcmVudCksIHN0cihSVU5USU1FKX0pLAogICAgICAgICAgICAgICAgICAgICAgICAgICd3cml0ZV9yb290cyc6IFtzdHIob3V0cHV0KV19fQoKCmRlZiB2YWxpZGF0ZV9wbGFuKHBsYW4pOgogICAgaWYgbm90IGlzaW5zdGFuY2UocGxhbiwgZGljdCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUExBTl9JTlZBTElEJykKICAgIHRyeToKICAgICAgICBlbmdpbmUgPSBwbGFuWydlbmdpbmUnXQogICAgICAgIGRlc2lyZWQgPSBtYWtlX3BsYW4ocGxhblsnam9iX2lkJ10sIHBsYW5bJ2lucHV0X3BhdGgnXSwgcGxhblsnc3FsX3BhdGgnXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRocmVhZHM9ZW5naW5lWyd0aHJlYWRzJ10sIG1lbW9yeV9naWI9ZW5naW5lWydtZW1vcnlfZ2liJ10sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzcGlsbF9naWI9ZW5naW5lWydzcGlsbF9naWInXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJlc3VsdF9naWI9cGxhblsncmVzdWx0X21heF9ieXRlcyddIC8vIEdJQikKICAgIGV4Y2VwdCAoS2V5RXJyb3IsIFR5cGVFcnJvciwgWmVyb0RpdmlzaW9uRXJyb3IpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1BMQU5fSU5WQUxJRCcpIGZyb20gTm9uZQogICAgaWYgcGxhbiAhPSBkZXNpcmVkOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1BMQU5fUkVTRVJWQVRJT05fTUlTTUFUQ0gnKQogICAgcmV0dXJuIGRlc2lyZWQKCgpkZWYgY29ubmVjdChwbGFuLCB0ZW1wKToKICAgICMgVXNlcyB0aGUgYWxyZWFkeS1pbnN0YWxsZWQgcGlubmVkIHBhY2thZ2U7IGRvZXMgbm90IGFsdGVyIHRoZSBvbGQgcnVudGltZSwKICAgICMgZGVwZW5kZW5jaWVzLCBjcmVkZW50aWFscywgaG9zdCBzZXR0aW5ncyBvciBzZWN1cml0eSBjb25maWd1cmF0aW9uLgogICAgZW5naW5lID0gcGxhblsnZW5naW5lJ10KICAgIGlmIGVuZ2luZVsndGhyZWFkcyddID4gbGVuKG9zLnNjaGVkX2dldGFmZmluaXR5KDApKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdFTkdJTkVfVEhSRUFEU19FWENFRURfQVNTSUdORURfQ1BVUycpCiAgICBzeXMucGF0aC5pbnNlcnQoMCwgc3RyKFJVTlRJTUUgLyAndmVudi9saWIvcHl0aG9uMy4xMi9zaXRlLXBhY2thZ2VzJykpCiAgICBkdWNrZGIgPSBpbXBvcnRsaWIuaW1wb3J0X21vZHVsZSgnZHVja2RiJykKICAgIGlmIGR1Y2tkYi5fX3ZlcnNpb25fXyAhPSBWRVJTSU9OOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0VOR0lORV9WRVJTSU9OX01JU01BVENIJykKICAgIGNvbiA9IGR1Y2tkYi5jb25uZWN0KCc6bWVtb3J5OicsIGNvbmZpZz17CiAgICAgICAgJ3RocmVhZHMnOiBzdHIoZW5naW5lWyd0aHJlYWRzJ10pLCAnbWVtb3J5X2xpbWl0Jzogc3RyKGVuZ2luZVsnbWVtb3J5X2dpYiddKSArICdHaUInLAogICAgICAgICdtYXhfdGVtcF9kaXJlY3Rvcnlfc2l6ZSc6IHN0cihlbmdpbmVbJ3NwaWxsX2dpYiddKSArICdHaUInLAogICAgICAgICd0ZW1wX2RpcmVjdG9yeSc6IHN0cih0ZW1wKSwgJ2F1dG9pbnN0YWxsX2tub3duX2V4dGVuc2lvbnMnOiAnZmFsc2UnLAogICAgICAgICdhdXRvbG9hZF9rbm93bl9leHRlbnNpb25zJzogJ2ZhbHNlJywgJ2FsbG93X2NvbW11bml0eV9leHRlbnNpb25zJzogJ2ZhbHNlJywKICAgICAgICAnYWxsb3dfdW5zaWduZWRfZXh0ZW5zaW9ucyc6ICdmYWxzZSd9KQogICAgdHJ5OgogICAgICAgIGNvbi5leGVjdXRlKCdTRVQgYWxsb3dlZF9wYXRocyA9ID8nLCBbW3BsYW5bJ2lucHV0X3BhdGgnXV1dKQogICAgICAgIGNvbi5leGVjdXRlKCdTRVQgYWxsb3dlZF9kaXJlY3RvcmllcyA9ID8nLCBbW3N0cihQYXRoKHBsYW5bJ291dHB1dF9kaXInXSkpICsgJy8nXV0pCiAgICAgICAgY29uLmV4ZWN1dGUoJ1NFVCBlbmFibGVfZXh0ZXJuYWxfYWNjZXNzID0gZmFsc2UnKQogICAgICAgIGNvbi5leGVjdXRlKCdTRVQgbG9ja19jb25maWd1cmF0aW9uID0gdHJ1ZScpCiAgICAgICAgcmV0dXJuIGNvbgogICAgZXhjZXB0IEJhc2VFeGNlcHRpb246CiAgICAgICAgY29uLmNsb3NlKCkKICAgICAgICByYWlzZQoKCmRlZiBwcml2YXRlX2RpcihwYXRoKToKICAgIGNhbm9uaWNhbF9wYXRoKHBhdGgpCiAgICB0cnk6CiAgICAgICAgcGF0aC5ta2Rpcihtb2RlPTBvNzAwKQogICAgZXhjZXB0IEZpbGVFeGlzdHNFcnJvcjoKICAgICAgICBwYXNzCiAgICBlbHNlOgogICAgICAgIHN5bmNfZGlyKHBhdGgucGFyZW50KQogICAgc3QgPSBwYXRoLnN0YXQoKQogICAgaWYgbm90IHBhdGguaXNfZGlyKCkgb3Igc3Quc3RfdWlkICE9IG9zLmdldHVpZCgpIG9yIHN0LnN0X21vZGUgJiAwbzA3NzoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdQUklWQVRFX09VVFBVVF9ESVJFQ1RPUllfUkVRVUlSRUQnKQoKCmRlZiBzeW5jX2RpcihwYXRoKToKICAgIGZkID0gb3Mub3BlbihwYXRoLCBvcy5PX0RJUkVDVE9SWSB8IG9zLk9fTk9GT0xMT1cpCiAgICB0cnk6CiAgICAgICAgb3MuZnN5bmMoZmQpCiAgICBmaW5hbGx5OgogICAgICAgIG9zLmNsb3NlKGZkKQoKCmRlZiB3cml0ZV9uZXcocGF0aCwgZGF0YSk6CiAgICBmZCA9IG9zLm9wZW4ocGF0aCwgb3MuT19XUk9OTFkgfCBvcy5PX0NSRUFUIHwgb3MuT19FWENMIHwgb3MuT19OT0ZPTExPVywgMG82MDApCiAgICB3aXRoIG9zLmZkb3BlbihmZCwgJ3diJykgYXMgc3RyZWFtOgogICAgICAgIHN0cmVhbS53cml0ZShkYXRhKQogICAgICAgIHN0cmVhbS5mbHVzaCgpCiAgICAgICAgb3MuZnN5bmMoc3RyZWFtLmZpbGVubygpKQogICAgc3luY19kaXIocGF0aC5wYXJlbnQpCgoKZGVmIGhhc2hfZmlsZShwYXRoKToKICAgIGggPSBoYXNobGliLnNoYTI1NigpCiAgICB3aXRoIG9wZW4ocGF0aCwgJ3JiJykgYXMgc3RyZWFtOgogICAgICAgIHdoaWxlIHZhbHVlIDo9IHN0cmVhbS5yZWFkKDEwMjQqKjIpOgogICAgICAgICAgICBoLnVwZGF0ZSh2YWx1ZSkKICAgIHJldHVybiBoLmhleGRpZ2VzdCgpCgoKZGVmIGJvdW5kZWRfY29weShjb24sIHRhcmdldCwgbWF4aW11bSk6CiAgICAiIiJTYW1wbGVkIG91dHB1dCBndWFyZCwgbm90IGEgZmlsZXN5c3RlbSBxdW90YTsgYnJpZWYgb3ZlcnNob290IGlzIHBvc3NpYmxlLiIiIgogICAgc3RvcCwgZXhjZWVkZWQgPSB0aHJlYWRpbmcuRXZlbnQoKSwgdGhyZWFkaW5nLkV2ZW50KCkKICAgIGRlZiB3YXRjaCgpOgogICAgICAgIHdoaWxlIG5vdCBzdG9wLndhaXQoMC4wNSk6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIG92ZXIgPSB0YXJnZXQuc3RhdCgpLnN0X3NpemUgPiBtYXhpbXVtCiAgICAgICAgICAgIGV4Y2VwdCBGaWxlTm90Rm91bmRFcnJvcjoKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGV4Y2VwdCBPU0Vycm9yOgogICAgICAgICAgICAgICAgb3ZlciA9IFRydWUgICMgVW5vYnNlcnZhYmxlIG91dHB1dCBpcyBub3Qgc2FmZSB0byBrZWVwIGdyb3dpbmcuCiAgICAgICAgICAgIGlmIG92ZXI6CiAgICAgICAgICAgICAgICBleGNlZWRlZC5zZXQoKQogICAgICAgICAgICAgICAgY29uLmludGVycnVwdCgpCiAgICAgICAgICAgICAgICByZXR1cm4KICAgIHdhdGNoZXIgPSB0aHJlYWRpbmcuVGhyZWFkKHRhcmdldD13YXRjaCwgbmFtZT0ncmVzdWx0LWJ1ZGdldCcsIGRhZW1vbj1UcnVlKQogICAgd2F0Y2hlci5zdGFydCgpCiAgICB0cnk6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByb3dzID0gY29uLmV4ZWN1dGUoJ0VYUExBSU4gQU5BTFlaRSBDT1BZIChTRUxFQ1QgKiBGUk9NIF9vZmZtZW51X3F1ZXJ5X291dHB1dCkgJwogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgJ1RPID8gKEZPUk1BVCBQQVJRVUVULCBDT01QUkVTU0lPTiBaU1REKScsIFtzdHIodGFyZ2V0KV0pLmZldGNoYWxsKCkKICAgICAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICBpZiBleGNlZWRlZC5pc19zZXQoKToKICAgICAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JFU1VMVF9CVURHRVRfRVhDRUVERUQnKSBmcm9tIE5vbmUKICAgICAgICAgICAgcmFpc2UKICAgIGZpbmFsbHk6CiAgICAgICAgc3RvcC5zZXQoKQogICAgICAgIHdhdGNoZXIuam9pbigpCiAgICBpZiBleGNlZWRlZC5pc19zZXQoKSBvciB0YXJnZXQuc3RhdCgpLnN0X3NpemUgPiBtYXhpbXVtOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JFU1VMVF9CVURHRVRfRVhDRUVERUQnKQogICAgcmV0dXJuIHJvd3MKCgpkZWYgcnVuKHBsYW4sICosIGNvbm5lY3Rvcj1jb25uZWN0KToKICAgIHBsYW4gPSB2YWxpZGF0ZV9wbGFuKHBsYW4pCiAgICBzb3VyY2UgPSBQYXRoKHBsYW5bJ2lucHV0X3BhdGgnXSkKICAgIHNxbCA9IHNlbGVjdGVkX2ZpbGUocGxhblsnc3FsX3BhdGgnXSwgTUFYX1NRTCkuZGVjb2RlKCd1dGYtOCcpCiAgICBiZWZvcmUgPSBzZWxlY3RlZF9maWxlKHNvdXJjZSkKICAgIG91dHB1dCA9IFBhdGgocGxhblsnb3V0cHV0X2RpciddKQogICAgIyBPd25lci1wcml2YXRlIHJvb3RzIGFscmVhZHkgZXhpc3QgZnJvbSBpbnN0YWxsYXRpb24uIE5ldmVyIGNyZWF0ZSAvb2ZmbWVudS4KICAgIGlmIG5vdCBST09ULmlzX2RpcigpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JVTlRJTUVfUk9PVF9NSVNTSU5HJykKICAgIHByaXZhdGVfZGlyKFJPT1QpCiAgICBwcml2YXRlX2RpcihPVVRQVVRfUk9PVCkKICAgIG91dHB1dC5ta2Rpcihtb2RlPTBvNzAwKSAgIyBFeGNsdXNpdmUgSUQ6IG5vIG92ZXJ3cml0ZSwgcmVwbGF5IG9yIHJlc3VtZS4KICAgIHN5bmNfZGlyKG91dHB1dC5wYXJlbnQpCiAgICB0ZW1wID0gb3V0cHV0IC8gJ3NwaWxsJwogICAgdGVtcC5ta2Rpcihtb2RlPTBvNzAwKQogICAgc3luY19kaXIodGVtcC5wYXJlbnQpCiAgICB3cml0ZV9uZXcob3V0cHV0IC8gJ3BsYW4uanNvbicsIGVuY29kZShwbGFuKSkKICAgIGNvbiA9IGNvbm5lY3RvcihwbGFuLCB0ZW1wKQogICAgdHJ5OgogICAgICAgIHN0YXRlbWVudHMgPSBjb24uZXh0cmFjdF9zdGF0ZW1lbnRzKHNxbCkKICAgICAgICBpZiBsZW4oc3RhdGVtZW50cykgIT0gMSBvciBzdHIoc3RhdGVtZW50c1swXS50eXBlKSAhPSAnU3RhdGVtZW50VHlwZS5TRUxFQ1QnOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdPTkVfU0VMRUNUX1JFUVVJUkVEJykKICAgICAgICAjIFNRTCBpcyBvd25lci1yZXZpZXdlZCwgbm90IGFyYml0cmFyeSBTUUwgZnJvbSBhbiB1bnRydXN0ZWQgd2ViIHVzZXIuCiAgICAgICAgY29uLnJlYWRfcGFycXVldChzdHIoc291cmNlKSkuY3JlYXRlX3ZpZXcoJ2lucHV0X2RhdGEnKQogICAgICAgIGNvbi5zcWwoc3FsKS5jcmVhdGVfdmlldygnX29mZm1lbnVfcXVlcnlfb3V0cHV0JykKICAgICAgICBpbnB1dF9tZXRhZGF0YSA9IGNvbi5leGVjdXRlKCdTRUxFQ1QgbnVtX3Jvd3MsIG51bV9yb3dfZ3JvdXBzIEZST00gcGFycXVldF9maWxlX21ldGFkYXRhKD8pJywKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFtzdHIoc291cmNlKV0pLmZldGNob25lKCkKICAgICAgICB0YXJnZXQgPSBvdXRwdXQgLyAncmVzdWx0LnBhcnF1ZXQnCiAgICAgICAgc3RhcnQsIGNwdSA9IHRpbWUucGVyZl9jb3VudGVyKCksIHRpbWUucHJvY2Vzc190aW1lKCkKICAgICAgICAjIEFOQUxZWkUgZXhlY3V0ZXMgdGhpcyBDT1BZIG9uY2U6IG5vIHNlY29uZCBkYXRhIHNjYW4ganVzdCBmb3IgcHJvZmlsaW5nLgogICAgICAgIHByb2ZpbGUgPSBib3VuZGVkX2NvcHkoY29uLCB0YXJnZXQsIHBsYW5bJ3Jlc3VsdF9tYXhfYnl0ZXMnXSkKICAgICAgICBlbGFwc2VkLCBjcHVfc2Vjb25kcyA9IHRpbWUucGVyZl9jb3VudGVyKCkgLSBzdGFydCwgdGltZS5wcm9jZXNzX3RpbWUoKSAtIGNwdQogICAgICAgIGlmIHNlbGVjdGVkX2ZpbGUoc291cmNlKSAhPSBiZWZvcmU6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0lOUFVUX0NIQU5HRURfRFVSSU5HX1FVRVJZJykKICAgICAgICBzaXplID0gdGFyZ2V0LnN0YXQoKS5zdF9zaXplCiAgICAgICAgaWYgc2l6ZSA+IHBsYW5bJ3Jlc3VsdF9tYXhfYnl0ZXMnXToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUkVTVUxUX0JVREdFVF9FWENFRURFRCcpCiAgICAgICAgb3MuY2htb2QodGFyZ2V0LCAwbzYwMCkKICAgICAgICBmZCA9IG9zLm9wZW4odGFyZ2V0LCBvcy5PX1JET05MWSB8IG9zLk9fTk9GT0xMT1cpCiAgICAgICAgdHJ5OgogICAgICAgICAgICBvcy5mc3luYyhmZCkKICAgICAgICBmaW5hbGx5OgogICAgICAgICAgICBvcy5jbG9zZShmZCkKICAgICAgICByb3dzID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBudW1fcm93cyBGUk9NIHBhcnF1ZXRfZmlsZV9tZXRhZGF0YSg/KScsIFtzdHIodGFyZ2V0KV0pLmZldGNob25lKClbMF0KICAgICAgICBwcm9maWxlX2J5dGVzID0gZW5jb2RlKHByb2ZpbGUpCiAgICAgICAgaWYgbGVuKHByb2ZpbGVfYnl0ZXMpID4gMTAyNCoqMjoKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUFJPRklMRV9CVURHRVRfRVhDRUVERUQnKQogICAgICAgIHdyaXRlX25ldyhvdXRwdXQgLyAncHJvZmlsZS5qc29uJywgcHJvZmlsZV9ieXRlcykKICAgICAgICByZWNlaXB0ID0geydmb3JtYXQnOiAnb2ZmbWVudS1kdWNrZGItcXVlcnktcmVjZWlwdC12MScsICdqb2JfaWQnOiBwbGFuWydqb2JfaWQnXSwKICAgICAgICAgICAgICAgICAgICdzdGF0dXMnOiAnY29tcGxldGVkJywgJ3BsYW5fc2hhMjU2Jzogc2hhKGVuY29kZShwbGFuKSksCiAgICAgICAgICAgICAgICAgICAnc3FsX3NoYTI1Nic6IHNoYShzcWwuZW5jb2RlKCkpLCAnaW5wdXRfc3RhdCc6IGJlZm9yZSwKICAgICAgICAgICAgICAgICAgICdpbnB1dF9jb250ZW50X2hhc2hfdmVyaWZpZWQnOiBGYWxzZSwKICAgICAgICAgICAgICAgICAgICdpbnB1dF9yb3dzJzogaW5wdXRfbWV0YWRhdGFbMF0sICdpbnB1dF9yb3dfZ3JvdXBzJzogaW5wdXRfbWV0YWRhdGFbMV0sCiAgICAgICAgICAgICAgICAgICAnZW5naW5lJzogcGxhblsnZW5naW5lJ10sICdyZXN1bHRfcm93cyc6IHJvd3MsICdyZXN1bHRfYnl0ZXMnOiBzaXplLAogICAgICAgICAgICAgICAgICAgJ3Jlc3VsdF9zaGEyNTYnOiBoYXNoX2ZpbGUodGFyZ2V0KSwgJ3Byb2ZpbGVfc2hhMjU2Jzogc2hhKHByb2ZpbGVfYnl0ZXMpLAogICAgICAgICAgICAgICAgICAgJ3F1ZXJ5X3dhbGxfc2Vjb25kcyc6IGVsYXBzZWQsICdxdWVyeV9jcHVfc2Vjb25kcyc6IGNwdV9zZWNvbmRzLAogICAgICAgICAgICAgICAgICAgJ2NwdV90b193YWxsX3JhdGlvJzogY3B1X3NlY29uZHMgLyBlbGFwc2VkIGlmIGVsYXBzZWQgZWxzZSAwLAogICAgICAgICAgICAgICAgICAgJ3Byb2Nlc3NfcGVha19yc3Nfa2liJzogcmVzb3VyY2UuZ2V0cnVzYWdlKHJlc291cmNlLlJVU0FHRV9TRUxGKS5ydV9tYXhyc3MsCiAgICAgICAgICAgICAgICAgICAnc2VjdXJpdHknOiB7J2V4dGVybmFsX2FjY2Vzcyc6IEZhbHNlLCAnZXh0ZW5zaW9uX2F1dG9sb2FkJzogRmFsc2UsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgJ2V4dGVuc2lvbl9hdXRvaW5zdGFsbCc6IEZhbHNlLCAnY29uZmlndXJhdGlvbl9sb2NrZWQnOiBUcnVlfX0KICAgICAgICAjIExhc3QgZmlsZSBpcyB0aGUgY29tcGxldGlvbiBtYXJrZXIuIEZhaWxlZC9pbmNvbXBsZXRlIG91dHB1dHMgYXJlIGtlcHQKICAgICAgICAjIGxvY2FsIGZvciByZWNvbmNpbGlhdGlvbiwgbmV2ZXIgY2FsbGVkIGNvbXBsZXRlZCBvciBzaWxlbnRseSByZXRyaWVkLgogICAgICAgIHdyaXRlX25ldyhvdXRwdXQgLyAncmVjZWlwdC5qc29uJywgZW5jb2RlKHJlY2VpcHQpKQogICAgICAgIHJldHVybiByZWNlaXB0CiAgICBmaW5hbGx5OgogICAgICAgIGNvbi5jbG9zZSgpCgoKZGVmIHJlYWRfc3RhdHVzKGpvYl9pZCk6CiAgICBpZiBub3QgaXNpbnN0YW5jZShqb2JfaWQsIHN0cikgb3Igbm90IEpPQi5mdWxsbWF0Y2goam9iX2lkKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdKT0JfSURfSU5WQUxJRCcpCiAgICBvdXRwdXQgPSBjYW5vbmljYWxfcGF0aChPVVRQVVRfUk9PVCAvIGpvYl9pZCkKICAgIHJlY2VpcHRfcGF0aCA9IG91dHB1dCAvICdyZWNlaXB0Lmpzb24nCiAgICBpZiBub3QgcmVjZWlwdF9wYXRoLmV4aXN0cygpOgogICAgICAgIHJldHVybiB7J2pvYl9pZCc6IGpvYl9pZCwgJ3N0YXR1cyc6ICdpbmNvbXBsZXRlJyBpZiBvdXRwdXQuZXhpc3RzKCkgZWxzZSAnbm90X2ZvdW5kJ30KICAgIHZhbHVlID0ganNvbi5sb2FkcyhzZWxlY3RlZF9maWxlKHJlY2VpcHRfcGF0aCwgTUFYX1NRTCkpCiAgICBwbGFuID0gdmFsaWRhdGVfcGxhbihqc29uLmxvYWRzKHNlbGVjdGVkX2ZpbGUob3V0cHV0IC8gJ3BsYW4uanNvbicsIE1BWF9TUUwpKSkKICAgIGlmICh2YWx1ZS5nZXQoJ2Zvcm1hdCcpICE9ICdvZmZtZW51LWR1Y2tkYi1xdWVyeS1yZWNlaXB0LXYxJwogICAgICAgICAgICBvciB2YWx1ZS5nZXQoJ2pvYl9pZCcpICE9IGpvYl9pZCBvciB2YWx1ZS5nZXQoJ3N0YXR1cycpICE9ICdjb21wbGV0ZWQnCiAgICAgICAgICAgIG9yIHZhbHVlLmdldCgncGxhbl9zaGEyNTYnKSAhPSBzaGEoZW5jb2RlKHBsYW4pKSk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUkVDRUlQVF9JREVOVElUWV9JTlZBTElEJykKICAgICMgU21hbGwgYWxsb3dsaXN0ZWQgc3RhdHVzLCBuZXZlciBTUUwvcHJvZmlsZSB0ZXh0IG9yIGFjdHVhbCByZXN1bHQgcm93cy4KICAgIGludGVnZXJzID0gKCdpbnB1dF9yb3dzJywgJ2lucHV0X3Jvd19ncm91cHMnLCAncmVzdWx0X3Jvd3MnLCAncmVzdWx0X2J5dGVzJywgJ3Byb2Nlc3NfcGVha19yc3Nfa2liJykKICAgIGZsb2F0cyA9ICgncXVlcnlfd2FsbF9zZWNvbmRzJywgJ3F1ZXJ5X2NwdV9zZWNvbmRzJywgJ2NwdV90b193YWxsX3JhdGlvJykKICAgIGhhc2hlcyA9ICgncGxhbl9zaGEyNTYnLCAnc3FsX3NoYTI1NicsICdyZXN1bHRfc2hhMjU2JywgJ3Byb2ZpbGVfc2hhMjU2JykKICAgIGZvciBmaWVsZCBpbiBpbnRlZ2VyczoKICAgICAgICBpZiB0eXBlKHZhbHVlLmdldChmaWVsZCkpIGlzIG5vdCBpbnQgb3IgdmFsdWVbZmllbGRdIDwgMDoKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUkVDRUlQVF9NRVRSSUNfSU5WQUxJRCcpCiAgICBmb3IgZmllbGQgaW4gZmxvYXRzOgogICAgICAgIGlmIHR5cGUodmFsdWUuZ2V0KGZpZWxkKSkgbm90IGluIChpbnQsIGZsb2F0KSBvciBub3QgbWF0aC5pc2Zpbml0ZSh2YWx1ZVtmaWVsZF0pIG9yIHZhbHVlW2ZpZWxkXSA8IDA6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JFQ0VJUFRfTUVUUklDX0lOVkFMSUQnKQogICAgZm9yIGZpZWxkIGluIGhhc2hlczoKICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh2YWx1ZS5nZXQoZmllbGQpLCBzdHIpIG9yIG5vdCByZS5mdWxsbWF0Y2goJ1swLTlhLWZdezY0fScsIHZhbHVlW2ZpZWxkXSk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JFQ0VJUFRfRElHRVNUX0lOVkFMSUQnKQogICAgaWYgc2VsZWN0ZWRfZmlsZShvdXRwdXQgLyAncmVzdWx0LnBhcnF1ZXQnKVsnYnl0ZXMnXSAhPSB2YWx1ZVsncmVzdWx0X2J5dGVzJ106CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignUkVTVUxUX1NJWkVfTUlTTUFUQ0gnKQogICAgcmV0dXJuIGRpY3Qoe2ZpZWxkOiB2YWx1ZVtmaWVsZF0gZm9yIGZpZWxkIGluICgqaW50ZWdlcnMsICpmbG9hdHMsICpoYXNoZXMpfSwKICAgICAgICAgICAgICAgIGpvYl9pZD1qb2JfaWQsIHN0YXR1cz0nY29tcGxldGVkJywgZW5naW5lPXBsYW5bJ2VuZ2luZSddLAogICAgICAgICAgICAgICAgaW5wdXRfY29udGVudF9oYXNoX3ZlcmlmaWVkPUZhbHNlLCByZXN1bHRfY29udGVudF9yZXZlcmlmaWVkPUZhbHNlKQoKCmRlZiBtYWluKCk6CiAgICBwYXJzZXIgPSBhcmdwYXJzZS5Bcmd1bWVudFBhcnNlcihkZXNjcmlwdGlvbj1fX2RvY19fKQogICAgc3ViID0gcGFyc2VyLmFkZF9zdWJwYXJzZXJzKGRlc3Q9J2FjdGlvbicsIHJlcXVpcmVkPVRydWUpCiAgICBwID0gc3ViLmFkZF9wYXJzZXIoJ3BsYW4nKQogICAgcC5hZGRfYXJndW1lbnQoJy0tam9iLWlkJywgcmVxdWlyZWQ9VHJ1ZSkKICAgIHAuYWRkX2FyZ3VtZW50KCctLWlucHV0JywgcmVxdWlyZWQ9VHJ1ZSkKICAgIHAuYWRkX2FyZ3VtZW50KCctLXNxbCcsIHJlcXVpcmVkPVRydWUpCiAgICBmb3IgZmxhZywgZGVmYXVsdCBpbiAoKCd0aHJlYWRzJywgNCksICgnbWVtb3J5LWdpYicsIDgpLCAoJ3NwaWxsLWdpYicsIDIwKSwgKCdyZXN1bHQtZ2liJywgMikpOgogICAgICAgIHAuYWRkX2FyZ3VtZW50KCctLScgKyBmbGFnLCB0eXBlPWludCwgZGVmYXVsdD1kZWZhdWx0KQogICAgc3ViLmFkZF9wYXJzZXIoJ3J1bicpICAjIEV4YWN0IHBsYW4gcGFzc2VkIG9uIHN0ZGluOyBzYW1lIHJlc291cmNlcyBnbyB0byBydW5uZXIuCiAgICBzdWIuYWRkX3BhcnNlcignc3RhdHVzJykuYWRkX2FyZ3VtZW50KCctLWpvYi1pZCcsIHJlcXVpcmVkPVRydWUpCiAgICBhcmdzID0gcGFyc2VyLnBhcnNlX2FyZ3MoKQogICAgdHJ5OgogICAgICAgIGlmIGFyZ3MuYWN0aW9uID09ICdwbGFuJzoKICAgICAgICAgICAgcmVzdWx0ID0gbWFrZV9wbGFuKGFyZ3Muam9iX2lkLCBhcmdzLmlucHV0LCBhcmdzLnNxbCwgdGhyZWFkcz1hcmdzLnRocmVhZHMsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBtZW1vcnlfZ2liPWFyZ3MubWVtb3J5X2dpYiwgc3BpbGxfZ2liPWFyZ3Muc3BpbGxfZ2liLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcmVzdWx0X2dpYj1hcmdzLnJlc3VsdF9naWIpCiAgICAgICAgZWxpZiBhcmdzLmFjdGlvbiA9PSAnc3RhdHVzJzoKICAgICAgICAgICAgcmVzdWx0ID0gcmVhZF9zdGF0dXMoYXJncy5qb2JfaWQpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcmF3ID0gc3lzLnN0ZGluLmJ1ZmZlci5yZWFkKE1BWF9TUUwgKyAxKQogICAgICAgICAgICBpZiBsZW4ocmF3KSA+IE1BWF9TUUw6CiAgICAgICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdQTEFOX1RPT19MQVJHRScpCiAgICAgICAgICAgIHJlc3VsdCA9IHJ1bihqc29uLmxvYWRzKHJhdykpCiAgICAgICAgcHJpbnQoanNvbi5kdW1wcyhyZXN1bHQsIHNvcnRfa2V5cz1UcnVlKSkKICAgICAgICByZXR1cm4gMAogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlcnJvcjoKICAgICAgICAjIE5ldmVyIGVjaG8gU1FMLCBkYXRhLCBwbGFucywgYXJiaXRyYXJ5IGV4Y2VwdGlvbiBib2RpZXMgb3IgY3JlZGVudGlhbHMuCiAgICAgICAgcHJpbnQoanNvbi5kdW1wcyh7J29rJzogRmFsc2UsICdlcnJvcl9jbGFzcyc6IHR5cGUoZXJyb3IpLl9fbmFtZV9ffSkpCiAgICAgICAgcmV0dXJuIDIKCgppZiBfX25hbWVfXyA9PSAnX19tYWluX18nOgogICAgcmFpc2UgU3lzdGVtRXhpdChtYWluKCkpCg=='
# Appended after the reviewed fixed-target transport helper.
import hashlib
import os
import re
import shlex

_RUNNER = 'u/admin/foo_jobs_20261027'
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')


def _query_namespace():
    ns = {'__name__': 'offmenu_query_worker'}
    exec(base64.b64decode(_QUERY_SOURCE_B64), ns)
    return ns


def _command(expression):
    program = ("import base64,json; ns={'__name__':'offmenu_query_host'}; "
               "exec(base64.b64decode(" + repr(_QUERY_SOURCE_B64) + "),ns); "
               "print(json.dumps(" + expression + ",sort_keys=True))")
    return 'python3 -I -S -B -c ' + shlex.quote(program)


def _receipt(job_id):
    ns = _query_namespace()
    if not isinstance(job_id, str) or not ns['JOB'].fullmatch(job_id):
        raise ValueError('QUERY_JOB_ID_INVALID')
    result = _confined_exec(_command("ns['read_status'](" + repr(job_id) + ")"))
    if (result.get('ok') is not True or any(result.get('truncated', {}).values())
            or len(result.get('stdout', '')) > 32000):
        raise RuntimeError('QUERY_RECEIPT_UNAVAILABLE')
    try:
        receipt = json.loads(result['stdout'])
    except (ValueError, KeyError):
        raise RuntimeError('QUERY_RECEIPT_INVALID') from None
    if receipt.get('job_id') != job_id or receipt.get('status') not in ('completed','incomplete','not_found'):
        raise RuntimeError('QUERY_RECEIPT_INVALID')
    return receipt


def main(action: str = 'plan', job_id: str = '', input_path: str = '', sql_path: str = '',
         threads: int = 4, memory_gib: int = 8, spill_gib: int = 20, result_gib: int = 2,
         timeout_seconds: int = 300, windmill_job_id: str = ''):
    """Owner-reviewed SQL only; original data stays on Foo. No implicit retries.

    plan: choose resources without running. submit: enqueue once, then inspect
    returned Windmill ID and logical ID. status/results read a bounded local
    receipt and never return query rows. cancel is an explicit user action.
    """
    if action not in ('plan','submit','status','results','cancel'):
        raise ValueError('QUERY_ACTION_INVALID')
    if os.environ.get('WM_WORKSPACE') != 'offmenu' or os.environ.get('WM_USERNAME') != 'admin':
        raise ValueError('QUERY_OWNER_REQUIRED')
    if action in ('status','results'):
        response = {'job_id': job_id, 'query': _receipt(job_id)}
        if windmill_job_id:
            if not _UUID.fullmatch(windmill_job_id):
                raise ValueError('WINDMILL_JOB_ID_INVALID')
            job = wmill.get_job(windmill_job_id)
            if job.get('script_path') != _RUNNER or job.get('args', {}).get('job_id') != job_id:
                raise ValueError('WINDMILL_JOB_ID_MISMATCH')
            state = wmill.get_job_status(windmill_job_id)
            state = getattr(state, 'value', state)
            response['windmill_status'] = str(state)
            if state == 'COMPLETED':
                response['windmill_success'] = job.get('success')
                if job.get('success') is True:
                    result = wmill.get_result(windmill_job_id)
                    if result.get('job_id') != job_id:
                        raise ValueError('WINDMILL_RESULT_ID_MISMATCH')
                    host = result.get('receipt', {})
                    response['admission'] = {'admitted':result.get('admitted'),
                                             'job_succeeded':result.get('job_succeeded'),
                                             'status':host.get('status'),
                                             'reason':host.get('reason'),
                                             'child_tree_gone':host.get('child_tree_gone')}
        if response['query']['status'] == 'completed':
            response['local_result'] = '/offmenu/data/.offmenu-platform/sql_queries/' + job_id + '/result.parquet'
            response['local_profile'] = '/offmenu/data/.offmenu-platform/sql_queries/' + job_id + '/profile.json'
        return response
    ns = _query_namespace()
    if action == 'cancel':
        if not isinstance(job_id, str) or not ns['JOB'].fullmatch(job_id):
            raise ValueError('QUERY_JOB_ID_INVALID')
        child = wmill.run_script_by_path_async(_RUNNER, args={'action':'cancel','job_id':job_id})
        return {'job_id':job_id,'cancellation_job_id':child,'terminal':False}
    plan = ns['make_plan'](job_id, input_path, sql_path, threads=threads,
                           memory_gib=memory_gib, spill_gib=spill_gib, result_gib=result_gib)
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1800:
        raise ValueError('QUERY_TIMEOUT_INVALID')
    if action == 'plan':
        return {'plan':plan,'timeout_seconds':timeout_seconds,'submitted':False,
                'query_source_sha256':hashlib.sha256(base64.b64decode(_QUERY_SOURCE_B64)).hexdigest()}
    payload = base64.b64encode(json.dumps(plan,sort_keys=True).encode()).decode()
    command = _command("ns['run'](json.loads(base64.b64decode(" + repr(payload) + ")))")
    if len(command.encode()) > 32000:
        raise ValueError('QUERY_COMMAND_TOO_LARGE')
    child = wmill.run_script_by_path_async(_RUNNER, args={
        'action':'run','job_id':job_id,'mode':'write','timeout_seconds':timeout_seconds,
        'command':command,'resources':plan['resources']})
    return {'job_id':job_id,'windmill_job_id':child,'submitted':True,'admitted':None,
            'run_url':'https://windmill.aldous.info/run/' + child + '?workspace=offmenu',
            'resources':plan['resources'],'engine':plan['engine'],
            'next':{'action':'status','job_id':job_id,'windmill_job_id':child}}
