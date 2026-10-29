// Original OffMenu procedural geometry. Metres, Y-up, no external model/texture.
export const palette={ink:'#23364b',cream:'#f6f1e6',blue:'#499be6',pale:'#c7dce5',orange:'#ed974c',skin:'#dca786',hair:'#293342',green:'#78a77f',red:'#cf7060',yellow:'#e8cb78',white:'#fffdf6'};
const P=palette;
function mesh(name,color){return {name,color,positions:[],normals:[],indices:[],edges:[]};}
function tri(m,a,b,c){const u=b.map((v,i)=>v-a[i]),v=c.map((v,i)=>v-a[i]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],l=Math.hypot(...n),k=m.positions.length/3;if(l<1e-12)return;m.positions.push(...a,...b,...c);m.normals.push(...n.map(x=>x/l),...n.map(x=>x/l),...n.map(x=>x/l));m.indices.push(k,k+1,k+2);}
function quad(m,a,b,c,d){tri(m,a,b,c);tri(m,a,c,d);}
export function box(name,w,h,d,color,x=0,y=0,z=0){const m=mesh(name,color),v=[[-w/2,0,-d/2],[w/2,0,-d/2],[w/2,h,-d/2],[-w/2,h,-d/2],[-w/2,0,d/2],[w/2,0,d/2],[w/2,h,d/2],[-w/2,h,d/2]].map(p=>[p[0]+x,p[1]+y,p[2]+z]);for(const f of [[0,3,2,1],[4,5,6,7],[0,4,7,3],[1,2,6,5],[3,7,6,2],[0,1,5,4]]){quad(m,...f.map(i=>v[i]));for(let i=0;i<4;i++)m.edges.push(...v[f[i]],...v[f[(i+1)%4]]);}return m;}
export function ellipsoid(name,rx,ry,rz,color,x=0,y=0,z=0,n=16,rings=10){const m=mesh(name,color),p=(i,j)=>{const a=i*Math.PI/rings,b=j*2*Math.PI/n;return [x+rx*Math.sin(a)*Math.cos(b),y+ry*Math.cos(a),z+rz*Math.sin(a)*Math.sin(b)];};for(let i=0;i<rings;i++)for(let j=0;j<n;j++)quad(m,p(i,j),p(i,j+1),p(i+1,j+1),p(i+1,j));return m;}
export function lathe(name,profile,color,x=0,y=0,z=0,n=32){const m=mesh(name,color),p=(i,j)=>[x+profile[i][0]*Math.cos(j*2*Math.PI/n),y+profile[i][1],z+profile[i][0]*Math.sin(j*2*Math.PI/n)];for(let i=0;i<profile.length-1;i++)for(let j=0;j<n;j++)quad(m,p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1));for(let i=0;i<profile.length;i++){if(i>0&&i<profile.length-1&&profile[i][0]===profile[i-1][0])continue;for(let j=0;j<n;j++)m.edges.push(...p(i,j),...p(i,j+1));}return m;}
function move(ms,x,y,z,scale=1){return ms.map(m=>({...m,positions:m.positions.map((v,i)=>v*scale+[x,y,z][i%3]),edges:m.edges.map((v,i)=>v*scale+[x,y,z][i%3])}));}
function bottle(){return [lathe('milk-body',[[0,0],[.044,0],[.048,.015],[.048,.16],[.036,.196],[.024,.205],[.024,.233],[0,.233]],P.white),lathe('blue-cap',[[0,.233],[.027,.233],[.027,.25],[0,.25]],P.blue),lathe('blue-label',[[.0485,.06],[.0485,.122]],P.blue),box('label-mark',.023,.025,.002,P.cream,0,.079,.049)];}
function phone(){return [box('phone-body',.085,.17,.013,P.ink),box('screen',.073,.15,.002,P.cream,0,.01,.0075),box('notch',.025,.006,.003,P.ink,0,.153,.009),...[-1,1].flatMap((a,i)=>[-1,1].map((c,j)=>box('screen-tile',.025,.032,.002,(i+j)%2?P.orange:P.blue,a*.018,.035+j*.045,.01)))];}
function fish(){return [ellipsoid('whole-fish',.12,.039,.027,P.pale,0,.042,0),ellipsoid('eye',.005,.005,.004,P.ink,-.078,.055,.025),ellipsoid('eye-other',.005,.005,.004,P.ink,-.078,.055,-.025),box('tail-volume',.05,.07,.012,P.blue,.125,.007,0),ellipsoid('dorsal-fin',.05,.016,.008,P.blue,.01,.081,0)];}
function oats(){const m=[lathe('bowl',[[0,0],[.052,0],[.074,.035],[.077,.05],[.071,.05],[.065,.035],[.045,.009],[0,.009]],P.pale)];for(let i=0;i<12;i++){const a=i*2.39996,r=.052*Math.sqrt(i/12);m.push(ellipsoid('oat-flake-'+i,.011,.003,.006,P.yellow,Math.cos(a)*r,.044+Math.sin(i)*.003,Math.sin(a)*r,6,3));}return m;}
function water(){return [lathe('glass-wall',[[.03,0],[.034,0],[.038,.13],[.034,.13],[.03,.006],[.03,0]],P.pale),lathe('water-volume',[[0,.006],[.03,.006],[.032,.09],[0,.09]],P.blue)];}
function butter(){return [box('butter-block',.095,.035,.06,P.yellow,0,.008,0),box('wrapper',.13,.004,.09,P.cream,0,.003,0)];}
function airfryer(){return [box('air-fryer-body',.29,.34,.29,P.pale),box('drawer',.25,.16,.017,P.ink,0,.025,.154),box('handle',.10,.025,.03,P.cream,0,.12,.176),box('control-panel',.2,.06,.008,P.ink,0,.24,.15),ellipsoid('dial',.014,.014,.008,P.blue,.06,.268,.16),box('display',.08,.018,.005,P.blue,-.03,.26,.157)];}
function person(){return [box('trousers-left',.105,.72,.13,P.ink,-.073,0,0),box('trousers-right',.105,.72,.13,P.ink,.073,0,0),ellipsoid('cream-shirt',.20,.30,.115,P.cream,0,.96,0),ellipsoid('neck',.055,.08,.05,P.skin,0,1.25,0),ellipsoid('face',.105,.145,.095,P.skin,0,1.43,0),ellipsoid('wavy-hair',.113,.075,.102,P.hair,0,1.53,-.009),ellipsoid('hair-wave',.06,.045,.05,P.hair,-.07,1.53,.067),ellipsoid('eye-left',.008,.009,.005,P.ink,-.034,1.45,.091),ellipsoid('eye-right',.008,.009,.005,P.ink,.035,1.45,.091),ellipsoid('left-arm',.055,.23,.055,P.cream,-.23,1.01,0),ellipsoid('right-arm',.055,.21,.055,P.cream,.23,1.01,0),ellipsoid('scanning-hand',.06,.04,.06,P.skin,.25,.86,.11),ellipsoid('holding-hand',.05,.045,.05,P.skin,-.23,.82,.09),...move(phone(),.25,.87,.13,.8)];}
export const assetBuilders={milk:bottle,fish,oats,water,butter,phone,airfryer,adult:person};
export function asset(id){if(!assetBuilders[id])throw Error('Unknown asset '+id);return assetBuilders[id]();}
function card(name,x,y,z,mode=0){return [box(name,.48,.64,.026,P.cream,x,y,z),box('blue-heading',.29,.035,.004,P.blue,x-.04,y+.54,z+.016),...Array.from({length:4},(_,i)=>[box('list-line',.27,.018,.004,P.pale,x+.04,y+.09+i*.098,z+.016),box('list-marker',.036,.036,.004,mode?P.orange:P.green,x-.16,y+.08+i*.098,z+.017)]).flat(),...move(mode?oats():bottle(),x,y+.27,z+.023,1.4)];}
export const focusPoints=[[-1.05,.78,0],[-.10,1.04,-.05],[.85,1.0,-.05],[1.55,1.02,-.05],[2.20,.90,0],[2.40,.94,0],[-.20,.90,0]];
export function scene(){const ms=[box('continuous-counter',4.5,.065,.74,palette.pale,.70,.72,0),box('ground',6,.015,2,palette.cream,.50,-.02,0),...move(person(),-1.77,0,.08)];
for(const x of [-1.40,2.80])for(const z of [-.29,.29])ms.push(box('table-leg-'+x+'-'+z,.065,.72,.065,palette.ink,x,0,z));
ms.push(...move(bottle(),-1.12,.785,.12,1.3),box('barcode',.07,.045,.003,palette.ink,-1.12,.895,.184));for(let i=0;i<6;i++)ms.push(box('barcode-line',.003,.04,.004,palette.cream,-1.147+i*.01,.898,.186));
ms.push({...box('scan-beam',.38,.008,.008,palette.orange,-1.35,.96,.18),motion:'scan'});
ms.push(box('pantry-back',.65,.85,.04,palette.pale,-.25,.785,-.28),box('pantry-side-left',.035,.85,.38,palette.pale,-.58,.785,-.10),box('pantry-side-right',.035,.85,.38,palette.pale,.08,.785,-.10),box('pantry-top',.68,.035,.40,palette.pale,-.25,1.60,-.10),box('stock-shelf',.65,.025,.38,palette.cream,-.25,1.19,-.10));
ms.push(...move(bottle(),-.43,1.22,-.07),...move(water(),-.17,1.22,-.07),...move(oats(),-.29,.80,.03,1.3));
ms.push({...box('inventory-door',.62,.80,.025,palette.pale,-.25,.80,.12),motion:'door',pivot:[.06,.8,.12]});
ms.push(...card('recipe-card',.65,.80,-.18,1),...move(fish(),.64,.80,.17,1.4));
ms.push(...card('meal-plan',1.36,.80,-.18),...move(oats(),1.35,.80,.16,1.3));
ms.push({...box('plan-marker',.05,.05,.012,palette.orange,1.20,1.25,-.15),motion:'plan'});
ms.push(box('paper-bag',.31,.38,.24,'#bd9470',1.91,.785,.02),...move(butter(),1.91,.80,.21,1.2));
ms.push(...move(airfryer(),2.54,.785,0,1.1),...move(oats(),2.24,.80,.22,1.25));
for(let i=0;i<3;i++)ms.push({...ellipsoid('steam-'+i,.012,.025,.012,palette.white,2.42+i*.055,1.19,.05,8,4),motion:'steam'});
ms.push({...box('stock-transfer',.07,.10,.06,palette.orange,-.98,.80,.08),motion:'stock'});return ms;}
export function camera(yaw=.65,pitch=.36){const c=Math.cos(yaw),s=Math.sin(yaw),p=Math.cos(pitch),q=Math.sin(pitch);return {right:[c,0,-s],up:[-s*q,p,-c*q],depth:[s*p,q,c*p]};}
export function project(v,cam){return [v[0]*cam.right[0]+v[2]*cam.right[2],v[0]*cam.up[0]+v[1]*cam.up[1]+v[2]*cam.up[2],v[0]*cam.depth[0]+v[1]*cam.depth[1]+v[2]*cam.depth[2]];}
