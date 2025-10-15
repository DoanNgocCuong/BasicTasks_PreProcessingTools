# filterer package

"""
Filterer Package - Content filtering and validation

This package handles local content filtering and file organization
for children's voice data.
"""

# Lazy import to avoid loading heavy dependencies at package import time
def __getattr__(name):
    if name == "run_filtering_phase":
        from .filtering_phases import run_filtering_phase
        return run_filtering_phase
    elif name == "run_local_filtering":
        from .filtering_phases import run_local_filtering
        return run_local_filtering
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")