# Contributing

Welcome! Please make focused changes on a separate branch. Include a failing regression test before a fix when practical; run `python -m unittest discover -s tests -v`, and clearly separate host validation from 3DS toolchain, emulator or hardware evidence.

## Legal boundary

Only submit your own code or appropriately licensed dependencies with attribution. Do **not** commit commercial ROMs, proprietary firmware, secrets, Nintendo keys, commercially owned textures/models/sounds, personal save data or unlicensed decompiler output. Respect source-project licenses (including GPL obligations where applicable). Do not bundle REA, Co-op Anything, N64Recomp, or other third-party code under this repo's MIT notice without checking their licenses.

## Engineering standard

Preserve functionality and backwards compatibility. Prefer existing credible 3DS ports and available source. New translation backends must document exact supported ISA/ABI/relocation set; add fixtures, positive and negative tests, and a reference oracle. Fail closed on unknown features. Every successful build claim needs a log, return code, environment, and SHA-256. Emulator screenshots and hardware results must come from real runs, not generated images.

## Development

```bash
python -m pip install -e .
python -m pip install -r requirements-optional.txt
python -m unittest discover -s tests -v
python -m pocketport doctor
```
