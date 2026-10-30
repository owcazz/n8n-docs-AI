# Licznik wody Diehl IZAR -> Home Assistant (ESP32 + CC1101)

## Co mamy
- Licznik **Diehl Metering** (Qs 2,5 m³/h, „Grey Ring Meter”) z nakładką radiową **IZAR RC 868 I R4 PL**, S/N 06436027.
- Nakładka nadaje cyklicznie (w testach co 8 s; okres podaje sama, pole `transmit_period_s`) w **wM-Bus T1, 868,95 MHz**, protokół **PRIOS** (Diehl).
- Obsługuje ją sterownik `izar` z wmbusmeters, w ESPHome przez komponent
  [SzczepanLeon/esphome-components](https://github.com/SzczepanLeon/esphome-components) (v5).
- **Klucz AES nie jest potrzebny** — sterownik próbuje wbudowanych domyślnych kluczy PRIOS.
  Jeśli wodociągi ustawiły własny klucz, trzeba go od nich uzyskać.

Odczyt jest **pasywny** (tylko słuchamy tego, co nakładka i tak nadaje do inkasenta).
Niczego nie odkręcamy i nie ruszamy plomb na liczniku.

## Lista zakupów (~50–70 zł)
| Element | Uwagi |
|---|---|
| ESP32 DevKit (ESP32-WROOM-32, 30/38 pin) | dowolny klasyczny ESP32 |
| Moduł **CC1101 868 MHz** | koniecznie wersja **868**, nie 433! Najlepiej z gniazdem SMA |
| Antena 868 MHz | spiralka bywa w zestawie; lepsza prosta 1/4 fali (ok. 8,2 cm) |
| Przewody dupont F-F, zasilacz USB 5 V | |
| (opcja) obudowa | jeśli piwnica wilgotna — hermetyczna |

## Podłączenie CC1101 -> ESP32
| CC1101 | ESP32 |
|---|---|
| VCC | **3V3** (nigdy 5 V) |
| GND | GND |
| SCK | GPIO18 |
| MOSI / SI | GPIO23 |
| MISO / SO | GPIO19 |
| CSN | GPIO5 |
| GDO0 | GPIO4 |
| GDO2 | nie podłączać |

## Instalacja krok po kroku
1. W Home Assistant: Ustawienia → Dodatki → zainstaluj **ESPHome Device Builder**.
2. Nowe urządzenie → wklej `licznik-wody.yaml`, uzupełnij `secrets.yaml` (wzór: `secrets.example.yaml`).
3. Pierwsze wgranie przez USB (z przeglądarki Chrome/Edge), kolejne już po Wi-Fi.
4. ESP32 postaw jak najbliżej licznika, ale w zasięgu Wi-Fi.
5. HA sam wykryje urządzenie → „Skonfiguruj”.
6. Encję „Woda - stan licznika” dodaj w **Ustawienia → Panele → Energia → Zużycie wody**.

## Ustalenie ID licznika (obowiązkowe przy pierwszym uruchomieniu)
ID radiowe **nie jest** numerem z naklejki nakładki (06436027) ani z tarczy (C23FA 096256).
Przykład z testów wmbusmeters dla tej samej nakładki: ID `21242472`, a licznik `C19UA 145842`.
1. Wgraj konfigurację z `meter_id: 0x00000000`. Otwórz LOGI urządzenia w ESPHome.
2. Pojawią się linie `RAMKA RSSI=-xxdBm ...hex...` (IZAR nadaje co kilka–kilkanaście sekund).
3. Szukaj ramek z **najsilniejszym** sygnałem (RSSI najbliżej 0) i kodem producenta
   `304C` (SAP) lub `A511` (DME) na pozycji 3–4 bajtu.
4. Następne **4 bajty** to ID zapisane **od tyłu**.
   Przykład z testów: `1944 304C 72242421 ...` → ID `21242472` → `meter_id: 0x21242472`.
5. Wpisz ID, wgraj ponownie. Kontrola: encje „prefiks” i „numer licznika” powinny pokazać
   **C23FA** i **096256** — wtedy masz pewność, że czytasz swój licznik, a nie sąsiada.
6. Gdy działa — zakomentuj blok `on_frame`, żeby nie zaśmiecać logów.

## Co dostaniesz w HA
- stan licznika (m³) + statystyki dzienne/miesięczne w panelu Energia,
- stan na koniec poprzedniego miesiąca,
- **alarmy**: wyciek, przepływ wsteczny, ingerencja (fraud) — można podpiąć powiadomienie na telefon,
- żywotność baterii nakładki, siła sygnału.

## Gdzie postawić ESP32 (licznik w łazience)
- **Nie w łazience** — wilgoć i para szkodzą elektronice. Wystarczy pokój obok lub korytarz, przy gniazdku USB.
- Sygnał 868 MHz przechodzi przez 1–2 ściany bez problemu. Po uruchomieniu sprawdź encję
  „Woda - sygnał radiowy”: **powyżej -90 dBm** jest dobrze, poniżej -95 dBm przysuń ESP32 bliżej.
- Antenę CC1101 ustaw **pionowo**, z dala od metalowych rur i lustra.

## Uwagi
- Odczyt przychodzi tylko wtedy, gdy nakładka nadaje — to nie jest przepływomierz w czasie rzeczywistym.
- Sterownik `izar` w wmbusmeters ma następcę `izarv2`; komponent ESPHome na dziś (29.10.2026) zawiera tylko `izar` — to nie przeszkadza.
- Konfiguracja nie była kompilowana w tej sesji (ESPHome niedostępny w środowisku) — klucze YAML sprawdzone ze źródłem komponentu (commit 03484db, 29.10.2026).
