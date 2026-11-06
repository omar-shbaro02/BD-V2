# Stage 15 Runtime Fixtures

This directory contains the project-authored, fully synthetic Stage 15 runtime
dataset `stage15-synthetic-v1.0.0`. It was generated at the user's explicit
request on 2026-10-19 from the documented C01–C10 and M01–M09 scenario
specification. It is a new governed baseline, not a recovered copy of the
unavailable original frozen dataset.

`manifest.json` records provenance, version, and a SHA-256 digest for every
runtime file. `base.json` contains the ten base cases, `mutations/` contains the
nine independent changes, and `captured_outputs.json` contains explicit test
doubles derived only from runtime observations.

Expected adjudications and answer-key material remain forbidden here. Runtime
code loads this tree through `vai_bd.conformity.load_runtime_bundle`; it has no
oracle path or oracle loader.

