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
    from .config import SETTINGS
    paths = ensure_models()
    photo_sess, video_sess = load_sessions(paths)
    # Restormer weights presence
    rest_dir = SETTINGS.models_dir / "restormer"
    present = {}
    if rest_dir.exists():
        for p in rest_dir.glob("*.pth"):
            present[p.name] = p.stat().st_size
    # Restormer readiness: arch file + torch + deps
    import os
    from pathlib import Path
    pkg_dir = Path(__file__).resolve().parent
    rest_arch = pkg_dir / 'vendor' / 'restormer_arch.py'
    try:
        import torch
        torch_ok = True
        mps = torch.backends.mps.is_available() and torch.backends.mps.is_built()
    except Exception:
        torch_ok = False
        mps = False

    # Attempt to fetch vendor file if missing (with GH token and fallback URL)
    if not rest_arch.exists():
        try:
            import os, urllib.request
            rest_arch.parent.mkdir(parents=True, exist_ok=True)
            urls = [
                "https://raw.githubusercontent.com/swz30/Restormer/master/basicsr/archs/restormer_arch.py",
                "https://github.com/swz30/Restormer/raw/master/basicsr/archs/restormer_arch.py",
            ]
            token = os.getenv("GITHUB_TOKEN")
            for u in urls:
                try:
                    req = urllib.request.Request(u)
                    if token:
                        req.add_header("Authorization", f"Bearer {token}")
                    with urllib.request.urlopen(req) as resp, open(rest_arch, 'wb') as out:
                        out.write(resp.read())
                    break
                except Exception:
                    continue
        except Exception:
            pass

    console.print({
        "photo_model": str(paths.photo),
        "photo_loaded": photo_sess is not None,
        "video_model": str(paths.video),
        "video_loaded": video_sess is not None,
        "restormer_weights": present,
        "restormer_arch_vendored": rest_arch.exists(),
        "torch_available": torch_ok,
        "mps": mps,
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

