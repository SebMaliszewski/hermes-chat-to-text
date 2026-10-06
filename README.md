# Rozmowy Hermes → tekst

Prosta aplikacja GUI dla Linuksa (GTK3), która z zapisu czatu
[Hermes Agent](https://github.com/NousResearch/hermes-agent) w formacie JSON
wyciąga czysty tekst rozmowy z podziałem na rozmówców:

```
Ja:
Tekst

Pati:
Tekst
```

Zrobiona pod Linux Mint / XFCE, ale powinna działać na każdym systemie z GTK3.

![status](https://img.shields.io/badge/status-działa-brightgreen)

## Co robi

- **Wybór pliku przez okno dialogowe albo przeciągnij i upuść**, jeden plik
  albo kilka naraz. Okno wyboru otwiera się od razu w `~/.hermes/sessions/saved`.
- **Zostawia samą rozmowę:** pomija wywołania narzędzi, wyniki narzędzi i puste
  odpowiedzi modelu (te, które były tylko wywołaniem narzędzia).
- **Skleja kolejne wiadomości tej samej osoby** w jedną wypowiedź, więc podział
  Ja / Pati zawsze się przeplata.
- **Usuwa komendy `role-play start` / `stop` / `status`** z początku wiadomości.
- **Zostawia formatowanie Markdown** (np. `*kursywę*`), żeby było widać, co jest
  myślą, a co mową.
- **Nigdy nie nadpisuje** istniejącego pliku. Przy powtórzonej nazwie dopisuje `(2)`, `(3)`…

## Gdzie ląduje wynik

```
~/Dokumenty/Rozmowy Hermes/Rozmowa RRRR-MM-DD GG.MM (<id sesji>).txt
```

Data i godzina pochodzą z początku sesji zapisanego w JSON-ie.

## Wymagania

- Python 3 + PyGObject / GTK3 (`python3-gi`, na Mincie zwykle już jest).
- Nic więcej, tylko biblioteka standardowa Pythona.

## Instalacja

```bash
git clone https://github.com/SebMaliszewski/hermes-chat-to-text.git
mkdir -p ~/.local/share/hermes-rozmowy
cp hermes-chat-to-text/rozmowy.py ~/.local/share/hermes-rozmowy/
cp hermes-chat-to-text/hermes-rozmowy.desktop ~/.local/share/applications/
chmod +x ~/.local/share/hermes-rozmowy/rozmowy.py
```

Jeśli trzymasz `rozmowy.py` gdzie indziej, popraw ścieżkę `Exec=` w pliku `.desktop`.

## Użycie

1. Uruchom **„Rozmowy Hermes → tekst”** z menu aplikacji.
2. Wybierz plik `.json` przyciskiem **„Wybierz plik…”** albo przeciągnij go na okno.
3. Kliknij **„Konwertuj”** (przy przeciąganiu startuje samo).
4. Przycisk **„Otwórz folder wyniku”** otwiera `~/Dokumenty/Rozmowy Hermes/`.

Z terminala, bez okna:

```bash
python3 ~/.local/share/hermes-rozmowy/rozmowy.py plik1.json plik2.json
```

## Własne nazwy rozmówców

Na górze `rozmowy.py`:

```python
LABEL_ME = "Ja"
LABEL_BOT = "Pati"
```

Tam też zmienisz folder wyniku (`OUT_ROOT`) i folder startowy okna wyboru (`START_DIR`).
