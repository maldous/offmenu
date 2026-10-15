"""Isolated conservative quantity evidence parser; no portions or ingredient identities inferred."""
import argparse
import gzip
import hashlib
import json
import re
import unicodedata
from fractions import Fraction

PARSER_VERSION = 'worker54-quantity/4'
DEFAULT = '/home/user/src/offmenu-data/world-recipes-global-final-20261014/normalized.jsonl.gz'
EXPECTED = '90dcf2c498c8b86ba723a66214ce4573f32b4fc2b6d1c88c184ce5e365247e73'
FRACTIONS = {'½': '1/2', '¼': '1/4', '¾': '3/4', '⅓': '1/3', '⅔': '2/3', '⅛': '1/8'}
DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
NUMBER = r'(?:\d+\s+\d+/\d+|\d+/\d+|\d+[½¼¾⅓⅔⅛]|[½¼¾⅓⅔⅛]|\d+(?:[.,٫]\d+)?)'
PREFIX = re.compile(r'^\s*(?P<amount>'+NUMBER+r')(?:\s*(?:–|—|-|to|à|bis)\s*(?P<upper>'+NUMBER+r'))?\s*', re.I)
UNITS = {'g':'g','gram':'g','grams':'g','grammes':'g','gramos':'g','г':'g','克':'g',
         'kg':'kg','кг':'kg','千克':'kg','ml':'ml','мл':'ml','毫升':'ml','l':'l','litre':'l','litres':'l',
         'cup':'cup','cups':'cup','tasse':'cup','tasses':'cup','taza':'cup','tazas':'cup',
         'teaspoon':'teaspoon','teaspoons':'teaspoon','tsp':'teaspoon',
         'tablespoon':'tablespoon','tablespoons':'tablespoon','tbsp':'tablespoon',
         'portion':'portion','portions':'portion','servings':'portion','份':'portion'}
UNIT = re.compile(r'(?P<unit>'+ '|'.join(re.escape(x) for x in sorted(UNITS,key=len,reverse=True))+r')(?![\w])',re.I)

def number(token, locale):
    token=token.translate(DIGITS).replace('٫','.')
    if re.fullmatch(r'\d+[.,]\d{3}',token):
        raise ValueError('ambiguous decimal/thousands separator')
    if ',' in token:
        if locale.split('-')[0] not in {'fr','de','es','it','pt','nl','ru'}:
            raise ValueError('decimal comma requires explicit locale')
        token=token.replace(',','.')
    if any(x in token for x in FRACTIONS):
        symbol=token[-1]; return Fraction(token[:-1] or '0')+Fraction(FRACTIONS[symbol])
    if ' ' in token.strip():
        whole, fraction=token.split();return Fraction(whole)+Fraction(fraction)
    return Fraction(token)

