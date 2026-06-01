"""Re-export shim — keeps ``from talktrace_ai.utils.intercoder import ...`` working.

The actual implementation lives in:
  - intercoder_parse.py   (report parsing: docx / xlsx / html → DataFrame)
  - intercoder_metrics.py (agreement statistics: κ, α, AC1, …)
  - intercoder_export.py  (result export: xlsx / csv / json / html / docx / pdf)
"""
from .intercoder_parse import parse_report_impulses  # noqa: F401
from .intercoder_metrics import (  # noqa: F401
    compute_intercoder_agreement,
    compute_intercoder_agreement_multi,
    p_value_stars,
)
from .intercoder_export import (  # noqa: F401
    export_testing_agreement,
    export_testing_agreement_any,
    export_testing_agreement_csv_zip,
    export_testing_agreement_json,
    export_testing_agreement_html,
    export_testing_agreement_docx,
    export_testing_agreement_pdf,
)

__all__ = [
    "parse_report_impulses",
    "compute_intercoder_agreement",
    "compute_intercoder_agreement_multi",
    "p_value_stars",
    "export_testing_agreement",
    "export_testing_agreement_any",
    "export_testing_agreement_csv_zip",
    "export_testing_agreement_json",
    "export_testing_agreement_html",
    "export_testing_agreement_docx",
    "export_testing_agreement_pdf",
]
