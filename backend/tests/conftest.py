import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(
    prefix="voicebridge-test-", suffix=".db"
)
os.environ["GNANI_API_KEY_ID"] = ""

# Unit/regression tests must never call a configured external or local model.
os.environ["LLM_PROVIDER"] = "deterministic-demo"
os.environ["LLM_API_KEY"] = ""