def parse(text, locale='und', coordinate=None, provenance=None):
    if not isinstance(text,str): raise TypeError('original lexeme must be a string')
    result={'parserVersion':PARSER_VERSION,'originalLexeme':text,'coordinate':coordinate,
            'provenance':provenance or {},'locale':locale,'status':'UNKNOWN','value':None,'range':None,
            'unit':None,'sourceUnit':None,'confidence':'unknown','amountSpan':None,
            'optional':'candidate' if re.search(r'\b(optional|facultatif|opcional|optionnel)\b',text,re.I) else 'unknown',
            'reason':'no unambiguous leading amount and explicit supported unit'}
    # Digit translation preserves character coordinates. Fractions stay original.
    match=PREFIX.match(text.translate(DIGITS))
    if not match:return result
    tail=text[match.end():];unit=UNIT.match(tail)
    if not unit:return result
    continuation=tail[unit.end():]
    if continuation:
        char=continuation[0]
        # Do not normalize or strip marks/joiners. Only explicit delimiters end a unit.
        category=unicodedata.category(char)
        whitespace=char.isspace() and (not category.startswith('C') or char in '\t\r\n')
        if not whitespace and char not in ',;:()[]':
            result['reason']='unsupported Unicode unit continuation';return result
    try:
        low=number(match['amount'],locale);high=number(match['upper'],locale) if match['upper'] else None
        if low<=0 or (high is not None and high<low): raise ValueError('nonpositive/reversed quantity')
    except (ValueError,ZeroDivisionError):return result
    rest=tail[unit.end():]
    # Multiple measures/pack multiplicities cannot safely be reduced to the first amount.
    # Numeric continuations include every Unicode numeric character, not just the
    # leading grammar's supported fractions. Do not normalize or combine measures.
    alternative = re.search(
        r'\b(?:or|plus|x|times|half|halves|quarter|quarters|third|thirds|'
        r'double|triple|twice|once|zero|one|two|three|four|five|six|seven|'
        r'eight|nine|ten|eleven|twelve|hundred|thousand)\b|[+×*]', rest, re.I)
    if any(char.isnumeric() for char in rest) or alternative:
        result['reason']='additional numeric basis or alternative measure requires review';return result
    result.update(status='candidate',value=str(low) if high is None else None,
                  range=[str(low),str(high)] if high is not None else None,
                  unit=UNITS[unit['unit'].lower()],sourceUnit=unit['unit'],
                  confidence='lexical-explicit-unit',amountSpan=[match.start('amount'),match.end('upper') if high is not None else match.end('amount')],
                  reason='source quantity only; no conversion, food identity, portion or scaling authority')
    return result

def parse_yield(text=None, locale='und', coordinate=None, provenance=None):
    result=parse(text or '',locale,coordinate,provenance)
    if result['unit']!='portion':
        result.update(status='UNKNOWN',value=None,range=None,confidence='unknown',reason='no explicit source serving yield')
    return result

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def inspect(path=DEFAULT,limit=20,expected=EXPECTED):
    if not 0<=limit<=1000:raise ValueError('limit must be 0..1000')
    before=digest(path)
    if before!=expected:raise ValueError('retained release hash mismatch')
    refs=[]
    with gzip.open(path,'rt',encoding='utf8') as f:
        for line_no,line in enumerate(f,1):
            if len(refs)>=limit:break
            value=json.loads(line)
            for index,record in enumerate(value if isinstance(value,list) else [value]):
                if len(refs)>=limit:break
                p=record.get('provenance',{});data=record.get('data',{})
                if p.get('license')!='CC BY-SA 4.0' or not p.get('revisionId') or not p.get('originalContentSha256'):continue
                locale=(data.get('languages') or ['und'])[0]
                # Retain only references/results, not recipe bodies; names belong to Worker42.
                ingredients=data.get('ingredients',[])
                results=[parse(i.get('originalText',''),locale,{'line':line_no,'index':index,'jsonPointer':f'/data/ingredients/{n}/originalText'},p) for n,i in enumerate(ingredients)]
                refs.append({'id':record.get('id'),'line':line_no,'index':index,'provenance':p,
                             'results':[{k:v for k,v in r.items() if k not in {'originalLexeme','provenance'}} for r in results],
                             'originalLexemeSHA256':[hashlib.sha256(i.get('originalText','').encode()).hexdigest() for i in ingredients],
                             'yield':'UNKNOWN (normalized yield is not an original source lexeme)'})
    if digest(path)!=before:raise ValueError('retained bytes changed')
    return {'path':path,'sha256':before,'limit':limit,'refs':refs,'admission':'independent review pending'}


