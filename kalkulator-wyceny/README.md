# Kalkulator wyceny projektu

Jednoplikowa strona (`index.html`) z formularzem, który zbiera od klienta dane
potrzebne do wstępnej wyceny projektu i na bieżąco pokazuje widełki cenowe,
rozbicie kwoty, orientacyjny czas realizacji oraz wstępną kwalifikację zapytania.

Brak zależności — czysty HTML, CSS i JavaScript. Wystarczy wrzucić plik na dowolny
hosting statyczny albo wkleić jako podstronę.

## Co ustawić na start

Wszystko siedzi w bloku `KONFIGURACJA` na początku `<script>` w `index.html`:

| Stała | Do czego służy |
| --- | --- |
| `KONTAKT.email` | adres, na który trafia zapytanie z przycisku „Wyślij zapytanie" (domyślnie `biuro@example.pl` — **zmień**) |
| `WEBHOOK_URL` | opcjonalny adres webhooka; pusty ciąg = wysyłka przez program pocztowy |
| `CENNIK` | stawki, mnożniki, minimum, dodatki, szerokość widełek |
| `OPISY_ZAKRESU` | teksty pod polem „Zakres opracowania" |

## Jak liczona jest cena

1. **Baza** — stawka za m² z progami marginalnymi (`CENNIK.progi`), malejąca wraz z metrażem,
   przemnożona przez współczynnik zakresu opracowania (koncepcja / budowlany / komplet / wykonawczy).
2. **Mnożniki** — typ obiektu, kondygnacje, piwnica, dach, bryła, standard, liczba pokoi i łazienek,
   warunki terenowe. Każdy widoczny w rozbiciu jako osobna pozycja.
3. **Minimum pracowni** — `CENNIK.minimum` przeskalowane mnożnikiem zakresu.
4. **Dopłaty kwotowe** — garaż, zagospodarowanie działki, dodatkowe opracowania, dojazdy.
5. **Tryb realizacji** — mnożnik na całość.
6. **Widełki** — ±`CENNIK.widelki` (domyślnie 8%), zaokrąglone do 500 zł.

Adaptacja projektu gotowego liczy się osobną, ryczałtową ścieżką (`CENNIK.adaptacja`).

## Kwalifikacja zapytania

Funkcja `kwalifikuj()` punktuje status działki, planowany start budowy i deklarowany budżet
względem wyliczonych widełek. Wynik (A / B / C) trafia do podsumowania wysyłanego na maila
lub webhook — klient widzi tylko życzliwy komunikat, nie ocenę.

Budżet poniżej 60% dolnych widełek od razu kieruje rozmowę na węższy zakres
(adaptacja projektu gotowego albo sama koncepcja).

## Podpięcie webhooka (np. n8n)

Ustaw `WEBHOOK_URL` na adres węzła Webhook. Strona wyśle `POST` z JSON-em:

```json
{
  "klient":   { "imie": "", "email": "", "telefon": "", "lokalizacja": "" },
  "wycena":   { "min": 0, "max": 0, "srodek": 0, "zaM2": 0, "tygodnie": [0, 0] },
  "kwalifikacja": "A",
  "budynek":  { "typ": "dom", "zakres": "komplet", "metraz": 160, "...": "" },
  "dzialka":  { "powierzchnia": 900, "status": "mam", "warunki": [] },
  "dodatki":  [],
  "termin": "standard",
  "budzet": "50000",
  "startBudowy": "6",
  "uwagi": "",
  "podsumowanie": "gotowy tekst do maila"
}
```

Jeśli żądanie się nie powiedzie, strona po cichu wraca do wysyłki mailem.
Uwaga: przy hostowaniu na innej domenie niż webhook trzeba włączyć CORS po stronie odbiornika.

## Skąd wzięły się stawki

Wartości domyślne w `CENNIK` są skalibrowane na publikacjach cenowych i cennikach
pracowni z 2025–2026 roku (stan na sierpień 2026). Poniżej co z czego wynika.

