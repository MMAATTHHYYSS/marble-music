"""
Marble Music Generator - Main Pipeline
========================================
Orchestrates the complete pipeline from MIDI input to rendered video.

Usage (standalone):
    blender --background --python main.py -- --midi input.mid --output output.mp4

Usage (with audio):
    blender --background --python main.py -- --midi input.mid --audio music.mp3 --output output.mp4

Usage (preview / Eevee):
    blender --background --python main.py -- --midi input.mid --preview --output preview.mp4

Usage (test mode):
    blender --background --python main.py -- --test --output test.mp4
"""

import sys
import os
import argparse
import time
import json

# Ensure our modules are in path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'modules'))

from config import MarbleMusicConfig, ThemePreset, RenderConfig


def parse_args():
    """Parse command line arguments (after Blender's --)."""
    # Find arguments after '--'
    try:
        argv = sys.argv[sys.argv.index('--') + 1:]
    except ValueError:
        argv = []
    
    parser = argparse.ArgumentParser(description='Marble Music Video Generator')
    parser.add_argument('--midi', type=str, help='Path to MIDI file')
    parser.add_argument('--audio', type=str, help='Path to audio file (MP3/WAV)')
    parser.add_argument('--output', type=str, default=os.path.join(os.environ.get('TEMP', 'C:\\tmp'), 'marble_music.mp4'),
                        help='Output video path')
    parser.add_argument('--theme', type=str, default='teal',
                        choices=[t.value for t in ThemePreset],
                        help='Visual theme preset')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--layout', type=str, default='cascade',
                        choices=['cascade', 'zigzag', 'spiral', 'horizontal', 'vertical'],
                        help='Level layout mode')
    parser.add_argument('--fps', type=int, default=60, help='Frames per second')
    parser.add_argument('--samples', type=int, default=128,
                        help='Render samples (Cycles)')
    parser.add_argument('--engine', type=str, default='CYCLES',
                        choices=['CYCLES', 'BLENDER_EEVEE'],
                        help='Render engine')
    parser.add_argument('--preview', action='store_true',
                        help='Preview mode (lower quality, Eevee)')
    parser.add_argument('--test', action='store_true',
                        help='Use generated test MIDI')
    parser.add_argument('--no-render', action='store_true',
                        help='Build scene but skip rendering')
    parser.add_argument('--save-blend', type=str, default=None,
                        help='Save .blend file for manual editing')
    parser.add_argument('--config-json', type=str, default=None,
                        help='Path to JSON config override file')
    parser.add_argument('--ball-type', type=str, default=None,
                        choices=['metallic', 'glass', 'rainbow', 'solid'],
                        help='Override ball material type')
    parser.add_argument('--bounce-sfx', type=str, default=None,
                        help='Path to bounce sound effect file')
    parser.add_argument('--batch', type=str, default=None,
                        help='Batch mode: JSON file with list of configs')
    parser.add_argument('--resolution', type=str, default='1080x1920',
                        help='Resolution WxH (default: 1080x1920 for TikTok)')
    
    return parser.parse_args(argv)


def build_config(args) -> MarbleMusicConfig:
    """Build configuration from command line arguments."""
    config = MarbleMusicConfig()
    
    # Apply JSON overrides first
    if args.config_json and os.path.exists(args.config_json):
        with open(args.config_json, 'r') as f:
            overrides = json.load(f)
        # Apply overrides (simplified - nested dict to dataclass)
        _apply_json_overrides(config, overrides)
    
    # Apply CLI arguments
    config.theme = ThemePreset(args.theme)
    config.seed = args.seed
    config.output_path = args.output
    config.layout.layout_mode = args.layout
    config.render.fps = args.fps
    config.render.samples = args.samples
    config.render.engine = args.engine
    
    # Resolution
    if args.resolution:
        parts = args.resolution.split('x')
        config.render.resolution_x = int(parts[0])
        config.render.resolution_y = int(parts[1])
    
    # Preview mode overrides
    if args.preview:
        config.render.engine = 'BLENDER_EEVEE'
        config.render.eevee_samples = 32
        config.render.use_motion_blur = False
        config.effects.enable_particles = False
        config.effects.particle_count = 5
        config.effects.enable_ambient_particles = False
        config.render.resolution_x = 540
        config.render.resolution_y = 960
        config.preview_mode = True
    
    return config


def _apply_json_overrides(config, overrides: dict):
    """Apply JSON config overrides to config dataclass."""
    for key, value in overrides.items():
        if hasattr(config, key):
            attr = getattr(config, key)
            if isinstance(value, dict) and hasattr(attr, '__dataclass_fields__'):
                _apply_json_overrides(attr, value)
            else:
                setattr(config, key, value)


