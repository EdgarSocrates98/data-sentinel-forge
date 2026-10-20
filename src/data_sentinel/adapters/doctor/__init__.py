"""Forge Doctor bundle adapter (optional, offline).

Accepts the three real Doctor output shapes identified in the
ds-0030 audit:

- ``export --format handoff``  → ``contract == "handoff-bundle"``,
  ``contract_version`` int 1, ``results`` + ``graph`` + ``capabilities``
- ``forge-contracts/1`` handoff → ``contract_version`` string,
  normalized ``findings``/``entities``/``relationships``
- ``scan --format json``       → ``schema_version == "3.0"``, ``results``

The adapter NEVER executes bundle content, never performs network I/O,
and never requires Forge Doctor to be installed.
"""

from data_sentinel.adapters.doctor.adapter import (
    DoctorBundleError,
    ImportedDiagnostics,
    detect_bundle_format,
    import_doctor_bundle,
    load_doctor_file,
)

__all__ = [
    "DoctorBundleError",
    "ImportedDiagnostics",
    "detect_bundle_format",
    "import_doctor_bundle",
    "load_doctor_file",
]
