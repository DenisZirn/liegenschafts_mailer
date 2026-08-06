"""Sensor entities for Liegenschafts Mailer."""
from __future__ import annotations

from typing import Any
import re

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BERTHS,
    CONF_MANAGEMENT_EMAIL,
    CONF_MANAGEMENT_INTERVAL,
    CONF_MANAGEMENT_INTERVALS,
    CONF_MANAGEMENT_MONTH,
    CONF_MANAGEMENT_MONTHDAY,
    CONF_MANAGEMENT_SEND_TIME,
    CONF_NOTIFY_SERVICE,
    CONF_OBJECT_LABEL,
    CONF_OBJECT_LABEL_PLURAL,
    CONF_PROPERTY_TYPE,
    CONF_RENTAL_TYPE,
    CONF_LAST_BILLING_PDF_URL,
    CONF_LAST_BILLING_PDF_PATH,
    CONF_LAST_BILLING_PDF_FILENAME,
    CONF_LAST_BILLING_AT,
    CONF_LAST_BILLING_SCOPE,
    CONF_LAST_BILLING_START_DATE,
    CONF_LAST_BILLING_END_DATE,
    CONF_TENANT_SALUTATION,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_OBJECT_LABEL,
    DEFAULT_OBJECT_LABEL_PLURAL,
    DEFAULT_PROPERTY_TYPE,
    DEFAULT_TENANT_SALUTATION,
    DEFAULT_RENTAL_TYPE,
    RENTAL_TYPE_PERMANENT,
    RENTAL_TYPE_SHORT_TERM,
    DOMAIN,
    INTERVAL_DAILY,
    INTERVAL_MONTHLY,
    INTERVAL_QUARTERLY,
    INTERVAL_WEEKLY,
    INTERVAL_YEARLY,
    PROPERTY_TYPE_DEFAULTS,
)

INTERVAL_LABELS = {
    INTERVAL_DAILY: "täglich",
    INTERVAL_WEEKLY: "wöchentlich",
    INTERVAL_MONTHLY: "monatlich",
    INTERVAL_QUARTERLY: "quartalsweise",
    INTERVAL_YEARLY: "jährlich",
}

