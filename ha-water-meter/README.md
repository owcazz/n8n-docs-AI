# Licznik wody Diehl IZAR → Home Assistant — kompletna instrukcja

Co budujemy: mały odbiornik radiowy (ESP32 + moduł CC1101), który **podsłuchuje** to, co nakładka
radiowa na Twoim liczniku i tak nadaje dla inkasenta, i wysyła odczyt do Home Assistanta.
Niczego nie rozkręcamy, nie ruszamy plomb — odbiór jest całkowicie pasywny.

Pliki w tym folderze:

| Plik | Do czego |
|---|---|
| `README.md` | ta instrukcja |
| `licznik-wody.yaml` | gotowa konfiguracja ESPHome (do wklejenia) |
| `secrets.example.yaml` | wzór pliku z hasłami |

---

## 1. Co mamy (z Twoich zdjęć)

- Licznik **Diehl Metering**, Qs = 2,5 m³/h, R160, klasa T30, naklejka „Grey Ring Meter”.
  Na tarczy: prefiks **C23FA**, numer **096256**, stan ok. 393 m³.
- Nakładka radiowa **IZAR RC 868 I R4 PL**, S/N 06436027, bateria litowa.
- Nakładka nadaje w standardzie **wM-Bus, tryb T1, 868,95 MHz**, protokołem Diehla (PRIOS).
  W testach wmbusmeters taka nakładka nadaje co **8 sekund**.
- Dokładnie ten model jest na liście obsługiwanych liczników projektu wmbusmeters
  („Diehl/Sappel IZAR RC 868 I R4 PL and R3 (izar)”), a jego sterownik `izar` jest
  wbudowany w komponent ESPHome, którego użyjemy.
- **Klucz szyfrujący nie jest potrzebny.** Sterownik `izar` ma wbudowane domyślne klucze Diehla
  i próbuje ich sam. Klucz od wodociągów byłby potrzebny tylko wtedy, gdyby go zmienili
  (rzadkie — jeśli po ustawieniu ID dane nie będą się dekodować, wrócimy do tego).

---

## 2. Zakupy (ok. 50–80 zł)

| # | Element | Na co uważać |
|---|---|---|
| 1 | **ESP32 DevKit** (ESP32-WROOM-32, 30- lub 38-pinowy, „ESP32 DevKitC”) | zwykły, klasyczny ESP32 z portem micro-USB/USB-C. Nie ESP8266, nie ESP32-C3/S3 (inne piny). |
| 2 | **Moduł CC1101 na 868 MHz** | **Koniecznie wersja 868 MHz**, nie 433 MHz — wyglądają identycznie, różnią się tylko opisem. Wybierz wersję z gniazdem antenowym SMA/IPEX, nie z lutowaną spiralką. |
| 3 | **Antena 868 MHz** | najlepiej prosta „pałka” SMA 868 MHz (ok. 8–10 cm). Jeśli moduł ma IPEX — dokup przejściówkę IPEX→SMA. |
| 4 | Przewody dupont **żeńsko-żeńskie**, 8 szt. (min. 10 cm) | do połączenia bez lutowania |
| 5 | Ładowarka USB 5 V + kabel do ESP32 | zwykła ładowarka od telefonu |
| 6 | (opcja) pudełko instalacyjne | zamknięcie całości w plastikowej obudowie — bez metalu wokół anteny |

Raster pinów CC1101 to zwykle **2 mm**, nie 2,54 mm — dupont F-F zwykle wchodzi, ale dociskaj
delikatnie. Jeśli wolisz pewność, kup CC1101 opisany jako „pin pitch 2.54 mm”.

---

## 3. Podłączenie („co z czym”)

Zasilanie CC1101 **wyłącznie z pinu 3V3** ESP32. Podanie 5 V uszkadza moduł.

