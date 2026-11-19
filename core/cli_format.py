"""
Pith Terminal CLI Renderer.
Formats today's brief in crisp, ANSI color-coded typography for terminal display.
Supports: curl localhost:8000/dev | curl localhost:8000/founder | curl localhost:8000/plain
"""

import sys
from typing import Optional
from core.db import Database
from core.models import DailyIssue, Card

# ANSI Escape Codes for Terminal
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"

# Colors
FG_WHITE = "\033[97m"
FG_GRAY = "\033[90m"
FG_CYAN = "\033[96m"
FG_GREEN = "\033[92m"
FG_AMBER = "\033[93m"
FG_BLUE = "\033[94m"
FG_RED = "\033[91m"
FG_GOLD = "\033[38;5;178m"
FG_EMERALD = "\033[38;5;35m"
FG_SLATE = "\033[38;5;245m"

BG_DARK = "\033[48;5;234m"
BG_GREEN = "\033[48;5;22m"
BG_AMBER = "\033[48;5;130m"
BG_BLUE = "\033[48;5;24m"
BG_OBSIDIAN = "\033[48;5;232m"


def render_cli_brief(issue: Optional[DailyIssue], role: str = "developer", width: int = 80) -> str:
    if not issue:
        return f"\n{FG_RED}No published issue found.{RESET}\n"

    role = role.lower()
    if role in ("dev", "developer"):
        role_key = "developer"
        role_label = "DEVELOPER LENS"
        role_color = FG_EMERALD
        border_char = "═"
    elif role in ("founder", "founders"):
        role_key = "founder"
        role_label = "FOUNDER LENS"
        role_color = FG_AMBER
        border_char = "═"
    elif role in ("investor", "investors"):
        role_key = "investor"
        role_label = "INVESTOR LENS"
        role_color = FG_CYAN
        border_char = "═"
    else:
        role_key = "everyday"
        role_label = "EVERYDAY PERSON (PLAIN ENGLISH)"
        role_color = FG_GOLD
        border_char = "═"

    lines = []
    lines.append("")
    lines.append(f"{FG_GOLD}╔{'═' * (width - 2)}╗{RESET}")
    lines.append(f"{FG_GOLD}║{RESET}  {BOLD}{FG_WHITE}P I T H{RESET}  {FG_GRAY}· High-Signal Daily Tech Intelligence{RESET}{' ' * (width - 48)}{FG_GOLD}║{RESET}")
    lines.append(f"{FG_GOLD}║{RESET}  {DIM}Issue: {issue.date}  ·  Beat: {issue.beat}{RESET}{' ' * max(1, width - 28 - len(issue.date) - len(issue.beat))}{FG_GOLD}║{RESET}")
    lines.append(f"{FG_GOLD}║{RESET}  {role_color}{BOLD}▶ {role_label}{RESET}{' ' * (width - 6 - len(role_label))}{FG_GOLD}║{RESET}")
    lines.append(f"{FG_GOLD}╚{'═' * (width - 2)}╝{RESET}")
    lines.append("")

    roman_numerals = ["I", "II", "III", "IV", "V"]

    for idx, card in enumerate(issue.cards):
        roman = roman_numerals[idx] if idx < len(roman_numerals) else f"#{idx+1}"
        rv = card.role_views.get(role_key) or card.role_views.get("developer")

        # Signal score badge
        sig_badge = f"{FG_EMERALD}[HIGH SIGNAL · {card.signal_score:.1f}]{RESET}" if card.signal_score >= 78 else f"{FG_AMBER}[MED SIGNAL · {card.signal_score:.1f}]{RESET}"

        lines.append(f"{FG_GRAY}{'─' * width}{RESET}")
        lines.append(f"{FG_GOLD}{BOLD}{roman}.{RESET} {BOLD}{FG_WHITE}{card.headline}{RESET}")
        lines.append(f"   {sig_badge} {FG_GRAY}· {len(card.evidence_links)} primary source · Resolves {card.prediction.resolves_at}{RESET}")
        lines.append("")
        
        # What Happened & Why it Matters
        lines.append(f"   {FG_CYAN}{BOLD}What Happened:{RESET} {card.what_happened}")
        lines.append(f"   {FG_GOLD}{BOLD}Why It Matters:{RESET} {card.why_it_matters}")
        lines.append("")

        # Action box
        action_type = rv.action_type.upper()
        if action_type == "DO":
            type_tag = f"{FG_EMERALD}{BOLD}[DO THIS WEEK]{RESET}"
        elif action_type == "WATCH":
            type_tag = f"{FG_AMBER}{BOLD}[WATCH TRIGGER]{RESET}"
        else:
            type_tag = f"{FG_GRAY}{BOLD}[IGNORE FOR NOW]{RESET}"

        lines.append(f"   ┌─ {type_tag} ────────────────────────────────────────────────────────┐")
        lines.append(f"   │ {BOLD}{FG_WHITE}{rv.action_text}{RESET}")
        lines.append(f"   │ {DIM}{rv.impact}{RESET}")
        lines.append(f"   └──────────────────────────────────────────────────────────────────┘")
        lines.append("")

        # Prediction & 1-Keystroke Vote Prompt
        prob_pct = int(card.prediction.probability * 100)
        lines.append(f"   {FG_GOLD}✦ Forecast ({prob_pct}%):{RESET} {card.prediction.statement}")
        lines.append(f"     {DIM}Resolution standard:{RESET} {card.prediction.resolution_criteria}")
        lines.append(f"     {BOLD}[Beat the Brief]:{RESET} {FG_EMERALD}[▲ H]igher{RESET}  {FG_GOLD}[● A]gree{RESET}  {FG_RED}[▼ L]ower{RESET}  {FG_GRAY}(curl lowpass.sh/vote/{card.id}/<pick>){RESET}")
        lines.append("")

    # Filtered noise summary
    if issue.not_included_today:
        lines.append(f"{FG_GRAY}{'─' * width}{RESET}")
        lines.append(f"{FG_RED}{BOLD}⚡ SAFELY IGNORE TODAY ({len(issue.not_included_today)} noise stories filtered):{RESET}")
        for ni in issue.not_included_today:
            lines.append(f"   {FG_GRAY}✕{RESET} {FG_WHITE}{ni.headline}{RESET}")
            lines.append(f"     {DIM}└─ {ni.reason}{RESET}")
        lines.append("")

    # Zero-FOMO Completion
    lines.append(f"{FG_EMERALD}{'═' * width}{RESET}")
    lines.append(f"  {FG_EMERALD}{BOLD}✓ Briefing complete. Go build.{RESET}")
    lines.append(f"  {DIM}5 high-signal shifts processed. Zero infinite scroll. Next issue tomorrow at 07:00 IST.{RESET}")
    lines.append(f"  {DIM}Web App: http://localhost:8000 (Interactive ELO, Audio Brief, 3D Cards){RESET}")
    lines.append(f"{FG_EMERALD}{'═' * width}{RESET}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    db = Database("brief.sqlite3")
    latest = db.get_latest_issue()
    role_arg = sys.argv[1] if len(sys.argv) > 1 else "developer"
    print(render_cli_brief(latest, role=role_arg))
