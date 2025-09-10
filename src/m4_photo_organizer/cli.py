import typer
from pathlib import Path
from rich.console import Console
from .organizer import Organizer
from .rclone_integration import Rclone, SUFFIXES
from .config import SETTINGS

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
                "https://raw.githubusercontent.com/swz30/Restormer/master/basicsr/models/archs/restormer_arch.py",
                "https://github.com/swz30/Restormer/raw/master/basicsr/models/archs/restormer_arch.py",
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
def run(
    limit: int = typer.Option(20, help="Max items to process this run"),
    scan_seconds: int = typer.Option(None, help="Max seconds to spend scanning per root"),
    scan_max: int = typer.Option(None, help="Max files to scan total"),
    src_dir: str = typer.Option(None, help="Specific directory to scan (within the mount)")
):
    org = Organizer()
    console.rule("Starting run")
    processed = org.run_once(limit=limit, scan_seconds=scan_seconds, scan_max=scan_max, src_dir=Path(src_dir) if src_dir else None)
    console.print(f"Processed: {processed}")

@app.command()
def debug_scan(scan_max: int = typer.Option(50), src_dir: str = typer.Option(None)):
    """Print sample media paths discovered by the scanner."""
    rc = Rclone()
    items = list(rc.iter_media(max_scan=scan_max, src_dir=Path(src_dir) if src_dir else None))
    for p in items[:scan_max]:
        console.print(str(p))
    console.print({"found": len(items)})

@app.command()
def debug_comprehensive(
    scan_max: int = typer.Option(50, help="Max files to find"),
    src_dir: str = typer.Option(None, help="Specific directory to scan"),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """Comprehensive debugging of the search system with detailed output."""
    import logging
    from .logging import get_logger
    
    # Set up verbose logging if requested
    if verbose:
        logging.getLogger("m4_photo_organizer").setLevel(logging.DEBUG)
        
    console.rule("🔍 Comprehensive Search Debug")
    
    # Show current configuration
    console.print("📋 [bold]Current Configuration:[/bold]")
    console.print(f"  • Google Photos Mount: {SETTINGS.google_photos_mount}")
    console.print(f"  • Mount Exists: {SETTINGS.google_photos_mount.exists()}")
    console.print(f"  • Scan Max Seconds: {SETTINGS.scan_max_seconds}")
    console.print(f"  • Scan Max Per Root: {SETTINGS.scan_max_entries_per_root}")
    console.print(f"  • Supported Extensions: {len(SUFFIXES)} types")
    console.print("")
    
    # Show search directories that will be tried
    console.print("📁 [bold]Search Directories:[/bold]")
    if src_dir:
        console.print(f"  • Specified: {src_dir} (exists: {Path(src_dir).exists()})")
    else:
        console.print("  • No specific directory - will try fallbacks")
        
    # Common directories that will be searched
    common_dirs = [
        Path.home() / "Pictures",
        Path.home() / "Downloads", 
        Path.home() / "Desktop",
        Path("/tmp"),
        Path("/var/tmp"),
        Path.cwd(),
    ]
    
    console.print("  • Common directories to try:")
    for d in common_dirs:
        exists = "✅" if d.exists() else "❌"
        console.print(f"    {exists} {d}")
    console.print("")
    
    # Perform the search
    console.print("🔎 [bold]Performing Search...[/bold]")
    rc = Rclone()
    
    try:
        items = list(rc.iter_media(max_scan=scan_max, src_dir=Path(src_dir) if src_dir else None))
        
        console.print(f"✅ [bold green]Found {len(items)} media files[/bold green]")
        
        if items:
            console.print("\n📄 [bold]Sample Files Found:[/bold]")
            for i, p in enumerate(items[:min(10, len(items))]):
                console.print(f"  {i+1:2d}. {p}")
            
            if len(items) > 10:
                console.print(f"  ... and {len(items) - 10} more files")
                
            # Show file type breakdown
            extensions = {}
            for p in items:
                ext = p.suffix.lower()
                extensions[ext] = extensions.get(ext, 0) + 1
                
            console.print(f"\n📊 [bold]File Types Found:[/bold]")
            for ext, count in sorted(extensions.items()):
                console.print(f"  • {ext}: {count} files")
        else:
            console.print("❌ [bold red]No media files found[/bold red]")
            console.print("\n💡 [bold]Suggestions:[/bold]")
            console.print("  1. Check if your Google Photos mount is properly configured")
            console.print("  2. Try specifying a directory with --src-dir")
            console.print("  3. Set PHOTOORG_SEARCH_DIRS environment variable (colon-separated paths)")
            console.print("  4. Set PHOTOORG_GOOGLE_MOUNT environment variable to your mount path")
            console.print("  5. Use --verbose flag to see detailed search logs")
            
    except Exception as e:
        console.print(f"❌ [bold red]Search failed with error:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())

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

