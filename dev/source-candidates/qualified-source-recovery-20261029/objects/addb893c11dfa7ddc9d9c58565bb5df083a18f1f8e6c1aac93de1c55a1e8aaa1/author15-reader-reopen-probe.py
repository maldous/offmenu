import json,tempfile
from pathlib import Path
from unittest.mock import patch
from test_portfolio15_binding import contract
from offmenu.refresh import portfolio15 as module
binding,raw=contract()
assert module.MAX_METADATA <16*1024*1024
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'metadata.json';path.write_bytes(raw)
 binding['evidence']['fixture']['recordedPath']=str(path)
 real_digest=module.digest
 def replace_after_verified(*args,**kwargs):
  digest=real_digest(*args,**kwargs)
  path.write_bytes(b'X'*(module.MAX_METADATA+1))
  return digest
 with patch.object(module,'digest',side_effect=replace_after_verified):
  result=module.read_metadata(binding)
 print(json.dumps({'candidate':'b583f0e0130135dff4ed896a1a292b3930e68fd0','authoredOnly':True,'verifiedOriginalBytes':len(raw),'configuredReadLimit':module.MAX_METADATA,'returnedAfterReplacementBytes':len(result['fixture']),'oversizeBytesReturned':len(result['fixture'])>module.MAX_METADATA,'returnedBufferMatchesExpectedSha':module.sha(result['fixture'])==binding['evidence']['fixture']['sha256'],'realSourceMetadataOrBodyReads':0,'authorEdits':0,'scope':'Actualread_metadata at exactcandidate; authoredfixture contract anddigest-then-replace hook only. No FIFOhang oractualsource processing.'}))
