.PHONY: install build app test
install:
	python -m pip install -r requirements-lock.txt
	python -m pip install -e . --no-deps
build:
	python -m retailsignal.cli build
app:
	python -m streamlit run app.py
test:
	python -m pytest -q
