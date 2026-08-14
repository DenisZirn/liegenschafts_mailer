<p align="center">
  <img src="custom_components/liegenschafts_mailer/logo.png" alt="Liegenschafts Mailer Logo" width="160">
</p>

# Liegenschafts Mailer

Home-Assistant-Custom-Integration zur Verwaltung von Liegenschaften, Mietobjekten und Zählerständen mit E-Mail-Versand, CSV-Export und PDF-Abrechnung.

> Aktuelle Version: **0.8.16**

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DenisZirn&repository=liegenschafts_mailer&category=integration)

## Funktionen

- Verwaltung von Objekten wie Liegeplätze, Wohnungen, Garagen, Stellplätze, E-Bike-Ladeplätze und Waschmaschinenplätze.
- Mieter-/Kundendaten mit optionaler E-Mail-Adresse.
- Zuordnung eines Home-Assistant-Zählerstand-Sensors pro Objekt.
- Automatische Infomails für Langzeitmiete/Dauermiete.
- Kurzzeitmiete mit manueller PDF-Rechnung über frei wählbaren Zeitraum.
- Standardpreis pro kWh in den Grundeinstellungen.
- PDF-Rechnung mit Startwert, Endwert, Verbrauch, Preis/kWh und Betrag.
- CSV-Datei „Zählerstände aktuell“ per E-Mail an die Verwaltung.
- Speicherung der letzten PDF-Abrechnung pro Objekt für Dashboard-Links.
- Dashboard-Vorlage mit Zählerstandsverlauf, Leistungsverlauf und letzter Rechnung.
- Optionaler Passwortschutz für die Einstellungsbereiche.

## Installation über HACS

### Variante A: Button

1. Klicke auf den Button [![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DenisZirn&repository=liegenschafts_mailer&category=integration)
2. Bestätige das Hinzufügen des benutzerdefinierten Repositorys.
3. Klicke anschließend in HACS auf **Herunterladen**.
4. Starte Home Assistant neu.
5. Füge die Integration **Liegenschafts Mailer** über die Home-Assistant-Oberfläche hinzu.

### Variante B: Manuell als HACS Custom Repository

1. HACS öffnen.
2. Drei-Punkte-Menü öffnen.
3. **Custom repositories** auswählen.
4. Repository-URL eintragen:

   ```text
   https://github.com/DenisZirn/liegenschafts_mailer
   ```

5. Kategorie **Integration** wählen.
6. Repository hinzufügen.
7. Integration herunterladen.
8. Home Assistant neu starten.

## Manuelle Installation ohne HACS

1. Repository herunterladen.
2. Den Ordner

   ```text
   custom_components/liegenschafts_mailer
   ```

   nach Home Assistant kopieren:

   ```text
   /config/custom_components/liegenschafts_mailer
   ```

3. Home Assistant vollständig neu starten.
4. Integration in Home Assistant hinzufügen.

## Dauerhafte Objektspeicherung

Ab Version 0.8.16 werden alle Objekte unabhängig von den Integrationsoptionen
in einer eigenen, von Home Assistant verwalteten Store-Datei gespeichert:

```text
/config/.storage/liegenschafts_mailer
```

Beim ersten Start werden vorhandene Objekte aus Version 0.8.15 automatisch in
diese Datei migriert. Danach ist diese Datei die alleinige Datenquelle für die
Objektliste. Änderungen werden vor dem Reload vollständig und atomisch
gespeichert. Die Datei darf nur bei vollständig gestopptem Home Assistant
manuell ersetzt werden. Vor einem Austausch muss eine Sicherung der vorhandenen
Datei angelegt werden.

## Wichtige Home-Assistant-Konfiguration

Damit PDF- und CSV-Dateien aus `/config/www/liegenschafts_mailer` als Anhang verwendet und über `/local/...` geöffnet werden können, sollte die Ablage in Home Assistant erlaubt sein:

```yaml
homeassistant:
  allowlist_external_dirs:
    - /config/www/liegenschafts_mailer
```

Die PDF-Rechnungen werden unter anderem hier abgelegt:

```text
/config/www/liegenschafts_mailer/abrechnungen/
```

Im Browser sind sie dann erreichbar über:

```text
/local/liegenschafts_mailer/abrechnungen/dateiname.pdf
```

In den Grundeinstellungen kann zusätzlich eine vollständige Home-Assistant-URL für PDF-Links gesetzt werden, zum Beispiel:

```text
http://192.168.8.248:8123
```

## Notify-Service

Die Integration verwendet einen Home-Assistant-Notify-Service für den Mailversand, zum Beispiel:

```text
notify.mail_ha
```

Der Notify-Service muss in Home Assistant bereits funktionieren. Ein typischer Test in den Entwicklerwerkzeugen sieht so aus:

```yaml
action: notify.mail_ha
data:
  title: "Test Liegenschafts Mailer"
  message: "Dies ist ein Test."
  target:
    - "verwaltung@example.de"
```

## Dashboard

Eine Beispiel-Dashboard-Datei liegt im Repository:

```text
dashboard_liegenschafts_mailer.yaml
```

Die Tabelle zeigt unter anderem:

- Objekt
- Mieter
- Nutzungsart
- E-Mail
- Versandstatus
- aktueller Zählerstand
- Link zum Zählerstandsverlauf
- Link zum Leistungsverlauf
- Link zur letzten PDF-Abrechnung pro Objekt

## Services

Die Integration stellt unter anderem folgende Services bereit:

```yaml
liegenschafts_mailer.send_csv_to_management
```

```yaml
liegenschafts_mailer.send_billing_pdf_to_management
```

Beispiel für eine PDF-Rechnung:

```yaml
action: liegenschafts_mailer.send_billing_pdf_to_management
data:
  scope: "Kurzzeitmiete"
  object_id: "platz_01"
  start_date: "2026-07-20"
  end_date: "2026-07-28"
  price_kwh: "0.40"
```

## Rechtlicher Hinweis

Die Integration erzeugt technische Abrechnungsübersichten auf Basis der in Home Assistant verfügbaren Sensor-, Statistik- und Historienwerte. Ob eine erzeugte Abrechnung rechtlich, steuerlich oder eichrechtlich ausreichend ist, muss im jeweiligen Einsatzkontext separat geprüft werden.

## Lizenz

MIT License. Siehe [LICENSE](LICENSE).
