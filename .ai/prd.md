# Dokument wymagań produktu (PRD) - Bills

## 1. Przegląd produktu

Celem aplikacji "Bills" jest zautomatyzowanie i uproszczenie procesu monitorowania wydatków osobistych. Użytkownicy, robiąc zdjęcie paragonu i wysyłając je do bota na Telegramie, otrzymują automatyczną analizę swoich zakupów. System wykorzystuje technologię OCR do odczytu danych, a zaawansowane modele AI do kategoryzacji i normalizacji produktów. Wersja MVP (Minimum Viable Product) skupia się na użytkownikach indywidualnych. Głównym interfejsem jest bot na Telegramie, uzupełniony o prostą aplikację webową w trybie "tylko do odczytu", która służy do wizualizacji podsumowań. Produkt działa w modelu freemium, z darmowym limitem do 100 paragonów miesięcznie.

## 2. Problem użytkownika

Ręczne śledzenie codziennych wydatków jest czasochłonne, podatne na błędy i często zniechęcające. Ludzie tracą kontrolę nad swoimi finansami, ponieważ brakuje im prostego i szybkiego narzędzia do rejestrowania każdej transakcji. Istniejące rozwiązania często wymagają manualnego wprowadzania danych, co jest główną barierą. Aplikacja "Bills" rozwiązuje ten problem, automatyzując cały proces. Użytkownik musi jedynie zrobić zdjęcie paragonu, a system zajmuje się resztą: odczytuje każdą pozycję, przypisuje ją do odpowiedniej kategorii i zapisuje w bazie danych. Daje to użytkownikowi pełen wgląd w strukturę swoich wydatków przy minimalnym wysiłku.

## 3. Wymagania funkcjonalne

- F-01: Integracja z botem na Telegramie: Użytkownicy mogą wchodzić w interakcję z aplikacją za pośrednictwem bota, wysyłając zdjęcia paragonów i używając prostych komend tekstowych.
- F-02: Przetwarzanie paragonów: System automatycznie przetwarza obrazy paragonów przy użyciu Gemini API w celu ekstrakcji poszczególnych pozycji.
- F-03: Kategoryzacja i Normalizacja AI: Wykorzystanie modeli AI (OpenAI) do przypisywania każdej pozycji z paragonu do predefiniowanej kategorii oraz normalizacji nazwy produktu w oparciu o wewnętrzny "słownik produktów".
- F-04: Weryfikacja przez użytkownika: Pozycje, których system nie jest pewien, są prezentowane użytkownikowi w Telegramie w formie prostego interfejsu z przyciskami do potwierdzenia lub odrzucenia sugestii.
- F-05: Walidacja sumy: System sprawdza poprawność odczytu, porównując sumę wartości wszystkich pozycji z kwotą końcową widoczną na paragonie.
- F-06: Podsumowania wydatków: Użytkownik może generować proste raporty tekstowe (dzienne, tygodniowe, miesięczne) bezpośrednio w bocie.
- F-07: Aplikacja webowa "Read-Only": Użytkownicy mają dostęp do aplikacji webowej, która wizualizuje ich podsumowania wydatków. Aplikacja nie pozwala na edycję danych.
- F-08: Autoryzacja "Magic Link": Logowanie do aplikacji webowej odbywa się bezhasłowo. Użytkownik prosi bota o link do logowania, który jest mu wysyłany w prywatnej wiadomości na Telegramie.
- F-09: Model Freemium: System śledzi liczbę przetworzonych paragonów dla każdego użytkownika i ogranicza darmowe użycie do 100 paragonów miesięcznie.
- F-10: Zarządzanie kategoriami (Admin): Kategorie produktów są predefiniowane. Nowe kategorie mogą być dodawane i zarządzane wyłącznie przez administratora systemu. Produkty niepasujące do żadnej kategorii trafiają do domyślnej kategorii "Inne".
- F-11: Prywatność: System jest zaprojektowany tak, aby ignorować i nie przetwarzać danych osobowych (np. imię i nazwisko kasjera) z paragonów. Prosta polityka prywatności jest dostępna dla użytkownika za pomocą komendy w bocie.

## 4. Granice produktu

Następujące funkcje i cechy celowo nie wchodzą w zakres wersji MVP:

