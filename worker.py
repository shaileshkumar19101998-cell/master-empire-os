import asyncio, logging, sqlite3
from pipeline_orchestrator import execute_full_pipeline_cycle

logger = logging.getLogger("autonomous_worker")
_worker_running = False
_worker_task = None

async def run_autonomous_business_worker(interval_seconds: int = 60):
    global _worker_running
    _worker_running = True
    logger.info("=== SINGLE AUTONOMOUS SUPERVISOR WORKER STARTED ===")
    try:
        while _worker_running:
            try:
                results = await asyncio.to_thread(execute_full_pipeline_cycle)
                logger.info(f"Autonomous pipeline cycle finished: {len(results)} items verified.")
            except Exception as e:
                logger.error(f"Pipeline worker cycle error: {e}")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Autonomous worker received cancellation signal. Clean shutdown.")
    finally:
        _worker_running = False

def start_worker_supervisor(interval: int = 60):
    global _worker_task
    if _worker_task is None or _worker_task.done():
        loop = asyncio.get_event_loop()
        _worker_task = loop.create_task(run_autonomous_business_worker(interval))
    return _worker_task

async def stop_worker_supervisor():
    global _worker_running, _worker_task
    _worker_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