```
      CC1101 (868 MHz)                       ESP32 DevKit
      ┌──────────────┐                     ┌──────────────┐
      │ VCC  ●───────┼──── czerwony ───────┼─● 3V3        │
      │ GND  ●───────┼──── czarny ─────────┼─● GND        │
      │ SCK  ●───────┼──── żółty ──────────┼─● GPIO18     │
      │ MOSI ●───────┼──── zielony ────────┼─● GPIO23     │   (na CC1101 może być "SI")
      │ MISO ●───────┼──── niebieski ──────┼─● GPIO19     │   (na CC1101 może być "SO")
      │ CSN  ●───────┼──── biały ──────────┼─● GPIO5      │   (może być "CS")
      │ GDO0 ●───────┼──── pomarańczowy ───┼─● GPIO4      │
      │ GDO2 ●       │  (nie podłączać)    │              │
      └──────────────┘                     └──────────────┘
```

| CC1101 | ESP32 | Rola |
|---|---|---|
| VCC | **3V3** | zasilanie 3,3 V |
| GND | GND | masa |
| SCK (SCLK) | GPIO18 | zegar SPI |
| MOSI (SI) | GPIO23 | dane ESP32 → CC1101 |
| MISO (SO) | GPIO19 | dane CC1101 → ESP32 |
| CSN (CS) | GPIO5 | wybór układu |
| GDO0 | GPIO4 | przerwanie „są dane” |
| GDO2 | — | niepodłączone (komponent go nie używa) |

Kolory przewodów są tylko propozycją, żeby się nie pomylić. Liczą się opisy pinów.
Opisy pinów na ESP32 są nadrukowane obok każdego pinu („D18”, „D23”, „D19”, „D5”, „D4”, „3V3”, „GND”).

Przed podaniem zasilania sprawdź dwa razy: **VCC → 3V3** i **GND → GND**.

### Lutowanie — czy w ogóle trzeba?

- **ESP32 DevKit** zwykle przychodzi z **wlutowanymi** listwami pinów. Jeśli listwy są luzem w torebce,
  trzeba je wlutować: listwę wsadź w płytkę stykową (breadboard), nałóż ESP32, lutuj po kolei
  każdy pin (lutownica 300–350 °C, cyna z topnikiem, 1–2 s na pin).
- **CC1101** ma zwykle **wlutowany** grzebień 2×4 piny o rastrze **2 mm**. Przewody dupont (2,54 mm)
  wchodzą na nie, ale luźno. Dwa sposoby na pewne połączenie:
  1. **Bez lutowania** — nałóż dupont F-F i zabezpiecz kroplą kleju na gorąco lub taśmą; do testów wystarczy.
  2. **Z lutowaniem (docelowo)** — odlutuj grzebień albo kup CC1101 bez pinów i przylutuj
     **7 przewodów bezpośrednio do padów** (VCC, GND, SCK, MOSI, MISO, CSN, GDO0), drugi koniec
     do pinów ESP32. To najpewniejsze połączenie i polecam je na stałe.
- Jeżeli CC1101 ma złącze antenowe **IPEX/U.FL**, nic nie lutujesz — antena wpina się na wcisk
  (przez przejściówkę IPEX→SMA). Jeśli ma tylko pady pod antenę bez złącza, przylutuj do pada ANT
  kawałek sztywnego drutu o długości **8,2 cm** (ćwierć fali 868 MHz) — to działa zaskakująco dobrze.
- **Nigdy nie lutuj przy podłączonym zasilaniu.** Po lutowaniu sprawdź multimetrem, że VCC i GND nie są zwarte.

---

## 4. Przygotowanie ESPHome (w Home Assistant)

Masz już dodatek ESPHome Device Builder, więc:

1. Otwórz **ESPHome Device Builder** w HA.
2. Prawy górny róg → **Secrets** (ikona klucza). Wklej i uzupełnij:

   ```yaml
   wifi_ssid: "NazwaTwojegoWiFi"
   wifi_password: "HasloWiFi"
   ap_password: "HasloAwaryjne12"
   api_key: "WKLEJ_WYGENEROWANY_KLUCZ"
   ota_password: "HasloDoAktualizacji"
   ```

   `api_key` wygeneruj tak: **+ New device → Continue → nazwa dowolna → Skip** — ESPHome pokaże
   w utworzonym szkicu linię `key: "xxxx…="`. Skopiuj tę wartość do `api_key` w Secrets, a sam
   szkic możesz skasować. (Alternatywnie: w terminalu `openssl rand -base64 32`.)

