import json
import os
from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

# Ensure tojson filter is available
def _tojson(value, indent=None):
    return Markup(json.dumps(value, ensure_ascii=False, indent=indent))

templates.env.filters["tojson"] = _tojson


def render(request: Request, template: str, **kwargs: Any):
    kwargs.setdefault("request", request)
    kwargs.setdefault("admin", getattr(request.state, "admin", {}))
    kwargs.setdefault("now", datetime.now())
    return templates.TemplateResponse(template, kwargs)
