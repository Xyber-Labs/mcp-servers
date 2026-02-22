from pathlib import Path

from dotenv import load_dotenv

# Load test environment variables BEFORE other imports
_tests_dir = Path(__file__).parent
_env_file = _tests_dir / ".env.tests"
if _env_file.exists():
    load_dotenv(_env_file, override=True)
