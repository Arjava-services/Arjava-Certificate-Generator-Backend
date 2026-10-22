from app.main import app
from app.config.settings import settings

print(f"Loaded {settings.PROJECT_NAME} v{settings.VERSION}")
print(f"Total routes in app: {len(app.routes)}")
for r in app.routes:
    methods = getattr(r, "methods", None)
    path = getattr(r, "path", str(r))
    print(f"  {methods} {path}")
