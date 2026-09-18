"""Browser lifecycle. One fresh Chromium context per run (clean cookies/storage = deterministic journeys).

This class is the platform adapter boundary: a future MobileAdapter would expose the same
start / observe / execute / screenshot / audit / close surface.
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from backend.config import settings
from backend.runtime import accessibility, executor, observer
from backend.runtime.executor import ActionResult
from backend.runtime.observer import ElementRegistry
from backend.schemas import AxeViolation, BrowserAction, Observation


class BrowserSession:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None
        self.registry: ElementRegistry | None = None
        self._shot_counter = 0

    async def start(self, url: str) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=settings.headless)
        self._context = await self._browser.new_context(
            viewport={"width": settings.viewport_width, "height": settings.viewport_height},
            locale="en-IN",
        )
        await self._context.add_init_script(path=str(settings.axe_path))
        self.page = await self._context.new_page()
        await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await executor.settle(self.page)

    async def observe(self) -> Observation:
        # Any previous registry expires here: its handles must not be reused.
        if self.registry:
            for h in self.registry.handles.values():
                await h.dispose()
        obs, self.registry = await observer.observe(self.page, settings.max_elements)
        obs.screenshot_id = await self.screenshot()
        return obs

    async def screenshot(self) -> str:
        self._shot_counter += 1
        name = f"step_{self._shot_counter:02d}.jpg"
        await self.page.screenshot(path=str(self.run_dir / name), type="jpeg", quality=62, full_page=False)
        return name

    async def execute(self, action: BrowserAction) -> ActionResult:
        return await executor.execute(self.page, self.registry, action, settings.action_timeout_ms)

    async def audit(self, final: bool = False) -> list[AxeViolation]:
        return await accessibility.run_axe(self.page, final=final)

    async def close(self) -> None:
        for closer in (self._context, self._browser):
            if closer:
                try:
                    await closer.close()
                except Exception:
                    pass  # best-effort teardown; the run result is already recorded
        if self._pw:
            await self._pw.stop()
