"""
Marble Music Generator - Level Generator
==========================================
Generates platform positions and properties from parsed MIDI data.
Calculates ball trajectories ensuring perfect synchronization.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from config import MarbleMusicConfig, LayoutConfig, THEME_PALETTES


@dataclass
class PlatformData:
    """Data for a single platform in the level."""
    index: int
    position: Tuple[float, float, float]  # (x, y, z)
    rotation: float  # Z rotation in degrees
    width: float
    depth: float
    height: float
    color: Tuple[float, float, float]
    color_alpha: float = 1.0
    # From MIDI
    pitch: int = 60
    velocity: int = 100
    time: float = 0.0
    frame: int = 0  # Frame number for this hit
    # Type
    platform_type: str = "xylophone"  # "xylophone", "rail", "ramp", "bouncer"
    # Material properties
    metalness: float = 0.3
    roughness: float = 0.4
    emission_strength: float = 0.0


@dataclass
class RailData:
    """Data for a rail segment."""
    start_pos: Tuple[float, float, float]
    end_pos: Tuple[float, float, float]
    control_points: List[Tuple[float, float, float]] = field(default_factory=list)
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    is_wavy: bool = False


@dataclass
class BallKeyframe:
    """Keyframe data for ball animation."""
    frame: int
    position: Tuple[float, float, float]
    is_contact: bool = False  # True when ball touches platform
    velocity_at_contact: float = 0.0
    platform_index: int = -1


@dataclass
class LevelData:
    """Complete level data for scene building."""
    platforms: List[PlatformData]
    rails: List[RailData]
    ball_keyframes: List[BallKeyframe]
    total_frames: int
    bounds_min: Tuple[float, float, float]
    bounds_max: Tuple[float, float, float]
    sections: List[Tuple[int, int]]  # (start_platform_idx, end_platform_idx)


def generate_level(midi_data, config: MarbleMusicConfig) -> LevelData:
    """
    Generate a complete level from MIDI data.
    
    Args:
        midi_data: Parsed MIDI data from midi_parser
        config: Master configuration
        
    Returns:
        LevelData with all platforms, rails, and ball keyframes
    """
    random.seed(config.seed)
    
    notes = midi_data.notes
    fps = config.render.fps
    theme = THEME_PALETTES[config.theme]
    layout = config.layout
    plat_cfg = config.platform
    phys_cfg = config.physics
    
    lead_in = config.midi.lead_in_time
    lead_out = config.midi.lead_out_time
    
    # ---- STEP 1: Calculate platform positions ----
    platforms = []
    
    for i, note in enumerate(notes):
        # Time to frame
        frame = int((note.time + lead_in) * fps)
        
        # Position calculation based on layout mode
        pos = _calculate_position(i, note, notes, layout, plat_cfg, config)
        
        # Size based on pitch (lower pitch = wider)
        pitch_factor = 1.0 - note.norm_pitch  # Invert: low pitch = large
        width = plat_cfg.base_width * (
            plat_cfg.min_width_factor + 
            pitch_factor * (plat_cfg.max_width_factor - plat_cfg.min_width_factor)
        )
        depth = plat_cfg.base_depth * (0.8 + pitch_factor * 0.4)
        
        # Color from theme, cycling through palette
        color_idx = i % len(theme["platform_colors"])
        # Optionally blend based on pitch for gradient effect
        if len(theme["platform_colors"]) > 1:
            color_pos = note.norm_pitch * (len(theme["platform_colors"]) - 1)
            c_idx1 = int(color_pos)
            c_idx2 = min(c_idx1 + 1, len(theme["platform_colors"]) - 1)
            t = color_pos - c_idx1
            c1 = theme["platform_colors"][c_idx1]
            c2 = theme["platform_colors"][c_idx2]
            color = tuple(c1[j] + t * (c2[j] - c1[j]) for j in range(3))
        else:
            color = theme["platform_colors"][0]
        
        # Rotation jitter
        rotation = random.uniform(-layout.rotation_jitter, layout.rotation_jitter)
        
        # Material properties based on velocity
        emission = note.norm_velocity * 0.3 if note.norm_velocity > 0.7 else 0.0
        
        platforms.append(PlatformData(
            index=i,
            position=pos,
            rotation=rotation,
            width=width,
            depth=depth,
            height=plat_cfg.base_height,
            color=color,
            pitch=note.pitch,
            velocity=note.velocity,
            time=note.time,
            frame=frame,
            metalness=0.2 + note.norm_pitch * 0.3,
            roughness=0.3 + (1.0 - note.norm_velocity) * 0.3,
            emission_strength=emission,
        ))
    
    # ---- STEP 2: Generate rails between certain platforms ----
    rails = _generate_rails(platforms, config, theme)
    
    # ---- STEP 3: Calculate ball trajectory keyframes ----
    ball_keyframes = _calculate_ball_trajectory(platforms, config)
    
    # ---- STEP 4: Compute bounds ----
    all_x = [p.position[0] for p in platforms]
    all_y = [p.position[1] for p in platforms]
    all_z = [p.position[2] for p in platforms]
    
    padding = 3.0
    bounds_min = (min(all_x) - padding, min(all_y) - padding, min(all_z) - padding)
    bounds_max = (max(all_x) + padding, max(all_y) + padding, max(all_z) + padding)
    
    # ---- STEP 5: Define sections ----
    section_size = layout.section_length
    sections = []
    for i in range(0, len(platforms), section_size):
        sections.append((i, min(i + section_size - 1, len(platforms) - 1)))
    
    # Total frames
    last_note_time = notes[-1].time + lead_in + lead_out
    total_frames = int(last_note_time * fps)
    
    print(f"[Level Generator] Generated {len(platforms)} platforms, {len(rails)} rails")
    print(f"  Total frames: {total_frames} ({total_frames/fps:.1f}s)")
    print(f"  Ball keyframes: {len(ball_keyframes)}")
    print(f"  Sections: {len(sections)}")
    
    return LevelData(
        platforms=platforms,
        rails=rails,
        ball_keyframes=ball_keyframes,
        total_frames=total_frames,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        sections=sections,
    )


def _calculate_position(
    index: int, 
    note, 
    all_notes: list,
    layout: LayoutConfig,
    plat_cfg,
    config: MarbleMusicConfig
) -> Tuple[float, float, float]:
    """Calculate platform position based on layout mode."""
    
    # Jitter
    jx = random.uniform(-layout.position_jitter, layout.position_jitter)
    jy = random.uniform(-layout.position_jitter, layout.position_jitter)
    
    if layout.layout_mode == "cascade":
        # Cascading waterfall - platforms descend with zigzag
        direction = 1 if (index // 4) % 2 == 0 else -1
        local_idx = index % 4
        
        x = direction * (local_idx * plat_cfg.base_spacing * 0.8) + jx
        y = -index * plat_cfg.base_spacing * 0.6 + jy
        z = -index * layout.vertical_drop
        
        # Add pitch-based X offset
        x += (note.norm_pitch - 0.5) * layout.zigzag_width
        
    elif layout.layout_mode == "zigzag":
        # Pure zigzag pattern
        segment = index // layout.section_length
        local_idx = index % layout.section_length
        direction = 1 if segment % 2 == 0 else -1
        
        angle_rad = math.radians(layout.zigzag_angle)
        
        x = direction * local_idx * plat_cfg.base_spacing * math.sin(angle_rad) + jx
        y = -index * plat_cfg.base_spacing * math.cos(angle_rad) * 0.5 + jy
        z = -index * layout.vertical_drop
        
    elif layout.layout_mode == "spiral":
        # Spiral downward
        angle = index * 0.4  # radians
        radius = layout.spiral_radius + index * 0.02
        
        x = math.cos(angle) * radius + jx
        y = math.sin(angle) * radius + jy
        z = -index * layout.spiral_pitch * 0.3
        
    elif layout.layout_mode == "horizontal":
        # Straight horizontal line
        x = index * plat_cfg.base_spacing + jx
        y = (note.norm_pitch - 0.5) * layout.zigzag_width + jy
        z = -index * layout.vertical_drop * 0.5
        
    elif layout.layout_mode == "vertical":
        # Straight vertical drop
        x = (note.norm_pitch - 0.5) * layout.zigzag_width + jx
        y = 0 + jy
        z = -index * layout.vertical_drop * 1.5
        
    else:
        # Default: cascade
        x = (note.norm_pitch - 0.5) * layout.zigzag_width + jx
        y = -index * plat_cfg.base_spacing * 0.6 + jy
        z = -index * layout.vertical_drop
    
    return (x, y, z)


def _generate_rails(
    platforms: List[PlatformData],
    config: MarbleMusicConfig,
    theme: dict
) -> List[RailData]:
    """Generate rail segments connecting some platforms."""
    rails = []
    rail_cfg = config.rail
    
    if not rail_cfg.enable_wavy_rails:
        return rails
    
    # Add rails at section transitions and long gaps
    for i in range(len(platforms) - 1):
        p1 = platforms[i]
        p2 = platforms[i + 1]
        
        # Calculate distance
        dx = p2.position[0] - p1.position[0]
        dy = p2.position[1] - p1.position[1]
        dz = p2.position[2] - p1.position[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        # Add rail for longer distances or at section boundaries
        if dist > config.platform.base_spacing * 2.5 or i % config.layout.section_length == 0:
            # Create control points for wavy rail
            mid_x = (p1.position[0] + p2.position[0]) / 2
            mid_y = (p1.position[1] + p2.position[1]) / 2
            mid_z = (p1.position[2] + p2.position[2]) / 2 + 0.2
            
            rail = RailData(
                start_pos=p1.position,
                end_pos=p2.position,
                control_points=[(mid_x, mid_y, mid_z)],
                color=theme["rail_color"],
                is_wavy=True,
            )
            rails.append(rail)
    
    return rails


def _calculate_ball_trajectory(
    platforms: List[PlatformData],
    config: MarbleMusicConfig
) -> List[BallKeyframe]:
    """
    Calculate exact ball positions for every frame.
    Uses parabolic arcs between platforms.
    """
    keyframes = []
    fps = config.render.fps
    phys = config.physics
    lead_in = config.midi.lead_in_time
    
    if not platforms:
        return keyframes
    
    # Starting position: above first platform
    first_plat = platforms[0]
    start_pos = (
        first_plat.position[0],
        first_plat.position[1],
        first_plat.position[2] + 3.0  # Start high above
    )
    
    # Lead-in: ball drops onto first platform
    start_frame = 0
    contact_frame = first_plat.frame
    
    # Generate drop-in arc
    for f in range(start_frame, contact_frame + 1):
        t = (f - start_frame) / max(contact_frame - start_frame, 1)
        # Simple drop with easing
        ease_t = t * t  # Accelerating
        x = start_pos[0] + (first_plat.position[0] - start_pos[0]) * t
        y = start_pos[1] + (first_plat.position[1] - start_pos[1]) * t
        z = start_pos[2] + (first_plat.position[2] + phys.ball_radius - start_pos[2]) * ease_t
        
        keyframes.append(BallKeyframe(
            frame=f,
            position=(x, y, z),
            is_contact=(f == contact_frame),
            platform_index=0 if f == contact_frame else -1,
        ))
    
    # For each pair of consecutive platforms, calculate parabolic arc
    for i in range(len(platforms) - 1):
        p1 = platforms[i]
        p2 = platforms[i + 1]
        
        f1 = p1.frame
        f2 = p2.frame
        
        if f2 <= f1:
            f2 = f1 + 2  # Minimum 2 frames
        
        # Contact positions (top of platform + ball radius)
        pos1 = (p1.position[0], p1.position[1], p1.position[2] + p1.height/2 + phys.ball_radius)
        pos2 = (p2.position[0], p2.position[1], p2.position[2] + p2.height/2 + phys.ball_radius)
        
        # Calculate arc height based on velocity and distance
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        horiz_dist = math.sqrt(dx*dx + dy*dy)
        
        # Arc height: combination of velocity influence and distance
        velocity_factor = p1.velocity / 127.0
        arc_height = (
            phys.min_arc_height + 
            (phys.max_arc_height - phys.min_arc_height) * velocity_factor * 0.5 +
            horiz_dist * 0.3
        )
        
        # If going down, need more arc; if going up, less
        if dz < 0:
            arc_height = max(arc_height, abs(dz) * 0.5 + 0.3)
        else:
            arc_height = max(arc_height + dz, phys.min_arc_height)
        
        # Generate intermediate keyframes with parabolic interpolation
        num_frames = f2 - f1
        
        for f in range(1, num_frames):
            t = f / num_frames  # 0 to 1 (exclusive of endpoints)
            
            # Horizontal interpolation: linear
            x = pos1[0] + dx * t
            y = pos1[1] + dy * t
            
            # Vertical: parabolic arc
            # z(t) = pos1.z + dz*t + arc_height * 4*t*(1-t)
            # This creates a parabola that starts at pos1.z and ends at pos2.z
            # with peak at t=0.5 being arc_height above the midpoint
            z_linear = pos1[2] + dz * t
            z_arc = arc_height * 4.0 * t * (1.0 - t)
            z = z_linear + z_arc
            
            keyframes.append(BallKeyframe(
                frame=f1 + f,
                position=(x, y, z),
                is_contact=False,
                platform_index=-1,
            ))
        
        # Add contact keyframe for p2
        keyframes.append(BallKeyframe(
            frame=f2,
            position=pos2,
            is_contact=True,
            velocity_at_contact=p2.velocity / 127.0,
            platform_index=i + 1,
        ))
    
    # Lead-out: ball bounces away from last platform
    last_plat = platforms[-1]
    lead_out_frames = int(config.midi.lead_out_time * fps)
    last_frame = last_plat.frame
    
    for f in range(1, lead_out_frames + 1):
        t = f / lead_out_frames
        x = last_plat.position[0] + t * 2.0
        y = last_plat.position[1] - t * 1.5
        # Parabolic exit arc
        z = (last_plat.position[2] + phys.ball_radius + 
             2.0 * 4.0 * t * (1.0 - t) - t * t * 3.0)
        
        keyframes.append(BallKeyframe(
            frame=last_frame + f,
            position=(x, y, z),
            is_contact=False,
            platform_index=-1,
        ))
    
    # Sort by frame and remove duplicates
    keyframes.sort(key=lambda k: k.frame)
    
    # Deduplicate frames (keep contact frames)
    seen = {}
    unique_keyframes = []
    for kf in keyframes:
        if kf.frame not in seen or kf.is_contact:
            seen[kf.frame] = True
            unique_keyframes.append(kf)
    
    return unique_keyframes
