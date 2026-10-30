"""Deterministic JSON→SVG renderer; no routing engine or model is involved."""
import argparse,json,xml.etree.ElementTree as E,subprocess
from pathlib import Path
N='{http://www.w3.org/2000/svg}';E.register_namespace('',N[1:-1])
def element(a):
 e=E.Element(a['tag'],a['attributes']);e.text=a.get('text')
 for c in a.get('children',[]):e.append(element(c))
 return e
def render(c):
 root=E.Element(N+'svg',c['canvas']['attributes']);root.set('viewBox',' '.join(map(str,c['canvas']['viewBox'])))
 for a in c['root_support']:root.append(element(a))
 g=E.SubElement(root,N+'g',c['graph_attributes']);nodes={x['id']:x for x in c['nodes']};edges={x['id']:x for x in c['edges']};groups={x['id']:x for x in c['groups']}
 for z in c['z_order']:
  kind,key=z['kind'],z['id']
  if kind=='node':
   n=nodes[key];e=element(n['element']);b,ref=n['box'],n['reference_box'];dx,dy=b[0]-ref[0],b[1]-ref[1]
   if b[2]-b[0]!=ref[2]-ref[0] or b[3]-b[1]!=ref[3]-ref[1]:raise ValueError('Resize requires updating node path/text geometry, not only box.')
   if dx or dy:e.set('transform',f'translate({dx} {dy})')
   e.find(N+'path').attrib.update(n['style'])
   for t,text in zip(e.findall(N+'text'),n['content']):t.attrib.update(text['attributes']);t.text=text['text']
  elif kind=='edge':
   n=edges[key];e=element(n['element']);d=' '.join(x['command']+' '.join(format(v,'.12g')for v in x['coordinates'])for x in n['path_commands'])
   for p in e.findall(N+'path'):
    if p.get('stroke')!='#fafbfc':p.attrib.update({k:v for k,v in n['style'].items()if k!='d'})
    p.set('d',d)
   for p,a in zip(e.findall(N+'polygon'),n['arrows']):p.attrib.update(a)
  elif kind=='labels':
   e=E.Element(N+'g',{'id':'protocol-labels'})
   for n in c['labels']:
    le=element(n['element']);x,y=n['center'];le.set('transform',f'translate({x} {y}) rotate(0)');le.find(N+'rect').attrib.update(n['background'])
    for t,tt in zip(le.findall(N+'text'),n['text_elements']):t.attrib.update({k:str(v)for k,v in tt.items()if k!='text'});t.text=tt['text']
    e.append(le)
  else:
   e=element(groups[key]['element'])
   if key=='domains-and-lanes':
    for container in c.get('containers',[]):
     el=next(x for x in e if x.get('id')==container['id']);x0,y0,x1,y1=container['bounds'];el.attrib.update(container['style']);el.set('x',str(x0));el.set('y',str(y0));el.set('width',str(x1-x0));el.set('height',str(y1-y0))
    for heading in c.get('headings',[]):
     el=next(x for x in e if x.get('id')==heading['id']);el.attrib.update(heading['attributes']);el.text=heading['text']
  g.append(e)
 return E.ElementTree(root)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('svg');p.add_argument('--png');a=p.parse_args();c=json.loads(Path(a.contract).read_text());render(c).write(a.svg,encoding='utf-8',xml_declaration=True)
 if a.png:
  subprocess.run(['inkscape',a.svg,'--export-type=png','--export-background=#ffffff','--export-background-opacity=1','--export-filename='+a.png],check=True)
  from PIL import Image
  im=Image.open(a.png).convert('RGB');im.save(a.png)
