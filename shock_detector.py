#!/usr/bin/env python3
"""
Laptop Shock Detector
Monitors the accelerometer and plays a sound when a shock is detected.
"""

import os
import sys
import time
import math
import random
import subprocess
from pathlib import Path
from typing import Optional, Tuple

class AccelerometerReader:
    """Reads accelerometer data from IIO device."""
    
    def __init__(self):
        self.device_path = self._find_accelerometer()
        if not self.device_path:
            raise RuntimeError("No accelerometer device found")
        
        self.x_path = self.device_path / "in_accel_x_raw"
        self.y_path = self.device_path / "in_accel_y_raw"
        self.z_path = self.device_path / "in_accel_z_raw"
        self.scale_path = self.device_path / "in_accel_scale"
        self.sampling_freq_path = self.device_path / "in_accel_sampling_frequency"
        
        # Set sampling frequency to ensure sensor is active
        self._set_sampling_frequency(100.0)
        
        # Read scale factor
        try:
            self.scale = float(self.scale_path.read_text().strip())
        except:
            self.scale = 1.0
        
        print(f"✓ Accelerometer found: {self.device_path}")
        print(f"  Scale factor: {self.scale}")
    
    def _set_sampling_frequency(self, freq: float):
        """Set the accelerometer sampling frequency."""
        try:
            if self.sampling_freq_path.exists():
                # Try to set frequency (may require sudo)
                try:
                    self.sampling_freq_path.write_text(str(freq))
                    print(f"  Sampling frequency set to: {freq} Hz")
                except PermissionError:
                    # If we can't set it, try with sudo hint
                    print(f"  ⚠ Cannot set sampling frequency (need sudo)")
                    print(f"    Run: sudo sh -c 'echo {freq} > {self.sampling_freq_path}'")
        except Exception as e:
            print(f"  ⚠ Could not configure sampling frequency: {e}")
    
    def _find_accelerometer(self) -> Optional[Path]:
        """Find the IIO accelerometer device."""
        # Search for IIO devices
        iio_base = Path("/sys/bus/iio/devices")
        if iio_base.exists():
            for device in iio_base.iterdir():
                if (device / "in_accel_x_raw").exists():
                    return device
        
        # Fallback: search in /sys/devices
        for root, dirs, files in os.walk("/sys/devices"):
            if "in_accel_x_raw" in files:
                return Path(root)
        
        return None
    
    def read(self) -> Tuple[float, float, float]:
        """Read current accelerometer values (x, y, z)."""
        try:
            x = int(self.x_path.read_text().strip()) * self.scale
            y = int(self.y_path.read_text().strip()) * self.scale
            z = int(self.z_path.read_text().strip()) * self.scale
            return (x, y, z)
        except Exception as e:
            print(f"Error reading accelerometer: {e}", file=sys.stderr)
            return (0.0, 0.0, 0.0)


class ShockDetector:
    """Detects shocks based on accelerometer data."""
    
    def __init__(self, threshold: float = 3.0, cooldown: float = 1.0):
        """
        Initialize shock detector.
        
        Args:
            threshold: Acceleration magnitude threshold for shock detection (in m/s²)
            cooldown: Minimum time (seconds) between shock detections
        """
        self.threshold = threshold
        self.cooldown = cooldown
        self.last_shock_time = 0
        self.baseline = None
        self.calibration_samples = []
    
    def calibrate(self, accel_reader: AccelerometerReader, samples: int = 10):
        """Calibrate by taking baseline measurements."""
        print(f"Calibrating... (taking {samples} samples)")
        for i in range(samples):
            x, y, z = accel_reader.read()
            self.calibration_samples.append((x, y, z))
            time.sleep(0.1)
        
        # Calculate average baseline
        avg_x = sum(s[0] for s in self.calibration_samples) / samples
        avg_y = sum(s[1] for s in self.calibration_samples) / samples
        avg_z = sum(s[2] for s in self.calibration_samples) / samples
        self.baseline = (avg_x, avg_y, avg_z)
        
        print(f"✓ Baseline: X={avg_x:.1f}, Y={avg_y:.1f}, Z={avg_z:.1f}")
    
    def detect_shock(self, x: float, y: float, z: float) -> bool:
        """
        Detect if current reading indicates a shock.
        
        Returns:
            True if shock detected, False otherwise
        """
        if self.baseline is None:
            return False
        
        # Calculate deviation from baseline
        dx = x - self.baseline[0]
        dy = y - self.baseline[1]
        dz = z - self.baseline[2]
        
        # Calculate magnitude of acceleration change
        magnitude = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        # Check if magnitude exceeds threshold and cooldown has passed
        current_time = time.time()
        if magnitude > self.threshold and (current_time - self.last_shock_time) > self.cooldown:
            self.last_shock_time = current_time
            return True
        
        return False


