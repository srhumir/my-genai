from logging import getLogger

from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers.agents_router import router as agents_router
from routers.chainlit_router import router as chainlit_router

logger = getLogger(__name__)
app = FastAPI()


@app.get("/")
def root() -> RedirectResponse:
    """Redirect root to the HTML guide."""
    return RedirectResponse(url="/chat_services/welcome/")


mount_chainlit(app=app, target="./chainlit_frontend.py", path="/chat")
app.mount(
    "/chat_services/welcome", StaticFiles(directory="html", html=True), name="html"
)
app.include_router(chainlit_router, prefix="/chat_services")

app.include_router(agents_router, prefix="/api/agents")
