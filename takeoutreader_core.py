# ============================================
# takeoutreader_core.py — WRAPPER DE COMPATIBILITE
# ============================================
# Ce fichier permet a takeoutreader_gui.py de continuer
# a fonctionner avec "import takeoutreader_core" sans modification.
# Toute la logique est dans le package takeoutreader/core/.
# ============================================

# Re-export tout ce que la GUI ou d'autres scripts utilisent
from takeoutreader.core.constants import *
from takeoutreader.core.sanitizer import sanitize_text, decode_hdr
from takeoutreader.core.detection import find_mbox_auto, find_mbox_in_zip, resolve_inputs, parse_args
from takeoutreader.core.parser import (
    get_date, extract_body_text, extract_pj_list, parse_gmail_labels,
    categorize_mail, parse_mbox, parse_eml_folder, parse_multi_sources,
    _build_mail_dict, _find_all_eml,
)
from takeoutreader.core.extractor import extract_pj_to_disk
from takeoutreader.core.renderer import generate_output
from takeoutreader.core.validator import validate_output
from takeoutreader.__main__ import main
