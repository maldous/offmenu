import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
base=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=24;scene.frame_start=1;scene.frame_end=577
scene.render.engine='CYCLES';scene.cycles.samples=4;scene.cycles.use_denoising=False
scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
scene.world.color=(.8,.8,.8)
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.84,.88,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8
mat={};objects=[]
def xyz(v):return (v[0],-v[2],v[1])
for i,m in enumerate(json.loads((base/'scene-input.json').read_text())):
 vs=[xyz(m['positions'][j:j+3]) for j in range(0,len(m['positions']),3)];fs=[m['indices'][j:j+3] for j in range(0,len(m['indices']),3)]
 mesh=bpy.data.meshes.new(m['name']);mesh.from_pydata(vs,[],fs);mesh.update();obj=bpy.data.objects.new(m['name'],mesh);scene.collection.objects.link(obj)
 if m['color'] not in mat:
  c=m['color'];color=tuple(int(c[j:j+2],16)/255 for j in (1,3,5))+(1,);ma=bpy.data.materials.new(c);ma.diffuse_color=color;ma.use_nodes=True;ma.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=color;ma.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85;mat[c]=ma
 obj.data.materials.append(mat[m['color']]);objects.append((obj,m))
 if m.get('motion')=='door':
  pivot=Vector(xyz(m['pivot']));obj.data.transform(__import__('mathutils').Matrix.Translation(-pivot));obj.location=pivot
  for frame,angle in [(1,0),(84,0),(132,-1.15),(577,-1.15)]:obj.rotation_euler[2]=-angle;obj.keyframe_insert(data_path='rotation_euler',frame=frame)
 if m.get('motion')=='stock':
  for frame,delta in [(1,(0,0,0)),(55,(0,0,0)),(85,(.32,.3,0)),(132,(.65,.01,0)),(577,(.65,.01,0))]:obj.location=xyz(delta);obj.keyframe_insert(data_path='location',frame=frame)
 if m.get('motion')=='scan':
  for frame,dy in [(1,0),(14,.06),(28,-.04),(42,.05),(56,0),(577,0)]:obj.location=(0,0,dy);obj.keyframe_insert(data_path='location',frame=frame)
 if m.get('motion')=='plan':
  for frame,dx in [(1,0),(288,0),(312,.14),(577,.14)]:obj.location=(dx,0,0);obj.keyframe_insert(data_path='location',frame=frame)
 if m.get('motion')=='steam':
  for frame in range(1,578,24):obj.location=(0,0,.07*max(0,math.sin(frame*.1)));obj.keyframe_insert(data_path='location',frame=frame)
cam_data=bpy.data.cameras.new('JourneyCamera');cam_data.type='ORTHO';cam_data.ortho_scale=6.8;cam=bpy.data.objects.new('JourneyCamera',cam_data);scene.collection.objects.link(cam);scene.camera=cam
shots=[(1,(.1,.78,0),.52,.55),(55,(-1.15,.86,.1),.64,.55),(132,(-.23,1.05,-.04),.96,.62),(216,(.65,.98,-.04),.48,.65),(300,(1.36,.96,0),.90,.58),(384,(1.95,.94,0),.62,.54),(468,(2.45,.95,0),.42,.65),(577,(.1,.78,0),.52,.55)]
for frame,target,yaw,elev in shots:
 t=Vector(target);depth=Vector((math.sin(yaw)*math.cos(elev),math.sin(elev),math.cos(yaw)*math.cos(elev)));eye=t+depth*7;cam.location=xyz(eye);direction=Vector(xyz(t))-cam.location;cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();cam.keyframe_insert(data_path='location',frame=frame);cam.keyframe_insert(data_path='rotation_euler',frame=frame)
for obj in bpy.data.objects:
 if obj.animation_data and obj.animation_data.action:
  for fc in obj.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
# Soft light and physically above-ground camera. Outline remains browser-renderer policy.
ld=bpy.data.lights.new('Softbox','AREA');lo=bpy.data.objects.new('Softbox',ld);scene.collection.objects.link(lo);lo.location=(-3,-4,6);ld.energy=450;ld.size=5
bpy.ops.wm.save_as_mainfile(filepath=str(base/'offmenu-journey.blend'))
bpy.ops.export_scene.gltf(filepath=str(base/'offmenu-journey.glb'),export_format='GLB',export_cameras=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_nla_strips=False)
def yup(v):return [float(v[0]),float(v[2]),float(-v[1])]
samples=[]
for frame in range(1,578,6):
 scene.frame_set(frame);matrix=cam.matrix_world
 samples.append({'frame':frame,'progress':(frame-1)/96,'eye':yup(matrix.translation),'right':yup(matrix.to_3x3().col[0]),'up':yup(matrix.to_3x3().col[1]),'depth':yup(matrix.to_3x3().col[2]),'halfHeight':1.9125,'objects':{m['motion']+':'+obj.name:{'shift':yup(obj.location-(Vector(xyz(m['pivot'])) if m.get('motion')=='door' else Vector((0,0,0)))),'turn':-obj.rotation_euler[2] if m.get('motion')=='door' else 0} for obj,m in objects if m.get('motion')}})
(base/'camera-timeline.json').write_text(json.dumps({'source':'offmenu-journey.blend','fps':24,'durationSeconds':24,'sampleStepFrames':6,'constantOrthographicScale':6.8,'samples':samples},separators=(',',':')))
scene.frame_set(1);scene.render.filepath=str(base/'roundtrip-shot.png');print('Reference rendering is a separate focused step')
print('ANIMATIC_READY',len(samples),str(base/'offmenu-journey.blend'))
