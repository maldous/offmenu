"""Explicit owner fetch/parse selection. No source authority or rights expansion."""
from .core import RefreshError
from . import retained_integrity_verification as verification


def base_arguments(args):
    args=list(args)
    if args[:2]!=['--mode','user']:
        return args
    if len(args)>=4 and args[2]=='--stage':
        if args[3] not in ('fetch','parse'):
            raise RefreshError('unexpected-arguments')
        args=args[:2]+args[4:]
    if args not in (['--mode','user'],['--mode','user','--publish-only']):
        raise RefreshError('unexpected-arguments')
    return args


def owner_arguments(args):
    return base_arguments(args) in (['--mode','user'],['--mode','user','--publish-only'])


def owner_stage(args):
    if not owner_arguments(args):
        return None
    return args[3] if len(args)>=4 and args[2]=='--stage' else 'fetch'


def verification_contract(preparation):
    """Narrow an already source-bound read contract to bounded identity inspection."""
    if preparation['permissions'].get('read') is not True:
        raise RefreshError('verification-read-held')
    result={'schemaVersion':verification.SCHEMA,'assetId':preparation['assetId'],
      'expectedSHA256':preparation['expectedSHA256'],'expectedBytes':preparation['expectedBytes'],
      'expectedMediaTypes':list(preparation['expectedMediaTypes']),
      'permissions':{'read':True,'copy':False,'extract':False},'holds':list(preparation['holds']),
      'maximumReadBytes':preparation['expectedBytes'],'chunkBytes':1024**2,
      'maximumSniffBytes':65536,'maximumSeconds':300,'maximumOutputBytes':0,
      'completeReadRequired':True,'decompressionAllowed':False,'networkRequests':0}
    return verification.validate_contract(result)
