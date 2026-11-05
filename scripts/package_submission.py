"""Package source and submission evidence, excluding local secrets and runtime data."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "SmartRepair_Submission.zip"
FILES = [
    "app.py", "config.py", "requirements.txt", "requirements-lock.txt", "README.md",
    ".env.example", ".gitignore", "start.cmd", "package.json", "package-lock.json",
    ".python-version", "render.yaml", "render_start.py",
]
DIRECTORIES = ["smart_repair", "migrations", "tests", "scripts", "docs"]


def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, f"SmartRepair/{name}")
        for directory in DIRECTORIES:
            for source in sorted((ROOT / directory).rglob("*")):
                if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
                    archive.write(source, "SmartRepair/" + source.relative_to(ROOT).as_posix())
    with ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        print(f"Verified submission archive: {len(archive.namelist())} files")
    print(OUTPUT)


if __name__ == "__main__":
    main()
