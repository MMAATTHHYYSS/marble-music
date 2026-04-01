"""
Marble Music Generator - Scene Builder (Blender)
==================================================
Creates the complete 3D scene in Blender from level data.
Handles object creation, materials, lighting, and world setup.

Must be run inside Blender's Python environment.
"""

import math
import random
import sys
import os

# Blender imports (only available when running inside Blender)
try:
    import bpy
    import bmesh
    from mathutils import Vector, Euler, Matrix
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    print("[Scene Builder] WARNING: Blender not available. Module can only be used for testing.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MarbleMusicConfig, THEME_PALETTES


def build_scene(level_data, config: MarbleMusicConfig):
    """
    Build the complete Blender scene from level data.
    
    Args:
        level_data: LevelData from level_generator
        config: Master configuration
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("This module must be run inside Blender!")
    
    random.seed(config.seed)
    theme = THEME_PALETTES[config.theme]
    
    print("[Scene Builder] Building scene...")
    
    # Step 1: Clean scene
    _clear_scene()
    
    # Step 2: Setup world (background, ambient)
    _setup_world(config, theme)
    
    # Step 3: Create materials library
    materials = _create_materials(config, theme)
    
    # Step 4: Create platforms
    _create_platforms(level_data.platforms, config, theme, materials)
    
    # Step 5: Create rails
    _create_rails(level_data.rails, config, theme, materials)
    
    # Step 6: Create ball
    ball_obj = _create_ball(config, theme, materials)
    
    # Step 7: Animate ball
    _animate_ball(ball_obj, level_data.ball_keyframes, config)
    
    # Step 8: Create impact effects
    _create_impact_effects(level_data, config, theme)
    
    # Step 9: Animate platform reactions
    _animate_platform_reactions(level_data, config)
    
    # Step 10: Setup lighting
    _setup_lighting(level_data, config, theme)
    
    # Step 11: Setup camera
    camera_obj = _setup_camera(level_data, config)
    
    # Step 12: Animate camera
    _animate_camera(camera_obj, ball_obj, level_data, config)
    
    # Step 13: Setup render settings
    _setup_render(level_data, config)
    
    print(f"[Scene Builder] Scene built successfully!")
    print(f"  Objects: {len(bpy.data.objects)}")
    print(f"  Materials: {len(bpy.data.materials)}")
    print(f"  Frames: {level_data.total_frames}")
    
    return ball_obj, camera_obj


def _clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)
    for block in bpy.data.lights:
        if block.users == 0:
            bpy.data.lights.remove(block)


def _setup_world(config: MarbleMusicConfig, theme: dict):
    """Setup world background and environment."""
    world = bpy.data.worlds.get("World")
    if not world:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    # Output node
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (600, 0)
    
    bg_top = theme["background_top"]
    bg_bottom = theme["background_bottom"]
    
    if config.lighting.background_type == "gradient":
        # Gradient background
        bg_node = nodes.new('ShaderNodeBackground')
        bg_node.location = (400, 0)
        
        mix_rgb = nodes.new('ShaderNodeMix')
        mix_rgb.data_type = 'RGBA'
        mix_rgb.location = (200, 0)
        mix_rgb.inputs['A'].default_value = (*bg_bottom, 1.0)
        mix_rgb.inputs['B'].default_value = (*bg_top, 1.0)
        
        # Use camera ray Z for gradient
        tex_coord = nodes.new('ShaderNodeTexCoord')
        tex_coord.location = (-200, 0)
        
        separate = nodes.new('ShaderNodeSeparateXYZ')
        separate.location = (0, 0)
        
        map_range = nodes.new('ShaderNodeMapRange')
        map_range.location = (100, 100)
        map_range.inputs['From Min'].default_value = -1.0
        map_range.inputs['From Max'].default_value = 1.0
        
        links.new(tex_coord.outputs['Generated'], separate.inputs['Vector'])
        links.new(separate.outputs['Z'], map_range.inputs['Value'])
        links.new(map_range.outputs['Result'], mix_rgb.inputs['Factor'])
        links.new(mix_rgb.outputs['Result'], bg_node.inputs['Color'])
        links.new(bg_node.outputs['Background'], output.inputs['Surface'])
        
        bg_node.inputs['Strength'].default_value = 1.0
        
    elif config.lighting.background_type == "solid":
        bg_node = nodes.new('ShaderNodeBackground')
        bg_node.location = (400, 0)
        bg_node.inputs['Color'].default_value = (*bg_top, 1.0)
        bg_node.inputs['Strength'].default_value = 1.0
        links.new(bg_node.outputs['Background'], output.inputs['Surface'])
    
    elif config.lighting.background_type == "hdri" and config.lighting.use_hdri:
        bg_node = nodes.new('ShaderNodeBackground')
        bg_node.location = (400, 0)
        env_tex = nodes.new('ShaderNodeTexEnvironment')
        env_tex.location = (0, 0)
        env_tex.image = bpy.data.images.load(config.lighting.hdri_path)
        links.new(env_tex.outputs['Color'], bg_node.inputs['Color'])
        links.new(bg_node.outputs['Background'], output.inputs['Surface'])


def _create_materials(config: MarbleMusicConfig, theme: dict) -> dict:
    """Create all reusable materials."""
    materials = {}
    
    # --- Platform materials (one per theme color) ---
    for i, color in enumerate(theme["platform_colors"]):
        mat = bpy.data.materials.new(f"Platform_{i}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Metallic'].default_value = 0.3
        bsdf.inputs['Roughness'].default_value = 0.4
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
        
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        materials[f"platform_{i}"] = mat
    
    # --- Ball material ---
    ball_mat = bpy.data.materials.new("Ball")
    ball_mat.use_nodes = True
    nodes = ball_mat.node_tree.nodes
    links = ball_mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)
    
    ball_type = theme.get("ball_type", "metallic")
    
    if ball_type == "metallic":
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bsdf.inputs['Base Color'].default_value = (*theme["ball_color"], 1.0)
        bsdf.inputs['Metallic'].default_value = 0.95
        bsdf.inputs['Roughness'].default_value = 0.05
        bsdf.inputs['Specular IOR Level'].default_value = 1.0
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
    elif ball_type == "glass":
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bsdf.inputs['Base Color'].default_value = (*theme["ball_color"], 1.0)
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.0
        bsdf.inputs['Transmission Weight'].default_value = 0.9
        bsdf.inputs['IOR'].default_value = 1.45
        bsdf.inputs['Specular IOR Level'].default_value = 1.0
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
    elif ball_type == "rainbow":
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (200, 0)
        bsdf.inputs['Metallic'].default_value = 0.6
        bsdf.inputs['Roughness'].default_value = 0.15
        bsdf.inputs['Specular IOR Level'].default_value = 0.8
        
        # Rainbow gradient based on surface normal
        tex_coord = nodes.new('ShaderNodeTexCoord')
        tex_coord.location = (-400, 0)
        
        separate = nodes.new('ShaderNodeSeparateXYZ')
        separate.location = (-200, 0)
        
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.location = (0, 0)
        # Setup rainbow gradient
        cr = color_ramp.color_ramp
        cr.elements[0].position = 0.0
        cr.elements[0].color = (1, 0, 0, 1)
        cr.elements.new(0.17).color = (1, 0.5, 0, 1)
        cr.elements.new(0.33).color = (1, 1, 0, 1)
        cr.elements.new(0.5).color = (0, 1, 0, 1)
        cr.elements.new(0.67).color = (0, 0.5, 1, 1)
        cr.elements.new(0.83).color = (0.3, 0, 1, 1)
        cr.elements[len(cr.elements)-1].position = 1.0
        cr.elements[len(cr.elements)-1].color = (0.8, 0, 0.8, 1)
        
        links.new(tex_coord.outputs['Normal'], separate.inputs['Vector'])
        links.new(separate.outputs['X'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    else:  # solid
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bsdf.inputs['Base Color'].default_value = (*theme["ball_color"], 1.0)
        bsdf.inputs['Metallic'].default_value = 0.5
        bsdf.inputs['Roughness'].default_value = 0.3
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    materials["ball"] = ball_mat
    
    # --- Leg/support material ---
    leg_mat = bpy.data.materials.new("Leg_Metal")
    leg_mat.use_nodes = True
    nodes = leg_mat.node_tree.nodes
    links = leg_mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*theme["leg_color"], 1.0)
    bsdf.inputs['Metallic'].default_value = 0.9
    bsdf.inputs['Roughness'].default_value = 0.3
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    materials["leg"] = leg_mat
    
    # --- Rail material ---
    rail_mat = bpy.data.materials.new("Rail_Metal")
    rail_mat.use_nodes = True
    nodes = rail_mat.node_tree.nodes
    links = rail_mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*theme["rail_color"], 1.0)
    bsdf.inputs['Metallic'].default_value = 0.85
    bsdf.inputs['Roughness'].default_value = 0.2
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    materials["rail"] = rail_mat
    
    # --- Glow material (for impact effects) ---
    glow_mat = bpy.data.materials.new("Glow")
    glow_mat.use_nodes = True
    nodes = glow_mat.node_tree.nodes
    links = glow_mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (0, 0)
    emission.inputs['Color'].default_value = (*theme["glow_color"], 1.0)
    emission.inputs['Strength'].default_value = 5.0
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    transparent.location = (0, -200)
    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (200, 0)
    mix.inputs['Fac'].default_value = 0.5
    links.new(transparent.outputs['BSDF'], mix.inputs[1])
    links.new(emission.outputs['Emission'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    materials["glow"] = glow_mat
    
    return materials


def _create_platforms(platforms, config: MarbleMusicConfig, theme: dict, materials: dict):
    """Create all platform objects with legs and dots."""
    plat_cfg = config.platform
    
    platform_collection = bpy.data.collections.new("Platforms")
    bpy.context.scene.collection.children.link(platform_collection)
    
    for plat in platforms:
        # --- Main platform body ---
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=plat.position,
        )
        obj = bpy.context.active_object
        obj.name = f"Platform_{plat.index:04d}"
        obj.scale = (plat.width, plat.depth, plat.height)
        
        # Apply scale to mesh
        bpy.ops.object.transform_apply(scale=True)
        
        # Add bevel
        bevel = obj.modifiers.new("Bevel", 'BEVEL')
        bevel.width = plat_cfg.bevel_width
        bevel.segments = plat_cfg.bevel_segments
        
        # Rotation
        obj.rotation_euler.z = math.radians(plat.rotation)
        
        # Assign material
        color_idx = plat.index % len(theme["platform_colors"])
        mat_key = f"platform_{color_idx}"
        
        # Create a unique material for this platform with its specific color
        unique_mat = materials[mat_key].copy()
        unique_mat.name = f"Platform_Mat_{plat.index:04d}"
        # Update color
        for node in unique_mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (*plat.color, 1.0)
                node.inputs['Metallic'].default_value = plat.metalness
                node.inputs['Roughness'].default_value = plat.roughness
                if plat.emission_strength > 0:
                    node.inputs['Emission Strength'].default_value = plat.emission_strength
                    node.inputs['Emission Color'].default_value = (*plat.color, 1.0)
                break
        
        obj.data.materials.append(unique_mat)
        
        # Move to collection
        for col in obj.users_collection:
            col.objects.unlink(obj)
        platform_collection.objects.link(obj)
        
        # Store custom properties
        obj["platform_index"] = plat.index
        obj["hit_frame"] = plat.frame
        obj["velocity"] = plat.velocity
        
        # --- Legs/supports ---
        _create_platform_legs(obj, plat, plat_cfg, materials)
        
        # --- Decorative dots ---
        if plat_cfg.enable_dots:
            _create_platform_dots(obj, plat, plat_cfg, materials)


def _create_platform_legs(parent_obj, plat, plat_cfg, materials):
    """Create metal legs/supports for a platform."""
    leg_positions = [
        (-plat.width/2 + plat_cfg.leg_offset, 0, -plat.height/2),
        (plat.width/2 - plat_cfg.leg_offset, 0, -plat.height/2),
    ]
    
    for i, (lx, ly, lz) in enumerate(leg_positions):
        # Vertical leg
        bpy.ops.mesh.primitive_cylinder_add(
            radius=plat_cfg.leg_radius,
            depth=plat_cfg.leg_height,
            location=(
                plat.position[0] + lx,
                plat.position[1] + ly,
                plat.position[2] + lz - plat_cfg.leg_height/2,
            )
        )
        leg = bpy.context.active_object
        leg.name = f"Leg_{plat.index:04d}_{i}"
        leg.data.materials.append(materials["leg"])
        leg.parent = parent_obj
        
        # Horizontal bar (bracket)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=plat_cfg.leg_radius * 0.8,
            depth=plat.depth * 0.3,
            location=(
                plat.position[0] + lx,
                plat.position[1],
                plat.position[2] + lz - plat_cfg.leg_height,
            )
        )
        bar = bpy.context.active_object
        bar.name = f"Bar_{plat.index:04d}_{i}"
        bar.rotation_euler.x = math.radians(90)
        bar.data.materials.append(materials["leg"])
        bar.parent = parent_obj


def _create_platform_dots(parent_obj, plat, plat_cfg, materials):
    """Create small decorative dots/holes on platform surface."""
    num_dots = random.randint(1, 3)
    
    for d in range(num_dots):
        dx = random.uniform(-plat.width * 0.3, plat.width * 0.3)
        dy = random.uniform(-plat.depth * 0.2, plat.depth * 0.2)
        
        bpy.ops.mesh.primitive_cylinder_add(
            radius=plat_cfg.dot_radius,
            depth=plat_cfg.dot_depth,
            location=(
                plat.position[0] + dx,
                plat.position[1] + dy,
                plat.position[2] + plat.height/2,
            )
        )
        dot = bpy.context.active_object
        dot.name = f"Dot_{plat.index:04d}_{d}"
        
        # Dark material for holes
        dot_mat = bpy.data.materials.new(f"Dot_{plat.index}_{d}")
        dot_mat.use_nodes = True
        for node in dot_mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (0.02, 0.02, 0.02, 1.0)
                node.inputs['Roughness'].default_value = 0.9
                break
        dot.data.materials.append(dot_mat)
        dot.parent = parent_obj


def _create_rails(rails, config: MarbleMusicConfig, theme: dict, materials: dict):
    """Create rail/track objects."""
    if not rails:
        return
    
    rail_collection = bpy.data.collections.new("Rails")
    bpy.context.scene.collection.children.link(rail_collection)
    
    rail_cfg = config.rail
    
    for i, rail in enumerate(rails):
        # Create curve for rail
        curve_data = bpy.data.curves.new(f"RailCurve_{i}", 'CURVE')
        curve_data.dimensions = '3D'
        curve_data.bevel_depth = rail_cfg.rail_radius
        curve_data.bevel_resolution = 4
        
        spline = curve_data.splines.new('BEZIER')
        
        # Points: start, control, end
        all_points = [rail.start_pos] + rail.control_points + [rail.end_pos]
        spline.bezier_points.add(len(all_points) - 1)
        
        for j, point in enumerate(all_points):
            bp = spline.bezier_points[j]
            bp.co = Vector(point)
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
        
        # Add waviness
        if rail.is_wavy and rail_cfg.enable_wavy_rails:
            for j, bp in enumerate(spline.bezier_points):
                offset = math.sin(j * rail_cfg.wave_frequency) * rail_cfg.wave_amplitude
                bp.co.z += offset
        
        # Create object
        rail_obj = bpy.data.objects.new(f"Rail_{i}", curve_data)
        rail_collection.objects.link(rail_obj)
        
        rail_obj.data.materials.append(materials["rail"])
        
        # Create parallel rail
        rail_obj2 = rail_obj.copy()
        rail_obj2.data = rail_obj.data.copy()
        rail_obj2.name = f"Rail_{i}_parallel"
        rail_obj2.location.x += rail_cfg.rail_spacing
        rail_collection.objects.link(rail_obj2)


def _create_ball(config: MarbleMusicConfig, theme: dict, materials: dict):
    """Create the marble ball."""
    phys = config.physics
    
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=phys.ball_radius,
        segments=48,
        ring_count=24,
        location=(0, 0, 5),  # Will be overwritten by animation
    )
    ball = bpy.context.active_object
    ball.name = "Marble_Ball"
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Assign material
    ball.data.materials.append(materials["ball"])
    
    # Add subdivision surface for smoother appearance
    subsurf = ball.modifiers.new("SubSurf", 'SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2
    
    return ball


def _animate_ball(ball_obj, keyframes, config: MarbleMusicConfig):
    """Apply keyframe animation to the ball."""
    phys = config.physics
    
    for kf in keyframes:
        ball_obj.location = Vector(kf.position)
        ball_obj.keyframe_insert(data_path="location", frame=kf.frame)
        
        # Add spin rotation
        if phys.enable_spin and kf.frame > 0:
            rot_speed = phys.spin_speed_multiplier
            ball_obj.rotation_euler.x = kf.frame * 0.05 * rot_speed
            ball_obj.rotation_euler.y = kf.frame * 0.03 * rot_speed
            ball_obj.keyframe_insert(data_path="rotation_euler", frame=kf.frame)
    
    # Set interpolation to smooth
    if ball_obj.animation_data and ball_obj.animation_data.action:
        action = ball_obj.animation_data.action
        fcurves = []
        if hasattr(action, 'fcurves'):
            fcurves = action.fcurves
        elif hasattr(action, 'layers') and action.layers:
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            fcurves.extend(cb.fcurves)
        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'AUTO'


def _create_impact_effects(level_data, config: MarbleMusicConfig, theme: dict):
    """Create impact glow and particle effects at contact points."""
    effects_cfg = config.effects
    
    if not effects_cfg.enable_impact_glow and not effects_cfg.enable_particles:
        return
    
    effects_collection = bpy.data.collections.new("Effects")
    bpy.context.scene.collection.children.link(effects_collection)
    
    contact_keyframes = [kf for kf in level_data.ball_keyframes if kf.is_contact]
    
    for kf in contact_keyframes:
        if kf.platform_index < 0 or kf.platform_index >= len(level_data.platforms):
            continue
            
        plat = level_data.platforms[kf.platform_index]
        
        # --- Glow sphere ---
        if effects_cfg.enable_impact_glow:
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.05,
                location=kf.position,
            )
            glow = bpy.context.active_object
            glow.name = f"Glow_{kf.platform_index:04d}"
            
            # Glow material
            glow_mat = bpy.data.materials.new(f"GlowMat_{kf.platform_index}")
            glow_mat.use_nodes = True
            for node in glow_mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    # Replace with emission
                    glow_mat.node_tree.nodes.remove(node)
                    break
            
            nodes = glow_mat.node_tree.nodes
            links = glow_mat.node_tree.links
            
            output = None
            for n in nodes:
                if n.type == 'OUTPUT_MATERIAL':
                    output = n
                    break
            if not output:
                output = nodes.new('ShaderNodeOutputMaterial')
            
            emission = nodes.new('ShaderNodeEmission')
            glow_color = theme["glow_color"] if not effects_cfg.glow_color_from_platform else plat.color
            emission.inputs['Color'].default_value = (*glow_color, 1.0)
            emission.inputs['Strength'].default_value = 0.0
            links.new(emission.outputs['Emission'], output.inputs['Surface'])
            
            glow.data.materials.append(glow_mat)
            
            # Animate glow: scale and emission
            dur = effects_cfg.glow_duration_frames
            
            # Before impact: invisible
            glow.scale = (0, 0, 0)
            glow.keyframe_insert(data_path="scale", frame=kf.frame - 1)
            emission.inputs['Strength'].default_value = 0
            emission.inputs['Strength'].keyframe_insert("default_value", frame=kf.frame - 1)
            
            # At impact: flash
            intensity = effects_cfg.glow_intensity * kf.velocity_at_contact
            glow.scale = (1, 1, 1)
            glow.keyframe_insert(data_path="scale", frame=kf.frame)
            emission.inputs['Strength'].default_value = intensity
            emission.inputs['Strength'].keyframe_insert("default_value", frame=kf.frame)
            
            # Fade out
            glow.scale = (2, 2, 2)
            glow.keyframe_insert(data_path="scale", frame=kf.frame + dur)
            emission.inputs['Strength'].default_value = 0
            emission.inputs['Strength'].keyframe_insert("default_value", frame=kf.frame + dur)
            
            for col in glow.users_collection:
                col.objects.unlink(glow)
            effects_collection.objects.link(glow)
        
        # --- Particle emitter (using mesh + keyframes as simple particles) ---
        if effects_cfg.enable_particles:
            _create_simple_particles(
                kf.position, kf.frame, kf.platform_index,
                plat.color, effects_cfg, effects_collection
            )


def _create_simple_particles(position, frame, index, color, effects_cfg, collection):
    """Create simple particle-like objects that burst on impact."""
    num = min(effects_cfg.particle_count, 12)  # Cap for performance
    lifetime = effects_cfg.particle_lifetime
    
    for p in range(num):
        angle = (p / num) * math.pi * 2
        speed = random.uniform(0.5, 1.5)
        
        # Random direction
        dx = math.cos(angle) * speed * 0.3
        dy = math.sin(angle) * speed * 0.3
        dz = random.uniform(0.2, 0.8)
        
        if effects_cfg.particle_type == "stars":
            # Small flat plane rotated randomly
            bpy.ops.mesh.primitive_plane_add(
                size=effects_cfg.particle_size * 2,
                location=position,
            )
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=effects_cfg.particle_size,
                segments=8,
                ring_count=4,
                location=position,
            )
        
        part = bpy.context.active_object
        part.name = f"Particle_{index:04d}_{p}"
        
        # Material
        part_mat = bpy.data.materials.new(f"PartMat_{index}_{p}")
        part_mat.use_nodes = True
        for node in part_mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (*color, 1.0)
                node.inputs['Emission Color'].default_value = (*color, 1.0)
                node.inputs['Emission Strength'].default_value = 2.0
                break
        part.data.materials.append(part_mat)
        
        # Animate: hidden -> burst -> fade
        # Before: hidden
        part.scale = (0, 0, 0)
        part.keyframe_insert(data_path="scale", frame=frame - 1)
        part.keyframe_insert(data_path="location", frame=frame - 1)
        
        # At impact: appear
        part.location = Vector(position)
        part.scale = (1, 1, 1)
        part.keyframe_insert(data_path="scale", frame=frame)
        part.keyframe_insert(data_path="location", frame=frame)
        
        # Fly outward and fade
        end_pos = (
            position[0] + dx,
            position[1] + dy,
            position[2] + dz,
        )
        part.location = Vector(end_pos)
        part.scale = (0.1, 0.1, 0.1)
        part.keyframe_insert(data_path="scale", frame=frame + lifetime)
        part.keyframe_insert(data_path="location", frame=frame + lifetime)
        
        # Random rotation
        part.rotation_euler = (
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
        )
        
        for col in part.users_collection:
            col.objects.unlink(part)
        collection.objects.link(part)


def _animate_platform_reactions(level_data, config: MarbleMusicConfig):
    """Animate platforms pressing down when the ball hits."""
    if not config.effects.enable_platform_reaction:
        return
    
    press_depth = config.effects.platform_press_depth
    press_dur = config.effects.platform_press_duration
    
    contact_keyframes = [kf for kf in level_data.ball_keyframes if kf.is_contact]
    
    for kf in contact_keyframes:
        if kf.platform_index < 0 or kf.platform_index >= len(level_data.platforms):
            continue
        
        plat = level_data.platforms[kf.platform_index]
        obj_name = f"Platform_{plat.index:04d}"
        obj = bpy.data.objects.get(obj_name)
        
        if not obj:
            continue
        
        # Rest position
        rest_z = plat.position[2]
        pressed_z = rest_z - press_depth * (plat.velocity / 127.0)
        
        # Before hit
        obj.location.z = rest_z
        obj.keyframe_insert(data_path="location", index=2, frame=kf.frame - 1)
        
        # At hit: press down
        obj.location.z = pressed_z
        obj.keyframe_insert(data_path="location", index=2, frame=kf.frame + 1)
        
        # Spring back
        obj.location.z = rest_z + press_depth * 0.2  # Slight overshoot
        obj.keyframe_insert(data_path="location", index=2, frame=kf.frame + press_dur // 2)
        
        # Settle
        obj.location.z = rest_z
        obj.keyframe_insert(data_path="location", index=2, frame=kf.frame + press_dur)


def _setup_lighting(level_data, config: MarbleMusicConfig, theme: dict):
    """Create the lighting setup."""
    light_cfg = config.lighting
    
    light_collection = bpy.data.collections.new("Lights")
    bpy.context.scene.collection.children.link(light_collection)
    
    # Calculate center of level
    platforms = level_data.platforms
    if platforms:
        center_x = sum(p.position[0] for p in platforms) / len(platforms)
        center_y = sum(p.position[1] for p in platforms) / len(platforms)
        center_z = sum(p.position[2] for p in platforms) / len(platforms)
    else:
        center_x, center_y, center_z = 0, 0, 0
    
    # --- Main key light ---
    bpy.ops.object.light_add(
        type='AREA',
        location=(center_x + 5, center_y - 5, center_z + 10)
    )
    main_light = bpy.context.active_object
    main_light.name = "Key_Light"
    main_light.data.energy = light_cfg.main_light_energy
    main_light.data.color = light_cfg.main_light_color
    main_light.data.size = 5.0
    main_light.data.shape = 'RECTANGLE'
    main_light.data.size = 8
    main_light.data.size_y = 6
    
    # Point at center
    direction = Vector((center_x, center_y, center_z)) - main_light.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    main_light.rotation_euler = rot_quat.to_euler()
    
    for col in main_light.users_collection:
        col.objects.unlink(main_light)
    light_collection.objects.link(main_light)
    
    # --- Fill light ---
    bpy.ops.object.light_add(
        type='AREA',
        location=(center_x - 4, center_y + 3, center_z + 6)
    )
    fill_light = bpy.context.active_object
    fill_light.name = "Fill_Light"
    fill_light.data.energy = light_cfg.fill_light_energy
    fill_light.data.color = theme["ambient_light"]
    fill_light.data.size = 6
    
    for col in fill_light.users_collection:
        col.objects.unlink(fill_light)
    light_collection.objects.link(fill_light)
    
    # --- Rim/back light ---
    bpy.ops.object.light_add(
        type='SPOT',
        location=(center_x, center_y + 8, center_z + 3)
    )
    rim_light = bpy.context.active_object
    rim_light.name = "Rim_Light"
    rim_light.data.energy = light_cfg.rim_light_energy
    rim_light.data.spot_size = math.radians(60)
    rim_light.data.spot_blend = 0.5
    
    direction = Vector((center_x, center_y, center_z)) - rim_light.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    rim_light.rotation_euler = rot_quat.to_euler()
    
    for col in rim_light.users_collection:
        col.objects.unlink(rim_light)
    light_collection.objects.link(rim_light)


def _setup_camera(level_data, config: MarbleMusicConfig):
    """Create and configure the camera."""
    cam_cfg = config.camera
    
    # Create camera
    cam_data = bpy.data.cameras.new("MainCamera")
    cam_data.lens = cam_cfg.focal_length
    cam_data.clip_start = 0.1
    cam_data.clip_end = 500
    
    if cam_cfg.enable_dof:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = cam_cfg.dof_fstop
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Initial position
    if level_data.platforms:
        first = level_data.platforms[0]
        cam_obj.location = (
            first.position[0] + cam_cfg.offset_x,
            first.position[1] + cam_cfg.offset_y,
            first.position[2] + cam_cfg.offset_z,
        )
    
    return cam_obj


def _animate_camera(camera_obj, ball_obj, level_data, config: MarbleMusicConfig):
    """Animate camera to follow the ball with cinematic movements."""
    cam_cfg = config.camera
    fps = config.render.fps
    
    if not level_data.ball_keyframes:
        return
    
    # Use DOF focus on ball
    if cam_cfg.enable_dof and camera_obj.data.dof:
        camera_obj.data.dof.focus_object = ball_obj
    
    # Create smooth camera path following ball with offset
    # Sample every N frames for smoother movement
    sample_interval = max(1, fps // 10)  # ~10 keyframes per second
    
    keyframes = level_data.ball_keyframes
    
    for i in range(0, len(keyframes), sample_interval):
        kf = keyframes[i]
        
        # Base position: offset from ball
        base_x = kf.position[0] + cam_cfg.offset_x
        base_y = kf.position[1] + cam_cfg.offset_y
        base_z = kf.position[2] + cam_cfg.offset_z
        
        # Add subtle rotation for dynamism
        if cam_cfg.enable_rotation:
            angle = kf.frame * cam_cfg.rotation_speed
            rot_radius = 1.0
            base_x += math.sin(angle) * rot_radius
            base_y += math.cos(angle) * rot_radius * 0.5
        
        # Look-ahead: bias camera slightly ahead in the path
        look_idx = min(i + int(cam_cfg.look_ahead * fps / sample_interval), len(keyframes) - 1)
        look_pos = keyframes[look_idx].position
        
        camera_obj.location = (base_x, base_y, base_z)
        camera_obj.keyframe_insert(data_path="location", frame=kf.frame)
        
        # Point camera at look-ahead position
        direction = Vector(look_pos) - camera_obj.location
        if direction.length > 0:
            rot_quat = direction.to_track_quat('-Z', 'Y')
            camera_obj.rotation_euler = rot_quat.to_euler()
            camera_obj.keyframe_insert(data_path="rotation_euler", frame=kf.frame)
    
    # Smooth all camera curves
    if camera_obj.animation_data and camera_obj.animation_data.action:
        action = camera_obj.animation_data.action
        fcurves = []
        if hasattr(action, 'fcurves'):
            fcurves = action.fcurves
        elif hasattr(action, 'layers') and action.layers:
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            fcurves.extend(cb.fcurves)
        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'AUTO'


def _setup_render(level_data, config: MarbleMusicConfig):
    """Configure render settings."""
    scene = bpy.context.scene
    render = scene.render
    rcfg = config.render
    
    # Resolution
    render.resolution_x = rcfg.resolution_x
    render.resolution_y = rcfg.resolution_y
    render.resolution_percentage = 100
    
    # FPS
    scene.frame_start = 0
    scene.frame_end = level_data.total_frames
    render.fps = rcfg.fps
    
    # Engine
    if rcfg.engine == "CYCLES":
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = rcfg.samples
        scene.cycles.use_denoising = rcfg.use_denoising
        
        if rcfg.use_gpu:
            scene.cycles.device = 'GPU'
            # Try to enable GPU
            try:
                prefs = bpy.context.preferences.addons['cycles'].preferences
                prefs.compute_device_type = 'CUDA'  # or 'OPTIX', 'HIP', 'METAL'
                prefs.get_devices()
                for device in prefs.devices:
                    device.use = True
            except Exception:
                print("[Render] GPU setup failed, falling back to CPU")
                scene.cycles.device = 'CPU'
    
    elif rcfg.engine == "BLENDER_EEVEE":
        scene.render.engine = 'BLENDER_EEVEE'
        try:
            scene.eevee.taa_render_samples = rcfg.eevee_samples
        except AttributeError:
            pass

        if rcfg.eevee_use_bloom:
            try:
                scene.eevee.use_bloom = True
                scene.eevee.bloom_threshold = rcfg.eevee_bloom_threshold
                scene.eevee.bloom_intensity = rcfg.eevee_bloom_intensity
            except AttributeError:
                pass

        if rcfg.eevee_use_ssr:
            try:
                scene.eevee.use_ssr = True
                scene.eevee.use_ssr_refraction = True
            except AttributeError:
                pass

        if rcfg.eevee_use_ao:
            try:
                scene.eevee.use_gtao = True
            except AttributeError:
                pass
    
    # Motion blur
    render.use_motion_blur = rcfg.use_motion_blur
    if rcfg.use_motion_blur:
        render.motion_blur_shutter = rcfg.motion_blur_shutter
    
    # Output: render PNG frames (FFMPEG encoder removed in Blender 5.1)
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_mode = 'RGB'
    frames_dir = config.output_path.replace('.mp4', '_frames') + '/'
    render.filepath = frames_dir
    
    # Color management
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    
    print(f"[Render Setup] Engine: {rcfg.engine}")
    print(f"  Resolution: {rcfg.resolution_x}x{rcfg.resolution_y} @ {rcfg.fps}fps")
    print(f"  Samples: {rcfg.samples if rcfg.engine == 'CYCLES' else rcfg.eevee_samples}")
    print(f"  Output: {config.output_path}")
