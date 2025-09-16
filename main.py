from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.check_env_variables import check_environment_variables
from core.services.prisma import prisma
from core.settings import config_auth
from authx_extra.metrics import MetricsMiddleware, get_metrics
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apscheduler.triggers.cron import CronTrigger

# IMPORT ROUTERS
from core.modules.auth.route import auth_router
from core.modules.media.route import media_router
from core.modules.auth.oauth import oauth_router
from core.agents.incomeStatementAnalyser.route import income_statement_analyser_router 
from core.modules.langfuse.route import langfuse_router
from core.modules.vector_db.route import vector_db_router
from core.modules.subscription.route import schedule_subscription_termination, subscription_router
from core.modules.webhook.route import webhook_router
from core.modules.user.route import user_router
from core.modules.seat.route import schedule_seat_termination, seat_router 

from starlette.middleware.sessions import SessionMiddleware
from core.settings import settings

# Define the required environment variables
required_env_vars = [
    "REQURV_DATABASE_URL",
    "REQURV_HIVE_ENDPOINT",
    "REQURV_MASTER_KEY",
    "REQURV_SECRET_KEY",
    "REQURV_LAGO_ENDPOINT",
    "REQURV_LAGO_API_KEY",
    "REQURV_LAGO_WEBHOOK_SECRET",
]
check_environment_variables(required_env_vars)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await prisma.connect()
    yield


# -------------- APP -------------- #
app = FastAPI(title="ReQurv AI - HUB", lifespan=lifespan)

# ------------- SCHEDULER -------------- #
scheduler = AsyncIOScheduler()

scheduler.add_job(schedule_seat_termination, CronTrigger(hour=1, minute=0))  # Every day at 1:00 AM
scheduler.add_job(schedule_subscription_termination, CronTrigger(hour=1, minute=0))  # Every minute
scheduler.start()

# -------------- MIDDLEWARE -------------- #
app.add_middleware(SessionMiddleware, secret_key=settings.requrv_session_secret)
app.add_middleware(MetricsMiddleware)  # type: ignore
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

app.add_route("/metrics", get_metrics)
config_auth(app)

# -----------MIDDLEWARE-------------- #
origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- #

# ROUTERS
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(income_statement_analyser_router)
app.include_router(media_router)
app.include_router(oauth_router)
app.include_router(langfuse_router)
app.include_router(vector_db_router)
app.include_router(subscription_router)
app.include_router(webhook_router)
app.include_router(seat_router)


@app.get("/")
def read_root():
    return {"status": "running"}


