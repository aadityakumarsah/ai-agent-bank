"""In-process DCA scheduler.

Runs as a background asyncio task: every ``DCA_SCAN_INTERVAL_S`` seconds it
pulls due DCA plans and executes them through ``dca_service.execute_due_plans``.

Single-process design (the deployment runs one web worker / one event loop).
The task is idempotent per-cycle via each plan's stable ``idempotency_key`` and
``next_run_at`` advancing on success or failure, so a restart can never
double-pay a cycle.
"""

import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.dca_service import dca_service

logger = logging.getLogger("app.dca-scheduler")


class DcaScheduler:
    def __init__(self, interval_s: int | None = None) -> None:
        self.interval_s = interval_s or settings.DCA_SCAN_INTERVAL_S
        self._task: asyncio.Task | None = None
        self._should_stop = False

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._should_stop = False
        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(self._on_task_done)

    async def stop(self) -> None:
        self._should_stop = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _on_task_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("DCA scheduler task crashed: %s", exc)

    async def _run(self) -> None:
        logger.info("DCA scheduler started (interval=%ss)", self.interval_s)
        while not self._should_stop:
            try:
                summary = await asyncio.to_thread(self._run_once)
                if summary and summary.get("plans_checked"):
                    logger.info("DCA scan summary: %s", summary)
            except Exception as e:
                logger.exception("DCA scheduler cycle failed: %s", e)
            await asyncio.sleep(self.interval_s)
        logger.info("DCA scheduler stopped")

    def _run_once(self) -> dict:
        db = SessionLocal()
        try:
            return dca_service.execute_due_plans(db)
        finally:
            db.close()


dca_scheduler = DcaScheduler()