| Pozycja w `CENNIK` | Wartość | Dane rynkowe |
| --- | --- | --- |
| `progi` (stawka za m²) | 190 → 115 zł/m² malejąco | projekt indywidualny 150–300 zł/m² (250–350 zł/m² w największych miastach); inne źródła 60–250 zł/m² i 90–160 zł/m² za 2025 r. |
| kwota łączna, kontrolnie | 160 m² → 28–34,5 tys. zł | do 120 m²: 15–25 tys.; 120–180 m²: 22–35 tys.; powyżej 180 m²: 30–50 tys.; 300 m²: 45–75 tys. |
| `zakres.koncepcja` = 0.32 | 160 m² → ok. 72 zł/m² | koncepcja 50–90 zł/m², czyli zwykle 2–5 tys. zł przy małym domu |
| `zakres.wykonawczy` = 1.30 | +30% do kompletu | projekt wykonawczy to 20–95% ceny projektu budowlanego |
| `adaptacja.baza` = 4 200 zł | z dopłatami 4,2–8,8 tys. | adaptacja 2,5–10 tys. zł, średnio 5,2 tys. (3,9 tys. Białystok – 6,8 tys. Warszawa) |
| `minimumTypu.rozbudowa` | 30 m² → 8,5–10,5 tys. zł | rozbudowy do 30 m² wyceniane ryczałtem 8–12 tys. zł; 200–350 zł/m² powierzchni rozbudowy |
| `rynek` = 1.15 / 1.00 / 0.92 | ±15% | duże miasta 250–350 zł/m² wobec 150–300 zł/m² w reszcie kraju |
| Projekt wnętrz 200 zł/m² | — | 170–270 zł/m² brutto, 140–450 zł/m² netto, pakiety 190–215 zł/m² |
| Wizualizacje 3D 2 600 zł | 4 ujęcia | 500–950 zł za ujęcie zewnętrzne, ok. 650 zł w pakiecie 4+ |
| Nadzór autorski 4 500 zł | ok. 10 wizyt | 250–500 zł za wizytę; 0,5–2% wartości inwestycji |
| Świadectwo energetyczne 450 zł | — | dom jednorodzinny 349–500 zł, do 300 m² od 399 zł |
| Wniosek o WZ 1 200 zł | usługa, bez opłaty skarbowej | przygotowanie wniosku 500–1 500 zł; opłata skarbowa 598 zł (właściciel działki zwolniony) |
| Inwentaryzacja 2 200 zł + 16 zł/m² | — | inwentaryzacja 5–25 zł/m² zależnie od szczegółowości; ekspertyza techniczna 2–2,5 tys. zł |
| Projekt ogrodu 3 500 zł | — | projekt ogrodu 3–25 tys. zł, proste opracowania 1–2 tys. zł |
| Fotowoltaika i pompa ciepła 3 000 zł | — | projekt instalacji z pompą ciepła dla domu 150–200 m²: 4–6,5 tys. zł (tutaj tylko część wykraczająca poza standardowe branże) |

Kontrola zdroworozsądkowa: dokumentacja to zwykle 1–3% budżetu budowy, a stan deweloperski
w 2026 r. kosztuje 5–6,5 tys. zł/m². Dla domu 160 m² daje to budowę za ok. 800 tys.–1 mln zł
i projekt za 8–30 tys. zł — domyślne 28–34,5 tys. zł mieści się w górnej części tego pasma,
co odpowiada pełnemu komplet‑owi z branżami.

### Czego NIE potwierdzają dane rynkowe

