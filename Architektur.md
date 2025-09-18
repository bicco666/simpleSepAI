# Architektur-Dokumentation für simpleSepAI

## Übersicht
simpleSepAI ist eine Anwendung für Solana-Trading, die Ideen generiert, analysiert und Trades ausführt. Die Architektur basiert auf einem modularen Design mit Backend (FastAPI), Frontend (HTML) und externen Services (LLM, Twitter).

## Hauptkomponenten

### 1. Backend (FastAPI)
- **app.py**: Hauptanwendung mit CORS-Middleware. Definiert Endpunkte für:
  - `/api/systemtest`: Systemtest (Stub-Modus)
  - `/api/idea`: Statische Idee aus idee.txt
  - `/api/analysis`: Statische Analyse aus analyse.txt
  - `/api/analysis/config`: Analyse mit Konfiguration
  - `/api/analysis/test`: Test-Endpunkt
  - `/api/execute`: Trade-Execution (simuliert)
  - `/api/run_test/*`: Testläufe mit pytest
- **research_router.py**: Erweiterte Research-API mit LLM-Integration
  - `/api/research/idea`: Ideen-Generierung mit OpenAI/Grok und Fallback
  - `/api/research/health`: Provider-Status
  - `/api/research/test/grok`: Grok-Test

### 2. Module (Module/)
- **analysis.py**: Statische Analyse-Funktion
- **execution.py**: Simulierte Trade-Execution mit Balance-Verwaltung
- **idea.py**: Statische Idee-Funktion
- **quality.py**: Test-Stub

### 3. Services (Backend/services/)
- **llm_openai.py**: OpenAI-Integration für Ideen-Generierung mit Retry/Fallback
- **llm_grok.py**: xAI Grok-Integration mit mehreren Endpoints/Models
- **twitter_x.py**: Twitter-API für Markt-Signale

### 4. Frontend (Frontend/)
- HTML-Dateien für UI (z.B. index.html, settings.html)
- Einfache Web-Interface für API-Interaktion

### 5. Konfiguration (Config/)
- **research.yaml**: YAML-Konfiguration für Provider, Policies, Logging

### 6. Tests (Tests/)
- **test_endpoints.py**: API-Tests
- **test_research_api.py**: Research-API-Tests
- **test_research_idea.py**: Idee-Tests

### 7. Reports (Report/)
- Automatische Berichte für Research und Tests

## Datenfluss
1. Frontend sendet Requests an Backend-Endpunkte
2. Backend lädt Konfiguration (config_loader.py)
3. Für Research: Router ruft LLM-Services auf (OpenAI/Grok mit Fallback)
4. Twitter-Signale werden optional integriert
5. Ergebnisse werden geloggt und als JSON zurückgegeben
6. Execution simuliert Trades mit lokaler Balance

## Abhängigkeiten
- FastAPI für Backend
- OpenAI/Grok für LLM
- Requests für HTTP-Calls
- Pydantic für Datenmodelle
- Pytest für Tests

## Sicherheit
- API-Keys aus Config oder Environment-Variablen
- CORS für Frontend-Zugriff
- Timeout und Retry für externe APIs

## Mögliche Verbesserungen/Erweiterungen
- **Datenbank-Integration**: Aktuell statische Dateien; hinzufügen von PostgreSQL/MySQL für persistente Daten
- **Authentifizierung**: JWT oder OAuth für sichere API-Zugriffe
- **Monitoring**: Prometheus/Grafana für Metriken und Logs
- **CI/CD**: GitHub Actions für automatische Tests und Deployments
- **Mehr LLM-Provider**: Claude, Gemini als weitere Fallbacks
- **Echte Execution**: Integration mit Solana RPC für reale Trades
- **UI-Framework**: React/Vue statt reinem HTML für bessere UX
- **Caching**: Redis für API-Responses und Konfiguration
- **Microservices**: Aufteilen in separate Services (Research, Execution, Analysis)
- **Containerisierung**: Docker für einfachere Deployment
- **API-Versionierung**: Versioning für Endpunkte
- **Error-Handling**: Verbesserte Fehlerbehandlung und Benachrichtigungen
- **Skalierung**: Load Balancer und horizontale Skalierung