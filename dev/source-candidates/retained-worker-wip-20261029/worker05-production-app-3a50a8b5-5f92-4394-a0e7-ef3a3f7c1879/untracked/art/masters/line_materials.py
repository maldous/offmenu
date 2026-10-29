import bpy,math
from mathutils import Vector
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.use_denoising=False;scene.cycles.samples=2;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.view_settings.view_transform='Standard';scene.camera.data.ortho_scale=6.8
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.85,.87,.84,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=1
for mat in bpy.data.materials:
 if mat.name.startswith('Outline'):continue
 color=tuple(((c+.055)/1.055)**2.4 if c>.04045 else c/12.92 for c in mat.diffuse_color[:3])+(1,)
 mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');geo=n.new('ShaderNodeNewGeometry');dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=(-.3,-.5,.81);maximum=n.new('ShaderNodeMath');maximum.operation='MAXIMUM';maximum.inputs[1].default_value=0;mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.22;add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=.78;paint=n.new('ShaderNodeMixRGB');paint.blend_type='MULTIPLY';paint.inputs[0].default_value=1;paint.inputs[1].default_value=color
 l=mat.node_tree.links;l.new(geo.outputs['Normal'],dot.inputs[0]);l.new(dot.outputs['Value'],maximum.inputs[0]);l.new(maximum.outputs[0],mul.inputs[0]);l.new(mul.outputs[0],add.inputs[0]);l.new(add.outputs[0],paint.inputs[2]);l.new(paint.outputs[0],em.inputs['Color']);l.new(em.outputs[0],out.inputs[0])
# Deterministic flat material shading keeps this rough animatic free of path-tracing grain.
scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
