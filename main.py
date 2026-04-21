from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI()

# CORS (para frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sapoturco.github.io/iub-frontend/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)