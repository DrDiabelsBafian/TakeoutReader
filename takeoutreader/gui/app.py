# ============================================
# takeoutreader_gui.py -- GUI v9 (Dark Violet + Matrix Deco)
# CustomTkinter | Dark + Violet/Teal accents
# Python 3.14 compatible | Deps: customtkinter, Pillow
# ============================================
# V9 -- Audit fixes + visual polish
#   + Cream text palette (#F5F0E8) instead of cold lavender
#   + Colored dots (CTkFrame 12x12) in badges — always render in color
#   + Accent bar height=40 (DPI-safe)
#   + Hover propagated to all card children
#   + Dead code cleanup
#   + Reduced badge padding for 125% DPI safety
#   + Logo from PNG file (no base64)
# V8 -- Refonte compacte dark+violet, 3 surfaces, CTA 3D
# V7 -- Dark+violet, watermarks, pitch encart
# ============================================

import os
import sys
import threading
import queue
import re

# --- DPI fix (AVANT toute fenetre) ---
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import customtkinter as ctk
from customtkinter import CTkImage
from tkinter import filedialog
from PIL import Image, ImageDraw

# ============================================
# BADGE ICON GENERATOR (Pillow, 16x16 RGBA)
# ============================================
def _make_lock_icon(color):
    """Draw a padlock icon."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    # Shackle (arc on top)
    d.arc([8, 2, 24, 18], 0, 360, fill=(*c, 255), width=3)
    # Body (rounded rect)
    d.rounded_rectangle([6, 14, 26, 28], radius=3, fill=(*c, 255))
    # Keyhole
    d.ellipse([14, 18, 18, 22], fill=(0, 0, 0, 180))
    return img.resize((16, 16), Image.LANCZOS)


def _make_shield_icon(color):
    """Draw a shield icon."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    # Shield shape
    d.polygon([16, 2, 28, 8, 26, 22, 16, 30, 6, 22, 4, 8], fill=(*c, 255))
    # Check mark inside
    d.line([10, 16, 14, 21, 22, 10], fill=(0, 0, 0, 180), width=2)
    return img.resize((16, 16), Image.LANCZOS)


def _make_star_icon(color):
    """Draw a 5-pointed star icon."""
    import math
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    cx, cy, r = 16, 16, 14
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    d.polygon(pts, fill=(*c, 255))
    return img.resize((16, 16), Image.LANCZOS)


def _make_inbox_icon(color):
    """Draw an inbox/download tray icon."""
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    # Arrow down
    d.polygon([24, 32, 16, 22, 20, 22, 20, 8, 28, 8, 28, 22, 32, 22],
              fill=(*c, 255))
    # Tray
    d.rounded_rectangle([6, 30, 42, 42], radius=4, fill=(*c, 255))
    return img.resize((24, 24), Image.LANCZOS)


def _make_envelope_icon(color):
    """Draw an envelope icon."""
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    # Envelope body
    d.rounded_rectangle([4, 12, 44, 38], radius=4, fill=(*c, 255))
    # Flap
    d.polygon([4, 12, 24, 28, 44, 12], fill=(*c, 180))
    d.line([4, 12, 24, 28, 44, 12], fill=(*c, 120), width=2)
    return img.resize((24, 24), Image.LANCZOS)


# ============================================
# PALETTE V9 - DARK VIOLET + CREAM TEXT
# ============================================
# Surfaces
BG_DEEP       = "#0F0E17"
BG_CARD       = "#181627"
BG_ELEVATED   = "#201E30"

# Bordures
BORDER_DIM    = "#2A2740"
BORDER_GLOW   = "#3D3660"
BORDER_ACTIVE = "#534AB7"

# Accents
VIOLET        = "#534AB7"
VIOLET_HOVER  = "#6358C4"
VIOLET_LIGHT  = "#D4D0F8"
VIOLET_SOFT   = "#7C6DAA"
TEAL          = "#5DCAA5"
GOLD          = "#E8B84A"