3. **+ New device → Continue** → nazwa `licznik-wody` → wybierz **ESP32** → **Skip** (bez instalacji).
4. Na kafelku `licznik-wody` kliknij **Edit**, skasuj całą zawartość i wklej **cały** plik
   `licznik-wody.yaml` (jest też w sekcji 10 poniżej). **Save**.
5. Kliknij **Validate** — powinno być zielone `Configuration is valid!`.
   Jeśli nie — skopiuj błąd i wyślij mi go, to poprawię.

---

## 5. Pierwsze wgranie (przez USB)

Pierwsze wgranie musi iść kablem USB, bo płytka nie ma jeszcze Wi-Fi. Kolejne idą już „po powietrzu”.

1. Podłącz ESP32 kablem USB do komputera (najlepiej Windows/Mac z **Chrome lub Edge**;
   Firefox nie obsługuje Web Serial).
2. W ESPHome na kafelku `licznik-wody` → **Install** → **Plug into this computer**.
3. Przeglądarka poprosi o wybór portu — zaznacz ten z „CP210x” / „CH340” / „USB Serial” i **Connect**.
4. Kompilacja trwa pierwszym razem **5–15 minut** (komponent wM-Bus jest duży). To normalne.
5. Po wgraniu płytka restartuje się, łączy z Wi-Fi i pojawia się jako **Online**.

Gdyby przeglądarka nie widziała portu: zainstaluj sterownik USB (CP210x lub CH340 — zależnie od
płytki, nazwa jest w Menedżerze urządzeń), a jeśli dalej nic — przytrzymaj przycisk **BOOT** na
płytce w momencie klikania Connect.

---

## 6. Dodanie urządzenia do Home Assistant

1. HA zwykle sam pokaże powiadomienie **„Wykryto nowe urządzenie: licznik-wody”** w
   Ustawienia → Urządzenia i usługi. Kliknij **Skonfiguruj** → gotowe.
2. Jeśli nie wykryje: Ustawienia → Urządzenia i usługi → **+ Dodaj integrację** → **ESPHome** →
   wpisz `licznik-wody.local` → dalej → wklej `api_key`.

Na tym etapie encje licznika będą jeszcze **puste** — to normalne, bo nie znamy jeszcze ID.

---

## 7. Ustalenie ID licznika (obowiązkowe, 5 minut)

ID radiowe **nie jest** ani numerem z naklejki nakładki (06436027), ani numerem z tarczy (096256).
Trzeba je odczytać z eteru. Konfiguracja startowa ma `meter_id: 0x00000000` i wypisuje w logu
**każdą** odebraną ramkę.

1. ESP32 postaw w pokoju obok łazienki (sekcja 9), podłącz do ładowarki.
2. W ESPHome na kafelku `licznik-wody` → **Logs** → **Wirelessly**.
3. Po kilkunastu sekundach pojawią się linie w stylu:

   ```
   [I][main]: RAMKA RSSI=-62dBm 1944304C72242421D401A2013D4013DD8B46A4999C1293E582CC
   [I][main]: RAMKA RSSI=-91dBm 2944A511780729662366A20118001378D3B3DB8CED...
   ```

   (To są prawdziwe ramki testowe z projektu wmbusmeters dla tej nakładki — Twoje będą miały
   inne cyfry, ale ten sam układ.)

4. Jak czytać ramkę — rozbij ciąg na pary znaków (bajty):

   ```
   19 44 30 4C 72 24 24 21 D4 01 A2 ...
   │  │  └──┬──┘ └────┬────┘
   │  │     │         └── ID licznika, zapisane OD TYŁU  →  21 24 24 72  →  ID = 21242472
   │  │     └── kod producenta: 30 4C = SAP (Sappel/Diehl) lub A5 11 = DME (Diehl Metering)
   │  └── 44 = typ ramki (zawsze 44 dla naszych)
   └── długość
   ```

   Czyli: bajty **5–8** (po `44` i po kodzie producenta) odwracasz kolejnością i to jest ID.

