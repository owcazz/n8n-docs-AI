# Kalkulator wyceny projektu — kontekst dla kolejnej sesji

Ten plik jest po to, żeby ktokolwiek (człowiek albo Claude Code) mógł wejść w projekt
bez czytania historii rozmowy. Opisuje po co to powstało, co zostało ustalone,
co jest zrobione i gdzie są miny.

Stan na: sierpień 2026. Gałąź: `claude/project-pricing-calculator-qknthx`
w repo `owcazz/n8n-docs-AI` (fork dokumentacji n8n — kalkulator nie ma z nią nic wspólnego,
po prostu tam wylądował). Katalog: `kalkulator-wyceny/`.

## Po co to powstało

Zamawiający prowadzi pracownię projektową. Zapytania od klientów przychodziły luzem,
bez kompletu danych, i każde wymagało osobnej wymiany maili tylko po to, żeby ustalić
podstawy — metraż, kondygnacje, zakres. Część rozmów kończyła się niczym, bo dopiero
po tygodniu wychodziło, że klient ma budżet trzykrotnie mniejszy niż wycena.

Kalkulator ma robić dwie rzeczy naraz:

1. **Zebrać komplet danych** wejściowych do wyceny w jednym przejściu formularza.
2. **Odsiać zapytania**, które i tak nie skończą się zleceniem — zanim pochłoną czas
   na rozmowę. Ma to działać życzliwie: klient z małym budżetem dostaje propozycję
   węższego zakresu, a nie ciszę.

To ma być **wstępne wsparcie sprzedaży**, nie wiążąca oferta. Kwoty są orientacyjne
i jest to napisane wprost na stronie.

## Wytyczne, które padły od zamawiającego

- Dane do zebrania: wielkość działki, liczba kondygnacji, piwnica tak/nie, metraż,
  liczba pokoi, rodzaj dachu (płaski / dwuspadowy) „itp." — reszta pól to rozwinięcie
  tego kierunku, nie życzenie klienta.
- Wycena ma być **szybka i wstępna**.
- Ma służyć **odsiewaniu klientów**.
- Później doszło twarde wymaganie: **ceny mają być realne**, oparte na cennikach
  rynkowych, nie zmyślone. Pierwsza wersja miała stawki wzięte z sufitu i zamawiający
  to wychwycił — patrz „Kalibracja cen" niżej. **To jest wrażliwy punkt tego projektu.
  Nie wstawiaj do `CENNIK` liczb, których nie umiesz uzasadnić źródłem albo decyzją
  zamawiającego.**

## Co powstało

| Plik | Zawartość |
| --- | --- |
| `index.html` | cały kalkulator: HTML, CSS i JS w jednym pliku, zero zależności |
| `README.md` | konfiguracja, model liczenia, tabela źródeł stawek, lista wartości niepotwierdzonych |
| `CLAUDE.md` | ten plik |

Podgląd opublikowany jako Artifact:
<https://claude.ai/code/artifact/242f71f0-5d42-4578-af1b-ef79661094d2>

Historia: `3e9eec8` pierwsza wersja strony, `e5e2d72` kalibracja cen na dane rynkowe.

### Co strona robi

- Formularz w pięciu krokach: inwestycja i zakres → budynek → działka → dodatki i termin → kontakt.
- Panel wyceny przeliczany przy każdej zmianie: widełki, rozbicie kwoty pozycja po pozycji,
  stawka za m², czas realizacji w tygodniach, status kwalifikacji.
- Na mobile panel schodzi pod formularz, a na dole zostaje przyklejony pasek z kwotą.
- „Wyślij zapytanie" → POST na webhook, jeśli `WEBHOOK_URL` jest ustawiony, inaczej `mailto:`
  z gotowym podsumowaniem. „Kopiuj podsumowanie" → schowek.
- Motyw jasny i ciemny, sterowany `prefers-color-scheme` oraz `data-theme` na `<html>`.

## Mapa `index.html`

Numery linii z ostatniego commita — po edycjach będą się przesuwać, trzymaj się nagłówków.

| Zakres | Co tam jest |
| --- | --- |
| 12–110 | tokeny CSS: paleta jasna, `@media (prefers-color-scheme: dark)`, `[data-theme="dark"]` |
| 111–319 | style: nagłówek, układ, formularz, pigułki radio, panel wyceny, pasek mobilny |
| 320–636 | HTML formularza (pięć `<section class="krok">`) i `<aside>` z panelem |
| 637–670 | trzy karty objaśnień pod formularzem |
| 671–737 | **blok KONFIGURACJA**: `KONTAKT`, `WEBHOOK_URL`, `CENNIK`, `ETYKIETY`, `OPISY_ZAKRESU` |
| 739–1089 | logika: `pobierz`, `bazaZaMetraz`, `stan`, `policz`, `kwalifikuj`, `podsumowanie`, `odswiez` |

