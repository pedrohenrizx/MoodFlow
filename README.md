# MoodFlow

Diário emocional mobile-first e 100% gratuito. Todos os recursos ficam liberados apenas para usuários logados, sem planos de assinatura.

## Rodar localmente

1. Crie o ambiente e instale dependências:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Inicie o servidor:

```bash
FLASK_APP=app.py flask run
```

3. Acesse em `http://localhost:5000` para criar uma conta e usar o dashboard, perfil e registros de humor (SQLite local).
