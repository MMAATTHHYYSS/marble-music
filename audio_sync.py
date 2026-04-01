"""
Marble Music Generator - Audio Synchronizer
=============================================
Handles audio synchronization and post-processing.
Merges the original audio with the rendered video.
"""

import os
import subprocess
import sys


def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    lead_in_time: float = 1.0,
    audio_offset: float = 0.0,
    add_bounce_sfx: bool = False,
    bounce_times: list = None,
    bounce_sfx_path: str = None,
):
    """
    Merge audio track with rendered video using FFmpeg.
    
    Args:
        video_path: Path to rendered video (from Blender)
        audio_path: Path to audio file (MP3, WAV, etc.)
        output_path: Path for final output video
        lead_in_time: Lead-in time added before first note (seconds)
        audio_offset: Additional audio offset in seconds
        add_bounce_sfx: Whether to add bounce sound effects
        bounce_times: List of timestamps where bounces occur
        bounce_sfx_path: Path to bounce sound effect file
    """
    # Check FFmpeg availability
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("ERROR: FFmpeg not found. Please install FFmpeg.")
        sys.exit(1)
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")
    
    # Calculate total audio delay
    total_delay = lead_in_time + audio_offset
    
    if add_bounce_sfx and bounce_times and bounce_sfx_path:
        # Complex merge with bounce SFX
        _merge_with_sfx(video_path, audio_path, output_path, 
                        total_delay, bounce_times, bounce_sfx_path)
    else:
        # Simple merge
        _simple_merge(video_path, audio_path, output_path, total_delay)
    
    print(f"[Audio Sync] Output saved to: {output_path}")


def _simple_merge(video_path, audio_path, output_path, delay):
    """Simple video + audio merge with offset."""
    
    # Build FFmpeg command
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
    ]
    
    if delay > 0:
        # Delay audio by adding silence at the beginning
        cmd.extend([
            '-filter_complex',
            f'[1:a]adelay={int(delay * 1000)}|{int(delay * 1000)}[delayed];'
            f'[delayed]apad[audio_out]',
            '-map', '0:v',
            '-map', '[audio_out]',
        ])
    else:
        cmd.extend([
            '-map', '0:v',
            '-map', '1:a',
        ])
    
    cmd.extend([
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_path,
    ])
    
    print(f"[Audio Sync] Running FFmpeg merge...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("FFmpeg merge failed")


def _merge_with_sfx(video_path, audio_path, output_path, 
                    delay, bounce_times, sfx_path):
    """Merge video with audio and bounce sound effects."""
    
    # Build complex filter for mixing bounce SFX at specific times
    filter_parts = []
    inputs = ['-i', video_path, '-i', audio_path, '-i', sfx_path]
    
    # Delay main audio
    filter_parts.append(
        f'[1:a]adelay={int(delay * 1000)}|{int(delay * 1000)}[music]'
    )
    
    # Create delayed copies of bounce SFX for each bounce
    bounce_labels = []
    for i, t in enumerate(bounce_times):
        ms = int(t * 1000)
        label = f'sfx{i}'
        filter_parts.append(
            f'[2:a]adelay={ms}|{ms},volume=0.3[{label}]'
        )
        bounce_labels.append(f'[{label}]')
    
    # Mix all audio together
    # Limit to first 50 bounces for complexity
    max_sfx = min(len(bounce_labels), 50)
    mix_inputs = f'[music]' + ''.join(bounce_labels[:max_sfx])
    num_inputs = 1 + max_sfx
    
    filter_parts.append(
        f'{mix_inputs}amix=inputs={num_inputs}:duration=first[audio_out]'
    )
    
    filter_complex = ';'.join(filter_parts)
    
    cmd = [
        'ffmpeg', '-y',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '0:v',
        '-map', '[audio_out]',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_path,
    ]
    
    print(f"[Audio Sync] Running FFmpeg merge with {max_sfx} bounce SFX...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("FFmpeg merge with SFX failed")


def convert_midi_to_audio(midi_path: str, output_path: str, soundfont: str = None):
    """
    Convert MIDI to audio using FluidSynth (optional utility).
    
    Args:
        midi_path: Path to MIDI file
        output_path: Output audio file path
        soundfont: Path to SoundFont (.sf2) file
    """
    try:
        if soundfont:
            cmd = ['fluidsynth', '-ni', soundfont, midi_path, '-F', output_path]
        else:
            cmd = ['timidity', midi_path, '-Ow', '-o', output_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Audio conversion error: {result.stderr}")
            raise RuntimeError("MIDI to audio conversion failed")
        
        print(f"[Audio] MIDI converted to audio: {output_path}")
    except FileNotFoundError:
        print("WARNING: Neither FluidSynth nor TiMidity found.")
        print("Please provide a pre-rendered audio file.")


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())
