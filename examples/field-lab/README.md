# Synthetic Field Lab fixture

These rows are **invented test data**, not measured on a Nintendo 3DS. They exist only to exercise the parser and keep CLI output stable across revisions.

Run:

    python -m pocketport profile-frames examples/field-lab/synthetic-frames.csv --target-fps 30

Expected: five samples, two frames over the 30 FPS budget, one stall over 50 ms, worst frame 82 ms and minimum recorded linear availability 14000 KiB. None of these numbers is evidence of any game running on hardware.

For actual ports, capture instrumentation from the real program, with the exact artifact hash and scenario evidence in a private manifest as described in docs/FIELD_TEST_PROTOCOL.md.
