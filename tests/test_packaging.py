import tomllib
from pathlib import Path


def test_pyproject_declares_vercel_runtime_dependencies():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"].get("dependencies", [])
    dependency_names = {dependency.split("==", 1)[0].lower() for dependency in dependencies}

    assert {"dash", "pandas", "plotly", "python-dotenv"}.issubset(dependency_names)