- Zaawansowana analiza trendów wydatków i prognozowanie.
- Wsparcie dla formatów innych niż zdjęcia (np. PDF, e-maile).
- Masowy import wielu paragonów jednocześnie.
- Interaktywne wykresy i zaawansowane wizualizacje danych.
- Możliwość tworzenia i zarządzania własnymi kategoriami przez użytkowników.
- Funkcjonalności dla grup lub współdzielenie budżetów.
- Eksport danych do formatów zewnętrznych, takich jak CSV czy Excel.
- Integracja z kontami bankowymi lub innymi systemami finansowymi.
- Obsługa wielu walut.

## 5. Historyjki użytkowników

### Rejestracja i Onboarding

- ID: US-001
- Tytuł: Pierwsze uruchomienie bota
- Opis: Jako nowy użytkownik, chcę po raz pierwszy uruchomić bota, aby otrzymać podstawowe informacje o jego działaniu i móc od razu z niego skorzystać.
- Kryteria akceptacji:
  1. Po wysłaniu komendy `/start`, bot wyświetla wiadomość powitalną.
  2. Wiadomość powitalna krótko wyjaśnia, co bot robi (przetwarza paragony) i jak to działa (wyślij zdjęcie).
  3. Wiadomość zawiera zachętę do wysłania pierwszego zdjęcia paragonu.
  4. Konto użytkownika jest tworzone w bazie danych po pierwszym uruchomieniu bota.

### Przetwarzanie paragonu

- ID: US-002
- Tytuł: Przesłanie paragonu do analizy
- Opis: Jako użytkownik, chcę wysłać zdjęcie paragonu do bota, aby system automatycznie odczytał i zapisał moje wydatki.
- Kryteria akceptacji:

  1. Mogę wysłać zdjęcie bezpośrednio w oknie czatu z botem.
  2. Po otrzymaniu zdjęcia bot natychmiast odpowiada komunikatem potwierdzającym, np. "Otrzymałem Twój paragon, przetwarzam...".
  3. Po pomyślnym przetworzeniu (bez pozycji do weryfikacji), bot wysyła podsumowanie odczytanych pozycji, ich kategorii i łącznej kwoty.
  4. Dane z paragonu są zapisywane w bazie danych i powiązane z moim kontem.

- ID: US-003
- Tytuł: Weryfikacja niepewnych pozycji
- Opis: Jako użytkownik, chcę mieć możliwość poprawienia lub potwierdzenia danych, jeśli system nie jest pewien co do odczytanej pozycji lub jej kategorii.
- Kryteria akceptacji:

  1. Jeśli system oflaguje pozycję jako niepewną, bot wysyła mi wiadomość z pytaniem o weryfikację.
  2. Wiadomość zawiera odczytaną nazwę produktu i proponowaną kategorię.
  3. Pod wiadomością znajdują się przyciski pozwalające mi "Potwierdzić" sugestię lub ją "Poprawić".
  4. Po potwierdzeniu, pozycja jest zapisywana w bazie z potwierdzonymi danymi.
  5. Wybranie opcji "Popraw" inicjuje dalszy dialog (poza zakresem MVP, w MVP odrzucenie może przypisać pozycję do "Inne" lub pozwolić na wpisanie nazwy). W MVP, odrzucenie przypisuje pozycję do kategorii "Inne".

- ID: US-004
- Tytuł: Obsługa nieudanej analizy paragonu
- Opis: Jako użytkownik, chcę otrzymać informację zwrotną, gdy wysłane przeze mnie zdjęcie jest nieczytelne lub system nie może go przetworzyć.
- Kryteria akceptacji:

  1. Jeśli OCR nie jest w stanie odczytać danych z paragonu (np. z powodu słabej jakości zdjęcia), bot wysyła komunikat o błędzie.
  2. Komunikat zawiera sugestie, jak zrobić lepsze zdjęcie (np. dobre oświetlenie, brak zagięć).
  3. W bazie danych nie są zapisywane żadne pozycje z nieudanego przetwarzania.

