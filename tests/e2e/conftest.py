import os

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from helpers import BASE_URL, MAILPIT_URL

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://34.171.152.81:4444/wd/hub")


@pytest.fixture(scope="session", autouse=True)
def stack_is_up():
    """Fail fast with a clear message instead of 40 browser timeouts."""
    for name, url in [("app", f"{BASE_URL}/api/v1/health/"), ("mailpit", f"{MAILPIT_URL}/livez")]:
        try:
            assert requests.get(url, timeout=10).status_code == 200
        except Exception as exc:  # noqa: BLE001
            pytest.exit(f"{name} is not reachable at {url}: {exc}. Start the stack first (make up).", returncode=2)


@pytest.fixture
def driver(request):
    options = Options()
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--lang=en-GB")
    browser = webdriver.Remote(command_executor=SELENIUM_URL, options=options)
    browser.implicitly_wait(2)
    yield browser
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        try:
            browser.save_screenshot(f"/results/{request.node.name}.png")
        except Exception:  # noqa: BLE001
            pass
    browser.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())


@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 20)
