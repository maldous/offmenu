"""Independent whole-polyline routing metrics; includes port stubs, not only grid steps."""
import json, math, sys
from pathlib import Path
EPS=1e-6
def close(a,b): return abs(a-b)<EPS
def metrics(path):
 raw=json.loads(Path(path).read_text());routes=raw['routes'];bounds=raw['node_bounds'];segs=[];bends=0;orthogonal=[];node_hits=[];port_bad=[]
 for name,pts in routes.items():
  clean=[]
  for p in pts:
   if not clean or math.dist(p,clean[-1])>EPS: clean.append(p)
  for a,b,c in zip(clean,clean[1:],clean[2:]):
   if abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))>EPS:bends+=1
  for a,b in zip(clean,clean[1:]):
   segs.append((name,a,b))
   if not close(a[0],b[0]) and not close(a[1],b[1]):orthogonal.append([name,a,b])
   for node,(x0,y0,x1,y1) in bounds.items():
    if close(a[0],b[0]) and x0+EPS<a[0]<x1-EPS and max(min(a[1],b[1]),y0+EPS)<min(max(a[1],b[1]),y1-EPS):node_hits.append([name,node,a,b])
    if close(a[1],b[1]) and y0+EPS<a[1]<y1-EPS and max(min(a[0],b[0]),x0+EPS)<min(max(a[0],b[0]),x1-EPS):node_hits.append([name,node,a,b])
  src,dst=name.split('->')
  for node,tip,away in [(src,clean[0],clean[1]),(dst,clean[-1],clean[-2])]:
   x0,y0,x1,y1=bounds[node];dx,dy=away[0]-tip[0],away[1]-tip[1]
   good=((close(tip[0],x0) and dx<0 and close(dy,0)) or(close(tip[0],x1) and dx>0 and close(dy,0)) or(close(tip[1],y0) and dy<0 and close(dx,0)) or(close(tip[1],y1) and dy>0 and close(dx,0)))
   if not good:port_bad.append([name,node,tip,away])
 overlaps=[];crossings=[];contacts=[]
 for i,(k,a,b) in enumerate(segs):
  for l,c,d in segs[i+1:]:
   if k==l:continue
   if close(a[0],b[0]) and close(c[0],d[0]) and close(a[0],c[0]):
    low=max(min(a[1],b[1]),min(c[1],d[1]));high=min(max(a[1],b[1]),max(c[1],d[1]))
    if high-low>EPS:overlaps.append([k,l,[a[0],low],[a[0],high]])
   if close(a[1],b[1]) and close(c[1],d[1]) and close(a[1],c[1]):
    low=max(min(a[0],b[0]),min(c[0],d[0]));high=min(max(a[0],b[0]),max(c[0],d[0]))
    if high-low>EPS:overlaps.append([k,l,[low,a[1]],[high,a[1]]])
   v,h=None,None
   if close(a[0],b[0]) and close(c[1],d[1]):v,h=(a,b),(c,d)
   elif close(a[1],b[1]) and close(c[0],d[0]):v,h=(c,d),(a,b)
   if v:
    x,y=v[0][0],h[0][1]
    if min(h[0][0],h[1][0])+EPS<x<max(h[0][0],h[1][0])-EPS and min(v[0][1],v[1][1])+EPS<y<max(v[0][1],v[1][1])-EPS:crossings.append([k,l,x,y])
    elif min(h[0][0],h[1][0])-EPS<=x<=max(h[0][0],h[1][0])+EPS and min(v[0][1],v[1][1])-EPS<=y<=max(v[0][1],v[1][1])+EPS:contacts.append([k,l,x,y])
 return {'source':str(path),'nodes':len(bounds),'edges':len(routes),'bends':bends,'length':round(sum(math.dist(a,b) for _,a,b in segs),2),'short_segments_under_10':sum(math.dist(a,b)<10-EPS for _,a,b in segs),'collinear_overlap_pairs':len(overlaps),'proper_crossings':len(crossings),'perpendicular_endpoint_contacts':len(contacts),'nonorthogonal_segments':len(orthogonal),'node_interior_intersections':len(node_hits),'bad_port_normals':len(port_bad),'overlaps':overlaps,'crossings':crossings,'endpoint_contacts':contacts,'nonorthogonal_details':orthogonal,'node_hit_details':node_hits,'bad_port_details':port_bad}
if __name__=='__main__':
 result=metrics(sys.argv[1]);s=json.dumps(result,indent=2)
 if len(sys.argv)>2:Path(sys.argv[2]).write_text(s+'\n')
 print(json.dumps({k:v for k,v in result.items() if not isinstance(v,list)},indent=2))
