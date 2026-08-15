import os
import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent / "app"
_INIT = _PACKAGE_DIR / "__init__.py"

# Load the app/ package even though this file is also named app.py.
if __name__ == "__main__" or "app" not in sys.modules:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "app",
        _INIT,
        submodule_search_locations=[str(_PACKAGE_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = module
    spec.loader.exec_module(module)
    app = module.app
else:
    from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
