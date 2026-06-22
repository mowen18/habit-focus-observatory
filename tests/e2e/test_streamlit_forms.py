from __future__ import annotations
 
import socket
import subprocess
import time
from datetime import date
 
import pytest
from playwright.sync_api import Page, expect
 
 
APP_PATH = "app/streamlit_app.py"
HOST = "localhost"
PORT = 8501
BASE_URL = f"http://{HOST}:{PORT}"
 
 
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
 
    # Streamlit exposes each widget's label text as the input's aria-label,
    # so get_by_label targets them. The morning form's "Check-in date"
    # defaults to today, so we don't need to touch it here.
    page.get_by_label("Sleep hours").fill("7.5")
    page.get_by_label("Sleep quality (1-10)").fill("8")
    page.get_by_label("Energy rating (1-10)").fill("7")
    page.get_by_label("Focus rating (1-10)").fill("8")
    page.get_by_label("Mood rating (1-10)").fill("7")
    page.get_by_label("Stress rating (1-10)").fill("4")
    page.get_by_label("Notes").fill("Playwright smoke test entry.")
 
    page.get_by_role("button", name="Save today's morning check-in").click()
 
    # st.form_submit_button triggers a rerun; expect() auto-waits for the
    # success alert that save_morning_checkin produces on the happy path.
    today = date.today().isoformat()
    expect(
        page.get_by_text(f"Saved today's morning check-in for {today}.")
    ).to_be_visible(timeout=15_000)
 