5. Ramek może być kilka — od sąsiadów też. **Twoja to ta z najsilniejszym sygnałem**
   (RSSI najbliżej zera, np. `-55` to mocniej niż `-90`) i powtarzająca się co ok. 8 s.
6. W konfiguracji podmień:

   ```yaml
   meter_id: 0x21242472      # ← Twoje ID odczytane z logu
   ```

7. **Install → Wirelessly**. Po restarcie w HA powinny pojawić się wartości.
8. **Kontrola, że to Twój licznik, a nie sąsiada:** w HA encje
   *Woda - prefiks licznika* i *Woda - numer licznika* muszą pokazać **C23FA** i **096256**
   (to z tarczy Twojego licznika), a *Woda - stan licznika* ok. **393 m³** (tyle było na zdjęciu;
   plus to, co zużyłeś od tego czasu). Jeśli nie — weź następną ramkę z listy.
9. Gdy działa, **zakomentuj** blok `on_frame:` w `wmbus_radio:` (6 linii), żeby nie zaśmiecać
   logów, i wgraj jeszcze raz.

Jeśli nie chcesz liczyć bajtów ręcznie — wklej mi 3–4 linie `RAMKA` z logów, odczytam ID za Ciebie.

---

## 8. Co dostajesz w Home Assistant i jak to wykorzystać

Encje urządzenia *Licznik wody*:

| Encja | Co pokazuje |
|---|---|
| Woda - stan licznika | stan w m³ (3 miejsca po przecinku = litry) |
| Woda - stan na koniec miesiąca | stan zapisany przez nakładkę na koniec poprzedniego miesiąca |
| Woda - alarmy | `no_alarm` albo np. `leakage`, `back_flow`, `meter_blocked`, `mechanical_fraud` |
| Woda - alarmy wcześniejsze | alarmy z poprzedniego okresu |
| Woda - bateria nakładki | szacowane lata pracy baterii |
| Woda - sygnał radiowy | RSSI w dBm (diagnostyka) |
| Woda - prefiks / numer licznika | do kontroli, że czytasz swój licznik |

**Panel Energia (zużycie dzienne/tygodniowe/miesięczne):**
Ustawienia → Panele → **Energia** → sekcja **Zużycie wody** → *Dodaj źródło wody* →
wybierz **Woda - stan licznika**. Po kilku godzinach pojawią się słupki zużycia.

**Powiadomienie o wycieku na telefon** (Ustawienia → Automatyzacje → nowa → edytuj w YAML):

```yaml
alias: Woda - alarm wycieku
triggers:
  - trigger: state
    entity_id: sensor.woda_alarmy_wyciek_cofka_ingerencja
    not_to: "no_alarm"
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable', ''] }}"
actions:
  - action: notify.notify
    data:
      title: "Licznik wody"
      message: "Alarm z licznika: {{ trigger.to_state.state }}"
mode: single
```

(Nazwę encji `sensor.woda_alarmy_...` sprawdź w HA po dodaniu urządzenia — HA tworzy ją z nazwy,
może się minimalnie różnić. Zamiast `notify.notify` możesz wpisać swój telefon, np.
`notify.mobile_app_thinkphone`.)

---

## 9. Gdzie postawić ESP32 (licznik w łazience)

- **Nie w łazience** — para i wilgoć szkodzą elektronice. Pokój obok lub korytarz, przy gniazdku.
- Sygnał 868 MHz przechodzi przez 1–2 ściany bez problemu. Orientacyjnie: RSSI
  **powyżej -90 dBm** jest dobrze, poniżej -95 dBm przysuń ESP32 bliżej lub zmień antenę.
- Antenę ustaw **pionowo**, z dala od metalowych rur, lustra, grzejnika.
- Nie zamykaj w metalowej puszce; plastikowa obudowa jest OK.

