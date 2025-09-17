import time
from pathlib import Path

_BALANCE_FILE = Path(".local_balance.txt")
_ADDRESS = "DevnetStub1111111111111111111111111111111"

def _read_balance() -> float:
    if not _BALANCE_FILE.exists():
        _BALANCE_FILE.write_text("0.000000000")
        return 0.0
    return float(_BALANCE_FILE.read_text().strip())

def _write_balance(v: float):
    _BALANCE_FILE.write_text(f"{v:.9f}")

def execute_trade_stub(sol: float = 0.01):
    """Simuliert eine Devnet-Transaktion (ohne echte RPC-Calls).
    - erhöht lokale 'Balance' minimal um 0.01 SOL (Airdrop-Simulation)
    - zieht dann 0.01 SOL als 'Send' wieder ab (Trade-Simulation)
    Ergebnis: Balance bleibt stabil, aber wir geben ein Log zurück.
    """
    bal = _read_balance()
    log = []
    log.append("Starte Stub-Execution ...")
    log.append("Airdrop (simuliert): +0.010000000 SOL")
    bal += 0.01
    time.sleep(0.1)
    log.append("Sende (simuliert) 0.010000000 SOL an Test-Empfänger ...")
    bal -= sol
    time.sleep(0.1)
    _write_balance(bal)
    log.append("Fertig.")
    return {
        "ok": True,
        "address": _ADDRESS,
        "balance": bal,
        "log": log
    }