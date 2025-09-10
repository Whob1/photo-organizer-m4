import typer
from rich.console import Console
from .organizer import Organizer

app = typer.Typer(help="M4 Photo & Video Organizer/Enhancer")
console = Console()

@app.command()
def setup():
    """Ensure directories exist."""
    from .config import SETTINGS
    for d in [SETTINGS.raw_dir, SETTINGS.processed_dir, SETTINGS.tmp_dir, SETTINGS.thumbnails_dir, SETTINGS.models_dir]:
        d.mkdir(parents=True, exist_ok=True)
    console.print("Project directories ready.")

@app.command()
def setup_models():
    """Download AI models if missing and verify they can be loaded."""
    from .ai.models import ensure_models, load_sessions
    paths = ensure_models()
    photo_sess, video_sess = load_sessions(paths)
    console.print({
        "photo_model": str(paths.photo),
        "photo_loaded": photo_sess is not None,
        "video_model": str(paths.video),
        "video_loaded": video_sess is not None,
    })

@app.command()
def run(limit: int = typer.Option(20, help="Max items to process this run")):
    org = Organizer()
    console.rule("Starting run")
    processed = org.run_once(limit=limit)
    console.print(f"Processed: {processed}")

@app.command()
def status():
    from .storage import StorageManager
    from .config import SETTINGS
    sm = StorageManager()
    console.print({
        "usage_bytes": sm.usage_bytes(),
        "limit_bytes": SETTINGS.max_disk_bytes,
        "raw_dir": str(SETTINGS.raw_dir),
        "processed_dir": str(SETTINGS.processed_dir),
    })

if __name__ == "__main__":
    app()

