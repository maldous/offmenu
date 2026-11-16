"""Build secretless private worker source; does not contact Foo or registries."""
import base64
import argparse
import json
from pathlib import Path

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--transport-client", type=Path, default=here.parent / "windmill_foo_jobs.py",
                    help="Reviewed transport source; default is ../windmill_foo_jobs.py in the repository")
args = parser.parse_args()
client = args.transport_client.read_text()
client = client[:client.index("\ndef main(")]
helper = (here / "transfer_helper.py").read_text()
files = {name: base64.b64encode((here / name).read_bytes()).decode() for name in (
    "install_offline.py", "runtime.py", "lock.json", "requirements.lock", "LICENSE.duckdb")}
suffix = '''
import tempfile
import urllib.request
import urllib.parse
import uuid

PACKAGE_URL = LOCK["url"]

def _get(url, limit):
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError("HTTPS required")
    with urllib.request.urlopen(url, timeout=60) as response:
        parsed = urllib.parse.urlparse(response.url)
        if parsed.scheme != "https" or parsed.hostname not in {"pypi.org", "files.pythonhosted.org"}:
            raise ValueError("Unexpected registry redirect")
        blob = response.read(limit+1)
    if len(blob)>limit:
        raise ValueError("Registry response exceeds bound")
    return blob


def _verified_wheel():
    metadata = json.loads(_get("https://pypi.org/pypi/duckdb/1.5.6/json", 2*1024*1024))
    selected = next(x for x in metadata["urls"] if x["filename"] == FILENAME)
    if selected["yanked"] or selected["size"] != SIZE or selected["url"] != PACKAGE_URL or selected["digests"]["sha256"] != SHA256:
        raise ValueError("Official registry metadata no longer agrees with reviewed pin")
    blob = _get(PACKAGE_URL, SIZE)
    if len(blob)!=SIZE or hashlib.sha256(blob).hexdigest()!=SHA256:
        raise ValueError("Downloaded artifact integrity mismatch")
    # Use exactly the same reviewed archive validator on the worker before transfer.
    namespace = {"__name__": "duckdb_offline_validator"}
    exec(base64.b64decode(FILES["install_offline.py"]), namespace)
    with tempfile.TemporaryDirectory(prefix="offmenu-duckdb-") as td:
        p = Path(td)/FILENAME
        p.write_bytes(blob)
        namespace["verify_archive"](p)
    return blob


def main(action: str = "verify_registry", stage_id: str = "", max_chunks: int = 128):
    # verify_registry is read-only with respect to Foo and never loads the SSH secret.
    if action not in {"verify_registry", "prepare", "transfer", "status", "install"}:
        raise ValueError("Unsupported action")
    if type(max_chunks) is not int or not 1 <= max_chunks <= 600:
        raise ValueError("max_chunks must be 1..600")
    blob = None
    if action in {"verify_registry", "transfer"}:
        blob = _verified_wheel()
    if action == "verify_registry":
        return {"ok":True,"sha256":SHA256,"bytes":len(blob),"archive_verified":True,"foo_writes":False}
    if action == "prepare":
        if stage_id:
            raise ValueError("prepare generates an exclusive random stage_id")
        stage_id = uuid.uuid4().hex
    stage_path(stage_id)
    client = None
    secret = None
    private_key = None
    try:
        client = paramiko.SSHClient()
        _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as key_stream:
            private_key = paramiko.Ed25519Key.from_private_key(key_stream)
        secret = None
        client.connect(HOST, port=PORT, username=USER, pkey=private_key,
                       allow_agent=False, look_for_keys=False,
                       timeout=5, banner_timeout=5, auth_timeout=5, channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise ConnectionError("Unauthenticated transport")
        def remote(cmd):
            payload = json.dumps({"command":cmd}, ensure_ascii=True).encode()
            if len(payload)>MAX_REQUEST_BYTES:
                raise ValueError("Request bound exceeded")
            channel = transport.open_session(timeout=5)
            try:
                channel.settimeout(5)
                channel.exec_command("offmenu-exec-v1")
                channel.sendall(payload)
                channel.shutdown_write()
                result = _drain(channel, 60)
                if result["exit_code"] or any(result["truncated"].values()):
                    return {"ok":False,"stage_id":stage_id,"remote":result}
                return json.loads(result["stdout"])
            finally:
                channel.close()
        if action=="prepare":
            return remote(prepare_command(stage_id,{name:base64.b64decode(value) for name,value in FILES.items()}))
        if action=="status":
            return remote(status_command(stage_id))
        if action=="install":
            return remote(install_command(stage_id))
        status = remote(status_command(stage_id))
        if status.get("ok") is False:
            return status
        offset = status["offset"]
        if type(offset) is not int or offset<0 or offset>SIZE or (offset != SIZE and offset%CHUNK_SIZE):
            raise ValueError("Invalid remote offset; incomplete chunk requires manual diagnosis")
        initial = offset
        for _ in range(max_chunks):
            if offset == SIZE:
                break
            chunk = blob[offset:offset+CHUNK_SIZE]
            result = remote(chunk_command(stage_id,offset,chunk))
            if result.get("ok") is False:
                return result
            if result["offset"] != offset+len(chunk):
                raise ValueError("Unexpected receiver offset")
            offset = result["offset"]
        return {"ok":True,"stage_id":stage_id,"offset":offset,"transferred_this_run":offset-initial,
                "total_bytes":SIZE,"transfer_complete":offset==SIZE,"installed":False,"sha256_pin":SHA256}
    except Exception as error:
        # No credential, payload, secret-provider exception text or traceback output.
        return {"ok":False,"stage_id":stage_id,"error_class":type(error).__name__[:64]}
    finally:
        secret = None
        private_key = None
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
'''
lock = json.loads((here / "lock.json").read_text())
source = client + "\n" + helper + "\nFILES = " + repr(files) + "\nLOCK = " + repr(lock) + "\n" + suffix
compile(source, "<worker>", "exec")
(here / "windmill_duckdb_offline.py").write_text(source)
print(json.dumps({"worker_source": str(here / "windmill_duckdb_offline.py"), "bytes": len(source.encode())}))