WEEKDAY_LABELS = {1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag", 5: "Freitag", 6: "Samstag", 7: "Sonntag"}
RENTAL_TYPE_LABELS = {RENTAL_TYPE_PERMANENT: "Dauermiete", RENTAL_TYPE_SHORT_TERM: "Kurzzeit"}


def _property_defaults(options: dict[str, Any]) -> tuple[str, str, str]:
    property_type = str(options.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    default_name, default_single, default_plural = PROPERTY_TYPE_DEFAULTS.get(property_type, PROPERTY_TYPE_DEFAULTS[DEFAULT_PROPERTY_TYPE])
    single = str(options.get(CONF_OBJECT_LABEL, default_single) or default_single).strip()
    plural = str(options.get(CONF_OBJECT_LABEL_PLURAL, default_plural) or default_plural).strip()
    return default_name, single, plural


def _entry_options(entry: ConfigEntry) -> dict[str, Any]:
    options = dict(entry.options or {})
    options.setdefault(CONF_NOTIFY_SERVICE, entry.data.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE))
    options.setdefault(CONF_BERTHS, [])
    options.setdefault(CONF_PROPERTY_TYPE, entry.data.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    _, single, plural = _property_defaults(options)
    options.setdefault(CONF_OBJECT_LABEL, single)
    options.setdefault(CONF_OBJECT_LABEL_PLURAL, plural)
    options.setdefault(CONF_MANAGEMENT_EMAIL, entry.data.get(CONF_MANAGEMENT_EMAIL, ""))
    options.setdefault(CONF_MANAGEMENT_INTERVAL, entry.data.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY))
    options.setdefault(CONF_MANAGEMENT_INTERVALS, options.get(CONF_MANAGEMENT_INTERVALS) or entry.data.get(CONF_MANAGEMENT_INTERVALS) or [options.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY)])
    options.setdefault(CONF_MANAGEMENT_SEND_TIME, entry.data.get(CONF_MANAGEMENT_SEND_TIME, "08:00"))
    options.setdefault(CONF_MANAGEMENT_MONTHDAY, int(entry.data.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_MONTH, int(entry.data.get(CONF_MANAGEMENT_MONTH, 1) or 1))
    return options


def _slug(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _interval_label(berth: dict[str, Any]) -> str:
    interval = berth.get("interval")
    if interval == INTERVAL_WEEKLY:
        weekday = int(berth.get("weekday", 1))
        return f"wöchentlich, {WEEKDAY_LABELS.get(weekday, weekday)}"
    if interval == INTERVAL_MONTHLY:
        return f"monatlich, Tag {int(berth.get('monthday', 1))}"
    if interval == INTERVAL_QUARTERLY:
        return f"quartalsweise, Tag {int(berth.get('monthday', 1))}"
    if interval == INTERVAL_YEARLY:
        return f"jährlich, Monat {int(berth.get('month', 1))}, Tag {int(berth.get('monthday', 1))}"
    return INTERVAL_LABELS.get(interval, str(interval))


def _berth_rows(entry: ConfigEntry) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    options = _entry_options(entry)
    _, single, _ = _property_defaults(options)
    for berth in options.get(CONF_BERTHS, []):
        rows.append(
            {
                # Existing German keys remain for dashboard compatibility.
                "liegeplatz": berth.get("berth_id", ""),
                "name": berth.get(CONF_NAME, ""),
                "anrede": berth.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION),
                "mieter": berth.get("tenant_name", ""),
                "email": berth.get(CONF_EMAIL, ""),
                "nutzungsart": RENTAL_TYPE_LABELS.get(str(berth.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)), "Dauermiete"),
                "rental_type": str(berth.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)),
                "zaehler_sensor": berth.get("meter_sensor", ""),
                "intervall": _interval_label(berth),
                "versandzeit": berth.get("send_time", ""),
                "aktiv": bool(berth.get("enabled", True)),
                "letzter_versand": berth.get("last_sent_at", ""),
                "letzte_abrechnung_url": berth.get(CONF_LAST_BILLING_PDF_URL, ""),
                "letzte_abrechnung_datei": berth.get(CONF_LAST_BILLING_PDF_FILENAME, ""),
                "letzte_abrechnung_am": berth.get(CONF_LAST_BILLING_AT, ""),
                "letzte_abrechnung_art": berth.get(CONF_LAST_BILLING_SCOPE, ""),
                "letzte_abrechnung_von": berth.get(CONF_LAST_BILLING_START_DATE, ""),
                "letzte_abrechnung_bis": berth.get(CONF_LAST_BILLING_END_DATE, ""),
                # New neutral keys.
                "objekt": berth.get("berth_id", ""),
                "objekt_typ": single,
                "tenant_salutation": berth.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION),
                "tenant_name": berth.get("tenant_name", ""),
                "meter_sensor": berth.get("meter_sensor", ""),
                "interval": berth.get("interval", ""),
                "send_time": berth.get("send_time", ""),
                "enabled": bool(berth.get("enabled", True)),
                "last_billing_pdf_url": berth.get(CONF_LAST_BILLING_PDF_URL, ""),
                "last_billing_pdf_filename": berth.get(CONF_LAST_BILLING_PDF_FILENAME, ""),
                "last_billing_at": berth.get(CONF_LAST_BILLING_AT, ""),
                "last_billing_scope": berth.get(CONF_LAST_BILLING_SCOPE, ""),
                "last_billing_start_date": berth.get(CONF_LAST_BILLING_START_DATE, ""),
                "last_billing_end_date": berth.get(CONF_LAST_BILLING_END_DATE, ""),
            }
        )
    return rows