Kluczowe funkcje:

- `stan()` — czyta cały formularz do jednego obiektu. Radio i select zwracają `{v, t}`
  (wartość + widoczna etykieta), bo etykiety trafiają wprost do rozbicia wyceny.
- `policz(s)` — cała matematyka, zwraca `{poz, kwota, min, max, tMin, tMax, perM2, adaptacja}`.
- `kwalifikuj(s, w)` — punktacja leada, zwraca klasę koloru, ocenę A/B/C i teksty dla klienta.
- `podsumowanie(s, w, k)` — tekst wysyłany mailem lub webhookiem; **tu jest ocena A/B/C,
  której klient nie widzi na ekranie**.
- `odswiez()` — jedyne miejsce, które dotyka DOM-u panelu. Wołane przy każdym `input`/`change`.

## Model liczenia

Kolejność ma znaczenie, bo mnożniki są nakładane po kolei i każdy zapisuje swoją deltę
jako osobną pozycję w rozbiciu:

1. **Baza** — `bazaZaMetraz()` sumuje progi marginalne (jak progi podatkowe, żeby nie było
   skoku ceny na granicy), potem mnożnik zakresu opracowania.
2. **Mnożniki** — typ obiektu, lokalizacja rynkowa, kondygnacje, piwnica, dach, bryła,
   standard, liczba pokoi i łazienek, warunki terenowe z `data-mnoznik`.
3. **Minimum** — `CENNIK.minimum × mnożnik zakresu × CENNIK.minimumTypu[typ]`.
   Skalowanie jest istotne: bez niego sama koncepcja kosztowała tyle, co pełny projekt,
   a rozbudowa 30 m² wpadała w minimum dla nowego domu.
4. **Kwoty stałe** — garaż, zagospodarowanie działki wg progów, warunki z `data-kwota`,
   dodatki (`data-kwota` i `data-za-m2` sumują się, jeśli oba są na jednym checkboxie),
   dojazdy.
5. **Tryb realizacji** — mnożnik na całość.
6. **Widełki** — ±`CENNIK.widelki`, zaokrąglone do 500 zł.

Adaptacja projektu gotowego ma osobną ścieżkę ryczałtową i pomija cały rachunek za m².

## Kalibracja cen — historia i status

Pierwsza wersja miała stawki zmyślone (300 → 180 zł/m², minimum 22 000 zł) i dawała
44 500 – 52 000 zł za dom 160 m² — wyraźnie powyżej rynku. Po researchu stawki zeszły
do 190 → 115 zł/m², minimum 16 000 zł, a domyślny scenariusz daje **28 000 – 34 500 zł**.

Punkty kontrolne, na których to sprawdzono (wszystkie mieszczą się w publikowanych pasmach):

| Scenariusz | Wynik | Pasmo rynkowe |
| --- | --- | --- |
| 100 m², komplet | 19 000 – 23 500 zł | do 120 m²: 15–25 tys. |
| 160 m², komplet | 28 000 – 34 500 zł | 120–180 m²: 22–35 tys. |
| 200 m², komplet | 33 500 – 40 500 zł | powyżej 180 m²: 30–50 tys. |
| 300 m², komplet | 45 500 – 56 000 zł | 300 m²: 45–75 tys. |
| 160 m², koncepcja | 72 zł/m² | koncepcja: 50–90 zł/m² |
| adaptacja | 4 000 – 4 500 zł | 2,5–10 tys., średnio 5,2 tys. |
| rozbudowa 30 m² | 8 500 – 10 500 zł | ryczałt 8–12 tys. |

**Jeśli zmieniasz `CENNIK.progi`, `minimum` albo mnożniki zakresu — przelicz te siedem
scenariuszy ponownie.** Recepta na test jest niżej.

Pełna tabela „wartość → dane rynkowe → źródło" siedzi w `README.md`. Tam też jest lista
wartości, których **żadne źródło nie potwierdza** (mnożniki za piwnicę, dach, bryłę,
standard, kondygnacje, pokoje, tryb ekspresowy, dojazdy, progi działki). Rynek potwierdza
tylko kierunek, nie wielkość dopłaty. Nie udawaj, że jest inaczej.

Research prowadzony był wyszukiwarką — w tamtej sesji proxy blokowało otwieranie stron,
więc cenniki pojedynczych pracowni i PDF „Zasad Wyceny Prac Projektowych SARP" nie zostały
przeczytane bezpośrednio. Jeśli masz dostęp do sieci, wejście w te źródła jest najtańszym
sposobem na poprawę kalibracji.

## Decyzje, których nie cofaj bez powodu

- **Jeden plik, zero zależności.** Ma się otwierać dwuklikiem i wgrywać na dowolny hosting
  statyczny. Żadnego builda, frameworka ani npm.
