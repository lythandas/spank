# Laptop Shock Detector

`shock_detector.py` reads the laptop's accelerometer and plays a random sound clip each time it detects a shock. The laptop yelps when you hit it.

## How it works

The script reads acceleration on the X, Y and Z axes from the Linux IIO subsystem (`/sys/bus/iio/devices`), computes a baseline over 10 calibration samples, and flags a shock whenever the deviation from that baseline exceeds a threshold. A cooldown prevents one physical shock from firing several detections.

- **Threshold:** 3 m/s² of deviation from baseline
- **Cooldown:** 1 second between detections
- **Sampling:** ~20 readings per second

On detection, `SoundPlayer` picks a random `.mp3`/`.wav`/`.ogg` file from the sound pack and plays it with the first available player (`paplay`, `aplay`, `ffplay`, `mpg123`, `play`).

## Sound packs

Two packs ship with the repository, in `sounds/`:

| Pack | Contents | Role |
|------|----------|------|
| `sounds/hentai` | 29 clips | Default pack |
| `sounds/real` | 60 clips | Alternative pack |

To switch packs, change the `sounds_dir` default in `SoundPlayer.__init__` (`shock_detector.py`), or drop your own files into a pack directory — any audio file there gets picked up automatically. Any directory named in `SoundPlayer` works the same way.

## Requirements

- Linux with an IIO-exposed accelerometer (check with `ls /sys/bus/iio/devices/`)
- Python 3 — standard library only, no `pip install` needed
- An audio player from the list above (`mpg123` or `ffmpeg` cover all file formats)

## Usage

```bash
python3 shock_detector.py
```

Calibration runs first — leave the laptop still for a second. Then the loop prints one line per shock:

```
[10:42:17] Shock detected! Magnitude: 5.3
🔔 SHOCK DETECTED! Playing: moan7.mp3
```

Stop with `Ctrl+C`.

## Notes

- If the sensor refuses to change its sampling frequency, the script prints the exact `sudo` command to set it manually — the detector still works with the sensor's default rate.
- `alert.wav` at the repo root serves as fallback when a pack directory is missing; the detector falls back to console output when no audio player exists.
