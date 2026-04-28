import psutil
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

console = Console()

# ── Layer 1: Data Collection ───────────────────────────────────────────────
def get_cpu():
    usage = psutil.cpu_percent(interval=0.5)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    return usage, per_core

def get_memory():
    m = psutil.virtual_memory()
    return (round(m.total / 1e9, 1), round(m.used / 1e9, 1), m.percent)

def get_disk():
    partitions = []
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            partitions.append((p.mountpoint, round(u.total / 1e9, 1), round(u.used / 1e9, 1), u.percent))
        except PermissionError:
            pass
    return partitions

def get_top_processes(n=8):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            procs.append((
                p.info['pid'],
                p.info['name'][:20],
                p.info['cpu_percent'],
                round(p.info['memory_info'].rss / 1e6, 1)
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x[2], reverse=True)[:n]

def get_network():
    snap1 = psutil.net_io_counters(pernic=True)
    time.sleep(0.5)
    snap2 = psutil.net_io_counters(pernic=True)
    result = {}
    for iface in snap1:
        if iface == 'lo':
            continue
        sent = (snap2[iface].bytes_sent - snap1[iface].bytes_sent) * 2  
        recv = (snap2[iface].bytes_recv - snap1[iface].bytes_recv) * 2
        result[iface] = (sent, recv)
    return result

# ── Layer 2: Bar Renderer Helper ───────────────────────────────────────────
def make_bar(percent, width=30, color="green"):
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    if percent > 85:
        color = "red"
    elif percent > 60:
        color = "yellow"
    return f"[{color}]{bar}[/{color}] [white]{percent:.1f}%[/white]"

# ── Layer 3: Layout and Render Loop ────────────────────────────────────────
def build_dashboard():
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

    # CPU Panel
    cpu_pct, per_core = get_cpu()
    cpu_text = Text()
    cpu_text.append(f"  Overall  {make_bar(cpu_pct)}\n\n", style="")
    for i, c in enumerate(per_core):
        cpu_text.append(f"  Core {i:<2}  {make_bar(c, width=20)}\n")
    cpu_panel = Panel(cpu_text, title="[bold cyan]CPU[/bold cyan]", border_style="cyan")

    # Memory Panel
    total_gb, used_gb, mem_pct = get_memory()
    mem_text = Text()
    mem_text.append(f"  {make_bar(mem_pct)}\n")
    mem_text.append(f"  {used_gb} GB used of {total_gb} GB\n")
    mem_panel = Panel(mem_text, title="[bold magenta]Memory[/bold magenta]", border_style="magenta")

    # Disk Panel
    disk_text = Text()
    for mount, total, used, pct in get_disk():
        disk_text.append(f"  {mount:<12} {make_bar(pct, width=20)}  {used}/{total} GB\n")
    disk_panel = Panel(disk_text, title="[bold yellow]Disk[/bold yellow]", border_style="yellow")

    # Network Panel
    net_text = Text()
    for iface, (sent, recv) in get_network().items():
        net_text.append(f"  {iface:<10} ↑ {sent/1024:>7.1f} KB/s   ↓ {recv/1024:>7.1f} KB/s\n")
    net_panel = Panel(net_text, title="[bold blue]Network[/bold blue]", border_style="blue")

    # Process Table
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold white")
    table.add_column("PID",   width=7)
    table.add_column("Name",  width=22)
    table.add_column("CPU",   width=8)
    table.add_column("Mem",   width=10)
    for pid, name, cpu, mem in get_top_processes():
        cpu_color = "red" if cpu > 50 else "yellow" if cpu > 10 else "green"
        table.add_row(str(pid), name, f"[{cpu_color}]{cpu:.1f}%[/{cpu_color}]", f"{mem} MB")
    proc_panel = Panel(table, title="[bold white]Top Processes[/bold white]", border_style="white")

    # Assemble Layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=1),
        Layout(name="top", size=14),
        Layout(name="bottom"),
    )
    layout["top"].split_row(
        Layout(cpu_panel, name="cpu"),
        Layout(name="right"),
    )
    layout["top"]["right"].split_column(
        Layout(mem_panel),
        Layout(disk_panel),
    )
    layout["bottom"].split_row(
        Layout(net_panel, ratio=1),
        Layout(proc_panel, ratio=2),
    )
    
    # Check for Stretch Goal 1 (Alerts)
    if cpu_pct > 90 or mem_pct > 85:
        alert = Text("⚠  HIGH LOAD DETECTED", style="bold white on red", justify="center")
        layout["header"].update(alert)
    else:
        layout["header"].update(Text(f"  System Health Dashboard  ·  {now}  ·  Press Ctrl+C to exit", style="bold white on dark_blue", justify="left"))
        
    return layout

def run():
    with Live(build_dashboard(), refresh_per_second=1, screen=True) as live:
        try:
            while True:
                time.sleep(5)
                live.update(build_dashboard())
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run()