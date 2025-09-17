# Research-Config & getrennte Provider

- Config/research.yaml steuert Provider, Routing, Policy und Logging (mit ${ENV}-Platzhaltern).
- Backend/services/llm_openai.py → NUR OpenAI (Responses API).
- Backend/services/twitter_x.py → NUR Twitter/X (optional, standardmäßig aus).
- Backend/research_router.py lädt Config, ruft OpenAI (oder Fallback) und optional Twitter.

Einbindung in Backend/app.py:
    from research_router import router as research_router
    app.include_router(research_router)

ENV setzen:
    export OPENAI_API_KEY=sk-...
    # optional:
    export X_BEARER_TOKEN=...

Install:
    pip install -r requirements.txt