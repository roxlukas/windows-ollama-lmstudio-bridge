\# Ollama ↔ LM Studio Sync



Narzędzie do synchronizacji modeli między Ollama a LM Studio poprzez symlinki. Program analizuje manifesty Ollama, identyfikuje modele i tworzy odpowiednią strukturę katalogów w LM Studio z linkami do plików blob.



\## 🎯 Funkcjonalności



\- \*\*Automatyczne mapowanie modeli\*\* - skanuje manifesty Ollama i buduje mapę model → digest

\- \*\*Inteligentne symlinki\*\* - tworzy symlinki do plików blob zamiast kopiowania (oszczędność miejsca)

\- \*\*Organizacja według vendor\*\* - strukturyzuje modele według dostawcy (library, speakleash, itp.)

\- \*\*Metadata dla LM Studio\*\* - generuje pliki `config.json` i `.lmstudio` dla właściwej integracji

\- \*\*Czyszczenie osieroconych modeli\*\* - usuwa nieaktualne symlinki

\- \*\*Bezpieczne nazwy plików\*\* - konwertuje znaki specjalne w nazwach modeli



\## 📁 Wymagana struktura katalogów



```

Ollama:

D:\\AI\\models\\

├── manifests\\

│   └── registry.ollama.ai\\

│       └── library\\

│           └── model-name\\

│               └── tag-name      # plik JSON z manifestem

└── blobs\\

&nbsp;   └── sha256-xxxxx...          # pliki blob modeli



LM Studio (docelowa):

D:\\AI\\LMstudio\\

├── vendor1\\

│   └── model-name-tag\\

│       ├── model-name-tag.gguf  # symlink do blob

│       ├── config.json          # metadata

│       └── .lmstudio           # marker LM Studio

└── vendor2\\

&nbsp;   └── ...

```



\## 🚀 Użycie



\### Podstawowa synchronizacja

```bash

python sync\_models.py "D:\\AI\\models\\manifests" "D:\\AI\\models\\blobs" "D:\\AI\\LMstudio"

```



\### Z dodatkowymi opcjami

```bash

\# Nadpisz istniejące symlinki

python sync\_models.py "D:\\AI\\models\\manifests" "D:\\AI\\models\\blobs" "D:\\AI\\LMstudio" --overwrite



\# Wyczyść osierocone modele

python sync\_models.py "D:\\AI\\models\\manifests" "D:\\AI\\models\\blobs" "D:\\AI\\LMstudio" --clean



\# Tryb debug (tylko budowanie mappingu)

python sync\_models.py "D:\\AI\\models\\manifests" "D:\\AI\\models\\blobs" "D:\\AI\\LMstudio" --debug



\# Własna lokalizacja pliku mapping.json

python sync\_models.py "D:\\AI\\models\\manifests" "D:\\AI\\models\\blobs" "D:\\AI\\LMstudio" --mapping "moj\_mapping.json"

```



\## 📋 Parametry



| Parametr | Typ | Opis |

|----------|-----|------|

| `manifests` | \*\*wymagany\*\* | Ścieżka do katalogu manifests Ollama |

| `ollama` | \*\*wymagany\*\* | Ścieżka do katalogu blobs Ollama |

| `lmstudio` | \*\*wymagany\*\* | Ścieżka do katalogu modeli LM Studio |

| `--mapping` | opcjonalny | Lokalizacja pliku mapping.json (domyślnie: `mapping.json`) |

| `--overwrite` | flaga | Nadpisuje istniejące symlinki |

| `--clean` | flaga | Usuwa osierocone modele w LM Studio |

| `--debug` | flaga | Tryb debug - tylko budowanie mappingu bez tworzenia symlinków |



\## 🔧 Jak to działa



\### 1. Analiza manifestów

Program skanuje katalog `manifests` i dla każdego znalezionego pliku JSON:

\- Parsuje manifest modelu

\- Identyfikuje największą warstwę (zazwyczaj plik GGUF modelu)

\- Wyciąga digest (hash) tej warstwy

\- Analizuje ścieżkę: `domain/vendor/model/tag`



\### 2. Generowanie nazw modeli

\- \*\*Ollama library\*\*: `model:tag` (np. `llama2:7b`)

\- \*\*Inne vendors\*\*: `vendor/model:tag` (np. `speakleash/polish-llm:q8\_0`)



\### 3. Tworzenie symlinków

\- Sprawdza czy blob istnieje w katalogu `blobs`

\- Tworzy strukturę `vendor/model-tag/`

\- Generuje symlink: `model-tag.gguf` → blob

\- Dodaje pliki metadata (`config.json`, `.lmstudio`)



\### 4. Organizacja według vendor

