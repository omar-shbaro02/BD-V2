# Stage 15 Held-Out Oracle

This directory is test-harness-only. Runtime application code and agent inputs
must never import, mount, read, or derive prompts from these files.

This directory contains the held-out expected outcomes for the authorized
project-authored dataset `stage15-synthetic-v1.0.0`. The oracle manifest binds
these files to the exact runtime-manifest digest and records a digest for every
expected-output file.

The test harness must serialize actual runtime results before reading this tree.
The original unavailable frozen dataset was not recovered; these expectations
govern only the newly authorized synthetic baseline.

