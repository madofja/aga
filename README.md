# Whisper Network: Sentient Society

A complete emergent-world simulation game built with **Pygame** and ready to package as an executable.

## Features

- Procedural continent terrain with functional biomes.
- Autonomous weather system with moving storm cells and rainfall fields.
- Wetness and rainfall affecting mobility, survival, and migration.
- Evolutionary agents with traits, memory biases, communication, trade, and conflict.
- Proto-language mutation and social cohesion behavior.
- Live dashboard with population, resources, cohesion, and conflict graphs.
- Observer controls for speed, reset, and runtime help overlay.

## Run from source

```bash
python -m pip install -r requirements.txt
python main.py
```

## Build executable locally

### Windows (.exe)

```bat
build_exe.bat
```

Output:

- `dist\WhisperNetwork.exe`

### Linux/macOS binary

```bash
./build_exe.sh
```

Output:

- `dist/WhisperNetwork`

## Repository release flow

This repository now supports automated release publishing through GitHub Actions.

1. Update `VERSION` and `CHANGELOG.md`.
2. Commit changes.
3. Push a version tag such as `v1.0.0`.

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow in `.github/workflows/release.yml` builds and uploads:

- `WhisperNetwork-windows.zip` (includes `WhisperNetwork.exe`)
- `WhisperNetwork-linux.zip` (includes `WhisperNetwork`)

## Controls

- `Space`: Pause / Resume
- `Up`: Increase simulation speed
- `Down`: Decrease simulation speed
- `R`: Regenerate world
- `H`: Toggle observer help overlay
- `Esc`: Quit

## Notes

- The simulation intentionally favors emergent behavior over scripted goals.
- Each run evolves differently due to procedural generation and stochastic agent decisions.
