import shutil
import subprocess
import sys
from pathlib import Path

import uuid

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
# print(f"Post-gen: project_dir = {project_dir}")

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
print(50 * "-" + "\n")

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

    template_dir = project_root / "{{cookiecutter.package_name}}"
    if template_dir.exists():
        shutil.rmtree(template_dir)

    cookiecutter_file = project_root / "cookiecutter.json"
    if cookiecutter_file.exists():
        cookiecutter_file.unlink()    
        
    hooks_dir = project_root / "hooks"
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)



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
    
    subprocess.run(["uv", "sync", "--group", "dev"], cwd=workspace_root, check=True) 
    
    r = subprocess.run(["uv", "run", "pytest", "-q"], cwd=workspace_root, check=False
    )
    if r.returncode != 0:
        print("Tests failed. Generation completed, but please fix before using.")

    print("✓ Basic tests executed.")
    print(50 * "-" + "\n")

    
    """
    Preparing docker compose test setup 
    #for testing connection to a CEM (e.g. the visualization container)
    """
    
    print("Setting up test environment for CEM connection tests...")
    project_dir_res = Path.cwd() / "resources"
    project_dir = Path.cwd().parent
    
    # environment.env
    env_file = project_dir / "environment.env"
    if env_file.exists():
        print("environment.env exists, skipping")
    else:
        env_file.write_text(
            f"""TZ=Europe/Berlin
MQTT_SERVER=host.docker.internal
MQTT_PORT=1883
CEM_ID={uuid.uuid4()}
"""
    )   

    # mosquitto.conf
    conf_file = project_dir / "mosquitto.conf"
    if conf_file.exists():
        print("mosquitto.conf exists, skipping")
    else:
        conf_file.write_text("""listener 1883
allow_anonymous true
""")

    # resources/config.json
    src = project_dir_res / "config.example.json"
    dst = project_dir_res / "config.json"

    if not src.exists():
        print("config.example.json not found, skipping")

    if dst.exists():
        print("config.json already exists, skipping")

    src.rename(dst)
    
    print("✓ Test environment setup ready.")
    print("You can now run 'docker compose -f {{cookiecutter.package_name}}/compose.yaml up -d' to test the interface.")
    print("Visit http://localhost:5001 to monitor the data received by a CEM.\n")



print("Post-gen: done.")
print(50 * "-" + "\n")