Poniższe wartości to konwencja pracowni, nie liczby z cenników. Rynek potwierdza wyłącznie
kierunek („piwnica, wielospadowy dach i skomplikowana bryła podnoszą cenę"), nie wielkość dopłaty:

- `kondygnacje`, `piwnica`, `dach`, `bryla`, `standard` — wszystkie mnożniki,
- `pokojeStawka` i `lazienkiStawka`,
- `termin` (dopłata 15% / 30% za przyspieszenie),
- `typ` poza `rozbudowa` — mnożniki dla bliźniaka, budynku wielorodzinnego i usługowego
  są ekstrapolacją; rynek podaje dla nich tylko „od kilkunastu tysięcy do kilkuset tysięcy zł",
- `odleglosc` (dopłata za dojazdy), `dzialkaProgi`, `widelki` ±10%.

Jeśli masz historię własnych wycen, to ona jest lepszym źródłem niż powyższa tabela —
podziel honorarium z ostatnich projektów przez metraż i podstaw własne liczby.

### Źródła

Stawki projektowe: [z500.pl](https://z500.pl/ceny-u-architektow-zaskakuja-ile-kosztuje-projekt-domu),
[rankomat.pl](https://rankomat.pl/nieruchomosci/ile-kosztuje-projekt-domu),
[disinn.pl](https://www.disinn.pl/post/ile-kosztuje-indywidualny-projekt-domu),
[domynamiare.pl](https://domynamiare.pl/projekt-indywidualny-domu-koszt-2026/),
[architekt-krakow.eu](https://www.architekt-krakow.eu/208,Ile_kosztuje_indywidualny_projekt_domu_w_2026_roku_Kompleksowy_przewodnik_dla_Inwestorow.html),
[muratordom.pl](https://muratordom.pl/prawo/finanse/ile-zaplacisz-za-projekt-domu-jednorodzinnego-w-2025-diabel-tkwi-w-szczegolach-zwroc-uwage-na-dodatkowe-wydatki-aa-nzBw-bGPn-1MP7.html),
[archeton.pl](https://archeton.pl/blog/ile-kosztuje-stworzenie-projektu-domu-n25),
[architektbudowlany.pl](https://architektbudowlany.pl/architekt-cena-za-projekt),
[2hplus.pl](https://www.2hplus.pl/ile-kosztuje-projekt-architektoniczny/),
[form.pl](https://form.pl/artykuly/ile-kosztuje-projekt-domu-u-architekta-i-od-czego-zalezy-jego-cena/),
[adrem.org.pl](https://adrem.org.pl/ile-kosztuje-projekt-budowlany/),
[extradom.pl](https://www.extradom.pl/porady/artykul-ile-kosztuje-projekt-domu-porownanie-cen).

Adaptacja i rozbudowa: [potrzebaprojekty.pl](https://potrzebaprojekty.pl/blog/adaptacja-projektu-gotowego-cena/),
[zbudujsamdom.pl](https://www.zbudujsamdom.pl/ile-kosztuje-adaptacja-projektu-domu-w-2026-roku-realne-ceny-i-bledy-inwestorow/),
[cenauslug.pl](https://cenauslug.pl/budowa-i-remont/adaptacja-projektu-domu),
[wycennik.pl](https://wycennik.pl/ile-kosztuje-adaptacja-projektu-cennik/),
[maddar.pl](https://maddar.pl/ile-kosztuje-projekt-rozbudowy-domu/),
[przebudowanie.pl](https://przebudowanie.pl/projekt-przebudowy-domu-cena),
[new-house.com.pl](https://new-house.com.pl/blog-akademia-budowlana/post/3685).

Dodatki: [architektbudowlany.pl – wnętrza](https://architektbudowlany.pl/architekt-wnetrz-cena-za-m2),
[kaim.work](https://kaim.work/ile-kosztuje-projekt-wnetrza-w-2026-roku-pelny-cennik-architekta-wnetrz-w-krakowie/),
[prolevel-design.pl](https://prolevel-design.pl/ile-kosztuje-projekt-wnetrz-w-2026-kompleksowy-cennik-projektowania-wnetrz/),
[3d-archi.pl](https://3d-archi.pl/cennik/),
[bearstudio.pl](https://bearstudio.pl/blog/orientacyjne-ceny-wizualizacji-3d/),
[ladnydom.pl](https://ladnydom.pl/budowa/1,161894,11257384,Ile_kosztuje_obecnosc_architekta_na_budowie_domu_jednorodzinnego.html),
[mfinanse.pl](https://mfinanse.pl/blog/czym-jest-nadzor-autorski-na-budowie-i-ile-kosztuje/),
[rynekpierwotny.pl](https://rynekpierwotny.pl/wiadomosci-mieszkaniowe/nadzor-autorski-w-prawie-budowlanym/12501/),
[certyfikatujakuba.pl](https://certyfikatujakuba.pl/ile-kosztuje-swiadectwo-energetyczne-2026/),
[certyfikatomat.pl](https://certyfikatomat.pl/ile-kosztuje-swiadectwo-energetyczne/),
[zleca.pl](https://zleca.pl/cennik/przygotowanie-wniosku-o-warunki-zabudowy-cena),
[mgprojekt.com.pl](https://www.mgprojekt.com.pl/blog/warunki-zabudowy/),
[cenauslug.pl – inwentaryzacja](https://cenauslug.pl/dom-i-ogrod/inwentaryzacja-architektoniczna-wnetrz),
[wytwornia-zieleni.pl](https://wytwornia-zieleni.pl/wiedza/koszt-projektu-ogrodu),
[rgbudinstal.pl](https://rgbudinstal.pl/projekt-centralnego-ogrzewania-cena).

Metodyka i kontrola: [Zasady Wyceny Prac Projektowych SARP](https://www.sarp.pl/pliki/1_539ec5f989836-zwpp_sarp.pdf),
[Regulamin honorariów architekta IARP](https://www.izbaarchitektow.pl/pliki/regulamin_honorariow_architekta-procenty.pdf),
[koszt budowy 2026 – muratordom.pl](https://muratordom.pl/przed-budowa/organizacja-budowy/ile-naprawde-kosztuje-budowa-domu-w-2026-aktualne-ceny-za-m2-dane-gus-aa-XFYc-id2u-7v46.html),
[ongeo.pl](https://blog.ongeo.pl/ile-kosztuje-budowa-domu-2026-ceny-za-m2-przyklady).

## Zastrzeżenie

Wyceny są orientacyjne i nie stanowią oferty w rozumieniu Kodeksu cywilnego —
informacja o tym jest widoczna pod przyciskami w panelu.
