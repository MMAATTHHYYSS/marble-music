"""
Marble Music Generator - MIDI Parser
======================================
Parses MIDI files and extracts note events with timing, pitch, and velocity.
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class NoteEvent:
    """Represents a single note event extracted from MIDI."""
    time: float          # Absolute time in seconds
    pitch: int           # MIDI pitch (0-127)
    velocity: int        # MIDI velocity (0-127)
    duration: float      # Note duration in seconds
    channel: int         # MIDI channel
    
    # Normalized values (filled during post-processing)
    norm_pitch: float = 0.0     # 0.0 to 1.0
    norm_velocity: float = 0.0  # 0.0 to 1.0
    norm_time: float = 0.0      # Normalized time position
    
    # Index in sequence
    index: int = 0


@dataclass 
class MIDIData:
    """Parsed MIDI data ready for level generation."""
    notes: List[NoteEvent]
    bpm: float
    duration: float          # Total duration in seconds
    time_signature: Tuple[int, int]  # (numerator, denominator)
    ticks_per_beat: int
    min_pitch: int
    max_pitch: int
    min_velocity: int
    max_velocity: int
    note_count: int
    
    def get_beat_duration(self) -> float:
        """Duration of one beat in seconds."""
        return 60.0 / self.bpm
    
    def get_bar_duration(self) -> float:
        """Duration of one bar/measure in seconds."""
        return self.get_beat_duration() * self.time_signature[0]


def parse_midi(midi_path: str, config=None) -> MIDIData:
    """
    Parse a MIDI file and extract note events.
    
    Args:
        midi_path: Path to the MIDI file
        config: Optional MIDIConfig for filtering parameters
        
    Returns:
        MIDIData with extracted and normalized note events
    """
    try:
        import mido
    except ImportError:
        print("ERROR: 'mido' library required. Install with: pip install mido")
        sys.exit(1)
    
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")
    
    mid = mido.MidiFile(midi_path)
    
    # Extract tempo and time signature
    bpm = 120.0  # Default
    time_sig = (4, 4)  # Default
    
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                bpm = mido.tempo2bpm(msg.tempo)
            elif msg.type == 'time_signature':
                time_sig = (msg.numerator, msg.denominator)
    
    # Extract notes
    notes = []
    
    # Determine which track(s) to use
    if config and config.track_index is not None:
        tracks_to_parse = [mid.tracks[config.track_index]]
    else:
        tracks_to_parse = mid.tracks
    
    for track_idx, track in enumerate(tracks_to_parse):
        abs_time = 0  # In ticks
        active_notes = {}  # pitch -> (start_time, velocity, channel)
        
        for msg in track:
            abs_time += msg.time
            abs_time_sec = mido.tick2second(abs_time, mid.ticks_per_beat, mido.bpm2tempo(bpm))
            
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = (abs_time_sec, msg.velocity, msg.channel)
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    start_time, velocity, channel = active_notes.pop(msg.note)
                    duration = abs_time_sec - start_time
                    
                    notes.append(NoteEvent(
                        time=start_time,
                        pitch=msg.note,
                        velocity=velocity,
                        duration=max(duration, 0.01),
                        channel=channel,
                    ))
    
    # Sort by time
    notes.sort(key=lambda n: (n.time, n.pitch))
    
    if not notes:
        raise ValueError("No notes found in MIDI file!")
    
    # Filter by config ranges
    if config:
        notes = [n for n in notes 
                 if config.min_midi_note <= n.pitch <= config.max_midi_note
                 and n.velocity >= config.min_velocity]
    
    # Remove near-simultaneous duplicates (chords -> keep highest)
    filtered_notes = []
    time_threshold = 0.02  # 20ms
    i = 0
    while i < len(notes):
        chord = [notes[i]]
        j = i + 1
        while j < len(notes) and abs(notes[j].time - notes[i].time) < time_threshold:
            chord.append(notes[j])
            j += 1
        # Keep the note with highest pitch from chord (most audible)
        best = max(chord, key=lambda n: n.pitch)
        filtered_notes.append(best)
        i = j
    
    notes = filtered_notes
    
    # Compute ranges
    min_pitch = min(n.pitch for n in notes)
    max_pitch = max(n.pitch for n in notes)
    min_vel = min(n.velocity for n in notes)
    max_vel = max(n.velocity for n in notes)
    total_duration = max(n.time + n.duration for n in notes)
    
    pitch_range = max(max_pitch - min_pitch, 1)
    vel_range = max(max_vel - min_vel, 1)
    
    # Normalize and index
    for i, note in enumerate(notes):
        note.index = i
        note.norm_pitch = (note.pitch - min_pitch) / pitch_range
        note.norm_velocity = (note.velocity - min_vel) / vel_range
        note.norm_time = note.time / total_duration if total_duration > 0 else 0
    
    # Quantize if requested
    if config and config.quantize:
        beat_dur = 60.0 / bpm
        q_res = config.quantize_resolution * beat_dur
        for note in notes:
            note.time = round(note.time / q_res) * q_res
    
    print(f"[MIDI Parser] Parsed {len(notes)} notes")
    print(f"  BPM: {bpm:.1f}")
    print(f"  Duration: {total_duration:.2f}s")
    print(f"  Pitch range: {min_pitch}-{max_pitch}")
    print(f"  Velocity range: {min_vel}-{max_vel}")
    print(f"  Time signature: {time_sig[0]}/{time_sig[1]}")
    
    return MIDIData(
        notes=notes,
        bpm=bpm,
        duration=total_duration,
        time_signature=time_sig,
        ticks_per_beat=mid.ticks_per_beat,
        min_pitch=min_pitch,
        max_pitch=max_pitch,
        min_velocity=min_vel,
        max_velocity=max_vel,
        note_count=len(notes),
    )


def generate_test_midi(output_path: str, bpm: float = 120, num_notes: int = 32):
    """
    Generate a simple test MIDI file for development.
    Creates a descending scale pattern.
    """
    try:
        import mido
    except ImportError:
        print("ERROR: 'mido' library required.")
        sys.exit(1)
    
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Set tempo
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    
    ticks_per_beat = mid.ticks_per_beat
    
    # Generate a musical pattern
    import random
    random.seed(42)
    
    # Pentatonic scale notes
    scale = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]
    
    current_tick = 0
    for i in range(num_notes):
        pitch = random.choice(scale)
        velocity = random.randint(60, 120)
        
        # Varying note durations (in ticks)
        duration_options = [
            ticks_per_beat // 2,   # 8th note
            ticks_per_beat,        # Quarter note
            ticks_per_beat // 4,   # 16th note
        ]
        duration = random.choice(duration_options)
        
        # Gap between notes
        gap = random.choice([0, ticks_per_beat // 4, ticks_per_beat // 2])
        
        if i == 0:
            track.append(mido.Message('note_on', note=pitch, velocity=velocity, time=ticks_per_beat))
        else:
            track.append(mido.Message('note_on', note=pitch, velocity=velocity, time=gap))
        
        track.append(mido.Message('note_off', note=pitch, velocity=0, time=duration))
    
    mid.save(output_path)
    print(f"[MIDI Parser] Test MIDI saved to: {output_path}")
    return output_path
