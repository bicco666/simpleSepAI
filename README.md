# simpleSepAI (Minimal Skeleton)

Dies ist die **einfachste** lauffähige Mini-Architektur deiner Idee. Alles ist stub/platzhalterhaft,
aber klickbar und testbar. Ziel: **Komplexität runter** und später Schritt für Schritt erweitern.

## Ordnerstruktur
- `Frontend/` – statische HTML mit 4 Buttons (Systemtest, Idee generieren, Analyse generieren, Execution durchführen) und 2 Anzeigen (Wallet Balance, Wallet Adresse).
- `Backend/` – FastAPI-Server mit 4 Endpoints (`/systemtest`, `/idea`, `/analysis`, `/execute`) + CORS aktiv.
- `Module/` – 4 sehr einfache Module (Forschung/Idee, Analyse, Execution, Quality/Test).
- `Tests/` – Pytest, der die 4 Endpoints über FastAPI TestClient prüft.
- `Scripts/` – Startskript und ein *Dummy* Devnet-Transfer-Skript (nur Echo).
- `Report/` – leer (Platzhalter).
- `Update/` – Changelog Platzhalter.

## Schnellstart
```bash
# (1) Python-Umgebung aktivieren/erstellen (optional)
python3 -m venv .venv && source .venv/bin/activate

# (2) Abhängigkeiten
pip install -r requirements.txt

# (3) Backend starten
uvicorn Backend.app:app --reload

# (4) Frontend öffnen
# Öffne Frontend/index.html im Browser (Doppelklick oder: python -m http.server im Projektroot)
```

## Endpoints (lokal)
- GET `http://127.0.0.1:8000/api/systemtest`
- GET `http://127.0.0.1:8000/api/idea`
- GET `http://127.0.0.1:8000/api/analysis`
- POST `http://127.0.0.1:8000/api/execute`

> **Hinweis:** Execution ist **stub** und simuliert nur eine Devnet-Transaktion (kein echter RPC-Call).

## Nächste Schritte
- Echte Solana-Devnet-Integration in `Module/execution.py`.
- Wallet-Handling (Keypair/Adresse) + echte Balance-Abfrage im Backend.
- Frontend-Statusbereich erweitern (Logs/Report).