def inspect_original(proof):
    """Check bounded pinned bodies; inspect bullet lexemes, never infer ingredient sections."""
    records=proof['records']
    if not 0<len(records)<=1000:raise ValueError('original reference bound')
    # Resolve only the requested normalized coordinates; no census or body copies.
    if digest(DEFAULT)!=EXPECTED:raise ValueError('normalized release mismatch')
    wanted={(r['normalized_coordinate']['line'],r['normalized_coordinate']['index']) for r in records}
    normalized={}
    with gzip.open(DEFAULT,'rt',encoding='utf8') as f:
        for line_no,line in enumerate(f,1):
            if line_no>max(x[0] for x in wanted):break
            if any(n==line_no for n,i in wanted):
                values=json.loads(line);values=values if isinstance(values,list) else [values]
                for n,i in wanted:
                    if n==line_no:normalized[(n,i)]=values[i]
    output=[]
    for ref in records:
        coord=ref['normalized_coordinate'];row=normalized[(coord['line'],coord['index'])]
        if row.get('provenance')!=ref['provenance']:raise ValueError('normalized provenance binding mismatch')

        original=ref['original'];path=original['path']
        if digest(path)!=original['file_sha256']:raise ValueError('original file changed')
        with open(path,encoding='utf8') as f:document=json.load(f)
        tokens=original['coordinate'].split('/')[1:]
        if len(tokens)!=8 or tokens[:2]!=['query','pages'] or tokens[3]!='revisions' or tokens[5:]!=['slots','main','content']:
            raise ValueError('unsupported original coordinate')
        pages=document['query']['pages']
        page=pages[int(tokens[2])] if isinstance(pages,list) else pages[tokens[2]]
        revision=page['revisions'][int(tokens[4])];slot=revision['slots']['main'];body=slot['content']
        provenance=ref['provenance']
        if (str(page['pageid'])!=original['recordId'] or str(page['pageid'])!=provenance['recordId']
            or revision['revid']!=original['revisionId'] or revision['revid']!=provenance['revisionId']
            or revision['timestamp']!=original['timestamp'] or revision['timestamp']!=provenance['sourceDate']
            or page['title']!=original['title'] or slot.get('contentmodel')!='wikitext'
            or slot.get('contentformat')!='text/x-wiki' or slot.get('contentmodel')!=original['contentmodel']
            or slot.get('contentformat')!=original['contentformat']
            or provenance['originSourceId']!='wikibooks:'+ref['language']
            or len(body.encode())!=original['body_bytes']):raise ValueError('original identity/date/schema binding mismatch')
        if hashlib.sha256(body.encode()).hexdigest()!=original['body_sha256']:raise ValueError('body mismatch')
        if original['body_sha256']!=ref['provenance']['originalContentSha256']:raise ValueError('provenance mismatch')
        rights=ref['rights']
        if digest(rights['path'])!=rights['sha256']:raise ValueError('rights changed')
        with open(rights['path'],encoding='utf8') as f:declaration=json.load(f)['query']['rightsinfo']
        if (declaration!=rights['publisher_declared'] or declaration['url']!=provenance['rightsEvidenceUrl']
            or provenance.get('license')!='CC BY-SA 4.0' or not provenance.get('attribution')):
            raise ValueError('rights declaration/provenance changed')
        results=[];offset=0
        for line in body.splitlines(keepends=True):
            if line.startswith('*'):
                start=offset+1;lexeme=line[1:].rstrip('\r\n')
                result=parse(lexeme,ref['language'],{'path':path,'jsonPointer':original['coordinate'],'bodyCharacterSpan':[start,start+len(lexeme)]},ref['provenance'])
                result.pop('originalLexeme');result.pop('provenance')
                result['lexemeSHA256']=hashlib.sha256(lexeme.encode()).hexdigest();results.append(result)
            offset+=len(line)
        if digest(path)!=original['file_sha256']:raise ValueError('original changed during read')
        output.append({'language':ref['language'],'original':original,'rights':rights,'provenance':ref['provenance'],'bullet_results':results,'sectionStatus':'unqualified bullet lexemes may be instructions, not ingredients','yield':'UNKNOWN'})
    if digest(DEFAULT)!=EXPECTED:raise ValueError('normalized release changed during read')
    return output

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--limit',type=int,default=20)
    args=cli.parse_args();print(json.dumps(inspect(limit=args.limit),ensure_ascii=False,indent=2))
