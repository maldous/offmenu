"""Validate semantic counts, exact attachments and rendered geometry without inference."""
import json,sys,math,tempfile
from pathlib import Path
import numpy as np
from svgpathtools import parse_path
from routing_metrics import metrics
c=json.loads(Path(sys.argv[1]).read_text());fail=[];nodes={n['id']:n for n in c['nodes']};edges={e['id']:e for e in c['edges']};labels={l['id']:l for l in c['labels']}
def check(ok,msg):
 if not ok:fail.append(msg)
def overlap(a,b,gap=0):return a[0]<b[2]+gap and a[2]>b[0]-gap and a[1]<b[3]+gap and a[3]>b[1]-gap
check(len(nodes)==24,'24 unique nodes');check(len(edges)==44,'44 unique edges');check(sum(len(e['arrows'])for e in edges.values())==49,'49 arrows');check(len(labels)==43,'43 labels')
for n in nodes.values():check(n['box'][2]-n['box'][0]==290 and n['box'][3]-n['box'][1]==100,'uniform node dimensions '+n['id'])
samples={}
for e in edges.values():
 check(e['id']==e['source']+'->'+e['target'],'stable edge ID '+e['id']);check(e['source_port']['position']==e['polyline'][0] and e['target_port']['position']==e['polyline'][-1],'ports/polyline '+e['id'])
 check(len(e['arrows'])==(2 if e['direction']=='bidirectional'else 1),'direction/arrow mapping '+e['id'])
 d=' '.join(x['command']+' '.join(map(str,x['coordinates']))for x in e['path_commands']);path=parse_path(d)
 check(abs(path.start-complex(*e['polyline'][0]))<.02 and abs(path.end-complex(*e['polyline'][-1]))<.02,'rendered path endpoints '+e['id'])
 out=[]
 for s in path:
  for t in np.linspace(0,1,max(2,math.ceil(s.length()/1.5))):z=s.point(t);out.append((z.real,z.imag))
 samples[e['id']]=np.array(out)
for key,points in samples.items():
 endpoints={edges[key]['source'],edges[key]['target']}
 for node in nodes.values():
  if node['id']in endpoints:continue
  b=node['box'];bb=[b[0]-12,b[1]-7,b[2]+12,b[3]+17]
  check(not np.any((points[:,0]>bb[0])&(points[:,0]<bb[2])&(points[:,1]>bb[1])&(points[:,1]<bb[3])),'unrelated curve/node visible shadow '+key+'/'+node['id'])
for l in labels.values():
 check(l['rotation_degrees']==0,'horizontal '+l['id']);check(l['text']==edges[l['edge_id']]['protocol'],'protocol '+l['id']);x,y=l['center'];a,b=l['own_segment'];check((a[0]==b[0]==x and min(a[1],b[1])<=y<=max(a[1],b[1]))or(a[1]==b[1]==y and min(a[0],b[0])<=x<=max(a[0],b[0])),'label own-line '+l['id'])
 bb=l['bbox']
 for n in nodes.values():check(not overlap(bb,n['box'],20),'label/node-shadow '+l['id']+'/'+n['id'])
 for key,s in samples.items():
  if key!=l['edge_id']:check(not np.any((s[:,0]>=bb[0]-3)&(s[:,0]<=bb[2]+3)&(s[:,1]>=bb[1]-3)&(s[:,1]<=bb[3]+3)),'label/other rendered curve '+l['id']+'/'+key)
for i,l in enumerate(c['labels']):
 for other in c['labels'][i+1:]:check(not overlap(l['bbox'],other['bbox'],4),'label/label '+l['id']+'/'+other['id'])
with tempfile.TemporaryDirectory()as td:
 p=Path(td)/'routes.json';p.write_text(json.dumps({'node_bounds':{k:n['box']for k,n in nodes.items()},'routes':{k:e['polyline']for k,e in edges.items()}}));m=metrics(p)
for key in ['collinear_overlap_pairs','perpendicular_endpoint_contacts','nonorthogonal_segments','node_interior_intersections','bad_port_normals']:check(m[key]==0,key)
parallel_gaps=[]
segments=[(key,a,b)for key,e in edges.items()for a,b in zip(e['polyline'],e['polyline'][1:])]
for i,(key,a,b)in enumerate(segments):
 for other,cp,dp in segments[i+1:]:
  if key==other:continue
  if a[0]==b[0]and cp[0]==dp[0]:gap=abs(a[0]-cp[0]);span=min(max(a[1],b[1]),max(cp[1],dp[1]))-max(min(a[1],b[1]),min(cp[1],dp[1]))
  elif a[1]==b[1]and cp[1]==dp[1]:gap=abs(a[1]-cp[1]);span=min(max(a[0],b[0]),max(cp[0],dp[0]))-max(min(a[0],b[0]),min(cp[0],dp[0]))
  else:continue
  if span>0 and gap>0:
   parallel_gaps.append([gap,span,key,other]);check(gap>=10,'concurrent parallel track gap '+key+'/'+other)
