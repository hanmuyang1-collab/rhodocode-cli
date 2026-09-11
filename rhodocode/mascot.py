"""The rhodocode mascot: a cyan flower with white eyes, no mouth, no arrows."""

CYAN = "\x1b[96m"
WHITE = "\x1b[97m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


def flower() -> str:
    """Cyan petals, white eyes, no mouth, no arrows."""
    return (
        f"    {CYAN}* * *{RESET}\n"
        f"  {CYAN}* {WHITE}o o{RESET} {CYAN}*{RESET}\n"
        f"    {CYAN}* * *{RESET}\n"
        f"      {CYAN}|{RESET}\n"
        f"     {CYAN}\\|/{RESET}"
    )


def plain_flower() -> str:
    return "    * * *\n  * o o *\n    * * *\n      |\n     \\|/"


def banner(version: str) -> str:
    return (
        flower()
        + f"\n\n  {BOLD}{CYAN}rhodocode{RESET} {DIM}v{version}{RESET}"
        + f"\n  {DIM}agentic coding, grown in the terminal{RESET}\n"
    )


def print_banner(version: str) -> None:
    print(banner(version))