# Texte -- CREAM (v9: warm instead of cold lavender)
TEXT_HI       = "#F5F0E8"
TEXT_MID      = "#C4B9A8"
TEXT_LO       = "#7A7068"
TEXT_SUCCESS  = "#5DCAA5"
TEXT_ERROR    = "#E24B4A"

# ============================================
# TYPOGRAPHIE V9 - bumped +2px
# 22 / 16 / 15 / 13 / 11
# ============================================
FONT_TITLE      = ("Segoe UI", 22, "bold")
FONT_BTN        = ("Segoe UI", 16, "bold")
FONT_CARD_TITLE = ("Segoe UI", 15, "bold")
FONT_BODY       = ("Segoe UI", 15)
FONT_SUBTITLE   = ("Segoe UI", 13)
FONT_SECTION    = ("Segoe UI", 13, "bold")
FONT_BADGE      = ("Segoe UI", 14, "bold")
FONT_PITCH      = ("Segoe UI", 13)
FONT_PITCH_B    = ("Segoe UI", 13, "bold")
FONT_CARD_DESC  = ("Segoe UI", 13)
FONT_BODY_SM    = ("Segoe UI", 13)
FONT_FOOTER     = ("Segoe UI", 11)
FONT_CREDIT     = ("Segoe UI", 9)
FONT_LOG        = ("Consolas", 10)

# ============================================
# DIMENSIONS
# ============================================
WIN_W = 640
WIN_H = 540

# ============================================
# LOGO: fichier PNG a cote du script/exe
# ============================================
LOGO_FILE = "takeoutreader_logo.png"


# ============================================
# PATH RESOLUTION (Nuitka + Dev)
# ============================================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ============================================
# QUEUE WRITER (redirect stdout/stderr)
# ============================================
class QueueWriter:
    def __init__(self, q, original):
        self._q = q
        self._orig = original

    def write(self, text):
        if text and text.strip():
            self._q.put(text)
        try:
            self._orig.write(text)
        except Exception:
            pass

    def flush(self):
        try:
            self._orig.flush()
        except Exception:
            pass