# Current explicit orientation anchors, derived from node dimensions/row spacing.
rb=nodes['runner']['box'];step=250
check(nodes['code']['box'][1]==rb[1]and nodes['isolated']['box'][1]==rb[1]and rb[0]<nodes['code']['box'][0]<nodes['isolated']['box'][0],'top Compute order')
check(rb[0]==min(n['box'][0]for n in nodes.values())and rb[1]==min(n['box'][1]for n in nodes.values()),'Runner top-left')
check(not any(n['box'][0]==rb[0]and n['box'][1]==rb[1]+step for n in nodes.values()),'empty row below Runner')
check(nodes['journal']['box'][0]==rb[0]and nodes['journal']['box'][1]==rb[1]+2*step,'Journal left after empty row')
check(nodes['delivery']['box'][0]==rb[0]and nodes['delivery']['box'][1]==rb[1]+3*step,'Delivery below Journal')
lg=nodes['langgraph']['box'];check(lg[0]==min(n['box'][0]for n in nodes.values())and lg[1]==max(n['box'][1]for n in nodes.values()),'LangGraph bottom-left')
expected_columns=[['runner',None,'journal','delivery','sqlite','langgraph'],['code','supervisor','workspace','integration','policy','stokowski'],['isolated','wm_mcp','tools','bridge','adapter','windmill'],[None,None,'pr','review','threads','github'],[None,None,None,'provider','durable','linear']]
for col,contents in enumerate(expected_columns):
 for row,node in enumerate(contents):
  if node:check(nodes[node]['box'][:2]==[560*col,250*row],'restored exact grid '+node)
check(len(edges['integration->delivery']['polyline'])==2,'Integration Delivery direct CLI')
check(edges['integration->delivery']['source_port']['position']!=edges['integration->journal']['source_port']['position'],'CLI and journal distinct source ports')
check(edges['runner->delivery']['source_port']['face']=='left' and edges['runner->delivery']['target_port']['face']=='left','Runner Delivery outside left faces')
check(len(edges['langgraph->sqlite']['polyline'])==2 and edges['langgraph->sqlite']['polyline'][0][0]==(lg[0]+lg[2])/2,'centered direct SQLite')
for container in c.get('containers',[]):
 box=container['bounds'];actual=[n['id']for n in nodes.values()if box[0]<=n['box'][0]and box[1]<=n['box'][1]and box[2]>=n['box'][2]and box[3]>=n['box'][3]];check(set(actual)==set(container['members']),'container membership '+container['id'])
 if container['id']=='ai-development-review':check(set(actual)=={'provider','review','pr'},'Engineering exact three members')
 for edge in edges.values():
  for a,b in zip(edge['polyline'],edge['polyline'][1:]):
   if a[0]==b[0]and min(a[1],b[1])<box[3]and max(a[1],b[1])>box[1]:check(min(abs(a[0]-box[0]),abs(a[0]-box[2]))>=10,'parallel edge/container '+edge['id']+'/'+container['id'])
   if a[1]==b[1]and min(a[0],b[0])<box[2]and max(a[0],b[0])>box[0]:check(min(abs(a[1]-box[1]),abs(a[1]-box[3]))>=10,'parallel edge/container '+edge['id']+'/'+container['id'])
 # Actual rectangular boundaries are label obstacles.
 x0,y0,x1,y1=box
 for label in labels.values():
  b=label['bbox'];hit=(b[0]-3<x0<b[2]+3 or b[0]-3<x1<b[2]+3)and b[1]-3<y1 and b[3]+3>y0 or (b[1]-3<y0<b[3]+3 or b[1]-3<y1<b[3]+3)and b[0]-3<x1 and b[2]+3>x0
  check(not hit,'label/container '+label['id']+'/'+container['id'])
for heading in c.get('headings',[]):
 bb=heading['glyph_bbox']
 for key,s in samples.items():check(not np.any((s[:,0]>=bb[0]-3)&(s[:,0]<=bb[2]+3)&(s[:,1]>=bb[1]-3)&(s[:,1]<=bb[3]+3)),'heading glyph/curve '+heading['id']+'/'+key)
 # Page extents in graph-local coordinates transformed to canvas.
import re
tr=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',c['coordinate_system']['graph_to_canvas_transform'])));vx,vy,vw,vh=c['canvas']['viewBox'];dx,dy=tr[:2]
for key,bb in [(n['id'],n['box'])for n in nodes.values()]+[(l['id'],l['bbox'])for l in labels.values()]+[(h['id'],h['glyph_bbox'])for h in c.get('headings',[])]:check(vx<=bb[0]+dx and vy<=bb[1]+dy and vx+vw>=bb[2]+dx and vy+vh>=bb[3]+dy,'page clipping '+key)
from render_contract import render
ids=[el.get('id')for el in render(c).getroot().iter()if el.get('id')]
check(len(ids)==len(set(ids)),'unique SVG IDs including filters')
report={'status':'passed'if not fail else'failed','failures':fail,'counts':{'nodes':len(nodes),'edges':len(edges),'arrows':sum(len(e['arrows'])for e in edges.values()),'labels':len(labels)},'routing':{k:v for k,v in m.items()if not isinstance(v,list)},'nearest_parallel_tracks':sorted(parallel_gaps)[:12],'limitations':['Font glyph boxes use the bundled DejaVu family metrics; visually review after changing fonts.','Geometry changes require revalidation and independent visual inspection; no automatic topology/routing optimization is hidden in the renderer.']}
print(json.dumps(report,indent=2));sys.exit(bool(fail))
