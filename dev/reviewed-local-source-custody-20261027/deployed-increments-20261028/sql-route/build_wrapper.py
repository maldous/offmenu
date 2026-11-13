import base64
from pathlib import Path
p=Path(__file__).resolve().parent
source=(p/'duckdb_query.py').read_bytes()
wrapper='#requirements:\n#paramiko==5.1.0\n#wmill==1.850.0\n'+(p/'transport_prefix.py').read_text()
wrapper+='\n_QUERY_SOURCE_B64 = '+repr(base64.b64encode(source).decode())+'\n'
wrapper+=(p/'wrapper_entrypoint.py').read_text()
(p/'windmill_sql_query.py').write_text(wrapper)
print('wrapper_bytes',len(wrapper.encode()))