def _markdown_table(entry: ConfigEntry, rows: list[dict[str, Any]]) -> str:
    if not rows:
        _, _, plural = _property_defaults(_entry_options(entry))
        return f"Noch keine {plural} angelegt."
    _, single, _ = _property_defaults(_entry_options(entry))
    lines = [f"| {single} | Mieter | E-Mail | Zähler | Intervall | Zeit | Aktiv | Letzter Versand | Letzte Abrechnung |", "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        active = "ja" if row["aktiv"] else "nein"
        billing_url = row.get("letzte_abrechnung_url") or row.get("last_billing_pdf_url") or ""
        billing_link = f"[📄 PDF öffnen]({billing_url})" if billing_url else "-"
        lines.append(
            "| {liegeplatz} | {mieter} | {email} | `{zaehler_sensor}` | {intervall} | {versandzeit} | {active} | {letzter_versand} | {billing_link} |".format(
                active=active,
                billing_link=billing_link,
                **row,
            )
        )
    return "\n".join(lines)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    entities: list[SensorEntity] = [LiegenschaftsMailerSummarySensor(entry)]
    for berth in _entry_options(entry).get(CONF_BERTHS, []):
        entities.append(LiegenschaftsMailerObjectSensor(hass, entry, berth.get("berth_id", "")))
    async_add_entities(entities, True)


class LiegenschaftsMailerSummarySensor(SensorEntity):
    """Overview sensor for all configured objects."""

    _attr_has_entity_name = True
    _attr_name = "Objekte"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_objects_overview"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Liegenschafts Mailer"}

    @property
    def native_value(self) -> int:
        return len(_entry_options(self._entry).get(CONF_BERTHS, []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        options = _entry_options(self._entry)
        rows = _berth_rows(self._entry)
        _, single, plural = _property_defaults(options)
        return {
            "notify_service": options.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
            "property_type": options.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE),
            "object_label": single,
            "object_label_plural": plural,
            "management_email": options.get(CONF_MANAGEMENT_EMAIL, ""),
            "management_interval": options.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY),
            "management_intervals": options.get(CONF_MANAGEMENT_INTERVALS, [options.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY)]),
            "management_send_time": options.get(CONF_MANAGEMENT_SEND_TIME, "08:00"),
            "management_monthday": options.get(CONF_MANAGEMENT_MONTHDAY, 1),
            "management_month": options.get(CONF_MANAGEMENT_MONTH, 1),
            "last_management_report_at": options.get("last_management_report_at", ""),
            "count": len(rows),
            "berths": rows,
            "objects": rows,
            "table": _markdown_table(self._entry, rows),
        }


class LiegenschaftsMailerObjectSensor(SensorEntity):
    """Visible sensor for one configured object."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:email-send-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, berth_id: str) -> None:
        self.hass = hass
        self._entry = entry
        self._berth_id = berth_id
        self._attr_unique_id = f"{entry.entry_id}_object_{_slug(berth_id)}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Liegenschafts Mailer"}

    def _berth(self) -> dict[str, Any] | None:
        for berth in _entry_options(self._entry).get(CONF_BERTHS, []):
            if berth.get("berth_id") == self._berth_id:
                return berth
        return None

    @property
    def name(self) -> str | None:
        berth = self._berth()
        label = berth.get(CONF_NAME, self._berth_id) if berth else self._berth_id
        return f"{label} Mailer"

    @property
    def native_value(self) -> str | None:
        berth = self._berth()
        if not berth:
            return None
        state = self.hass.states.get(str(berth.get("meter_sensor", "")))
        if state is None:
            return "Sensor fehlt"
        return state.state

    @property
    def native_unit_of_measurement(self) -> str | None:
        berth = self._berth()
        if not berth:
            return None
        state = self.hass.states.get(str(berth.get("meter_sensor", "")))
        if state is None:
            return None
        return state.attributes.get("unit_of_measurement")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        berth = self._berth() or {}
        _, single, _ = _property_defaults(_entry_options(self._entry))
        return {
            "objekt": berth.get("berth_id", self._berth_id),
            "objekt_typ": single,
            "liegeplatz": berth.get("berth_id", self._berth_id),
            "name": berth.get(CONF_NAME, ""),
            "anrede": berth.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION),
            "mieter": berth.get("tenant_name", ""),
            "email": berth.get(CONF_EMAIL, ""),
            "zaehler_sensor": berth.get("meter_sensor", ""),
            "intervall": _interval_label(berth) if berth else "",
            "versandzeit": berth.get("send_time", ""),
            "aktiv": bool(berth.get("enabled", True)),
            "letzter_versand": berth.get("last_sent_at", ""),
            "letzte_abrechnung_url": berth.get(CONF_LAST_BILLING_PDF_URL, ""),
            "letzte_abrechnung_datei": berth.get(CONF_LAST_BILLING_PDF_FILENAME, ""),
            "letzte_abrechnung_am": berth.get(CONF_LAST_BILLING_AT, ""),
            "letzte_abrechnung_art": berth.get(CONF_LAST_BILLING_SCOPE, ""),
            "letzte_abrechnung_von": berth.get(CONF_LAST_BILLING_START_DATE, ""),
            "letzte_abrechnung_bis": berth.get(CONF_LAST_BILLING_END_DATE, ""),
            "last_billing_pdf_url": berth.get(CONF_LAST_BILLING_PDF_URL, ""),
        }
