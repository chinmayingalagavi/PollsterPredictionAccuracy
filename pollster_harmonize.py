"""Manual pollster name harmonization mappings."""

from __future__ import annotations


# Manual dictionary: variant -> canonical pollster name.
POLLSTER_ALIASES: dict[str, str] = {
    # CVoter
    "ABP News - CVoter": "CVoter",
    "ABP News – C Voter": "CVoter",
    "ABP News – C-Voter": "CVoter",
    "ABP News-C Voter": "CVoter",
    "ABP News-C-Voter": "CVoter",
    "ABP News-CVoter": "CVoter",
    "ABP-CVoter": "CVoter",
    "ABP-C Voter": "CVoter",
    "India Today - CVoter": "CVoter",
    "India Today – CVoter": "CVoter",
    # Axis My India
    "Axis My India": "Axis My India",
    "India Today - Axis My India": "Axis My India",
    "India Today -Axis My India": "Axis My India",
    "India Today – Axis My India": "Axis My India",
    "India Today- Axis My India": "Axis My India",
    "India Today-Axis My India": "Axis My India",
    "Aaj Tak - Axis My India": "Axis My India",
    # Matrize
    "Matrize": "Matrize",
    "News18 Matrize": "Matrize",
    "ABP News-Matrize": "Matrize",
    "India TV -Matrize": "Matrize",
    "Zee News -Matrize": "Matrize",
    "Zee News-Matrize": "Matrize",
    "Republic TV -Matrize": "Matrize",
    "Republic TV-Matrize": "Matrize",
    # P-Marq
    "P Marq": "P-Marq",
    "P-Marq": "P-Marq",
    "P-MARQ": "P-Marq",
    "Republic -P Marq": "P-Marq",
    "Republic P-Marq": "P-Marq",
    "Republic TV -P MARQ": "P-Marq",
    # CNX
    "CNX": "CNX",
    "CNX Exit Poll": "CNX",
    "India TV-CNX": "CNX",
    "India TV - CNX": "CNX",
    "India TV -CNX": "CNX",
    # Today's Chanakya
    "Today's Chanakya": "Today's Chanakya",
    "News 24 -Today's Chanakya": "Today's Chanakya",
    "News 24 Today's Chanakya": "Today's Chanakya",
    "News 24-Today's Chanakya": "Today's Chanakya",
    "News24-Today's Chanakya": "Today's Chanakya",
    "News18-Today's Chanakya": "Today's Chanakya",
    # Jan Ki Baat
    "Jan Ki Baat": "Jan Ki Baat",
    "India News-Jan Ki Baat": "Jan Ki Baat",
    "India News -Jan Ki Baat": "Jan Ki Baat",
    "NewsX -Jan Ki Baat": "Jan Ki Baat",
    "Suvarna News -Jan Ki Baat": "Jan Ki Baat",
    # Polstrat
    "Polstrat-NewsX": "Polstrat",
    "NewsX Polstrat": "Polstrat",
    "NewsX – Polstrat": "Polstrat",
    "TV9 Bharatvarsh-Polstrat": "Polstrat",
    "TV9 Bharatvarsh -Polstrat": "Polstrat",
    "TV 9 Bharatvarsh-Polstrat": "Polstrat",
    "TV 9 Marathi-Polstrat": "Polstrat",
    # ETG
    "Times Now-ETG": "ETG",
    "Times Now - ETG": "ETG",
    "Times Now -ETG": "ETG",
    "Times Now – ETG": "ETG",
    # Veto
    "Times Now -Veto": "Veto",
    "Times Now – VETO": "Veto",
    # People's Pulse
    "People's Pulse": "People's Pulse",
    "People's Pulse - Codemo": "People's Pulse",
    "South First - People's Pulse": "People's Pulse",
    "South First – People's Pulse": "People's Pulse",
    "South First-People's Pulse": "People's Pulse",
}


def harmonize_pollster(name: str) -> str:
    """Return the canonical pollster name for a given variant."""
    if not name:
        return name
    return POLLSTER_ALIASES.get(name.strip(), name.strip())

