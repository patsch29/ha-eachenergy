# Each Energy (lokal) – Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/patsch29/ha-eachenergy/actions/workflows/validate.yml/badge.svg)](https://github.com/patsch29/ha-eachenergy/actions/workflows/validate.yml)

Lokale, cloudfreie Anbindung von **Each Energy** Hybrid-Wechselrichtern an Home Assistant – direkt über den mitgelieferten SOLARMAN-WLAN-Stick (z. B. LSW-5), ohne Solarman-Cloud.

*English version below.*

> **Inoffizielles Community-Projekt.** Nicht von Each Energy entwickelt, unterstützt oder geprüft. Nutzung auf eigenes Risiko. Die Integration arbeitet **nur lesend** – sie sendet keine Steuer- oder Schreibbefehle an den Wechselrichter.

## Warum diese Integration?

Each-Energy-Wechselrichter sprechen über den SOLARMAN-Stick **kein Modbus**, sondern ein eigenes Protokoll (`0x7E`-Frames mit CRC16), das im SOLARMAN-V5-Rahmen getunnelt wird. Die bekannten Solarman/Modbus-Integrationen bekommen deshalb keine Antwort. Diese Integration implementiert das Protokoll direkt.

## Getestete Geräte

| Wechselrichter | Logger | Firmware Logger | Status |
|---|---|---|---|
| PHT12K-M1-25A (3-phasig, Hybrid) mit 12-kWh-Batterie | LSW-5 | LSW5_01_DD01_SS_00_02.00.00.05 | ✅ läuft |

Andere Modelle der Serie nutzen sehr wahrscheinlich dasselbe Protokoll. Rückmeldungen (auch „funktioniert“) bitte als [Issue](https://github.com/patsch29/ha-eachenergy/issues) – gern mit Modell und Logger-Firmware.

## Funktionen

- Einrichtung komplett über die Oberfläche (Config Flow), Abfrageintervall einstellbar (Standard 15 s)
- Rund 50 Sensoren, u. a.:
  - **PV:** Gesamtleistung, PV1–PV3 (Spannung, Strom, Leistung), Ertrag heute/gesamt
  - **Netz:** Netzleistung (+ Bezug / − Einspeisung), Spannung/Strom je Phase, Frequenz, Bezug und Einspeisung heute/gesamt
  - **Haus:** Verbrauch gesamt und je Phase, heute/gesamt
  - **Batterie:** Ladezustand, SOH, Leistung, Spannung, Strom, Temperatur, Status, Zyklen, geladen/entladen heute/gesamt
  - **Gerät:** Betriebsstatus, Temperaturen, Backup-Ausgang, Isolationswiderstand, Warn- und Fehlercodes
- Gesamtzähler sind als `total_increasing` angelegt und können direkt im **Energie-Dashboard** von Home Assistant verwendet werden.

## Installation

### Über HACS (empfohlen)

1. HACS → Menü (⋮) → **Benutzerdefinierte Repositories**
2. URL `https://github.com/patsch29/ha-eachenergy`, Typ **Integration** hinzufügen
3. „Each Energy (lokal)“ installieren und Home Assistant neu starten

### Manuell

Ordner `custom_components/eachenergy` nach `/config/custom_components/eachenergy` kopieren und Home Assistant neu starten.

## Einrichtung

Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Each Energy (lokal)“

| Feld | Bedeutung |
|---|---|
| IP-Adresse des Loggers | IP des WLAN-Sticks im Heimnetz (am besten im Router fest vergeben) |
| Port | `8899` (Standard bei SOLARMAN-Sticks) |
| Seriennummer des Loggers | Die **Logger**-Seriennummer (10 Ziffern, Aufkleber am Stick bzw. Web-Oberfläche des Sticks) – *nicht* die Seriennummer des Wechselrichters |
| Geräteadresse | `1` (Standard) |
| Abfrageintervall | 5–300 Sekunden |

## Hinweise

- Der Stick bedient nur wenige gleichzeitige Verbindungen. Andere lokale Abfragen (z. B. eine zusätzliche Solarman-Integration) sollten deaktiviert sein.
- Die Solarman-App/Cloud funktioniert parallel weiter.
- Sensornamen sind derzeit deutsch.

## Mitmachen

Pull Requests und Issues sind willkommen. Die Protokoll-Hilfsfunktionen lassen sich ohne Home Assistant testen:

```bash
pip install pytest
python -m pytest tests
```

---

## English

Local, cloud-free integration for **Each Energy** hybrid inverters via the bundled SOLARMAN Wi-Fi stick logger (e.g. LSW-5).

> **Unofficial community project**, not affiliated with or endorsed by Each Energy. **Read-only** – no write/control commands are ever sent.

Each Energy inverters do **not** speak Modbus through the stick; they use a proprietary `0x7E` frame protocol (CRC16) tunnelled inside SOLARMAN V5. That's why generic Solarman/Modbus integrations get no response.

**Install:** HACS → Custom repositories → `https://github.com/patsch29/ha-eachenergy` (type *Integration*) → install → restart. Or copy `custom_components/eachenergy` manually.

**Configure:** Settings → Devices & services → Add integration → "Each Energy (lokal)". Enter the logger IP, port `8899`, the **logger** serial number (10 digits, not the inverter serial), device address `1`.

**Tested:** PHT12K-M1-25A with LSW-5 logger. Reports for other models are very welcome via issues. Sensor names are currently German.

## Lizenz / License

[MIT](LICENSE)