class SoundPlayer:
    """Plays alert sounds."""
    
    def __init__(self, sound_file: str = None, sounds_dir: str = "sounds"):
        """
        Initialize sound player.
        
        Args:
            sound_file: Path to a specific sound file (fallback if sounds_dir doesn't exist)
            sounds_dir: Directory containing sound files to play randomly
        """
        self.sound_file = sound_file
        self.sounds_dir = Path(sounds_dir)
        self.player = self._find_player()
        self.sound_files = []
        
        # Check if sounds directory exists and has audio files
        if self.sounds_dir.exists() and self.sounds_dir.is_dir():
            # Common audio file extensions
            audio_extensions = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.opus'}
            self.sound_files = [
                f for f in self.sounds_dir.iterdir()
                if f.is_file() and f.suffix.lower() in audio_extensions
            ]
            
            if self.sound_files:
                print(f"✓ Found {len(self.sound_files)} sound files in '{sounds_dir}' directory")
            else:
                print(f"⚠ Warning: No audio files found in '{sounds_dir}' directory")
        else:
            print(f"⚠ Warning: '{sounds_dir}' directory not found, using fallback sound")
        
        if not self.player:
            print("⚠ Warning: No audio player found. Shocks will be printed only.")
        else:
            print(f"✓ Audio player: {self.player}")
    
    def _find_player(self) -> Optional[str]:
        """Find available audio player."""
        players = ["paplay", "aplay", "ffplay", "mpg123", "play"]
        for player in players:
            if subprocess.run(["which", player], capture_output=True).returncode == 0:
                return player
        return None
    
    def _get_random_sound(self) -> Optional[Path]:
        """Get a random sound file from the sounds directory."""
        if self.sound_files:
            return random.choice(self.sound_files)
        elif self.sound_file and os.path.exists(self.sound_file):
            return Path(self.sound_file)
        return None
    
    def play(self):
        """Play a random alert sound."""
        if not self.player:
            print("🔔 SHOCK DETECTED! (no audio player available)")
            return
        
        sound_to_play = self._get_random_sound()
        if not sound_to_play:
            print("🔔 SHOCK DETECTED! (no sound files available)")
            return
        
        try:
            if self.player == "paplay":
                subprocess.Popen([self.player, str(sound_to_play)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            elif self.player == "aplay":
                subprocess.Popen([self.player, str(sound_to_play)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            elif self.player == "ffplay":
                subprocess.Popen([self.player, "-nodisp", "-autoexit", str(sound_to_play)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen([self.player, str(sound_to_play)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            print(f"🔔 SHOCK DETECTED! Playing: {sound_to_play.name}")
        except Exception as e:
            print(f"🔔 SHOCK DETECTED! (Error playing sound: {e})")


def main():
    """Main program loop."""
    print("=" * 60)
    print("  LAPTOP SHOCK DETECTOR")
    print("=" * 60)
    
    # Get script directory
    script_dir = Path(__file__).parent
    sound_file = script_dir / "alert.wav"
    
    try:
        # Initialize components
        accel = AccelerometerReader()
        detector = ShockDetector(threshold=3.0, cooldown=1.0)
        player = SoundPlayer(str(sound_file))
        
        # Calibrate
        detector.calibrate(accel)
        
        print("\n✓ Monitoring started. Press Ctrl+C to stop.")
        print(f"  Threshold: {detector.threshold}")
        print(f"  Cooldown: {detector.cooldown}s")
        print("-" * 60)
        
        # Main monitoring loop
        while True:
            x, y, z = accel.read()
            
            if detector.detect_shock(x, y, z):
                magnitude = math.sqrt(
                    (x - detector.baseline[0])**2 + 
                    (y - detector.baseline[1])**2 + 
                    (z - detector.baseline[2])**2
                )
                print(f"[{time.strftime('%H:%M:%S')}] Shock detected! Magnitude: {magnitude:.1f}")
                player.play()
            
            time.sleep(0.05)  # 20 Hz sampling rate
    
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
