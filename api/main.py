from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import init_db
    from data.loader import load_all
    from services.portfolio import precompute
    from services.returns import populate_cost_basis_history

    # 1. Schema first
    init_db()
    # 2. Sync all Copilot data (best-effort — don't block startup on API errors)
    try:
        load_all()
    except Exception as e:
        print(f"WARNING: Sync failed ({e}), starting with existing data")
    # 3. Precompute derived data (benchmark prices, cost basis snapshots)
    try:
        precompute()
    except Exception as e:
        print(f"WARNING: Precompute failed ({e})")
    # 4. Populate cost basis history
    try:
        populate_cost_basis_history()
    except Exception as e:
        print(f"WARNING: Cost basis history failed ({e})")
    yield


app = FastAPI(title="Investment Simulator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Investment & returns routers
from routers.investments import router as investments_router
from routers.returns import router as returns_router

app.include_router(investments_router)
app.include_router(returns_router)

# Conditionally import future routers (spending, simulation)
try:
    from routers.spending import router as spending_router
    app.include_router(spending_router)
except ImportError:
    pass

try:
    from routers.simulation import router as simulation_router
    app.include_router(simulation_router)
except ImportError:
    pass
