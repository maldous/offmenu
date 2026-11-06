from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent
template=(p/'launcher-template.txt').read_text()
if 'pass_fds' in template or '/proc/self/fd/' in template:raise SystemExit('Unsafe descriptor inheritance')
s='#!/usr/bin/python3 -I\n# Approved incremental input readonly ACL and mount update.\n'
for variable,name in [('LAUNCHER_TEMPLATE','launcher-template.txt'),('ORIGINAL_LAUNCHER_TEMPLATE','original-launcher-template.txt'),('ACL_SOURCE','readonly_acl.py'),('ACL_IO_SOURCE','acl_io.py')]:
 s+=variable+' = '+repr((p/name).read_text())+'\n'
s+='ACLM = {}; exec(compile(ACL_SOURCE,"<readonly-acl>","exec"),ACLM)\nACLIO_MOD = {}; exec(compile(ACL_IO_SOURCE,"<acl-io>","exec"),ACLIO_MOD)\n'
s+=(p/'incremental_core.py').read_text();compile(s,'combined','exec')
f=p/'offmenu_input_readonly_acl_mount.py';f.write_text(s)
print(f);print(hashlib.sha256(s.encode()).hexdigest())