---

## 10. Pełna konfiguracja `licznik-wody.yaml`

Ta sama treść jest w pliku obok — tu dla kompletności.

```yaml
# ESP32 + CC1101 (868 MHz) -> Home Assistant
# Licznik: Diehl Metering z nakładką radiową IZAR RC 868 I R4 PL (S/N nakładki 06436027)
# Komponent: SzczepanLeon/esphome-components (wersja 5, gałąź main), sterownik "izar"

substitutions:
  name: licznik-wody
  friendly_name: Licznik wody

esphome:
  name: ${name}
  friendly_name: ${friendly_name}

esp32:
  board: esp32dev
  framework:
    type: esp-idf          # komponent wmbus v5 działa tylko na esp-idf (bez Arduino)

external_components:
  - source: github://SzczepanLeon/esphome-components@main
    components: [wmbus_radio, wmbus_common, wmbus_meter]
    refresh: 1d

logger:
  level: DEBUG
  logs:
    CC1101: ERROR          # wycisza ostrzeżenia "RX timeout after 0 bytes"

api:
  encryption:
    key: !secret api_key

ota:
  - platform: esphome
    password: !secret ota_password

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  power_save_mode: none    # radio odbiera ciągle - oszczędzanie Wi-Fi przeszkadza
  ap:
    ssid: ${name}-ap
    password: !secret ap_password

captive_portal:

# --- CC1101 ---------------------------------------------------------------
# Połączenia (CC1101 -> ESP32):
#   VCC  -> 3V3   (NIE 5V!)
#   GND  -> GND
#   SCK  -> GPIO18
#   MOSI -> GPIO23   (na niektórych płytkach opisane SI)
#   MISO -> GPIO19   (SO)
#   CSN  -> GPIO5    (CS)
#   GDO0 -> GPIO4    (przerwanie, irq_pin)
#   GDO2 -> niepodłączone (komponent go nie używa)
spi:
  clk_pin: GPIO18
  mosi_pin: GPIO23
  miso_pin: GPIO19

wmbus_radio:
  radio_type: CC1101
  cs_pin:
    number: GPIO5
    ignore_strapping_warning: true
  irq_pin: GPIO4
  frequency: 868.950MHz    # tryb T1 - tak nadaje IZAR
  # ETAP 1: loguje KAŻDĄ odebraną ramkę, żeby znaleźć ID licznika.
  # Po ustaleniu ID możesz ten blok zakomentować.
  on_frame:
    - then:
        - logger.log:
            format: "RAMKA RSSI=%ddBm %s"
            args: [ 'frame->rssi()', 'frame->as_hex().c_str()' ]

wmbus_common:
  drivers:
    - izar                 # kompiluj tylko potrzebny sterownik

# --- Licznik --------------------------------------------------------------
wmbus_meter:
  - id: woda
    # ID radiowe wM-Bus - INNE niż numery z naklejek! Odczytaj je z logów
    # (ETAP 1, instrukcja w README.md) i wpisz tutaj, np. 0x21242472.
    meter_id: 0x00000000
    type: izar
    # Klucz NIE jest potrzebny: sterownik izar ma wbudowane domyślne klucze
    # PRIOS Diehla. Wpisz key: tylko jeśli wodociągi zmieniły klucz.

sensor:
  - platform: wmbus_meter
    parent_id: woda
    field: total_m3
    name: Woda - stan licznika
    unit_of_measurement: "m³"
    device_class: water
    state_class: total_increasing
    accuracy_decimals: 3
    icon: mdi:water

  - platform: wmbus_meter
    parent_id: woda
    field: last_month_total_m3
    name: Woda - stan na koniec miesiąca
    unit_of_measurement: "m³"
    device_class: water
    accuracy_decimals: 3

  - platform: wmbus_meter
    parent_id: woda
    field: remaining_battery_life_y
    name: Woda - bateria nakładki
    unit_of_measurement: "lat"
    accuracy_decimals: 1
    entity_category: diagnostic

  - platform: wmbus_meter
    parent_id: woda
    field: rssi_dbm
    name: Woda - sygnał radiowy
    unit_of_measurement: "dBm"
    device_class: signal_strength
    state_class: measurement
    entity_category: diagnostic

  - platform: wifi_signal
    name: Licznik wody - Wi-Fi
    update_interval: 120s
    entity_category: diagnostic

text_sensor:
  # Kontrola, że to Twój licznik: powinno pokazać C23FA / 096256 (z tarczy)
  - platform: wmbus_meter
    parent_id: woda
    field: prefix
    name: Woda - prefiks licznika
    entity_category: diagnostic

  - platform: wmbus_meter
    parent_id: woda
    field: serial_number
    name: Woda - numer licznika
    entity_category: diagnostic

  - platform: wmbus_meter
    parent_id: woda
    field: current_alarms
    name: Woda - alarmy (wyciek, cofka, ingerencja)

  - platform: wmbus_meter
    parent_id: woda
    field: previous_alarms
    name: Woda - alarmy wcześniejsze

binary_sensor:
  - platform: status
    name: Licznik wody - online
```