- ID: US-005
- Tytuł: Obsługa paragonu z nierozpoznanym produktem
- Opis: Jako użytkownik, chcę, aby system radził sobie z produktami, których nie potrafi automatycznie skategoryzować.
- Kryteria akceptacji:
  1. Jeżeli model AI nie jest w stanie przypisać kategorii do produktu, zostaje on automatycznie przypisany do domyślnej kategorii "Inne".
  2. Użytkownik jest informowany w podsumowaniu, że niektóre pozycje zostały zaklasyfikowane jako "Inne".

### Przeglądanie wydatków

- ID: US-006
- Tytuł: Generowanie podsumowania wydatków w bocie
- Opis: Jako użytkownik, chcę móc poprosić bota o proste podsumowanie moich wydatków z danego okresu.
- Kryteria akceptacji:

  1. Bot reaguje na komendy: `/dzis`, `/tydzien`, `/miesiac`.
  2. Po otrzymaniu komendy, bot wysyła tekstowe podsumowanie zawierające łączną kwotę wydatków w danym okresie.
  3. Podsumowanie zawiera również listę top 3 kategorii wydatków wraz z wydanymi w nich kwotami.

- ID: US-007
- Tytuł: Dostęp do aplikacji webowej
- Opis: Jako użytkownik, chcę zalogować się do aplikacji webowej, aby w bardziej przejrzystej formie zobaczyć moje podsumowania wydatków.
- Kryteria akceptacji:

  1. Bot reaguje na komendę `/login`.
  2. Po wysłaniu komendy `/login`, bot wysyła unikalny, jednorazowy link ("Magic Link").
  3. Kliknięcie linku otwiera aplikację webową i automatycznie mnie loguje.
  4. Sesja w aplikacji webowej wygasa po określonym czasie.

- ID: US-008
- Tytuł: Przeglądanie podsumowań w aplikacji webowej
- Opis: Jako zalogowany użytkownik, chcę widzieć w aplikacji webowej te same podsumowania, które są dostępne w bocie.
- Kryteria akceptacji:
  1. Aplikacja webowa wyświetla podsumowania dzienne, tygodniowe i miesięczne.
  2. Dane są prezentowane w czytelnej formie (np. lista, tabela).
  3. Aplikacja ma charakter "read-only" - nie mogę edytować ani dodawać żadnych danych.

### Ograniczenia i Polityka

- ID: US-009
- Tytuł: Osiągnięcie limitu darmowych paragonów
- Opis: Jako użytkownik darmowego planu, chcę wiedzieć, kiedy zbliżam się do miesięcznego limitu paragonów i co się stanie, gdy go przekroczę.
- Kryteria akceptacji:

  1. Gdy przetworzę 90. paragon w miesiącu, otrzymuję powiadomienie, że zbliżam się do limitu.
  2. Przy próbie wysłania 101. paragonu w miesiącu, bot informuje mnie o przekroczeniu limitu i odmawia przetworzenia.
  3. Komunikat o przekroczeniu limitu informuje, kiedy limit zostanie zresetowany (np. pierwszego dnia następnego miesiąca).

- ID: US-010
- Tytuł: Dostęp do polityki prywatności
- Opis: Jako użytkownik, chcę mieć łatwy dostęp do polityki prywatności, aby zrozumieć, jak przetwarzane są moje dane.
- Kryteria akceptacji:
  1. Bot reaguje na komendę `/prywatnosc`.
  2. Po jej użyciu, bot wysyła link do strony internetowej z polityką prywatności lub wyświetla jej treść bezpośrednio w czacie.

## 6. Metryki sukcesu

- MS-01: Dokładność automatycznego przetwarzania

  - Cel: 90% pozycji z paragonów jest automatycznie i prawidłowo odczytana, znormalizowana i skategoryzowana bez interwencji człowieka.
  - Pomiar: Regularny, ręczny audyt przeprowadzany przez administratora na losowej próbie 1% wszystkich przetworzonych paragonów. Wyniki automatu są porównywane ze stanem faktycznym na paragonie.

- MS-02: Minimalizacja interwencji użytkownika
  - Cel: Mniej niż 10% wszystkich przetworzonych pozycji wymaga ręcznej weryfikacji przez użytkownika.
  - Pomiar: Automatyczne śledzenie w systemie. Metryka jest obliczana jako stosunek liczby pozycji oflagowanych do weryfikacji do całkowitej liczby przetworzonych pozycji w danym okresie (np. tygodniowym).
