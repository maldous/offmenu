"""HTTPS transport with one per-source bounded response-header envelope.

No proxy, cookies, redirects, auth, retries, or ambient credentials. Redirect
selection and capability validation belong to known_asset_intake, not transport.
"""
import http.client
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit
from .core import RefreshError
from .acquisition import _Response

class HeaderEnvelope:
 def __init__(self,maximum=65536):self.remaining=maximum;self.read=0

class HeaderReader:
 def __init__(self,raw,envelope):self.raw=raw;self.envelope=envelope
 def readline(self,limit=-1):
  if self.envelope.remaining<=0:raise RefreshError('media-intake-header-invalid')
  bound=self.envelope.remaining if limit<0 else min(limit,self.envelope.remaining)
  line=self.raw.readline(bound);self.envelope.read+=len(line);self.envelope.remaining-=len(line)
  if line and not line.endswith(b'\n') and not self.envelope.remaining:raise RefreshError('media-intake-header-invalid')
  return line
 def read(self,*args):return self.raw.read(*args)
 def readinto(self,*args):return self.raw.readinto(*args)
 def read1(self,*args):return self.raw.read1(*args)
 def flush(self):return self.raw.flush()
 def close(self):self.raw.close()

class BoundedHTTPSFileTransport:
 def __init__(self,maximum_header_bytes=65536):self.envelope=HeaderEnvelope(maximum_header_bytes)
 def __call__(self,spec,headers,*,deadline=None):
  remaining=deadline-time.monotonic() if deadline is not None else 300
  if remaining<=0:raise RefreshError('acquisition-duration-limit-exceeded')
  parts=urlsplit(spec.url);envelope=self.envelope
  if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.fragment or parts.port not in (None,443) or spec.request_method!='GET' or spec.request_body:raise RefreshError('media-intake-contract-invalid')
  if headers!={'Accept-Encoding':'identity'}:raise RefreshError('media-intake-contract-invalid')
  class Response(http.client.HTTPResponse):
   def __init__(self,*args,**kwargs):
    super().__init__(*args,**kwargs);self.fp=HeaderReader(self.fp,envelope)
  connection=http.client.HTTPSConnection(parts.hostname,443,timeout=min(30,remaining),context=ssl.create_default_context());connection.response_class=Response
  expired=threading.Event();active_socket=[None]
  def abort():
   expired.set();sock=connection.sock or active_socket[0]
   if sock is not None:
    try:sock.shutdown(socket.SHUT_RDWR)
    except OSError:pass
   connection.close()
  watchdog=threading.Timer(remaining,abort);watchdog.daemon=True;watchdog.start()
  try:
   target=(parts.path or '/')+('?' + parts.query if parts.query else '')
   connection.request('GET',target,headers=headers);active_socket[0]=connection.sock;response=connection.getresponse()
   if expired.is_set():raise TimeoutError('acquisition-deadline')
  except BaseException:
   watchdog.cancel();connection.close();raise
  return _Response(connection,response,watchdog,expired)
