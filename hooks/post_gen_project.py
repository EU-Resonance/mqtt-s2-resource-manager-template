import shutil
import subprocess
import sys
from pathlib import Path

workspace_root = Path.cwd().parent

# =============== Move pyproject.toml =============

FILES_TO_MOVE_UP = ["pyproject.toml"]
OVERWRITE = False


def move_up(project_dir: Path, filename: str) -> None:
    src = project_dir / filename
    dst = project_dir.parent / filename

    if not src.exists():
        print(f"! Skipping {filename}: not found in generated project ({src})")
        return

    if dst.exists() and not OVERWRITE:
        print(f"! Not copying {filename}: already exists at parent level ({dst})")
        return

    shutil.move(src, dst)
    print(f"✓ Moved {filename} -> {dst}")


project_dir = Path.cwd()  # cookiecutter runs hooks in the generated project directory
print(f"Post-gen: project_dir = {project_dir}")

for fname in FILES_TO_MOVE_UP:
    move_up(project_dir, fname)

print(f"""
    A new RM folder was generated as module in:
    {project_dir}

    The project is integrated into the parent workspace at:
    {workspace_root}

    Next steps:
    cd ..
    uv lock
    uv run ruff format
    uv run pytest
    """)

# ============== Dependencies ===================
print("Running uv lock...")
try:
    subprocess.run(["uv", "lock"], cwd=workspace_root, check=True)
except FileNotFoundError:
    print("! uv not found; skipping 'uv lock'")
except subprocess.CalledProcessError:
    print("! 'uv lock' failed; run it manually inside the generated project")

# ============= Cleaning the code =============
print("Running Ruff code formatter...")
try:
    subprocess.run(
        ["uvx", "ruff", "format", f"{project_dir}"],
        cwd=workspace_root,
        check=False,
    )
except subprocess.CalledProcessError:
    print("⚠️ Ruff formatting failed (is Ruff installed?)")



# ============= Creating new branch =============

project_root = Path.cwd()


def in_git_repo() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


if "{{ cookiecutter.create_new_branch }}" == "yes":
    prefix = "{{ cookiecutter.prefix }}"
    branch_name = f"device/{prefix}"

    if in_git_repo():
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            print(f"✓ Created and switched to git branch: {branch_name}")
        except subprocess.CalledProcessError:
            print(
                f"! Git branch '{branch_name}' already exists or could not be created."
            )
    else:
        print("! Not inside a git repository – skipping branch creation.")

    # ============= Cleanup template artifacts =============

    hooks_dir = project_root / "hooks"
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)

    cookiecutter_file = project_root / "cookiecutter.json"
    if cookiecutter_file.exists():
        cookiecutter_file.unlink()

    # ============= Cleaning the code =============

    try:
        subprocess.run(
            ["uvx", "ruff", "format", "."],
            cwd=project_root,
            check=False,
        )
    except subprocess.CalledProcessError:
        print("⚠️ Ruff formatting failed (is Ruff installed?)")

    try:
        subprocess.run(
            ["uvx", "ruff", "check", ".", "--fix"],
            cwd=project_root,
            check=False,
        )
    except subprocess.CalledProcessError:
        print("⚠️ Ruff lint-fix failed")

# ============= Runnign basic tests =============

if "{{ cookiecutter.run_tests }}" == "yes":
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=workspace_root, check=False
    )
    if r.returncode != 0:
        print("Tests failed. Generation completed, but please fix before using.")


print("Post-gen: done.")