- **Wszystko po polsku** — nazwy funkcji, zmiennych, klas CSS i komentarze też.
  Trzymaj konwencję, mieszanka języków w tym pliku wygląda fatalnie.
- **Cała konfiguracja w jednym bloku na górze skryptu.** Zamawiający ma stroić ceny sam,
  bez szukania liczb po kodzie. Nie rozsypuj stawek po funkcjach.
- **Ocena leada A/B/C nie jest pokazywana klientowi.** Na ekranie jest życzliwy komunikat,
  ocena idzie tylko do podsumowania dla pracowni. To celowe.
- **Markery `<!-- ARTIFACT:HEAD -->` i `<!-- ARTIFACT:BODY -->`** służą do wycięcia wersji
  bez `<html>`/`<head>`/`<body>` przy publikacji jako Artifact. Nie usuwaj ich.
- **Motyw ciemny przez tokeny.** Kolory definiowane wyłącznie wewnątrz `@media` albo
  `[data-theme]` dają nieczytelną stronę u części odbiorców — trzymaj każdą barwę w tokenie
  z `:root`.

## Jak testować

Nie ma frameworka testowego. Sprawdzanie szło przez headless Chromium — działa i jest szybkie:

```bash
# wynik liczenia dla podstawionych wartości
python3 - <<'PY'
import io
s=io.open('index.html',encoding='utf-8').read()
test='''<div id="wynik"></div><script>
function ustaw(z){for(const [k,v] of Object.entries(z)){const el=form.elements[k];
 if(typeof el.length==="number"&&!el.tagName){[...el].find(x=>x.value===v).checked=true}else el.value=v}
 odswiez();return document.getElementById("kwota-tekst").textContent}
document.getElementById("wynik").textContent=[
  "160m2: "+ustaw({}),
  "300m2: "+ustaw({metraz:"300"}),
  "adaptacja: "+ustaw({zakres:"adaptacja"})
].join(" ||| ");
</script>'''
io.open('/tmp/test.html','w',encoding='utf-8').write(s.replace('</body>',test+'</body>'))
PY

chromium --headless --no-sandbox --virtual-time-budget=2500 \
  --dump-dom file:///tmp/test.html | grep -o 'id="wynik">[^<]*'

# zrzut ekranu, motyw jasny i ciemny (ciemny: podmień <html lang="pl"> na data-theme="dark")
chromium --headless=new --no-sandbox --hide-scrollbars --virtual-time-budget=4000 \
  --window-size=1400,1600 --screenshot=/tmp/light.png file://$PWD/index.html
```

Sprawdź też składnię JS po większej zmianie: wytnij zawartość `<script>` do pliku
i puść `node --check`.

## Co dalej — otwarte wątki

Uporządkowane od najbardziej wartościowego:

1. **Podstawić prawdziwe stawki zamawiającego.** Honorarium z ostatnich 5–10 projektów
   podzielone przez metraż da lepszą bazę niż mediany rynkowe. To jest najważniejsza
   rzecz do zrobienia i wymaga danych od zamawiającego — zapytaj, jeśli ich nie masz.
2. **`KONTAKT.email` to nadal `biuro@example.pl`.** Bez podmiany przycisk wysyłki otwiera
   pocztę bez adresata. Blokuje wypuszczenie strony do klientów.
3. **Podpięcie webhooka n8n.** `WEBHOOK_URL` jest przygotowany, struktura JSON opisana
   w `README.md`. Wymaga CORS po stronie odbiornika. Zamawiający ma konektor n8n,
   ale w sesji, w której to powstawało, nie był autoryzowany.
4. **Mnożniki bryły, dachu i piwnicy** — dziś to konwencja. Jeśli zamawiający poda,
   ile realnie dolicza za piwnicę czy dach wielospadowy, to najprostsza droga do wyceny,
   która trafia w jego własny cennik.
5. **Zapis leadów.** Dziś zapytanie idzie mailem albo webhookiem i tyle — nie ma żadnej
   listy. Jeśli pojawi się potrzeba historii, to raczej po stronie n8n niż w przeglądarce.
6. Drobne: brak walidacji formatu telefonu, brak wersji do druku/PDF podsumowania,
   pasek skali w panelu ma zakres na sztywno w `CENNIK.skala` i przy nietypowych
   inwestycjach dobija do krańca.

## Czego nie robić

- Nie dopisuj do `CENNIK` liczb „na oko". Jeśli musisz coś oszacować, oznacz to
  w `README.md` w sekcji wartości niepotwierdzonych.
- Nie pokazuj klientowi oceny A/B/C ani punktacji.
- Nie obiecuj na stronie, że wycena jest wiążąca — zastrzeżenie pod przyciskami
  jest tam celowo i ma zostać.
