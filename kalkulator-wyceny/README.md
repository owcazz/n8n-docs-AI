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

## Zastrzeżenie

Wyceny są orientacyjne i nie stanowią oferty w rozumieniu Kodeksu cywilnego —
informacja o tym jest widoczna pod przyciskami w panelu.
