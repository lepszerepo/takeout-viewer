# Takeout Viewer

Lokalna aplikacja webowa do przeglądania, porównywania **i analizy** wielu zrzutów **Google Takeout** uruchamiana jednym poleceniem przez Docker Compose. Wszystkie dane (i analiza AI) pozostają wyłącznie na komputerze użytkownika.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Docker Compose](https://img.shields.io/badge/docker-compose-2496ED?logo=docker)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python)
![React 18](https://img.shields.io/badge/react-18-61DAFB?logo=react)
![SQLite + FTS5 + vec](https://img.shields.io/badge/sqlite-FTS5%20%2B%20vec0-003B57?logo=sqlite)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%2B%20Bielik%2011B-black)

---

## 1. Co to jest aplikacja

Takeout Viewer pozwala:

- **Importować wiele zrzutów Takeout** i dokładać kolejne w czasie bez nadpisywania,
- **Deduplikować** rekordy występujące w wielu zrzutach (jeden event = wszystkie zrzuty w których wystąpił),
- Przeglądać dane na osi czasu z filtrami (zrzut, źródło, typ, daty, treść),
- Zobaczyć z którego zrzutu pochodzi każdy rekord.

Obsługiwane parsery i typy danych:

| Źródło Google Takeout | Co wyciągamy |
|---|---|
| **Mail (mbox)** | pełne body (text + HTML) + tematy z MIME-decode, threading (In-Reply-To/References), etykiety (X-Gmail-Labels), załączniki (nazwy + rozmiary + treść z PDF/DOCX/XLSX/PPTX + OCR obrazów), binaria zapisane content-addressed dla pobierania |
| **Mail (User Settings)** | sygnatury, vacation responder, blocked addresses, delegaci |
| **My Activity** (JSON + HTML) | YouTube watch/search, Chrome visits, Search queries, Maps, Assistant, Ads, Play, Gemini Apps z auto-klasyfikacją typu |
| **Calendar (.ics)** | wydarzenia z uczestnikami i lokalizacjami |
| **Google Meet** | konferencje z atendance i czasem trwania |
| **Tasks** | zadania z listami, statusami, terminami |
| **Contacts** | vCard / CSV |
| **Drive** | metadane + ekstrahowana treść PDF/DOCX/XLSX/PPTX/TXT/CSV oraz **OCR** obrazów (JPG/PNG/HEIC/TIFF) i scanned PDF (poppler + tesseract pol+eng) |
| **Location History** | punkty z linkiem do Google Maps |
| **YouTube** | historia oglądania/wyszukiwań |

Funkcje **analityczne** (lokalne AI):

- **FTS5** — błyskawiczne wyszukiwanie pełnotekstowe z BM25 (operatory `AND/OR/NOT`, `"fraza"`, `słowo*`, `NEAR/N`)
- **Embeddings** (bge-m3) — wektory 1024D dla wszystkich maili w `sqlite-vec`
- **Semantyczne wyszukiwanie** — naturalne zapytania, np. „maile o zwolnieniu z marca", „korespondencja o umowach z kontrahentami"
- **Streszczenia i kategoryzacja AI** — Bielik 11B (dedykowany polski model) generuje per-mail streszczenie / przypisuje kategorię (HR/Legal/Finance/...) / ekstrahuje encje
- **NER** (spaCy `pl_core_news_lg`) — osoby, organizacje, miejsca, kwoty, daty, e-maile, URL-e wyciągnięte z pełnej treści. Pozwala szukać „wszystkie maile gdzie wystąpił `Jan Kowalski`" niezależnie od pola od/do
- **Cross-dataset dedup** — ten sam event widoczny w wielu zrzutach pokazuje, kto z kogo (np. „Company meeting" w 5 kalendarzach)

UI: Gmail-like 3-pane dla maila, dedykowane strony dla zrzutów / źródeł / korespondentów / encji / wyszukiwania.

## 2. Model prywatności

- **Wszystko działa lokalnie** w kontenerach Docker. Dane nie są nigdzie wysyłane.
- Backend nie używa żadnych usług chmurowych, telemetrii ani zewnętrznych trackerów.
- Frontend ładuje wyłącznie zasoby z kontenera; brak CDN-ów w runtime.
- Logi techniczne (`data/logs/backend.log`) zawierają tylko komunikaty o postępie importu i błędach bez treści rekordów użytkownika.
- W UI nigdy nie pokazujemy absolutnej ścieżki hosta. Surowe dane (`raw_json`) są ukryte za przyciskiem „Pokaż dane techniczne”.
- Walidacja nazwy zrzutu zabezpiecza przed wyjściem poza katalog `data/imports` (path traversal).

## 3. Wymagania

- **Docker** (Docker Desktop dla macOS/Windows lub Docker Engine dla Linuksa)
- **Docker Compose** (wbudowany w nowsze wersje Dockera)

Nic więcej. Python ani Node nie są wymagane na hoście.

## 4. Przygotowanie katalogów na hoście

W katalogu projektu utwórz strukturę:

```bash
mkdir -p data/imports data/db data/logs
```

- `data/imports/` — tutaj wkładasz rozpakowane zrzuty Google Takeout
- `data/db/` — aplikacja zapisze tu bazę SQLite (`takeout_viewer.sqlite`)
- `data/logs/` — logi techniczne

## 5. Jak dodać pierwszy zrzut Google Takeout

1. Pobierz archiwum z https://takeout.google.com/.
2. Rozpakuj plik `.zip` w **osobnym podkatalogu** wewnątrz `data/imports/`. Nazwa katalogu może być dowolna, ale czytelna — np. `takeout_2024_01`.

Przykład:

```
data/
├── db/
├── logs/
└── imports/
    └── takeout_2024_01/
        └── Takeout/
            ├── YouTube and YouTube Music/
            ├── My Activity/
            └── ...
```

## 6. Jak dodać kolejne zrzuty Google Takeout

Powtórz krok z punktu 5, ale użyj innej, unikalnej nazwy katalogu:

```
data/imports/
├── takeout_2024_01/
├── takeout_2024_06/
└── takeout_2025_02/
```

Każdy katalog to osobny **Dataset**. Możesz dokładać kolejne w dowolnym momencie — aplikacja wykryje nowe katalogi przy najbliższym odświeżeniu i pozwoli je zaimportować bez ingerencji w już zaimportowane dane.

## 7. Uruchamianie aplikacji

W katalogu `takeout-viewer/`:

```bash
docker compose up --build
```

Pierwsze uruchomienie zbuduje obrazy backend i frontend (zajmuje to kilka minut).

Aby zatrzymać:

```bash
docker compose down
```

## 8. Wejście do UI

Po starcie kontenerów otwórz przeglądarkę i wejdź na:

```
http://localhost:5173
```

Backend (API + dokumentacja `/docs`) dostępny jest na:

```
http://localhost:8001
```

## 9. Jak zaimportować jeden zrzut

1. Otwórz UI: http://localhost:5173.
2. Wybierz w nawigacji **„Zrzuty”**.
3. Na liście wykrytych katalogów kliknij **„Importuj”** obok wybranego zrzutu.
4. Po zakończeniu zobaczysz podsumowanie: ile rekordów zaimportowano, ile rozpoznano jako duplikaty i ile było błędów.

## 10. Jak zaimportować wiele zrzutów naraz

Na ekranie „Zrzuty”:

1. Zaznacz checkboxy obok kilku katalogów.
2. Kliknij **„Importuj zaznaczone (N)”**.

Aplikacja zaimportuje je po kolei, zachowując osobny licznik dla każdego zrzutu.

## 11. Jak działa deduplikacja

Każde zdarzenie ma obliczany **stable_hash** na podstawie pól: `source`, `type`, `timestamp`, `title`, `url`. Jeżeli `timestamp` jest niedostępny, hash wykorzystuje też `raw_path`.

- Ten sam rekord zaimportowany ponownie z tego samego zrzutu → policzony jako duplikat, nie tworzy nowego wpisu.
- Ten sam rekord z innego zrzutu → policzony jako duplikat między zrzutami; UI oznaczy go etykietą „Duplikat między zrzutami”. Tworzony jest dodatkowy wpis w tabeli `event_dataset_links` z informacją, że to samo zdarzenie wystąpiło też w nowym zrzucie.

Dzięki temu każdy event widzisz tylko raz, ale wiesz, z których zrzutów pochodzi.

## 12. Jakie dane są obsługiwane w MVP

| Usługa Google           | Format wejściowy          | Status MVP |
|-------------------------|---------------------------|------------|
| YouTube — historia oglądania | JSON / HTML           | ✅         |
| YouTube — historia wyszukiwań | JSON / HTML          | ✅         |
| My Activity (wszystkie produkty) | JSON / HTML       | ✅ (auto-klasyfikacja YouTube / Chrome / Search / Maps / Assistant / Play / Ads) |
| Chrome — historia        | JSON / CSV               | ✅         |
| Chrome — zakładki        | HTML                     | ✅         |
| Location History         | Records.json             | ✅ (z linkiem do Google Maps) |
| Calendar                 | .ics                     | ✅         |
| Contacts                 | vCard (.vcf) / CSV       | ✅         |
| Pozostałe usługi (Drive, Mail, Photos, Fit, Keep, Tasks...) | — | rozpoznawane przez skaner, ale dla MVP są pomijane — wyświetlamy je jako „nieobsłużone typy danych” w podsumowaniu importu |

## 13. Jak dodać nowy parser

Parsery żyją w `backend/app/importer/parsers/`. Aby dodać kolejny:

1. Utwórz nowy plik, np. `mail.py`, w którym zaimplementujesz funkcję:

   ```python
   def my_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
       ...
   ```

2. Dodaj funkcję `register_parsers(register)`, która woła `register("source", "type", my_parser)`.
3. Zaimportuj nowy moduł w `backend/app/importer/registry.py` w funkcji `_load_parsers()`.
4. Jeżeli trzeba — dodaj heurystyki rozpoznawania ścieżek w `backend/app/importer/scanner.py` (`_HEURISTICS`) i typy plików w `_DEFAULT_EXT_BY_SERVICE`.
5. Dodaj testy w `backend/tests/test_parsers.py`.

Wszystkie parsery wykorzystują wspólny model `NormalizedEvent` — wystarczy poprawnie wypełnić pola `source`, `type`, `title`, `timestamp`, `url`, ewentualnie `metadata`/`location`/`people`.

## 14. Backup bazy SQLite

Baza znajduje się na hoście pod ścieżką:

```
data/db/takeout_viewer.sqlite
```

Aby zrobić backup, **zatrzymaj aplikację** (`docker compose down`), a następnie skopiuj plik:

```bash
cp data/db/takeout_viewer.sqlite data/db/takeout_viewer.backup.$(date +%Y%m%d).sqlite
```

Możesz też zarchiwizować cały katalog `data/`:

```bash
tar czf takeout-viewer-backup-$(date +%Y%m%d).tar.gz data/
```

Aby przywrócić — zamień plik `takeout_viewer.sqlite` na wybraną kopię zapasową i uruchom kontenery ponownie.

## 15. Znane ograniczenia MVP

- **Bardzo duże pliki** (np. wielogigabajtowe `MyActivity.html`) są wczytywane w całości do pamięci. Dla MVP to akceptowalne; przy plikach > 1–2 GB lepiej najpierw rozdzielić je na fragmenty albo użyć formatu JSON.
- **Mail / Photos / Drive** są wykrywane przez skaner, ale nie posiadają jeszcze dedykowanych parserów — pojawią się jako „nieobsłużone typy danych” w raporcie importu.
- **Brak edycji** zaimportowanych danych w UI — to świadoma decyzja, aplikacja jest tylko przeglądarką.
- **Mapy lokalizacji** nie są renderowane — pokazujemy współrzędne i klikalne linki do Google Maps, ale bez wbudowanej mapy w MVP.
- **FTS5** nie jest jeszcze włączony — używamy zwykłego `LIKE` na tytule, opisie i URL. Działa dobrze przy zbiorach do kilkuset tysięcy rekordów.
- **Wyłącznie SQLite** w MVP. Warstwa danych jest jednak na tyle prosta, że przejście na PostgreSQL wymaga tylko zmiany URL bazy oraz drobnej zamiany zapytań specyficznych dla SQLite (np. `strftime` w statystykach).

---

## Diagnostyka

- **Backend nie startuje** → sprawdź `docker compose logs backend` oraz `data/logs/backend.log`.
- **„Brak połączenia” w UI** → sprawdź, czy działa kontener `backend` (`docker ps`), czy port `8001` nie jest zajęty.

> Uwaga: na tym hoście port 8000 był już zajęty przez inny projekt, więc backend został przemapowany na **8001**. Jeśli masz wolny 8000, możesz zmienić w `docker-compose.yml` mapowanie z `8001:8000` na `8000:8000` i `VITE_API_BASE_URL` z `8001` na `8000`.
- **„Nie znaleziono żadnych zrzutów”** → upewnij się, że katalogi z Takeoutem leżą **bezpośrednio** w `data/imports/` (np. `data/imports/takeout_2024_01/Takeout/...`).
- **Błąd importu jednego pliku** → reszta importu kontynuuje. Wszystkie błędy znajdziesz w widoku szczegółów ostatniego importu (`GET /api/import-runs/{id}`) oraz w `data/logs/backend.log`.

## Pełna struktura projektu

```
takeout-viewer/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── labels.py
│   │   ├── logging_setup.py
│   │   ├── api/             # routes
│   │   ├── services/        # search, stats
│   │   └── importer/        # scanner, importer, parsers/
│   └── tests/
│       ├── fixtures/        # małe, sztuczne dane testowe (bez rzeczywistych danych)
│       └── test_*.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── App.tsx · main.tsx · api.ts · types.ts · index.css
│       ├── components/      # Layout, ImportManager, EventCard, Filters, EventDetailsDrawer, ...
│       └── pages/           # Dashboard, DatasetsPage, EventsPage, SourcesPage
├── data/
│   ├── imports/             # ← tutaj wkładasz rozpakowane zrzuty Takeout
│   ├── db/                  # SQLite
│   └── logs/                # logi
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── README.md
```