# ============================================
# APPLICATION PRINCIPALE
# ============================================
class TakeoutReaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TakeoutReader")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(WIN_W, WIN_H)
        self.resizable(False, False)
        self.configure(fg_color=BG_DEEP)

        # --- Icon + base path ---
        base = get_base_dir()
        try:
            ico = os.path.join(base, "takeoutreader.ico")
            if os.path.isfile(ico):
                self.iconbitmap(ico)
        except Exception:
            pass

        # --- State ---
        self._selected_files = []
        self._selected_mode = None
        self._running = False
        self._log_queue = queue.Queue()

        # --- Logo image (charge depuis fichier PNG) ---
        self._logo_img = None
        try:
            logo_path = os.path.join(base, LOGO_FILE)
            if os.path.isfile(logo_path):
                pil = Image.open(logo_path).convert("RGBA")
                self._logo_img = CTkImage(light_image=pil,
                                          dark_image=pil,
                                          size=(52, 52))
        except Exception:
            pass

        self._build_ui()
        self.after(100, self._poll_queue)

    # ================================================
    # BUILD UI
    # ================================================
    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color=BG_DEEP)
        main.pack(fill="both", expand=True, padx=18, pady=14)

        # ---- HEADER ----
        header = ctk.CTkFrame(main, fg_color=BG_CARD,
                              corner_radius=14,
                              border_width=1, border_color=BORDER_DIM)
        header.pack(fill="x")

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(padx=18, pady=(14, 12), fill="x")

        # Top row: logo + title
        top = ctk.CTkFrame(h_inner, fg_color="transparent")
        top.pack(fill="x")

        if self._logo_img:
            ctk.CTkLabel(top, image=self._logo_img, text="",
                         fg_color="transparent"
                         ).pack(side="left", padx=(0, 12))

        tcol = ctk.CTkFrame(top, fg_color="transparent")
        tcol.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(tcol, text="TakeoutReader",
                     font=FONT_TITLE, text_color=TEXT_HI
                     ).pack(anchor="w")
        ctk.CTkLabel(tcol, text="Gmail Takeout \u2192 HTML offline archive",
                     font=FONT_SUBTITLE, text_color=TEXT_MID
                     ).pack(anchor="w", pady=(1, 0))

        # Badge pills (Pillow-drawn icons — always colored)
        badge_row = ctk.CTkFrame(h_inner, fg_color="transparent")
        badge_row.pack(fill="x", pady=(8, 0))
        badge_icons = [
            ("100% Offline", _make_lock_icon(VIOLET_LIGHT)),
            ("Vie privee", _make_shield_icon(TEAL)),
            ("Open source", _make_star_icon(GOLD)),
        ]
        self._badge_imgs = []  # prevent GC
        for label, icon_img in badge_icons:
            cimg = CTkImage(light_image=icon_img,
                            dark_image=icon_img, size=(16, 16))
            self._badge_imgs.append(cimg)
            pill = ctk.CTkFrame(badge_row, fg_color=BG_ELEVATED,
                                corner_radius=8,
                                border_width=1, border_color=BORDER_GLOW)
            pill.pack(side="left", padx=(0, 6))
            inner_pill = ctk.CTkFrame(pill, fg_color="transparent")
            inner_pill.pack(padx=8, pady=5)
            ctk.CTkLabel(inner_pill, image=cimg, text="",
                         fg_color="transparent"
                         ).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(inner_pill, text=label,
                         font=FONT_BADGE,
                         text_color=TEXT_HI
                         ).pack(side="left")

        # Pitch (accent bar = natural height, no fixed px)
        pitch = ctk.CTkFrame(h_inner, fg_color="transparent")
        pitch.pack(fill="x", pady=(8, 0))

        accent = ctk.CTkFrame(pitch, fg_color=VIOLET,
                              width=3, height=44, corner_radius=2)
        accent.pack(side="left")
        accent.pack_propagate(False)

        ptxt = ctk.CTkFrame(pitch, fg_color="transparent")
        ptxt.pack(side="left", fill="x", padx=(10, 0))

        p1 = ctk.CTkFrame(ptxt, fg_color="transparent")
        p1.pack(fill="x")
        ctk.CTkLabel(p1, text="Google Takeout exporte vos mails en ",
                     font=FONT_PITCH, text_color=TEXT_MID
                     ).pack(side="left")
        ctk.CTkLabel(p1, text=".mbox",
                     font=FONT_PITCH_B, text_color=VIOLET_LIGHT
                     ).pack(side="left")
        ctk.CTkLabel(p1, text=" (illisible).",
                     font=FONT_PITCH, text_color=TEXT_MID
                     ).pack(side="left")

        p2 = ctk.CTkFrame(ptxt, fg_color="transparent")
        p2.pack(fill="x")
        ctk.CTkLabel(p2, text="TakeoutReader les convertit en ",
                     font=FONT_PITCH, text_color=TEXT_MID
                     ).pack(side="left")
        ctk.CTkLabel(p2, text="pages HTML navigables",
                     font=FONT_PITCH_B, text_color=TEAL
                     ).pack(side="left")
        ctk.CTkLabel(p2, text=" \u2014 sans connexion.",
                     font=FONT_PITCH, text_color=TEXT_MID
                     ).pack(side="left")

        # ---- SOURCE SECTION ----
        ctk.CTkLabel(main, text="CHOISIR VOTRE SOURCE",
                     font=FONT_SECTION, text_color=TEXT_LO
                     ).pack(anchor="w", padx=2, pady=(14, 8))

        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.pack(fill="x")
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        self._card_mbox_icon = CTkImage(
            light_image=_make_inbox_icon("#D4D0F8"),
            dark_image=_make_inbox_icon("#D4D0F8"), size=(24, 24))
        self._card_eml_icon = CTkImage(
            light_image=_make_envelope_icon("#D4D0F8"),
            dark_image=_make_envelope_icon("#D4D0F8"), size=(24, 24))

        self._card_mbox = self._make_card(
            cards, 0, 0, (0, 5),
            self._card_mbox_icon,
            "Fichier .mbox / .zip",
            "Export Google Takeout"
        )
        self._card_eml = self._make_card(
            cards, 0, 1, (5, 0),
            self._card_eml_icon,
            "Dossier .eml",
            "Dossier de fichiers .eml"
        )
        self._bind_card(self._card_mbox, self._select_mbox)
        self._bind_card(self._card_eml, self._select_eml)

        # Selection display
        self._sel_label = ctk.CTkLabel(
            main, text="", font=FONT_BODY_SM, text_color=TEXT_LO
        )
        self._sel_label.pack(anchor="w", padx=2, pady=(6, 0))

        # Help
        ctk.CTkLabel(main,
                     text="\u24d8  Pas encore d'export ? google.com/takeout",
                     font=FONT_FOOTER, text_color=TEXT_LO
                     ).pack(anchor="w", padx=2, pady=(4, 8))

        # ---- CTA BUTTON (3D effect) ----
        self._cta_btn = ctk.CTkButton(
            main,
            text="\u25b6   Lancer la conversion",
            font=FONT_BTN,
            fg_color=VIOLET,
            text_color=TEXT_HI,
            hover_color=VIOLET_HOVER,
            corner_radius=12,
            border_width=2,
            border_color=VIOLET_LIGHT,
            height=46,
            command=self._start_conversion
        )
        self._cta_btn.pack(fill="x", padx=2, pady=(0, 8))

        # ---- PROGRESS (hidden) ----
        self._pf = ctk.CTkFrame(
            main, fg_color=BG_CARD,
            corner_radius=12,
            border_width=1, border_color=BORDER_DIM
        )

        pf_inner = ctk.CTkFrame(self._pf, fg_color="transparent")
        pf_inner.pack(fill="x", padx=16, pady=12)

        self._status = ctk.CTkLabel(
            pf_inner, text="En attente...",
            font=FONT_BODY, text_color=TEXT_MID, anchor="w"
        )
        self._status.pack(anchor="w")

        self._pbar = ctk.CTkProgressBar(
            pf_inner, height=8,
            fg_color=BORDER_DIM, progress_color=VIOLET,
            corner_radius=4
        )
        self._pbar.pack(fill="x", pady=(6, 4))
        self._pbar.set(0)

        self._phase = ctk.CTkLabel(
            pf_inner, text="",
            font=FONT_BODY_SM, text_color=TEXT_LO, anchor="w"
        )
        self._phase.pack(anchor="w")

        # ---- LOG (hidden) ----
        self._log = ctk.CTkTextbox(
            main, height=120,
            font=FONT_LOG,
            fg_color=BG_CARD, text_color=TEXT_MID,
            corner_radius=10,
            border_width=1, border_color=BORDER_DIM,
            state="disabled"
        )

        # ---- FOOTER ----
        self._footer = ctk.CTkFrame(main, fg_color="transparent")
        self._footer.pack(side="bottom", pady=(4, 0))
        ctk.CTkLabel(self._footer,
            text=(
                "TakeoutReader v1.0.0 \u00b7 MIT License"
                " \u00b7 100% offline, zero serveur"
            ),
            font=FONT_FOOTER, text_color=TEXT_LO
        ).pack()
        ctk.CTkLabel(self._footer,
            text="by Dr. Diabels Bafian",
            font=FONT_CREDIT, text_color=TEXT_LO
        ).pack(pady=(2, 0))

    # ================================================
    # CARD FACTORY
    # ================================================
    def _make_card(self, parent, row, col, padx, icon_img,
                   title, desc):
        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD,
            corner_radius=12,
            border_width=1, border_color=BORDER_DIM,
            cursor="hand2"
        )
        card.grid(row=row, column=col, padx=padx, sticky="nsew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=14, pady=14, fill="both", expand=True)

        row_f = ctk.CTkFrame(inner, fg_color="transparent")
        row_f.pack(fill="x")

        # Icon box with Pillow-drawn CTkImage
        ic = ctk.CTkFrame(row_f, fg_color=VIOLET,
                          corner_radius=10, width=48, height=48)
        ic.pack(side="left")
        ic.pack_propagate(False)
        ctk.CTkLabel(ic, image=icon_img, text="",
                     fg_color="transparent"
                     ).place(relx=0.5, rely=0.5, anchor="center")

        tcol = ctk.CTkFrame(row_f, fg_color="transparent")
        tcol.pack(side="left", fill="x", padx=(12, 0))
        ctk.CTkLabel(tcol, text=title,
                     font=FONT_CARD_TITLE, text_color=TEXT_HI
                     ).pack(anchor="w")
        ctk.CTkLabel(tcol, text=desc,
                     font=FONT_CARD_DESC, text_color=TEXT_LO
                     ).pack(anchor="w", pady=(2, 0))

        # Hover — propagated to ALL children (fix P3)
        def on_enter(e):
            card.configure(border_color=VIOLET_SOFT, fg_color=BG_ELEVATED)

        def on_leave(e):
            if card.cget("border_color") != BORDER_ACTIVE:
                card.configure(border_color=BORDER_DIM, fg_color=BG_CARD)

        self._bind_hover(card, on_enter, on_leave)

        return card

    def _bind_hover(self, widget, on_enter, on_leave):
        """Bind hover events to widget AND all descendants (fix P3)."""
        for w in [widget] + self._all_children(widget):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def _all_children(self, widget):
        """Recursively collect all child widgets."""
        children = []
        for child in widget.winfo_children():
            children.append(child)
            children.extend(self._all_children(child))
        return children

    def _bind_card(self, card, cb):
        card.bind("<Button-1>", lambda e: cb())
        for w in self._all_children(card):
            w.bind("<Button-1>", lambda e, f=cb: f())

    def _reset_cards(self):
        self._card_mbox.configure(border_color=BORDER_DIM, fg_color=BG_CARD)
        self._card_eml.configure(border_color=BORDER_DIM, fg_color=BG_CARD)

    # ================================================
    # FILE SELECTION
    # ================================================
    def _select_mbox(self):
        paths = filedialog.askopenfilenames(
            title="Choisis tes fichiers .mbox ou .zip Takeout",
            filetypes=[
                ("Fichiers mail", "*.mbox"),
                ("Archives ZIP", "*.zip"),
                ("Tous", "*.*"),
            ]
        )
        if paths:
            self._selected_files = list(paths)
            self._selected_mode = "files"
            self._reset_cards()
            self._card_mbox.configure(border_color=BORDER_ACTIVE)
            names = [os.path.basename(p) for p in self._selected_files]
            display = ", ".join(names)
            if len(display) > 60:
                display = display[:57] + "..."
            self._sel_label.configure(
                text="\u2714  " + display, text_color=TEXT_SUCCESS
            )

    def _select_eml(self):
        folder = filedialog.askdirectory(
            title="Choisis le dossier contenant des .eml"
        )
        if folder:
            self._selected_files = [folder]
            self._selected_mode = "folder"
            self._reset_cards()
            self._card_eml.configure(border_color=BORDER_ACTIVE)
            self._sel_label.configure(
                text="\u2714  " + os.path.basename(folder) + "/",
                text_color=TEXT_SUCCESS
            )

    # ================================================
    # CONVERSION
    # ================================================
    def _start_conversion(self):
        if self._running:
            return
        self._running = True
        self._cta_btn.configure(
            state="disabled", text="Conversion en cours..."
        )
        self._status.configure(text="Demarrage...", text_color=TEXT_HI)
        self._pbar.set(0)
        self._phase.configure(text="")
        self._clear_log()

        self._footer.pack_forget()
        self._pf.pack(fill="x", pady=(0, 6))
        self._log.pack(fill="both", expand=True, pady=(0, 4))

        threading.Thread(target=self._run_core, daemon=True).start()

    def _run_core(self):
        base = get_base_dir()
        core_path = os.path.join(base, "takeoutreader_core.py")
        if not os.path.isfile(core_path):
            self._log_queue.put(
                "[ERREUR] takeoutreader_core.py introuvable dans : " + base
            )
            self._signal_done(False)
            return

        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = QueueWriter(self._log_queue, old_stdout)
        sys.stderr = QueueWriter(self._log_queue, old_stderr)
        original_argv = original_input = None

        try:
            import builtins
            original_argv = sys.argv[:]
            original_input = builtins.input
            sys.argv = (
                [core_path] + self._selected_files
                if self._selected_files
                else [core_path]
            )
            builtins.input = lambda *a, **kw: ""

            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "takeoutreader_core", core_path
            )
            core = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(core)
            core.main()
            self._signal_done(True)
        except Exception as e:
            import traceback
            self._log_queue.put(f"[ERREUR] {e}")
            self._log_queue.put(traceback.format_exc())
            self._signal_done(False)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            if original_argv is not None:
                sys.argv = original_argv
            if original_input is not None:
                import builtins
                builtins.input = original_input

    def _signal_done(self, ok):
        self._log_queue.put("__DONE_OK__" if ok else "__DONE_FAIL__")

    # ================================================
    # LOG POLLING + PROGRESS
    # ================================================
    def _poll_queue(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                if msg == "__DONE_OK__":
                    self._on_done(True)
                    continue
                elif msg == "__DONE_FAIL__":
                    self._on_done(False)
                    continue
                self._append_log(msg)
                self._update_progress(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _update_progress(self, msg):
        ml = msg.lower().strip()
        if "mbox-to-html" in ml and "parse" in ml:
            self._status.configure(text="Analyse des mails...")
            self._pbar.set(0.15)
            self._phase.configure(text="Phase 1/4 : Lecture .mbox")
        elif "parse =" in ml or "parse eml" in ml:
            self._status.configure(text="Parsing en cours...")
            self._pbar.set(0.25)
        elif "bilan parse" in ml:
            self._status.configure(text="Analyse terminee")
            self._pbar.set(0.40)
            self._phase.configure(text="Phase 2/4 : Deduplication")
        elif "[pj" in ml or "extraction pj" in ml.replace(" ", ""):
            self._status.configure(text="Extraction des pieces jointes...")
            self._pbar.set(0.55)
            self._phase.configure(text="Phase 3/4 : Pieces jointes")
        elif "[output]" in ml and "generation" in ml:
            self._status.configure(text="Generation HTML...")
            self._pbar.set(0.70)
            self._phase.configure(text="Phase 4/4 : Creation archive")
        elif "validation" in ml and "invariants" in ml:
            self._status.configure(text="Validation...")
            self._pbar.set(0.85)
            self._phase.configure(text="Validation Rebouclage")
        elif "bilan final" in ml:
            self._status.configure(text="Termine !")
            self._pbar.set(1.0)
            self._phase.configure(text="Conversion reussie")

        m = re.search(r'(\d{1,3})%', msg)
        if m and "parse" in ml:
            self._pbar.set(
                min(0.15 + int(m.group(1)) / 100.0 * 0.25, 0.40)
            )

    def _on_done(self, ok):
        self._running = False
        self._cta_btn.configure(
            state="normal", text="\u25b6   Lancer la conversion"
        )
        if ok:
            self._status.configure(
                text="\u2714  Conversion reussie !",
                text_color=TEXT_SUCCESS
            )
            self._pbar.set(1.0)
            self._phase.configure(
                text="Double-clic INDEX_GMAIL.html pour ouvrir"
                " votre archive"
            )
        else:
            self._status.configure(
                text="\u274c  Erreur pendant la conversion",
                text_color=TEXT_ERROR
            )
            self._phase.configure(text="Consultez le log ci-dessous")

    def _append_log(self, text):
        self._log.configure(state="normal")
        self._log.insert("end", text.rstrip() + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")


# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    TakeoutReaderApp().mainloop()
