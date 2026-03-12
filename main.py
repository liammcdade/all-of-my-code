import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint

console = Console()

def main():
    while True:
        console.clear()
        console.print(Panel.fit("All-Code-In-One Launcher", style="bold blue"))
        
        options = {
            "1": ("Sudoku Solver", "sudoku_solver.py"),
            "2": ("Deal or No Deal", "deal_or_no_deal.py"),
            "3": ("Relativity Calculator", "relativity_calculator.py"),
            "4": ("Electoral Tie Calculator", "electoral_tie_calculator.py"),
            "5": ("RCV Simulator", "rcv_simulator.py"),
            "6": ("Minecraft World Calc", "minecraft_world_calc.py"),
            "7": ("Match Analyzer", "match_analyzer.py"),
            "q": ("Quit", None)
        }
        
        for key, (name, _) in options.items():
            console.print(f"[bold cyan]{key}[/bold cyan]. {name}")
            
        choice = Prompt.ask("Choose an option", choices=list(options.keys()), default="q")
        
        if choice == 'q':
            console.print("[bold red]Exiting...[/bold red]")
            break
            
        name, script = options[choice]
        console.print(f"[green]Running {name}...[/green]")
        
        # Run the script using the current python executable
        try:
            exit_code = os.system(f'"{sys.executable}" "{script}"')
            if exit_code != 0:
                console.print(f"[bold red]Error running {name}. Exit code: {exit_code}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Failed to run {name}: {e}[/bold red]")
        
        Prompt.ask("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
