"""Execute the guided analysis and save outputs only after every cell succeeds.

Install with: python -m pip install -e '.[notebook]'
PNG chart export requires Chrome or Chromium (used by Kaleido).
"""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/01_business_analysis.ipynb"


def main():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count and cell.outputs for cell in cells)
    assert not any(output.output_type == "error" for cell in cells for output in cell.outputs)
    charts = sum("image/png" in output.get("data", {}) for cell in cells for output in cell.outputs)
    assert charts == 2, "Both charts must have embedded PNG output for GitHub."
    nbformat.validate(notebook)
    nbformat.write(notebook, NOTEBOOK)
    print(f"Saved {len(cells)} executed cells and {charts} embedded charts: {NOTEBOOK.name}")


if __name__ == "__main__":
    main()
