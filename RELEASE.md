# Release Guide

## Create a release

1. Ensure `VERSION` and `CHANGELOG.md` are updated.
2. Commit your changes.
3. Create and push a Git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

4. GitHub Actions workflow `.github/workflows/release.yml` will:
   - build Windows and Linux binaries,
   - upload artifacts,
   - publish a GitHub Release with zipped binaries.

## Release assets

- `WhisperNetwork-windows.zip` (contains `WhisperNetwork.exe`)
- `WhisperNetwork-linux.zip` (contains `WhisperNetwork`)
