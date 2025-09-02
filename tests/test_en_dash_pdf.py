import io
from pathlib import Path
import sys

from pdfminer.high_level import extract_text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from document_generator import make_brief_pdf


def test_make_brief_pdf_handles_en_dash():
    analyzer = {
        "scenes": [
            {
                "start_s": 0,
                "end_s": 1,
                "shot_type": "",
                "framing": "",
                "action": "",
                "dialogue": "",
                "on_screen_text": "",
                "screenshot_path": "",
            }
        ]
    }

    pdf_bytes = make_brief_pdf(analyzer=analyzer, script={}, product_facts={})

    text = extract_text(io.BytesIO(pdf_bytes))

    assert "0.00–1.00" in text