Modele są organizowane według dostawcy:

```

lmstudio/

├── library/           # modele z registry.ollama.ai/library/

├── speakleash/        # modele z vendor speakleash

├── microsoft/         # modele z vendor microsoft

└── ...

```



\## 📄 Przykładowe wyjście



```

🔍 Szukam plików w: D:\\AI\\models\\manifests

📁 Znaleziono 45 plików/katalogów łącznie

📄 Z tego 12 to pliki



🔎 Przetwarzam: manifests\\registry.ollama.ai\\library\\llama2\\7b

&nbsp; 📋 Klucze w JSON: \['schemaVersion', 'mediaType', 'config', 'layers']

&nbsp; 📦 Znaleziono 2 warstw

&nbsp;   🧩 Warstwa: sha256:abc123... (rozmiar: 3825819648, typ: application/vnd.ollama.image.model)

&nbsp; 🔑 Wybrano największą warstwę: sha256:abc123def456...

&nbsp; 📝 Nazwa modelu: llama2:7b

&nbsp; ✅ Dodano do mappingu



✅ Znaleziono blob dla llama2:7b: D:\\AI\\models\\blobs\\sha256-abc123def456...

✅ Link: D:\\AI\\LMstudio\\library\\llama2-7b\\llama2-7b.gguf -> D:\\AI\\models\\blobs\\sha256-abc123def456...

&nbsp; 📄 Utworzono config.json dla llama2:7b

&nbsp; 🏷️ Utworzono .lmstudio dla llama2:7b



📄 Wygenerowano mapping.json (8 modeli)

```



\## 🛠️ Wymagania



\- \*\*Python 3.6+\*\*

\- \*\*System operacyjny z obsługą symlinków\*\* (Windows 10+, Linux, macOS)

\- \*\*Uprawnienia administratora\*\* (Windows) lub odpowiednie uprawnienia (Linux/macOS) do tworzenia symlinków



\### Windows

Na Windows może być konieczne uruchomienie jako administrator lub włączenie trybu developer:

```powershell

\# Włącz tryb developer (Windows 10/11)

Settings → Update \& Security → For developers → Developer Mode

```



\## 📊 Plik mapping.json



Program generuje plik `mapping.json` z mapowaniem modeli:



```json

{

&nbsp; "llama2:7b": {

&nbsp;   "digest": "sha256:abc123def456...",

&nbsp;   "vendor": "library"

&nbsp; },

&nbsp; "speakleash/polish-llm:q8\_0": {

&nbsp;   "digest": "sha256:def789abc123...",

&nbsp;   "vendor": "speakleash"

&nbsp; }

}

```



\## ⚠️ Uwagi



\- \*\*Symlinki vs kopiowanie\*\*: Program używa symlinków, więc modele zajmują miejsce tylko raz

\- \*\*Bezpieczeństwo\*\*: Sprawdź uprawnienia przed pierwszym uruchomieniem

\- \*\*Backup\*\*: Zalecane jest utworzenie kopii zapasowej katalogu LM Studio przed pierwszym użyciem

\- \*\*Aktualizacje\*\*: Uruchom ponownie po dodaniu nowych modeli do Ollama



\## 🔍 Rozwiązywanie problemów



\### Błąd "Blob nie istnieje"

\- Sprawdź czy podana ścieżka do `blobs` jest poprawna

\- Upewnij się, że model został rzeczywiście pobrany przez Ollama



\### Błąd uprawnień przy tworzeniu symlinków

\- Windows: uruchom jako administrator lub włącz tryb developer

\- Linux/macOS: sprawdź uprawnienia do katalogów docelowych



\### Puste wyniki przy skanowaniu manifestów

\- Sprawdź czy ścieżka do `manifests` jest poprawna

\- Upewnij się, że manifesty mają poprawny format JSON



\## 📞 Przykłady użycia



```bash

\# Pierwsza synchronizacja

python sync\_models.py "C:\\Users\\%USERNAME%\\.ollama\\models\\manifests" "C:\\Users\\%USERNAME%\\.ollama\\models\\blobs" "D:\\AI\\LMstudio"



\# Aktualizacja z nadpisywaniem

python sync\_models.py "C:\\Users\\%USERNAME%\\.ollama\\models\\manifests" "C:\\Users\\%USERNAME%\\.ollama\\models\\blobs" "D:\\AI\\LMstudio" --overwrite --clean



\# Tylko podgląd mappingu

python sync\_models.py "C:\\Users\\%USERNAME%\\.ollama\\models\\manifests" "C:\\Users\\%USERNAME%\\.ollama\\models\\blobs" "D:\\AI\\LMstudio" --debug

```

