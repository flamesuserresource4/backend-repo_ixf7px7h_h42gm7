from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import random
import asyncio

app = FastAPI(title="OptiSwap API", version="1.0.0")

# CORS for local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PriceRow(BaseModel):
    pair: str
    uni: float
    sushi: float
    curve: float


class ExecutionRow(BaseModel):
    id: str
    route: str
    pair: str
    size: str
    profit: float


BASE_PRICES: List[PriceRow] = [
    PriceRow(pair="ETH/USDC", uni=100.5, sushi=100.3, curve=100.7),
    PriceRow(pair="WBTC/ETH", uni=14.12, sushi=14.09, curve=14.16),
    PriceRow(pair="DAI/USDC", uni=1.0002, sushi=1.0001, curve=1.0004),
]

BASE_EXECS: List[ExecutionRow] = [
    ExecutionRow(id="ARB-10231", route="Buy on Sushi → Sell on Curve", pair="ETH/USDC", size="10 ETH", profit=20.00),
    ExecutionRow(id="ARB-10232", route="ETH→USDC→DAI→WBTC→ETH", pair="Multi-hop", size="2 ETH", profit=45.50),
    ExecutionRow(id="ARB-10233", route="Buy on Uni → Sell on Curve", pair="WBTC/ETH", size="0.5 WBTC", profit=32.10),
]


@app.get("/test")
def test() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/api/prices", response_model=List[PriceRow])
def get_prices() -> List[PriceRow]:
    rows: List[PriceRow] = []
    for row in BASE_PRICES:
        jitter = lambda v: round(v * (1 + random.uniform(-0.001, 0.001)), 6)
        rows.append(
            PriceRow(
                pair=row.pair,
                uni=jitter(row.uni),
                sushi=jitter(row.sushi),
                curve=jitter(row.curve),
            )
        )
    return rows


@app.get("/api/executions", response_model=List[ExecutionRow])
def get_executions() -> List[ExecutionRow]:
    # Randomly add a synthetic execution
    execs = list(BASE_EXECS)
    if random.random() < 0.3:
        nid = 10234 + random.randint(0, 999)
        profit = round(random.uniform(8.0, 95.0), 2)
        route = random.choice([
            "Buy on Uni → Sell on Curve",
            "Sushi → Curve",
            "ETH→USDC→DAI→WBTC→ETH",
            "Curve → Uni",
        ])
        pair = random.choice(["ETH/USDC", "WBTC/ETH", "DAI/USDC", "Multi-hop"])
        size = random.choice(["1 ETH", "2 ETH", "0.5 WBTC", "5 ETH", "20k USDC"]).strip()
        execs.insert(0, ExecutionRow(id=f"ARB-{nid}", route=route, pair=pair, size=size, profit=profit))
    return execs[:10]


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            prices = [r.model_dump() for r in get_prices()]
            executions = [e.model_dump() for e in get_executions()]
            payload = {"type": "snapshot", "prices": prices, "executions": executions}
            await ws.send_json(payload)
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return