---

## 11. Rozwiązywanie problemów

| Objaw | Co sprawdzić |
|---|---|
| `Validate` zgłasza błąd | wyślij mi treść błędu — konfiguracja była sprawdzana ze źródłem komponentu (stan z 29.10.2026), ale nie była kompilowana w tym środowisku |
| Kompilacja pada z braku pamięci / miejsca | ESPHome na słabym RPi może potrzebować 15–30 min; nie przerywaj. Ewentualnie skompiluj na komputerze |
| W logu brak linii `RAMKA` | 1) CC1101 to na pewno **868 MHz**? 2) przewody SCK/MOSI/MISO/CSN/GDO0 — porównaj z tabelą; 3) VCC na **3V3**; 4) antena przykręcona; 5) w logu szukaj `CC1101` błędów SPI (np. `chip not found` = złe połączenie SPI) |
| Są ramki, ale żadna nie jest „moja” (prefiks/numer się nie zgadzają) | weź ramkę z innym ID (najsilniejszy sygnał), powtórz sekcję 7 |
| Jest ID, ale encje puste / w logu „could not decrypt” lub podobne | wodociągi mogły ustawić własny klucz — wtedy trzeba o niego poprosić (podaj numer nakładki 06436027) i wpisać `key: "…"` pod `type: izar` |
| Stan skacze lub jest bez sensu | upewnij się, że to Twój licznik (sekcja 7 pkt 8) |
| Urządzenie co chwilę „offline” | `power_save_mode: none` jest w konfiguracji; sprawdź zasilanie (ładowarka min. 1 A) i siłę Wi-Fi (encja *Licznik wody - Wi-Fi*) |
| Chcesz czytać też licznik ciepła / drugi licznik | dodaj drugi wpis w `wmbus_meter:` i jego sterownik w `wmbus_common: drivers:` — ten sam odbiornik obsłuży wiele liczników |

---

## 12. Uwagi końcowe

- Odczyt przychodzi tylko wtedy, gdy nakładka nadaje — to nie jest przepływomierz w czasie
  rzeczywistym, ale przy nadawaniu co 8 s różnica jest nieistotna.
- Wartości pochodzą z nakładki, więc są **takie same, jakie widzi inkasent** — dobra podstawa do
  sprawdzenia rachunków.
- Sterownik `izar` w wmbusmeters ma już następcę `izarv2`; komponent ESPHome na dziś zawiera
  `izar` — działa, a gdy pojawi się `izarv2`, zmiana to jedna linia `type:`.
- Źródła, z których zweryfikowałem konfigurację: komponent
  [SzczepanLeon/esphome-components](https://github.com/SzczepanLeon/esphome-components)
  (commit 03484db z 29.10.2026) i [wmbusmeters](https://github.com/wmbusmeters/wmbusmeters)
  (plik `simulations/simulation_izars.txt`, w którym jest ramka testowa z IZAR RC 868 I R4 PL).