def run_pipeline(args):
    """Execute the complete pipeline."""
    
    print("=" * 60)
    print("  MARBLE MUSIC VIDEO GENERATOR")
    print("=" * 60)
    
    start_time = time.time()
    
    # --- Step 0: Build config ---
    config = build_config(args)
    print(f"\n[Config] Theme: {config.theme.value}")
    print(f"[Config] Layout: {config.layout.layout_mode}")
    print(f"[Config] Engine: {config.render.engine}")
    print(f"[Config] Seed: {config.seed}")
    
    # --- Step 1: Get MIDI data ---
    from midi_parser import parse_midi, generate_test_midi
    
    if args.test:
        print("\n[Step 1] Generating test MIDI...")
        midi_path = os.path.join(os.environ.get('TEMP', 'C:\\tmp'), 'test_marble_music.mid')
        generate_test_midi(midi_path, bpm=120, num_notes=32)
    elif args.midi:
        midi_path = args.midi
        if not os.path.exists(midi_path):
            print(f"ERROR: MIDI file not found: {midi_path}")
            sys.exit(1)
    else:
        print("ERROR: Must provide --midi or --test flag")
        sys.exit(1)
    
    print(f"\n[Step 1] Parsing MIDI: {midi_path}")
    midi_data = parse_midi(midi_path, config.midi)
    
    # --- Step 2: Generate level ---
    print(f"\n[Step 2] Generating level...")
    from level_generator import generate_level
    level_data = generate_level(midi_data, config)
    
    # --- Step 3: Build Blender scene ---
    print(f"\n[Step 3] Building Blender scene...")
    from scene_builder import build_scene
    ball_obj, camera_obj = build_scene(level_data, config)
    
    # --- Step 4: Save .blend file (optional) ---
    if args.save_blend:
        import bpy
        blend_path = args.save_blend
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"\n[Step 4] Saved .blend file: {blend_path}")
    
    # --- Step 5: Render ---
    if not args.no_render:
        print(f"\n[Step 5] Rendering video...")
        import bpy
        
        render_start = time.time()
        
        # Render animation (outputs PNG frames)
        bpy.ops.render.render(animation=True)

        render_time = time.time() - render_start
        print(f"  Render completed in {render_time:.1f}s")

        # Assemble frames into MP4 with FFmpeg
        frames_dir = config.output_path.replace('.mp4', '_frames')
        fps = config.render.fps
        print(f"\n[Step 5b] Assembling video with FFmpeg...")
        import subprocess
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', os.path.join(frames_dir, '%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            config.output_path
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr}")
        else:
            print(f"  Video assembled: {config.output_path}")
        
        # --- Step 6: Merge audio ---
        if args.audio and os.path.exists(args.audio):
            print(f"\n[Step 6] Merging audio...")
            from audio_sync import merge_audio_video
            
            # Get bounce times for SFX
            bounce_times = None
            if args.bounce_sfx:
                bounce_times = [
                    kf.position[0]  # time in seconds
                    for kf in level_data.ball_keyframes 
                    if kf.is_contact
                ]
            
            final_output = config.output_path.replace('.mp4', '_final.mp4')
            merge_audio_video(
                video_path=config.output_path,
                audio_path=args.audio,
                output_path=final_output,
                lead_in_time=config.midi.lead_in_time,
                add_bounce_sfx=bool(args.bounce_sfx),
                bounce_times=bounce_times,
                bounce_sfx_path=args.bounce_sfx,
            )
            print(f"  Final output: {final_output}")
        else:
            print(f"\n[Step 6] No audio file provided, skipping audio merge.")
            print(f"  Video output: {config.output_path}")
    else:
        print(f"\n[Step 5] Rendering skipped (--no-render flag)")
    
    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE in {total_time:.1f}s")
    print(f"{'=' * 60}")


def run_batch(batch_config_path: str):
    """Run multiple renders from a batch config file."""
    with open(batch_config_path, 'r') as f:
        batch = json.load(f)
    
    total = len(batch.get('renders', []))
    print(f"[Batch] Running {total} renders...")
    
    for i, render_config in enumerate(batch['renders']):
        print(f"\n[Batch {i+1}/{total}] Starting render...")
        
        # Create args namespace from batch config
        args = argparse.Namespace(**{
            'midi': render_config.get('midi'),
            'audio': render_config.get('audio'),
            'output': render_config.get('output', os.path.join(os.environ.get('TEMP', 'C:\\tmp'), f'marble_batch_{i}.mp4')),
            'theme': render_config.get('theme', 'teal'),
            'seed': render_config.get('seed', 42 + i),
            'layout': render_config.get('layout', 'cascade'),
            'fps': render_config.get('fps', 60),
            'samples': render_config.get('samples', 128),
            'engine': render_config.get('engine', 'CYCLES'),
            'preview': render_config.get('preview', False),
            'test': render_config.get('test', False),
            'no_render': False,
            'save_blend': render_config.get('save_blend'),
            'config_json': render_config.get('config_json'),
            'ball_type': render_config.get('ball_type'),
            'bounce_sfx': render_config.get('bounce_sfx'),
            'batch': None,
            'resolution': render_config.get('resolution', '1080x1920'),
        })
        
        try:
            run_pipeline(args)
        except Exception as e:
            print(f"[Batch {i+1}] ERROR: {e}")
            continue


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    args = parse_args()
    
    if args.batch:
        run_batch(args.batch)
    else:
        run_pipeline(args)
