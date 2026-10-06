#!/usr/bin/env python3
"""Eksport rozmów Hermesa: JSON z czatu -> czysty tekst z podziałem Ja/Pati.

GUI (GTK3) jak Konwerter do Obsidiana: wybór pliku albo przeciągnij-i-upuść.
Tryb terminalowy: python3 rozmowy.py plik1.json [plik2.json ...]
"""
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from urllib.parse import urlparse, unquote

OUT_ROOT = os.path.expanduser("~/Dokumenty/Rozmowy Hermes")
START_DIR = os.path.expanduser("~/.hermes/sessions/saved")
LABEL_ME = "Ja"
LABEL_BOT = "Pati"

# linie-komendy, które nie są częścią rozmowy (tylko na początku wiadomości)
COMMAND_LINE = re.compile(r"^\s*/?role-play\s+(start|stop|status)\b[ \t]*\n?", re.IGNORECASE)


def _clean(value):
    """Hermes zapisuje puste pola jako tekst 'None' — traktuj to jak brak treści."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    if value.strip() == "None":
        return ""
    return value


def load_messages(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return data["messages"], data
    raise RuntimeError("To nie wygląda na zapis czatu Hermesa (brak listy 'messages').")


def extract_turns(messages):
    """Zwraca listę (etykieta, tekst). Pomija narzędzia i puste odpowiedzi,
    skleja kolejne wiadomości tej samej osoby w jedną wypowiedź."""
    turns = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        if _clean(m.get("active")) == "0":
            continue
        role = m.get("role")
        if role == "user":
            label = LABEL_ME
        elif role == "assistant":
            label = LABEL_BOT
        else:
            continue  # tool, system itp.
        text = _clean(m.get("content")).replace("\r\n", "\n")
        if label == LABEL_ME:
            text = COMMAND_LINE.sub("", text, count=1)
        text = text.strip()
        if not text:
            continue
        if turns and turns[-1][0] == label:
            turns[-1] = (label, turns[-1][1] + "\n\n" + text)
        else:
            turns.append((label, text))
    return turns


def render(turns):
    return "\n\n".join(f"{label}:\n{text}" for label, text in turns) + "\n"


def output_name(path, meta):
    stamp = None
    try:
        stamp = datetime.fromtimestamp(float(meta.get("started_at")))
    except (TypeError, ValueError):
        pass
    sid = _clean(meta.get("id"))
    if stamp:
        base = f"Rozmowa {stamp:%Y-%m-%d %H.%M}"
        if sid:
            base += f" ({sid})"
    else:
        base = os.path.splitext(os.path.basename(path))[0]
    return base


def unique_path(directory, base, ext=".txt"):
    candidate = os.path.join(directory, base + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base} ({n}){ext}")
        n += 1
    return candidate


def convert(path, out_root=OUT_ROOT):
    messages, meta = load_messages(path)
    turns = extract_turns(messages)
    if not turns:
        raise RuntimeError("Nie znalazłem w pliku żadnych wypowiedzi.")
    os.makedirs(out_root, exist_ok=True)
    out = unique_path(out_root, output_name(path, meta))
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(turns))
    me = sum(1 for t in turns if t[0] == LABEL_ME)
    return out, me, len(turns) - me


def uri_to_path(uri):
    parsed = urlparse(uri)
    return unquote(parsed.path) if parsed.scheme == "file" else None


def run_gui():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GLib

    class Window(Gtk.Window):
        def __init__(self):
            super().__init__(title="Rozmowy Hermes → tekst")
            self.set_border_width(16)
            self.set_default_size(460, 220)
            self.set_position(Gtk.WindowPosition.CENTER)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            self.add(box)

            info = Gtk.Label(label=f"Wybierz zapis czatu Hermesa (.json), a dostaniesz czysty tekst\n"
                                   f"rozmowy z podziałem {LABEL_ME} / {LABEL_BOT}.\n\n"
                                   f"Możesz też przeciągnąć i upuścić plik (albo kilka) tutaj.")
            info.set_justify(Gtk.Justification.CENTER)
            box.pack_start(info, False, False, 0)

            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.IN)
            frame.set_size_request(-1, 60)
            self.file_label = Gtk.Label(label="Nie wybrano pliku")
            self.file_label.set_line_wrap(True)
            for side in ("top", "bottom", "start", "end"):
                getattr(self.file_label, f"set_margin_{side}")(8)
            frame.add(self.file_label)
            box.pack_start(frame, False, False, 0)

            buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.pack_start(buttons, False, False, 0)
            self.choose_btn = Gtk.Button(label="Wybierz plik…")
            self.choose_btn.connect("clicked", self.on_choose)
            buttons.pack_start(self.choose_btn, True, True, 0)
            self.convert_btn = Gtk.Button(label="Konwertuj")
            self.convert_btn.set_sensitive(False)
            self.convert_btn.connect("clicked", lambda _b: self.start(self.selected))
            buttons.pack_start(self.convert_btn, True, True, 0)

            self.status = Gtk.Label(label="")
            self.status.set_line_wrap(True)
            self.status.set_selectable(True)
            box.pack_start(self.status, False, False, 0)

            self.open_btn = Gtk.Button(label="Otwórz folder wyniku")
            self.open_btn.set_sensitive(False)
            self.open_btn.connect("clicked", lambda _b: subprocess.Popen(["xdg-open", OUT_ROOT]))
            box.pack_start(self.open_btn, False, False, 0)

            self.selected = []
            targets = Gtk.TargetList.new([])
            targets.add_uri_targets(0)
            self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
            self.drag_dest_set_target_list(targets)
            self.connect("drag-data-received", self.on_drop)

        def on_choose(self, _btn):
            dialog = Gtk.FileChooserDialog(title="Wybierz zapis czatu", parent=self,
                                           action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                               Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
            dialog.set_select_multiple(True)
            if os.path.isdir(START_DIR):
                dialog.set_current_folder(START_DIR)
            filt = Gtk.FileFilter()
            filt.set_name("Zapis czatu (JSON)")
            filt.add_pattern("*.json")
            filt.add_pattern("*.JSON")
            dialog.add_filter(filt)
            if dialog.run() == Gtk.ResponseType.OK:
                self.selected = dialog.get_filenames()
                self.file_label.set_text("\n".join(self.selected))
                self.convert_btn.set_sensitive(True)
                self.status.set_text("")
            dialog.destroy()

        def on_drop(self, _w, _ctx, _x, _y, data, _info, _time):
            paths = [p for p in (uri_to_path(u) for u in data.get_uris()) if p]
            paths = [p for p in paths if p.lower().endswith(".json")]
            if not paths:
                self.status.set_text("To nie jest plik .json z czatu.")
                return
            self.file_label.set_text("\n".join(paths))
            self.start(paths)

        def start(self, paths):
            if not paths:
                return
            self.choose_btn.set_sensitive(False)
            self.convert_btn.set_sensitive(False)
            self.status.set_text("Konwertuję…")
            threading.Thread(target=self.work, args=(list(paths),), daemon=True).start()

        def work(self, paths):
            lines, ok = [], 0
            for p in paths:
                try:
                    out, me, bot = convert(p)
                    ok += 1
                    lines.append(f"✓ {out}\n   {LABEL_ME}: {me} wypowiedzi, {LABEL_BOT}: {bot}")
                except Exception as e:  # pokazujemy błąd zamiast cichej porażki
                    lines.append(f"✗ {os.path.basename(p)}: {e}")
            GLib.idle_add(self.done, ok, lines)

        def done(self, ok, lines):
            self.status.set_text("\n".join(lines))
            self.choose_btn.set_sensitive(True)
            self.selected = []
            self.open_btn.set_sensitive(ok > 0)

    win = Window()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


def main():
    if len(sys.argv) > 1:
        code = 0
        for p in sys.argv[1:]:
            try:
                out, me, bot = convert(p)
                print(f"OK  {out}  ({LABEL_ME}: {me}, {LABEL_BOT}: {bot})")
            except Exception as e:
                print(f"BŁĄD {p}: {e}", file=sys.stderr)
                code = 1
        return code
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
