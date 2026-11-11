# Original asset optimization demo

`assets/star.png` and `assets/player.png` are original synthetic images, generated for this MIT-licensed example. The stage runs the *actual* `pocketport.assets` Pillow processor and writes intermediate PNGs plus a complete report. Run:

```bash
python -m pocketport optimize examples/asset-pipeline/manifest.json --out /tmp/pocketport-images --profile old-3ds
```

The image output is not a GPU texture until actual `tex3ds` conversion runs with `--encode-3ds`. Non-image files and corrupt inputs are reported explicitly. Dimensions, UV fractions, original/processed sizes and hashes are recorded in `asset-report.json`. The sample includes a 700x350 image, demonstrating proportional resize to 256x128 in the old-3ds profile, and a 60x48 image padded to a 64x64 power-of-two texture.
