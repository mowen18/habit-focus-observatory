from __future__ import annotations
 
import socket
import subprocess
import time
from datetime import date
 
import pytest
from playwright.sync_api import Locator, Page, expect
 
 
APP_PATH = "app/streamlit_app.py"
HOST = "localhost"
PORT = 8501
BASE_URL = f"http://{HOST}:{PORT}"


def get_streamlit_number_input(page: Page, form: Locator, label: str) -> Locator:
    """Return one number input from its labeled Streamlit widget container."""
    widget = form.locator('[data-testid="stNumberInput"]').filter(
        has=page.get_by_text(label, exact=True)
    )
    return widget.get_by_role("spinbutton")
 
 
def _port_open(host: str, port: int) -> bool:
    """Return True when something is already listening on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0
 
 
@pytest.fixture(scope="session", autouse=True)
def streamlit_server():
    """Start the Streamlit app once per session, unless one is already up."""
    if _port_open(HOST, PORT):
        # A dev server is already running; leave its lifecycle alone.
        yield
        return
 
    process = subprocess.Popen(
        [
            "streamlit", "run", APP_PATH,
            "--server.port", str(PORT),
            "--server.headless", "true",
        ]
    )
    for _ in range(30):  # wait up to ~30s for the port to open
        if _port_open(HOST, PORT):
            break
        time.sleep(1)
    else:
        process.terminate()
        raise RuntimeError("Streamlit server did not start in time.")
 
    yield
    process.terminate()
    process.wait()
 
 
def test_app_loads_with_all_form_sections(page: Page):
    """The single-page app renders its title and all four logging sections."""
    page.goto(BASE_URL)
 
    expect(page.get_by_role("heading", name="Habit Focus Observatory")).to_be_visible()
    expect(page.get_by_text("1. Today Morning Check-in")).to_be_visible()
    expect(page.get_by_text("2. Yesterday Deep Work")).to_be_visible()
    expect(page.get_by_text("3. Yesterday Caffeine Summary")).to_be_visible()
    expect(page.get_by_text("4. Yesterday Exercise")).to_be_visible()
 
 
def test_morning_checkin_saves_successfully(page: Page):
    """Filling and submitting the morning check-in shows a success message."""
    page.goto(BASE_URL)

    expect(
        page.get_by_role(
            "heading",
            name="Habit Focus Observatory",
            exact=True,
        )
    ).to_be_visible()
    expect(
        page.get_by_role(
            "heading",
            name="1. Today Morning Check-in",
            exact=True,
        )
    ).to_be_visible()

    morning_form = page.locator('[data-testid="stForm"]').filter(
        has=page.get_by_text("Sleep hours", exact=True)
    )
    expect(morning_form).to_be_visible()

    number_input_values = {
        "Sleep hours": "7.5",
        "Sleep quality (1-10)": "8",
        "Energy rating (1-10)": "7",
        "Focus rating (1-10)": "8",
        "Mood rating (1-10)": "7",
        "Stress rating (1-10)": "4",
    }
    for label, value in number_input_values.items():
        get_streamlit_number_input(page, morning_form, label).fill(value)

    notes = (
        morning_form.locator('[data-testid="stTextArea"]')
        .filter(has=page.get_by_text("Notes", exact=True))
        .get_by_role("textbox")
    )
    notes.fill("Playwright smoke test entry.")

    submit_button = morning_form.locator(
        '[data-testid="stFormSubmitButton"]'
    ).get_by_role(
        "button",
        name="Save today's morning check-in",
        exact=True,
    )
    submit_button.click()

    today = date.today().isoformat()
    success_message = f"Saved today's morning check-in for {today}."
    success_alert = page.locator('[data-testid="stAlert"]').filter(
        has=page.get_by_text(success_message, exact=True)
    )
    expect(success_alert).to_be_visible(timeout=15_000)
