#!/bin/sh
# PROPOSAL ONLY: root-owned installed file, never run this source as root.
# No candidate parsing/execution in root phase. All input checks follow setpriv.
unset ENV BASH_ENV CDPATH
exec /usr/bin/setpriv --reuid=1000 --regid=1000 --clear-groups \
  --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
  --no-new-privs --reset-env -- /usr/local/libexec/offmenu-coding-guard "$@"
