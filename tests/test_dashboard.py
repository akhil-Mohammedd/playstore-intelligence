from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_smoke_without_crashing():
    app = Path(__file__).resolve().parents[1] / "app.py"
    result = AppTest.from_file(str(app), default_timeout=60).run()
    assert not result.exception
    assert result.title[0].value == "PlayStore Intelligence"
