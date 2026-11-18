from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("page", ["Revenue overview", "Customer retention", "Decision lab", "Model evidence", "Data trust", "Analyst desk"])
def test_dashboard_pages(page):
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.radio[0].set_value(page).run()
    assert not app.exception


def test_country_filter_changes_metrics():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    all_net = app.metric[0].value
    app.multiselect[0].set_value(["France"]).run()
    assert not app.exception
    assert app.metric[0].value != all_net


def test_scenario_reacts_to_cost():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.radio[0].set_value("Decision lab").run()
    initial = app.metric[2].value
    app.number_input[1].set_value(2.0).run()
    assert not app.exception
    assert app.metric[2].value != initial


def test_retention_shortcut_and_return_navigation():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.radio[0].value == "Customer retention"
    app.radio[0].set_value("Revenue overview").run()
    assert not app.exception
    assert app.metric[0].value == "£9.75m"


def test_empty_reporting_day_and_single_market():
    from datetime import date
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.date_input[0].set_value((date(2010, 12, 25), date(2010, 12, 25))).run()
    assert not app.exception
    assert "No transactions" in app.info[0].value
    app.date_input[0].set_value((date(2010, 12, 1), date(2011, 12, 9))).run()
    app.multiselect[0].set_value(["EIRE"]).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
