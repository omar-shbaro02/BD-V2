"""Shared test configuration."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("EXTERNAL_EXECUTION_ALLOWED", "false")
os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")
os.environ.setdefault("TRACE_INCLUDE_SENSITIVE_DATA", "0")
