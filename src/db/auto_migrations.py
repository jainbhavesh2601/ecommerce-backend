import asyncio
import subprocess
import os
import platform
from datetime import datetime
from pathlib import Path

# adjust this to point to your model directories
MODEL_DIRS = [
    "src/category/models",
    "src/product/models",
    "src/cart/models",
    "src/auth/user/models",
    "src/orders/models",
]

STATE_FILE = Path("alembic/.migration_state")

async def run_cmd(*args):
    if platform.system() == "Windows":
        # Run synchronously on Windows
        process = subprocess.run(args, capture_output=True, text=True)
        return process.returncode, process.stdout, process.stderr
    else:
        # Async on Linux/macOS
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(), stderr.decode()

def get_latest_model_change_time() -> float:
    """Return the latest modification timestamp among all model files."""
    latest_time = 0.0
    for directory in MODEL_DIRS:
        path = Path(directory)
        if not path.exists():
            continue
        for file in path.rglob("*.py"):
            mtime = file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
    return latest_time


def get_last_migration_time() -> float:
    """Get timestamp from .migration_state file if exists."""
    if STATE_FILE.exists():
        try:
            return float(STATE_FILE.read_text().strip())
        except ValueError:
            pass
    return 0.0


def save_migration_time(timestamp: float):
    """Save latest migration timestamp."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(timestamp))


async def run_auto_migrations():
    """
    Automatically autogenerate and apply Alembic migrations only if model files changed.
    """
    print("\n🚀 Starting database auto-migration process...")

    latest_model_time = get_latest_model_change_time()
    last_migration_time = get_last_migration_time()

    print(f"🕓 Latest model change: {datetime.fromtimestamp(latest_model_time)}")
    print(f"🧾 Last migration time: {datetime.fromtimestamp(last_migration_time)}")

    should_autogenerate = latest_model_time > last_migration_time

    if should_autogenerate:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        message = f"auto_migration_{timestamp}"
        print("⚙  Detected model changes — generating new Alembic migration...")

        code, stdout, stderr = await run_cmd("alembic", "revision", "--autogenerate", "-m", message)
        if code == 0:
            print("✅ Migration file generated successfully.")
            print(stdout)
            save_migration_time(latest_model_time)
        elif "No changes in schema detected" in stderr:
            print("ℹ  No schema differences detected by Alembic.")
            save_migration_time(latest_model_time)
        else:
            print("❌ Error generating migration:")
            print(stderr)
            return
    else:
        print("ℹ  No model changes detected since last migration. Skipping autogenerate.")

    # Always apply the latest migrations
    print("\n⚙  Applying Alembic migrations...")
    code, stdout, stderr = await run_cmd("alembic", "upgrade", "head")

    if code == 0:
        print("✅ Database successfully upgraded to latest revision!")
        if stdout:
            print(stdout)
    else:
        print("❌ Alembic upgrade failed!")
        print(stderr)

    print("✅ Auto migration process complete!\n")