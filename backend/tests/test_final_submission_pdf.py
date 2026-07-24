from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter


def _write_blank_pdf(path: Path, page_count: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


def _write_png(path: Path, size=(40, 30)) -> None:
    Image.new("RGB", size, color=(20, 40, 60)).save(path)


def test_produce_final_submission_pdfs_order(tmp_path: Path):
    from fatina_paths import produce_final_submission_pdfs

    item = tmp_path / "40.01.001"
    calc_dir = item / "20_1"
    invoice_dir = item / "05_m"
    calc_dir.mkdir(parents=True)
    invoice_dir.mkdir(parents=True)

    _write_blank_pdf(item / "40.01.001.pdf", page_count=2)
    _write_blank_pdf(calc_dir / "drawing_b.pdf", page_count=1)
    _write_blank_pdf(calc_dir / "drawing_a.pdf", page_count=1)
    _write_png(calc_dir / "drawing_c.png")
    _write_blank_pdf(invoice_dir / "invoice.pdf", page_count=1)
    _write_png(invoice_dir / "photo.png")
    # Should be ignored as an input if re-run leftover exists
    _write_blank_pdf(item / "40.01.001_final.pdf", page_count=9)

    empty = tmp_path / "empty_item"
    empty.mkdir()

    result = produce_final_submission_pdfs(base_dir=tmp_path)

    assert result["produced_count"] == 1
    assert result["skipped_count"] == 1
    assert result["errors"] == []

    out = item / "40.01.001_final.pdf"
    assert out.is_file()
    reader = PdfReader(str(out))
    # conc(2) + invoice.pdf(1) + photo.png(1) + drawing_a(1) + drawing_b(1) + drawing_c.png(1)
    assert len(reader.pages) == 7


def test_produce_final_submission_skips_missing_fatina(tmp_path: Path):
    from fatina_paths import produce_final_submission_pdfs

    missing = tmp_path / "no_such_fatina"
    result = produce_final_submission_pdfs(base_dir=missing)
    assert result["produced_count"] == 0
    assert result["errors"]
