"""
Marble Music Generator - Configuration
========================================
All configurable parameters for the pipeline.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum


class ThemePreset(Enum):
    PASTEL = "pastel"
    NEON = "neon"
    DARK = "dark"
    WARM = "warm"
    OCEAN = "ocean"
    TEAL = "teal"
    SUNSET = "sunset"


@dataclass
class RenderConfig:
    """Rendering settings."""
    # TikTok vertical format
    resolution_x: int = 1080
    resolution_y: int = 1920
    fps: int = 60
    engine: str = "CYCLES"  # CYCLES or BLENDER_EEVEE_NEXT
    samples: int = 128  # For Cycles
    use_denoising: bool = True
    use_motion_blur: bool = True
    motion_blur_shutter: float = 0.5
    output_format: str = "FFMPEG"
    video_codec: str = "H264"
    video_quality: str = "HIGH"  # LOWEST, LOW, MEDIUM, HIGH, LOSSLESS
    film_transparent: bool = False
    use_gpu: bool = True
    # For Eevee (faster preview)
    eevee_samples: int = 64
    eevee_use_bloom: bool = True
    eevee_bloom_threshold: float = 0.8
    eevee_bloom_intensity: float = 0.1
    eevee_use_ssr: bool = True  # Screen Space Reflections
    eevee_use_ao: bool = True   # Ambient Occlusion


@dataclass
class PhysicsConfig:
    """Ball physics parameters."""
    gravity: float = 9.81
    restitution: float = 0.7  # Bounce coefficient
    ball_radius: float = 0.15
    ball_mass: float = 1.0
    # Arc parameters
    min_arc_height: float = 0.5
    max_arc_height: float = 3.0
    # Velocity mapping
    velocity_to_arc_multiplier: float = 0.02
    # Spin
    enable_spin: bool = True
    spin_speed_multiplier: float = 2.0


@dataclass
class PlatformConfig:
    """Xylophone platform settings."""
    # Base dimensions
    base_width: float = 0.6
    base_depth: float = 0.4
    base_height: float = 0.08
    # Size variation based on pitch
    min_width_factor: float = 0.5   # High pitch = smaller
    max_width_factor: float = 1.5   # Low pitch = larger
    # Leg/support settings
    leg_radius: float = 0.02
    leg_height: float = 0.15
    leg_offset: float = 0.05  # Distance from platform edge
    # Bevel
    bevel_width: float = 0.01
    bevel_segments: int = 3
    # Spacing
    base_spacing: float = 1.5  # Base distance between platforms
    # Dot holes (decorative)
    enable_dots: bool = True
    dot_radius: float = 0.015
    dot_depth: float = 0.02


@dataclass
class RailConfig:
    """Rail/ramp settings."""
    rail_radius: float = 0.025
    rail_spacing: float = 0.1  # Distance between parallel rails
    rail_segments: int = 32
    enable_wavy_rails: bool = True
    wave_amplitude: float = 0.05
    wave_frequency: float = 2.0


@dataclass
class CameraConfig:
    """Camera settings."""
    # Follow parameters
    follow_smoothing: float = 0.1
    look_ahead: float = 2.0  # How far ahead the camera looks
    # Offset from ball
    offset_x: float = 0.0
    offset_y: float = -3.0
    offset_z: float = 5.0
    # Field of view
    focal_length: float = 35.0
    # Depth of field
    enable_dof: bool = True
    dof_fstop: float = 2.8
    # Dynamic effects
    enable_zoom_on_impact: bool = True
    zoom_amount: float = 0.05
    enable_rotation: bool = True
    rotation_speed: float = 0.01
    # View angle
    # "top_down", "isometric", "side", "dynamic"
    view_mode: str = "dynamic"


@dataclass
class EffectsConfig:
    """Visual effects settings."""
    # Impact glow
    enable_impact_glow: bool = True
    glow_intensity: float = 5.0
    glow_duration_frames: int = 8
    glow_color_from_platform: bool = True
    # Particles
    enable_particles: bool = True
    particle_count: int = 20
    particle_lifetime: int = 15  # frames
    particle_size: float = 0.02
    particle_type: str = "stars"  # "stars", "dots", "sparks"
    # Motion trail
    enable_trail: bool = False
    trail_length: int = 5
    # Platform animation
    enable_platform_reaction: bool = True
    platform_press_depth: float = 0.03
    platform_press_duration: int = 6  # frames
    # Background particles (ambient)
    enable_ambient_particles: bool = True
    ambient_particle_count: int = 50


@dataclass
class LightingConfig:
    """Lighting setup."""
    # Main light
    main_light_energy: float = 500.0
    main_light_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    main_light_angle: float = 45.0
    # Fill light
    fill_light_energy: float = 200.0
    # Rim light
    rim_light_energy: float = 300.0
    # Dynamic lighting on impact
    enable_dynamic_lights: bool = True
    impact_light_energy: float = 100.0
    impact_light_duration: int = 8
    # HDRI
    use_hdri: bool = False
    hdri_path: str = ""
    # Background
    background_type: str = "gradient"  # "solid", "gradient", "hdri"


@dataclass
class LayoutConfig:
    """Level layout parameters."""
    # Direction of travel
    # "horizontal", "vertical", "spiral", "zigzag", "cascade"
    layout_mode: str = "cascade"
    # For cascade/zigzag
    zigzag_width: float = 3.0
    zigzag_angle: float = 30.0
    # For spiral
    spiral_radius: float = 5.0
    spiral_pitch: float = 1.0
    # Vertical drop per platform
    vertical_drop: float = 0.4
    # Randomization
    position_jitter: float = 0.1
    rotation_jitter: float = 5.0  # degrees
    # Section breaks (for camera cuts)
    section_length: int = 16  # notes per section
    section_gap: float = 2.0


@dataclass
class MIDIConfig:
    """MIDI parsing configuration."""
    # Note range mapping
    min_midi_note: int = 36   # C2
    max_midi_note: int = 96   # C7
    # Velocity mapping
    min_velocity: int = 20
    max_velocity: int = 127
    # Track selection
    track_index: Optional[int] = None  # None = auto-detect
    # Timing
    lead_in_time: float = 1.0  # seconds before first note
    lead_out_time: float = 2.0  # seconds after last note
    # Quantization (optional)
    quantize: bool = False
    quantize_resolution: float = 0.25  # quarter note


@dataclass
class MarbleMusicConfig:
    """Master configuration combining all sub-configs."""
    render: RenderConfig = field(default_factory=RenderConfig)
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    rail: RailConfig = field(default_factory=RailConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    effects: EffectsConfig = field(default_factory=EffectsConfig)
    lighting: LightingConfig = field(default_factory=LightingConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    midi: MIDIConfig = field(default_factory=MIDIConfig)
    
    # Theme
    theme: ThemePreset = ThemePreset.TEAL
    seed: int = 42  # Random seed for reproducibility
    
    # Output
    output_path: str = "/tmp/marble_music_output.mp4"
    
    # Debug
    debug: bool = False
    preview_mode: bool = False  # Lower quality for preview


# ============================================================
# THEME DEFINITIONS
# ============================================================

THEME_PALETTES = {
    ThemePreset.PASTEL: {
        "name": "Pastel Dreams",
        "background_top": (0.85, 0.88, 0.90),
        "background_bottom": (0.95, 0.93, 0.92),
        "platform_colors": [
            (0.95, 0.70, 0.70),  # Soft pink
            (0.70, 0.85, 0.95),  # Soft blue
            (0.80, 0.95, 0.75),  # Soft green
            (0.95, 0.90, 0.70),  # Soft yellow
            (0.85, 0.75, 0.95),  # Soft purple
            (0.95, 0.80, 0.70),  # Soft orange
        ],
        "ball_color": (0.95, 0.95, 0.97),
        "ball_type": "rainbow",  # "solid", "metallic", "rainbow", "glass"
        "leg_color": (0.3, 0.3, 0.35),
        "rail_color": (0.7, 0.7, 0.75),
        "particle_color": (1.0, 1.0, 0.9),
        "glow_color": (1.0, 0.95, 0.85),
        "ambient_light": (0.95, 0.92, 0.90),
    },
    ThemePreset.NEON: {
        "name": "Neon Nights",
        "background_top": (0.02, 0.02, 0.05),
        "background_bottom": (0.05, 0.02, 0.08),
        "platform_colors": [
            (1.0, 0.0, 0.4),    # Hot pink
            (0.0, 1.0, 0.8),    # Cyan
            (0.4, 0.0, 1.0),    # Purple
            (1.0, 0.8, 0.0),    # Yellow
            (0.0, 0.8, 1.0),    # Blue
            (0.0, 1.0, 0.2),    # Green
        ],
        "ball_color": (0.9, 0.9, 0.95),
        "ball_type": "glass",
        "leg_color": (0.1, 0.1, 0.15),
        "rail_color": (0.8, 0.0, 0.3),
        "particle_color": (1.0, 1.0, 1.0),
        "glow_color": (0.8, 0.2, 1.0),
        "ambient_light": (0.1, 0.05, 0.15),
    },
    ThemePreset.DARK: {
        "name": "Dark Elegance",
        "background_top": (0.05, 0.05, 0.08),
        "background_bottom": (0.02, 0.02, 0.04),
        "platform_colors": [
            (0.15, 0.15, 0.18),
            (0.20, 0.18, 0.22),
            (0.12, 0.14, 0.18),
            (0.18, 0.15, 0.15),
            (0.22, 0.20, 0.18),
            (0.10, 0.12, 0.16),
        ],
        "ball_color": (0.02, 0.02, 0.03),
        "ball_type": "metallic",
        "leg_color": (0.05, 0.05, 0.08),
        "rail_color": (0.6, 0.1, 0.1),
        "particle_color": (0.8, 0.8, 0.85),
        "glow_color": (1.0, 0.8, 0.6),
        "ambient_light": (0.05, 0.05, 0.08),
    },
    ThemePreset.WARM: {
        "name": "Warm Sunset",
        "background_top": (0.95, 0.55, 0.15),
        "background_bottom": (0.98, 0.70, 0.25),
        "platform_colors": [
            (0.90, 0.80, 0.20),  # Gold
            (0.95, 0.50, 0.30),  # Orange-pink
            (0.85, 0.25, 0.15),  # Red-orange
            (0.50, 0.15, 0.10),  # Dark red
            (0.70, 0.60, 0.15),  # Olive gold
            (0.95, 0.70, 0.40),  # Light gold
        ],
        "ball_color": (0.9, 0.85, 0.95),
        "ball_type": "glass",
        "leg_color": (0.15, 0.10, 0.05),
        "rail_color": (0.3, 0.15, 0.05),
        "particle_color": (1.0, 0.95, 0.7),
        "glow_color": (1.0, 0.8, 0.4),
        "ambient_light": (0.95, 0.75, 0.45),
    },
    ThemePreset.OCEAN: {
        "name": "Deep Ocean",
        "background_top": (0.05, 0.20, 0.45),
        "background_bottom": (0.02, 0.10, 0.30),
        "platform_colors": [
            (0.70, 0.15, 0.25),  # Red accent
            (0.20, 0.80, 0.60),  # Sea green
            (0.30, 0.50, 0.80),  # Ocean blue
            (0.15, 0.30, 0.50),  # Deep blue
            (0.10, 0.20, 0.40),  # Navy
            (0.50, 0.70, 0.85),  # Light blue
        ],
        "ball_color": (0.02, 0.02, 0.05),
        "ball_type": "metallic",
        "leg_color": (0.05, 0.08, 0.15),
        "rail_color": (0.6, 0.15, 0.2),
        "particle_color": (0.3, 0.5, 0.8),
        "glow_color": (0.4, 0.7, 1.0),
        "ambient_light": (0.1, 0.2, 0.4),
    },
    ThemePreset.TEAL: {
        "name": "Teal Vibes",
        "background_top": (0.10, 0.55, 0.52),
        "background_bottom": (0.08, 0.45, 0.42),
        "platform_colors": [
            (0.85, 0.80, 0.30),  # Yellow-green
            (0.60, 0.80, 0.25),  # Lime
            (0.30, 0.60, 0.50),  # Green-teal
            (0.10, 0.30, 0.28),  # Dark teal
            (0.05, 0.20, 0.20),  # Very dark
            (0.70, 0.85, 0.40),  # Light green
        ],
        "ball_color": (0.02, 0.02, 0.05),
        "ball_type": "metallic",
        "leg_color": (0.05, 0.15, 0.15),
        "rail_color": (0.7, 0.15, 0.15),
        "particle_color": (0.2, 0.3, 0.3),
        "glow_color": (0.5, 0.9, 0.8),
        "ambient_light": (0.15, 0.4, 0.38),
    },
    ThemePreset.SUNSET: {
        "name": "Sunset Gradient",
        "background_top": (0.95, 0.40, 0.30),
        "background_bottom": (0.50, 0.15, 0.40),
        "platform_colors": [
            (1.0, 0.85, 0.40),
            (1.0, 0.60, 0.30),
            (0.95, 0.35, 0.35),
            (0.70, 0.20, 0.45),
            (0.45, 0.15, 0.50),
            (0.85, 0.70, 0.35),
        ],
        "ball_color": (0.95, 0.90, 0.85),
        "ball_type": "rainbow",
        "leg_color": (0.2, 0.1, 0.15),
        "rail_color": (0.8, 0.3, 0.2),
        "particle_color": (1.0, 0.9, 0.7),
        "glow_color": (1.0, 0.6, 0.3),
        "ambient_light": (0.8, 0.4, 0.35),
    },
}
