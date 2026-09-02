import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("auth_module", Path(__file__).with_name("auth.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert callable(getattr(module, "signup", None)), "signup endpoint is missing"
assert callable(getattr(module, "login", None)), "login endpoint is missing"
