from celery import Celery
from celery.schedules import crontab

from src.cache import ttl as ttl_constants
from src.core.config import settings
from src.core.logging import structlog

logger = structlog.get_logger()

celery_app = Celery(
    "crypto_api",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.ingestion.scheduler",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,
    task_soft_time_limit=25,
)


@celery_app.task(name="ingestion.fetch_defillama_data")
def fetch_defillama_data() -> dict:
    import asyncio
    from src.ingestion.providers import defillama

    async def _fetch():
        try:
            tvl_data = await defillama.get_tvl_data()
            logger.info("defillama_fetch_completed", networks=len(tvl_data))
            return {"status": "success", "networks": len(tvl_data), "data": tvl_data}
        except Exception as e:
            logger.error("defillama_fetch_failed", error=str(e))
            return {"status": "error", "error": str(e)}

    return asyncio.run(_fetch())


@celery_app.task(name="ingestion.fetch_coingecko_data")
def fetch_coingecko_data() -> dict:
    import asyncio
    from src.ingestion.providers import coingecko

    async def _fetch():
        try:
            networks = ["ethereum", "solana", "polygon", "arbitrum", "base", "optimism", "avalanche", "bsc"]
            data = await coingecko.get_network_data(networks)
            logger.info("coingecko_fetch_completed", networks=len(data))
            return {"status": "success", "networks": len(data), "data": data}
        except Exception as e:
            logger.error("coingecko_fetch_failed", error=str(e))
            return {"status": "error", "error": str(e)}

    return asyncio.run(_fetch())


@celery_app.task(name="ingestion.fetch_gas_prices")
def fetch_gas_prices() -> dict:
    import asyncio
    from src.ingestion.providers import coingecko

    async def _fetch():
        try:
            gas_data = await coingecko.get_gas_prices()
            logger.info("gas_fetch_completed")
            return {"status": "success", "data": gas_data}
        except Exception as e:
            logger.error("gas_fetch_failed", error=str(e))
            return {"status": "error", "error": str(e)}

    return asyncio.run(_fetch())


@celery_app.task(name="ingestion.update_network_scores")
def update_network_scores() -> dict:
    import asyncio
    from src.scoring.engine import calculate_all_scores

    async def _update():
        try:
            scores = await calculate_all_scores()
            logger.info("scores_updated", networks=len(scores))
            return {"status": "success", "networks": len(scores)}
        except Exception as e:
            logger.error("scores_update_failed", error=str(e))
            return {"status": "error", "error": str(e)}

    return asyncio.run(_update())


@celery_app.task(name="ingestion.fetch_alerts")
def fetch_alerts() -> dict:
    logger.info("alerts_fetch_completed")
    return {"status": "success", "alerts": []}


celery_app.conf.beat_schedule = {
    "fetch-defillama-every-300s": {
        "task": "ingestion.fetch_defillama_data",
        "schedule": ttl_constants.TTL_TVL,
    },
    "fetch-coingecko-every-60s": {
        "task": "ingestion.fetch_coingecko_data",
        "schedule": ttl_constants.TTL_NETWORK_SCORE,
    },
    "fetch-gas-every-15s": {
        "task": "ingestion.fetch_gas_prices",
        "schedule": ttl_constants.TTL_GAS_CURRENT,
    },
    "update-scores-every-60s": {
        "task": "ingestion.update_network_scores",
        "schedule": ttl_constants.TTL_NETWORK_SCORE,
    },
    "fetch-alerts-every-30s": {
        "task": "ingestion.fetch_alerts",
        "schedule": ttl_constants.TTL_INCIDENTS,
    },
}
