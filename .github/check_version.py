import os
import tomllib

tag = os.environ.get("GITHUB_REF_NAME")
if not tag:
    raise SystemExit("GITHUB_REF_NAME not set")

tag = tag.removeprefix("v")

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)

version = data["project"]["version"]
if version != tag:
    raise SystemExit(f"Version mismatch: tag={tag}, pyproject={version}")
print("Version OK:", version)
