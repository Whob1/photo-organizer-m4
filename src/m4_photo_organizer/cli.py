import typer
from rich.console import Console
from .organizer import Organizer

app = typer.Typer(help="M4 Photo & Video Organizer/Enhancer")
console = Console()

@app.command()
def run(limit: int = typer.Option(20, help="Max items to process this run")):
    org = Organizer()
    console.rule("Starting run")
    processed = org.run_once(limit=limit)
    console.print(f"Processed: {processed}")

if __name__ == "__main__":
    app()

