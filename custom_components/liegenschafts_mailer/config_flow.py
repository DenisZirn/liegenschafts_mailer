"""Config flow for Liegenschafts Mailer."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_ADMIN_PASSWORD,
    CONF_BERTHS,
    CONF_MANAGEMENT_EMAIL,
    CONF_MANAGEMENT_INTERVAL,
    CONF_MANAGEMENT_INTERVALS,
    CONF_MANAGEMENT_MONTH,
    CONF_DEFAULT_KWH_PRICE,
    CONF_HA_BASE_URL,
    CONF_MANAGEMENT_MONTHDAY,
    CONF_MANAGEMENT_SEND_TIME,
    CONF_MANAGEMENT_DEFAULT_EMAIL,
    CONF_MANAGEMENT_MONTHLY_ENABLED,
    CONF_MANAGEMENT_MONTHLY_EMAIL,
    CONF_MANAGEMENT_MONTHLY_SEND_TIME,
    CONF_MANAGEMENT_MONTHLY_MONTHDAY,
    CONF_MANAGEMENT_QUARTERLY_ENABLED,
    CONF_MANAGEMENT_QUARTERLY_EMAIL,
    CONF_MANAGEMENT_QUARTERLY_SEND_TIME,
    CONF_MANAGEMENT_QUARTERLY_MONTHDAY,
    CONF_MANAGEMENT_QUARTERLY_MODE,
    CONF_MANAGEMENT_QUARTERLY_Q1,
    CONF_MANAGEMENT_QUARTERLY_Q2,
    CONF_MANAGEMENT_QUARTERLY_Q3,
    CONF_MANAGEMENT_QUARTERLY_Q4,
    CONF_MANAGEMENT_YEARLY_ENABLED,
    CONF_MANAGEMENT_YEARLY_EMAIL,
    CONF_MANAGEMENT_YEARLY_SEND_TIME,
    CONF_MANAGEMENT_YEARLY_MONTHDAY,
    CONF_MANAGEMENT_YEARLY_MONTH,
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
    CONF_SEND_MODE,
    CONF_TENANT_SALUTATION,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_OBJECT_LABEL,
    DEFAULT_OBJECT_LABEL_PLURAL,
    DEFAULT_PROPERTY_TYPE,
    DEFAULT_TENANT_SALUTATION,
    DEFAULT_RENTAL_TYPE,
    DOMAIN,
    INTERVAL_DAILY,
    INTERVAL_MONTHLY,
    INTERVAL_QUARTERLY,
    INTERVAL_WEEKLY,
    INTERVAL_YEARLY,
    INTERVALS,
    MANAGEMENT_INTERVALS,
    PROPERTY_TYPE_APARTMENTS,
    PROPERTY_TYPE_CAMPING,
    PROPERTY_TYPE_EBIKE,
    PROPERTY_TYPE_LAUNDRY,
    PROPERTY_TYPE_CUSTOM,
    PROPERTY_TYPE_DEFAULTS,
    PROPERTY_TYPE_GARAGES,
    PROPERTY_TYPE_MARINA,
    SEND_MODE_TARGET,
    RENTAL_TYPE_PERMANENT,
    RENTAL_TYPE_SHORT_TERM,
    BILLING_SCOPE_SHORT_TERM,
    BILLING_SCOPE_LONG_TERM,
    BILLING_SCOPE_ALL,
    BILLING_SCOPE_OBJECT,
    QUARTER_MODE_START,
    QUARTER_MODE_END,
    TENANT_SALUTATION_MR,
    TENANT_SALUTATION_MS,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
CONF_ADMIN_PASSWORD_DISABLED = "admin_password_disabled"
CONF_ADMIN_PASSWORD_ENABLED = "admin_password_enabled"


def _is_german_lang(hass) -> bool:
    return str(getattr(hass.config, "language", "de") or "de").lower().startswith("de")


def _tenant_salutation_options(hass):
    if _is_german_lang(hass):
        return [
            selector.SelectOptionDict(value=TENANT_SALUTATION_MR, label="Herr"),
            selector.SelectOptionDict(value=TENANT_SALUTATION_MS, label="Frau"),
        ]
    return [
        selector.SelectOptionDict(value=TENANT_SALUTATION_MR, label="Mr"),
        selector.SelectOptionDict(value=TENANT_SALUTATION_MS, label="Ms"),
    ]


def _ui_text(hass, de: str, en: str) -> str:
    return de if _is_german_lang(hass) else en

WEEKDAY_OPTIONS = [
    selector.SelectOptionDict(value="1", label="Montag"),
    selector.SelectOptionDict(value="2", label="Dienstag"),
    selector.SelectOptionDict(value="3", label="Mittwoch"),
    selector.SelectOptionDict(value="4", label="Donnerstag"),
    selector.SelectOptionDict(value="5", label="Freitag"),
    selector.SelectOptionDict(value="6", label="Samstag"),
    selector.SelectOptionDict(value="7", label="Sonntag"),
]

MONTH_OPTIONS = [selector.SelectOptionDict(value=str(i), label=name) for i, name in enumerate(
    ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"], start=1
)]

INTERVAL_OPTIONS = [
    selector.SelectOptionDict(value=INTERVAL_DAILY, label="Täglich"),
    selector.SelectOptionDict(value=INTERVAL_WEEKLY, label="Wöchentlich"),
    selector.SelectOptionDict(value=INTERVAL_MONTHLY, label="Monatlich"),
    selector.SelectOptionDict(value=INTERVAL_QUARTERLY, label="Quartalsweise"),
    selector.SelectOptionDict(value=INTERVAL_YEARLY, label="Jährlich"),
]

MANAGEMENT_INTERVAL_OPTIONS = [
    selector.SelectOptionDict(value=INTERVAL_MONTHLY, label="Monatlich"),
    selector.SelectOptionDict(value=INTERVAL_QUARTERLY, label="Quartalsweise"),
    selector.SelectOptionDict(value=INTERVAL_YEARLY, label="Jährlich"),
]

QUARTER_MODE_OPTIONS = [
    selector.SelectOptionDict(value=QUARTER_MODE_START, label="Quartalsanfang"),
    selector.SelectOptionDict(value=QUARTER_MODE_END, label="Quartalsende"),
]

REPORT_TEST_QUARTER_OPTIONS = [
    selector.SelectOptionDict(value="1", label="Quartal 1"),
    selector.SelectOptionDict(value="2", label="Quartal 2"),
    selector.SelectOptionDict(value="3", label="Quartal 3"),
    selector.SelectOptionDict(value="4", label="Quartal 4"),
]

RENTAL_TYPE_OPTIONS = [
    selector.SelectOptionDict(value=RENTAL_TYPE_PERMANENT, label="Dauermiete"),
    selector.SelectOptionDict(value=RENTAL_TYPE_SHORT_TERM, label="Kurzzeit"),
]

BILLING_SCOPE_OPTIONS = [
    selector.SelectOptionDict(value=BILLING_SCOPE_SHORT_TERM, label="Kurzzeitmiete"),
    selector.SelectOptionDict(value=BILLING_SCOPE_LONG_TERM, label="Langzeitmiete"),
]

MANAGEMENT_ACTION_OPTIONS = [
    selector.SelectOptionDict(value="management_default", label="Standard-Verwaltungsmail einstellen"),
    selector.SelectOptionDict(value="management_monthly", label="Monatsbericht einstellen"),
    selector.SelectOptionDict(value="management_quarterly", label="Quartalsbericht einstellen"),
    selector.SelectOptionDict(value="management_yearly", label="Jahresbericht einstellen"),
]

PROPERTY_TYPE_OPTIONS = [
    selector.SelectOptionDict(value=PROPERTY_TYPE_MARINA, label="Yachthafen"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_APARTMENTS, label="Mietwohnungen"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_GARAGES, label="Garagen"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_CAMPING, label="Campingplätze"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_EBIKE, label="E-Bike-Ladeplätze"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_LAUNDRY, label="Waschmaschinenplätze"),
    selector.SelectOptionDict(value=PROPERTY_TYPE_CUSTOM, label="Benutzerdefiniert"),
]

ACTION_OPTIONS = [
    selector.SelectOptionDict(value="list_berths", label="Übersicht / Tabelle"),
    selector.SelectOptionDict(value="invoice_menu", label="Rechnung erstellen"),
    selector.SelectOptionDict(value="test_menu", label="Testmail"),
    selector.SelectOptionDict(value="send_management_report", label="Verwaltungsliste jetzt senden"),
    selector.SelectOptionDict(value="manage_objects", label="Einstellungen öffnen / bearbeiten"),
]

INVOICE_ACTION_OPTIONS = [
    selector.SelectOptionDict(value="billing_pdf", label="PDF-Rechnung erstellen"),
    selector.SelectOptionDict(value="export_csv_current", label="CSV Datei (Zählerstände aktuell) per Email an Verwaltung senden"),
]

TEST_ACTION_OPTIONS = [
    selector.SelectOptionDict(value="test_mail", label="Testmail an beliebige Adresse"),
    selector.SelectOptionDict(value="test_berth_mail", label="Testmail an Objekt-Empfänger"),
]

ADMIN_ACTION_OPTIONS = [
    selector.SelectOptionDict(value="global_options", label="Grundeinstellungen"),
    selector.SelectOptionDict(value="management_options", label="Verwaltungsversand einstellen"),
    selector.SelectOptionDict(value="add_berth", label="Objekt hinzufügen"),
    selector.SelectOptionDict(value="edit_berth", label="Objekt bearbeiten"),
    selector.SelectOptionDict(value="remove_object", label="Objekt löschen"),
]

PROTECTED_ACTIONS = {"manage_objects", "global_options", "management_options", "add_berth", "edit_berth", "remove_object"}


def _property_defaults(options: dict[str, Any]) -> tuple[str, str, str]:
    property_type = str(options.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    default_name, default_single, default_plural = PROPERTY_TYPE_DEFAULTS.get(property_type, PROPERTY_TYPE_DEFAULTS[DEFAULT_PROPERTY_TYPE])
    single = str(options.get(CONF_OBJECT_LABEL, default_single) or default_single).strip()
    plural = str(options.get(CONF_OBJECT_LABEL_PLURAL, default_plural) or default_plural).strip()
    return default_name, single, plural


def _natural_sort_key(value: str) -> tuple[str, int]:
    text = str(value or "").strip()
    match = re.search(r"^(.*?)[\s_-]*0*(\d+)$", text, re.IGNORECASE)
    if match:
        return (match.group(1).strip().lower(), int(match.group(2)))
    return (text.lower(), 0)


def _next_object_number(objects: list[dict[str, Any]], label: str) -> int:
    used: set[int] = set()
    pattern = re.compile(r"^" + re.escape(label) + r"\s+0*(\d+)$", re.IGNORECASE)
    for obj in objects:
        for key in ("berth_id", CONF_NAME):
            match = pattern.match(str(obj.get(key, "")).strip())
            if match:
                used.add(int(match.group(1)))
    number = 1
    while number in used:
        number += 1
    return number


def _format_object(label: str, number: int) -> str:
    return f"{label} {number:02d}"


def _default_new_berth(options: dict[str, Any]) -> dict[str, Any]:
    _, single, _ = _property_defaults(options)
    label = _format_object(single, _next_object_number(options.get(CONF_BERTHS, []), single))
    return {"berth_id": label, CONF_NAME: label}


def _interval_label(berth: dict[str, Any]) -> str:
    interval = berth.get("interval")
    if interval == INTERVAL_DAILY:
        return "täglich"
    if interval == INTERVAL_WEEKLY:
        weekday_labels = {1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag", 5: "Freitag", 6: "Samstag", 7: "Sonntag"}
        return f"wöchentlich, {weekday_labels.get(int(berth.get('weekday', 1)), berth.get('weekday', 1))}"
    if interval == INTERVAL_MONTHLY:
        return f"monatlich, Tag {int(berth.get('monthday', 1))}"
    if interval == INTERVAL_QUARTERLY:
        return f"quartalsweise, Tag {int(berth.get('monthday', 1))}"
    if interval == INTERVAL_YEARLY:
        return f"jährlich, Monat {int(berth.get('month', 1))}, Tag {int(berth.get('monthday', 1))}"
    return str(interval)


def _berths_markdown_table(options: dict[str, Any]) -> str:
    berths = options.get(CONF_BERTHS, [])
    _, single, plural = _property_defaults(options)
    if not berths:
        return f"Noch keine {plural} angelegt."
    lines = [f"| {single} | Mieter | E-Mail | Zähler | Intervall | Zeit | Aktiv |", "|---|---|---|---|---|---|---|"]
    for berth in berths:
        active = "ja" if berth.get("enabled", True) else "nein"
        lines.append(
            f"| {berth.get('berth_id', '')} | {berth.get('tenant_name', '')} | {berth.get(CONF_EMAIL, '')} | `{berth.get('meter_sensor', '')}` | {_interval_label(berth)} | {berth.get('send_time', '')} | {active} |"
        )
    return "\n".join(lines)


def _entry_options(config_entry) -> dict[str, Any]:
    options = dict(config_entry.options or {})
    options.setdefault(CONF_NOTIFY_SERVICE, config_entry.data.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE))
    options.setdefault(CONF_SEND_MODE, SEND_MODE_TARGET)
    options.setdefault(CONF_BERTHS, [])
    legacy_password = str(config_entry.data.get(CONF_ADMIN_PASSWORD, "") or "").strip()
    option_password = str(options.get(CONF_ADMIN_PASSWORD, "") or "").strip()
    raw_enabled = options.get(CONF_ADMIN_PASSWORD_ENABLED, config_entry.data.get(CONF_ADMIN_PASSWORD_ENABLED, None))
    raw_disabled = options.get(CONF_ADMIN_PASSWORD_DISABLED, config_entry.data.get(CONF_ADMIN_PASSWORD_DISABLED, None))
    if raw_enabled is None:
        password_enabled = bool((option_password or legacy_password) and not bool(raw_disabled))
    else:
        password_enabled = bool(raw_enabled)
    options[CONF_ADMIN_PASSWORD_ENABLED] = password_enabled
    options[CONF_ADMIN_PASSWORD_DISABLED] = not password_enabled
    if password_enabled:
        options[CONF_ADMIN_PASSWORD] = option_password or legacy_password
    else:
        options[CONF_ADMIN_PASSWORD] = ""
    options.setdefault(CONF_PROPERTY_TYPE, config_entry.data.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    _, single, plural = _property_defaults(options)
    options.setdefault(CONF_OBJECT_LABEL, single)
    options.setdefault(CONF_OBJECT_LABEL_PLURAL, plural)
    options.setdefault(CONF_MANAGEMENT_EMAIL, config_entry.data.get(CONF_MANAGEMENT_EMAIL, ""))
    options.setdefault(CONF_MANAGEMENT_INTERVAL, config_entry.data.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY))
    options.setdefault(CONF_MANAGEMENT_INTERVALS, _management_intervals_from_options(options, config_entry.data))
    options.setdefault(CONF_MANAGEMENT_SEND_TIME, config_entry.data.get(CONF_MANAGEMENT_SEND_TIME, "08:00"))
    options.setdefault(CONF_MANAGEMENT_MONTHDAY, int(config_entry.data.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_MONTH, int(config_entry.data.get(CONF_MANAGEMENT_MONTH, 1) or 1))
    default_mgmt_email = str(options.get(CONF_MANAGEMENT_EMAIL, config_entry.data.get(CONF_MANAGEMENT_EMAIL, "")) or "")
    options.setdefault(CONF_MANAGEMENT_DEFAULT_EMAIL, default_mgmt_email)
    options.setdefault(CONF_MANAGEMENT_MONTHLY_ENABLED, INTERVAL_MONTHLY in _management_intervals_from_options(options, config_entry.data))
    options.setdefault(CONF_MANAGEMENT_MONTHLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_MONTHLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_MONTHLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_ENABLED, INTERVAL_QUARTERLY in _management_intervals_from_options(options, config_entry.data))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_MODE, QUARTER_MODE_START)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q1, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q2, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q3, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q4, True)
    options.setdefault(CONF_MANAGEMENT_YEARLY_ENABLED, INTERVAL_YEARLY in _management_intervals_from_options(options, config_entry.data))
    options.setdefault(CONF_MANAGEMENT_YEARLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_YEARLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_YEARLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_YEARLY_MONTH, int(options.get(CONF_MANAGEMENT_MONTH, 1) or 1))
    return options


def _clean_time(value: Any) -> str:
    send_time = str(value or "").strip()
    if len(send_time) == 8 and send_time.endswith(":00"):
        send_time = send_time[:5]
    return send_time


def _management_intervals_from_options(options: dict[str, Any], data: dict[str, Any] | None = None) -> list[str]:
    source = options.get(CONF_MANAGEMENT_INTERVALS)
    if source is None and data:
        source = data.get(CONF_MANAGEMENT_INTERVALS)
    if source is None:
        source = options.get(CONF_MANAGEMENT_INTERVAL, (data or {}).get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY))
    if isinstance(source, str):
        intervals = [source]
    else:
        intervals = [str(item) for item in (source or [])]
    valid = [item for item in intervals if item in MANAGEMENT_INTERVALS]
    return valid or [INTERVAL_MONTHLY]


def _normalize_berth(user_input: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    berth = {
        "berth_id": str(user_input.get("berth_id", "")).strip(),
        CONF_NAME: str(user_input.get(CONF_NAME, "")).strip(),
        CONF_TENANT_SALUTATION: str(user_input.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION)),
        "tenant_name": str(user_input.get("tenant_name", "")).strip(),
        CONF_EMAIL: str(user_input.get(CONF_EMAIL, "")).strip(),
        CONF_RENTAL_TYPE: str(user_input.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE) or DEFAULT_RENTAL_TYPE),
        "meter_sensor": str(user_input.get("meter_sensor", "")).strip(),
        "interval": str(user_input.get("interval", INTERVAL_MONTHLY)),
        "send_time": _clean_time(user_input.get("send_time")),
        "weekday": int(user_input.get("weekday", 1)),
        "monthday": int(user_input.get("monthday", 1)),
        "month": int(user_input.get("month", 1)),
        "enabled": bool(user_input.get("enabled", True)),
    }
    if existing:
        for key in ("last_sent_date", "last_sent_at", CONF_LAST_BILLING_PDF_URL, CONF_LAST_BILLING_PDF_PATH, CONF_LAST_BILLING_PDF_FILENAME, CONF_LAST_BILLING_AT, CONF_LAST_BILLING_SCOPE, CONF_LAST_BILLING_START_DATE, CONF_LAST_BILLING_END_DATE):
            if key in existing:
                berth[key] = existing[key]
        berth.setdefault(CONF_TENANT_SALUTATION, existing.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION))
    return berth


def _validate_berth(berth: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not berth["berth_id"]:
        errors["berth_id"] = "required"
    if not berth[CONF_NAME]:
        errors[CONF_NAME] = "required"
    if berth.get(CONF_TENANT_SALUTATION) not in (TENANT_SALUTATION_MR, TENANT_SALUTATION_MS):
        errors[CONF_TENANT_SALUTATION] = "invalid_salutation"
    if not berth["tenant_name"]:
        errors["tenant_name"] = "required"
    if berth.get(CONF_EMAIL) and not EMAIL_RE.match(berth[CONF_EMAIL]):
        errors[CONF_EMAIL] = "invalid_email"
    if berth.get(CONF_RENTAL_TYPE) not in (RENTAL_TYPE_PERMANENT, RENTAL_TYPE_SHORT_TERM):
        errors[CONF_RENTAL_TYPE] = "invalid_rental_type"
    if not berth["meter_sensor"].startswith("sensor."):
        errors["meter_sensor"] = "invalid_sensor"
    if berth["interval"] not in INTERVALS:
        errors["interval"] = "invalid_interval"
    if not TIME_RE.match(berth["send_time"]):
        errors["send_time"] = "invalid_time"
    if not 1 <= berth["weekday"] <= 7:
        errors["weekday"] = "invalid_weekday"
    if not 1 <= berth["monthday"] <= 31:
        errors["monthday"] = "invalid_monthday"
    if not 1 <= berth["month"] <= 12:
        errors["month"] = "invalid_month"
    return errors


def _berth_schema(hass, defaults: dict[str, Any] | None = None, *, edit: bool = False):
    defaults = defaults or {}
    default_id = defaults.get("berth_id", "Objekt 01")
    return vol.Schema(
        {
            vol.Required("berth_id", default=default_id): str,
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, default_id)): str,
            vol.Required(CONF_TENANT_SALUTATION, default=defaults.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=_tenant_salutation_options(hass), mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("tenant_name", default=defaults.get("tenant_name", "")): str,
            vol.Optional(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): str,
            vol.Required(CONF_RENTAL_TYPE, default=defaults.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=RENTAL_TYPE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("meter_sensor", default=defaults.get("meter_sensor", "")): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("interval", default=defaults.get("interval", INTERVAL_MONTHLY)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=INTERVAL_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("send_time", default=defaults.get("send_time", "08:00")): selector.TimeSelector(),
            vol.Required("weekday", default=str(defaults.get("weekday", 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=WEEKDAY_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("monthday", default=int(defaults.get("monthday", 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required("month", default=str(defaults.get("month", 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=MONTH_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("enabled", default=defaults.get("enabled", True)): bool,
        }
    )



# German form keys are used for the billing dialog on purpose.
# If a Home Assistant frontend instance does not load custom integration
# translations immediately after an update, the raw field names are still
# displayed in German instead of internal keys like scope/start_date.
FORM_SCOPE = "Abrechnungsart"
FORM_OBJECT_ID = "Objekt"
FORM_START_DATE = "Beginndatum"
FORM_END_DATE = "Enddatum"
FORM_PRICE_KWH = "Preis pro kWh"
FORM_HA_BASE_URL = "Home Assistant URL für PDF-Link"


def _detected_ha_base_url(hass) -> str:
    """Return Home Assistant base URL if HA can provide one."""
    try:
        from homeassistant.helpers.network import get_url

        return str(get_url(hass, allow_internal=True, allow_external=True) or "").rstrip("/")
    except Exception:
        pass
    for attr in ("external_url", "internal_url"):
        try:
            value = getattr(hass.config, attr, None)
            if value:
                return str(value).rstrip("/")
        except Exception:
            pass
    return ""


class LiegenschaftsMailerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Liegenschafts Mailer."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            notify_service = str(user_input[CONF_NOTIFY_SERVICE]).strip() or DEFAULT_NOTIFY_SERVICE
            property_type = str(user_input.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
            _, single, plural = PROPERTY_TYPE_DEFAULTS.get(property_type, PROPERTY_TYPE_DEFAULTS[DEFAULT_PROPERTY_TYPE])
            admin_password = str(user_input.get(CONF_ADMIN_PASSWORD, "")).strip()
            title = str(user_input[CONF_NAME]).strip() or "Liegenschafts Mailer"
            return self.async_create_entry(
                title=title,
                data={CONF_NOTIFY_SERVICE: notify_service, CONF_PROPERTY_TYPE: property_type, CONF_ADMIN_PASSWORD: admin_password, CONF_ADMIN_PASSWORD_ENABLED: bool(admin_password), CONF_ADMIN_PASSWORD_DISABLED: not bool(admin_password)},
                options={
                    CONF_NOTIFY_SERVICE: notify_service,
                    CONF_SEND_MODE: SEND_MODE_TARGET,
                    CONF_BERTHS: [],
                    CONF_PROPERTY_TYPE: property_type,
                    CONF_OBJECT_LABEL: single,
                    CONF_OBJECT_LABEL_PLURAL: plural,
                    CONF_ADMIN_PASSWORD: admin_password,
                    CONF_ADMIN_PASSWORD_ENABLED: bool(admin_password),
                    CONF_ADMIN_PASSWORD_DISABLED: not bool(admin_password),
                    CONF_MANAGEMENT_EMAIL: "",
                    CONF_MANAGEMENT_INTERVAL: INTERVAL_MONTHLY,
                    CONF_MANAGEMENT_INTERVALS: [INTERVAL_MONTHLY],
                    CONF_MANAGEMENT_SEND_TIME: "08:00",
                    CONF_MANAGEMENT_MONTHDAY: 1,
                    CONF_MANAGEMENT_MONTH: 1,
                    CONF_MANAGEMENT_DEFAULT_EMAIL: "",
                    CONF_MANAGEMENT_MONTHLY_ENABLED: True,
                    CONF_MANAGEMENT_MONTHLY_EMAIL: "",
                    CONF_MANAGEMENT_MONTHLY_SEND_TIME: "08:00",
                    CONF_MANAGEMENT_MONTHLY_MONTHDAY: 1,
                    CONF_MANAGEMENT_QUARTERLY_ENABLED: False,
                    CONF_MANAGEMENT_QUARTERLY_EMAIL: "",
                    CONF_MANAGEMENT_QUARTERLY_SEND_TIME: "08:00",
                    CONF_MANAGEMENT_QUARTERLY_MONTHDAY: 1,
                    CONF_MANAGEMENT_QUARTERLY_MODE: QUARTER_MODE_START,
                    CONF_MANAGEMENT_QUARTERLY_Q1: True,
                    CONF_MANAGEMENT_QUARTERLY_Q2: True,
                    CONF_MANAGEMENT_QUARTERLY_Q3: True,
                    CONF_MANAGEMENT_QUARTERLY_Q4: True,
                    CONF_MANAGEMENT_YEARLY_ENABLED: False,
                    CONF_MANAGEMENT_YEARLY_EMAIL: "",
                    CONF_MANAGEMENT_YEARLY_SEND_TIME: "08:00",
                    CONF_MANAGEMENT_YEARLY_MONTHDAY: 1,
                    CONF_MANAGEMENT_YEARLY_MONTH: 1,
                    CONF_DEFAULT_KWH_PRICE: 0.0,
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Liegenschafts Mailer"): str,
                    vol.Required(CONF_PROPERTY_TYPE, default=DEFAULT_PROPERTY_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=PROPERTY_TYPE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
                    ),
                    vol.Required(CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE): str,
                    vol.Optional(CONF_ADMIN_PASSWORD, default=""): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LiegenschaftsMailerOptionsFlow(config_entry)


class LiegenschaftsMailerOptionsFlow(config_entries.OptionsFlow):
    """Handle options and object management."""

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._selected_berth_id: str | None = None
        self._pending_action: str | None = None

    def _options(self) -> dict[str, Any]:
        return _entry_options(self._config_entry)

    def _save_options(self, options: dict[str, Any]):
        return self.async_create_entry(title="", data=options)

    def _update_options_keep_open(self, options: dict[str, Any]) -> None:
        self.hass.config_entries.async_update_entry(self._config_entry, options=options)
        # Reload the integration after object/admin changes so sensors and dashboard
        # attributes are refreshed immediately without a manual reload.
        self.hass.async_create_task(self.hass.config_entries.async_reload(self._config_entry.entry_id))

    async def _return_manage_objects(self):
        return await self.async_step_manage_objects()

    async def _return_init(self):
        return await self.async_step_init()

    def _password_active(self) -> bool:
        options = self._options()
        return bool(options.get(CONF_ADMIN_PASSWORD_ENABLED, False)) and bool(str(options.get(CONF_ADMIN_PASSWORD, "") or "").strip())

    def _is_authorized(self, user_input: dict[str, Any] | None) -> tuple[bool, dict[str, str]]:
        if not self._password_active():
            return True, {}
        options = self._options()
        password = str(options.get(CONF_ADMIN_PASSWORD, "")).strip()
        if not password:
            return True, {}
        if user_input is None:
            return False, {}
        supplied = str(user_input.get("password", "")).strip()
        if supplied == password:
            return True, {}
        return False, {"base": "invalid_password"}

    def _berth_select_schema(self):
        berths = self._options().get(CONF_BERTHS, [])
        select_options = [
            selector.SelectOptionDict(value=b.get("berth_id", ""), label=f"{b.get('berth_id', '')} - {b.get(CONF_NAME, '')} / {b.get('tenant_name', '')}")
            for b in berths
        ]
        return vol.Schema({vol.Required("berth_id"): selector.SelectSelector(selector.SelectSelectorConfig(options=select_options, mode=selector.SelectSelectorMode.DROPDOWN))})

    def _billing_object_options(self, *, rental_type: str | None = None):
        berths = self._options().get(CONF_BERTHS, [])
        if rental_type == RENTAL_TYPE_SHORT_TERM:
            berths = [b for b in berths if str(b.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) == RENTAL_TYPE_SHORT_TERM]
            empty_label = "Keine Kurzzeitobjekte vorhanden"
        elif rental_type == RENTAL_TYPE_PERMANENT:
            berths = [b for b in berths if str(b.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) != RENTAL_TYPE_SHORT_TERM]
            empty_label = "Keine Langzeitobjekte vorhanden"
        else:
            empty_label = "Keine Objekte vorhanden"
        options = [
            selector.SelectOptionDict(
                value=b.get("berth_id", ""),
                label=f"{b.get(CONF_NAME, b.get('berth_id', ''))} - {b.get('tenant_name', '')}"
            )
            for b in berths
        ]
        if not options:
            options = [selector.SelectOptionDict(value="", label=empty_label)]
        return options


    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            action = str(user_input.get("action", "")).strip()
            options = self._options()
            password_active = self._password_active()
            if action in PROTECTED_ACTIONS and password_active:
                self._pending_action = action
                return await self.async_step_password()
            return await self._route_action(action)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("action"): selector.SelectSelector(selector.SelectSelectorConfig(options=ACTION_OPTIONS, mode=selector.SelectSelectorMode.LIST))}),
        )

    async def _route_action(self, action: str):
        if action == "manage_objects":
            return await self.async_step_manage_objects()
        if action == "invoice_menu":
            return await self.async_step_invoice_menu()
        if action == "test_menu":
            return await self.async_step_test_menu()
        if action == "export_csv_current":
            return await self.async_step_export_csv_current()
        if action == "billing_pdf":
            return await self.async_step_billing_pdf()
        if action == "global_options":
            return await self.async_step_global_options()
        if action == "management_options":
            return await self.async_step_management_options()
        if action == "list_berths":
            return await self.async_step_list_berths()
        if action == "add_berth":
            return await self.async_step_add_berth()
        if action == "edit_berth":
            return await self.async_step_edit_berth()
        if action == "remove_object":
            return await self.async_step_remove_object()
        if action == "test_mail":
            return await self.async_step_test_mail()
        if action == "test_berth_mail":
            return await self.async_step_test_berth_mail()
        if action == "send_management_report":
            return await self.async_step_send_management_report()
        return await self.async_step_init()

    async def async_step_password(self, user_input: dict[str, Any] | None = None):
        ok, errors = self._is_authorized(user_input)
        if ok:
            action = self._pending_action or "init"
            self._pending_action = None
            return await self._route_action(action)
        return self.async_show_form(step_id="password", data_schema=vol.Schema({vol.Required("password"): str}), errors=errors)

    async def async_step_invoice_menu(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            action = str(user_input.get("invoice_action", "")).strip()
            return await self._route_action(action)
        return self.async_show_form(
            step_id="invoice_menu",
            data_schema=vol.Schema(
                {
                    vol.Required("invoice_action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=INVOICE_ACTION_OPTIONS, mode=selector.SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def async_step_test_menu(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            action = str(user_input.get("test_action", "")).strip()
            return await self._route_action(action)
        return self.async_show_form(
            step_id="test_menu",
            data_schema=vol.Schema(
                {
                    vol.Required("test_action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=TEST_ACTION_OPTIONS, mode=selector.SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def async_step_manage_objects(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            action = str(user_input.get("admin_action", "")).strip()
            return await self._route_action(action)
        return self.async_show_form(
            step_id="manage_objects",
            data_schema=vol.Schema(
                {
                    vol.Required("admin_action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=ADMIN_ACTION_OPTIONS, mode=selector.SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def async_step_export_csv_current(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                from . import _async_export_current_csv_and_mail
                path = await _async_export_current_csv_and_mail(self.hass, self._config_entry)
                options = self._options()
                recipient = str(options.get("management_default_email", "")).strip()
                filename = path.rsplit("/", 1)[-1]
                return await self.async_step_csv_mail_sent_done()
            except Exception:
                errors["base"] = "export_failed"
        return self.async_show_form(
            step_id="export_csv_current",
            data_schema=vol.Schema({vol.Required("export_now", default=True): bool}),
            errors=errors,
        )

    async def async_step_global_options(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        if user_input is not None:
            notify_service = str(user_input[CONF_NOTIFY_SERVICE]).strip() or DEFAULT_NOTIFY_SERVICE
            property_type = str(user_input.get(CONF_PROPERTY_TYPE, current.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE)))
            default_name, default_single, default_plural = PROPERTY_TYPE_DEFAULTS.get(property_type, PROPERTY_TYPE_DEFAULTS[DEFAULT_PROPERTY_TYPE])
            object_label = str(user_input.get(CONF_OBJECT_LABEL, default_single)).strip() or default_single
            object_label_plural = str(user_input.get(CONF_OBJECT_LABEL_PLURAL, default_plural)).strip() or default_plural
            admin_password = str(user_input.get(CONF_ADMIN_PASSWORD, "") or "").strip()
            password_enabled = bool(user_input.get(CONF_ADMIN_PASSWORD_ENABLED, False)) and bool(admin_password)
            current[CONF_NOTIFY_SERVICE] = notify_service
            current[CONF_SEND_MODE] = SEND_MODE_TARGET
            current[CONF_PROPERTY_TYPE] = property_type
            current[CONF_OBJECT_LABEL] = object_label
            current[CONF_OBJECT_LABEL_PLURAL] = object_label_plural
            # Explicit rule: disabled checkbox OR empty password disables protection.
            # This writes both positive and legacy negative flags into options and data
            # so old config-entry data can no longer reactivate a deleted password.
            current[CONF_ADMIN_PASSWORD_ENABLED] = password_enabled
            current[CONF_ADMIN_PASSWORD_DISABLED] = not password_enabled
            current[CONF_ADMIN_PASSWORD] = admin_password if password_enabled else ""
            raw_default_price = user_input.get(FORM_PRICE_KWH, user_input.get(CONF_DEFAULT_KWH_PRICE, current.get(CONF_DEFAULT_KWH_PRICE, 0.0)))
            try:
                current[CONF_DEFAULT_KWH_PRICE] = float(str(raw_default_price or 0).replace(",", "."))
            except Exception:
                current[CONF_DEFAULT_KWH_PRICE] = 0.0
            current[CONF_HA_BASE_URL] = str(user_input.get(FORM_HA_BASE_URL, user_input.get(CONF_HA_BASE_URL, current.get(CONF_HA_BASE_URL, ""))) or "").strip().rstrip("/")
            data = dict(self._config_entry.data or {})
            data[CONF_ADMIN_PASSWORD_ENABLED] = password_enabled
            data[CONF_ADMIN_PASSWORD_DISABLED] = not password_enabled
            data[CONF_ADMIN_PASSWORD] = admin_password if password_enabled else ""
            self.hass.config_entries.async_update_entry(self._config_entry, data=data)
            current.setdefault(CONF_BERTHS, [])
            self._update_options_keep_open(current)
            return await self.async_step_manage_objects()
        _, single, plural = _property_defaults(current)
        return self.async_show_form(
            step_id="global_options",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NOTIFY_SERVICE, default=current.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)): str,
                    vol.Required(CONF_PROPERTY_TYPE, default=current.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE)): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=PROPERTY_TYPE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
                    ),
                    vol.Required(CONF_OBJECT_LABEL, default=single): str,
                    vol.Required(CONF_OBJECT_LABEL_PLURAL, default=plural): str,
                    vol.Required(CONF_ADMIN_PASSWORD_ENABLED, default=bool(current.get(CONF_ADMIN_PASSWORD_ENABLED, False))): bool,
                    vol.Optional(CONF_ADMIN_PASSWORD, default=current.get(CONF_ADMIN_PASSWORD, "")): str,
                    vol.Optional(FORM_PRICE_KWH, default=str(current.get(CONF_DEFAULT_KWH_PRICE, 0.0) or 0.0)): str,
                    vol.Optional(FORM_HA_BASE_URL, default=str(current.get(CONF_HA_BASE_URL, "") or _detected_ha_base_url(self.hass))): str,
                }
            ),
        )

    async def async_step_management_options(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            action = str(user_input.get("management_action", "")).strip()
            if action == "management_default":
                return await self.async_step_management_default()
            if action == "management_monthly":
                return await self.async_step_management_monthly()
            if action == "management_quarterly":
                return await self.async_step_management_quarterly()
            if action == "management_yearly":
                return await self.async_step_management_yearly()
        return self.async_show_form(
            step_id="management_options",
            description_placeholders={"info": "Verwaltungsversand separat fuer Monats-, Quartals- und Jahresbericht einstellen."},
            data_schema=vol.Schema(
                {
                    vol.Required("management_action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=MANAGEMENT_ACTION_OPTIONS, mode=selector.SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def async_step_management_default(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        errors: dict[str, str] = {}
        if user_input is not None:
            email = str(user_input.get(CONF_MANAGEMENT_DEFAULT_EMAIL, "")).strip()
            if email and not EMAIL_RE.match(email):
                errors[CONF_MANAGEMENT_DEFAULT_EMAIL] = "invalid_email"
            if not errors:
                current[CONF_MANAGEMENT_DEFAULT_EMAIL] = email
                current[CONF_MANAGEMENT_EMAIL] = email
                self._update_options_keep_open(current)
                return await self.async_step_management_options()
        return self.async_show_form(
            step_id="management_default",
            data_schema=vol.Schema({vol.Required(CONF_MANAGEMENT_DEFAULT_EMAIL, default=current.get(CONF_MANAGEMENT_DEFAULT_EMAIL, current.get(CONF_MANAGEMENT_EMAIL, ""))): str}),
            errors=errors,
        )

    def _management_email_value(self, current: dict[str, Any], key: str) -> str:
        return str(current.get(key, "") or "")

    def _management_default_email(self, current: dict[str, Any]) -> str:
        return str(current.get(CONF_MANAGEMENT_DEFAULT_EMAIL) or current.get(CONF_MANAGEMENT_EMAIL) or "").strip()

    def _notify_service_is_configured(self, current: dict[str, Any]) -> bool:
        return bool(str(current.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE) or "").strip())

    async def async_step_management_monthly(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        errors: dict[str, str] = {}
        if user_input is not None:
            send_time = _clean_time(user_input.get(CONF_MANAGEMENT_MONTHLY_SEND_TIME, "08:00"))
            if not TIME_RE.match(send_time):
                errors[CONF_MANAGEMENT_MONTHLY_SEND_TIME] = "invalid_time"
            day = int(user_input.get(CONF_MANAGEMENT_MONTHLY_MONTHDAY, 1))
            if not 1 <= day <= 31:
                errors[CONF_MANAGEMENT_MONTHLY_MONTHDAY] = "invalid_monthday"
            if not errors:
                current[CONF_MANAGEMENT_MONTHLY_ENABLED] = bool(user_input.get(CONF_MANAGEMENT_MONTHLY_ENABLED, False))
                current[CONF_MANAGEMENT_MONTHLY_EMAIL] = ""
                current[CONF_MANAGEMENT_MONTHLY_SEND_TIME] = send_time
                current[CONF_MANAGEMENT_MONTHLY_MONTHDAY] = day
                self._sync_legacy_management_fields(current)
                self._save_options(current)
                if bool(user_input.get("send_test_now", False)):
                    if not self._management_default_email(current):
                        errors["base"] = "management_email_missing"
                        return self.async_show_form(step_id="management_monthly", data_schema=self._management_monthly_schema(current), errors=errors)
                    try:
                        from . import _async_send_management_report, _management_recipient
                        await _async_send_management_report(self.hass, self._config_entry, manual=True, interval=INTERVAL_MONTHLY, recipient=_management_recipient(current))
                    except HomeAssistantError:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_monthly", data_schema=self._management_monthly_schema(current), errors=errors)
                    except Exception:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_monthly", data_schema=self._management_monthly_schema(current), errors=errors)
                self._update_options_keep_open(current)
                return await self.async_step_management_options()
        return self.async_show_form(step_id="management_monthly", data_schema=self._management_monthly_schema(current), errors=errors)

    def _management_monthly_schema(self, current: dict[str, Any]) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_MANAGEMENT_MONTHLY_ENABLED, default=bool(current.get(CONF_MANAGEMENT_MONTHLY_ENABLED, False))): bool,
            vol.Required(CONF_MANAGEMENT_MONTHLY_SEND_TIME, default=current.get(CONF_MANAGEMENT_MONTHLY_SEND_TIME, "08:00")): selector.TimeSelector(),
            vol.Required(CONF_MANAGEMENT_MONTHLY_MONTHDAY, default=int(current.get(CONF_MANAGEMENT_MONTHLY_MONTHDAY, 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("send_test_now", default=False): bool,
        })

    async def async_step_management_quarterly(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        errors: dict[str, str] = {}
        if user_input is not None:
            send_time = _clean_time(user_input.get(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, "08:00"))
            if not TIME_RE.match(send_time):
                errors[CONF_MANAGEMENT_QUARTERLY_SEND_TIME] = "invalid_time"
            day = int(user_input.get(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, 1))
            if not 1 <= day <= 31:
                errors[CONF_MANAGEMENT_QUARTERLY_MONTHDAY] = "invalid_monthday"
            mode = str(user_input.get(CONF_MANAGEMENT_QUARTERLY_MODE, QUARTER_MODE_START))
            if mode not in (QUARTER_MODE_START, QUARTER_MODE_END):
                errors[CONF_MANAGEMENT_QUARTERLY_MODE] = "invalid_quarter_mode"
            q_enabled = any(bool(user_input.get(key, False)) for key in (CONF_MANAGEMENT_QUARTERLY_Q1, CONF_MANAGEMENT_QUARTERLY_Q2, CONF_MANAGEMENT_QUARTERLY_Q3, CONF_MANAGEMENT_QUARTERLY_Q4))
            if bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False)) and not q_enabled:
                errors[CONF_MANAGEMENT_QUARTERLY_Q1] = "at_least_one_quarter"
            test_quarter = int(user_input.get("test_quarter", 1) or 1)
            if not 1 <= test_quarter <= 4:
                test_quarter = 1
            if not errors:
                current[CONF_MANAGEMENT_QUARTERLY_ENABLED] = bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False))
                current[CONF_MANAGEMENT_QUARTERLY_EMAIL] = ""
                current[CONF_MANAGEMENT_QUARTERLY_SEND_TIME] = send_time
                current[CONF_MANAGEMENT_QUARTERLY_MONTHDAY] = day
                current[CONF_MANAGEMENT_QUARTERLY_MODE] = mode
                current[CONF_MANAGEMENT_QUARTERLY_Q1] = bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_Q1, False))
                current[CONF_MANAGEMENT_QUARTERLY_Q2] = bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_Q2, False))
                current[CONF_MANAGEMENT_QUARTERLY_Q3] = bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_Q3, False))
                current[CONF_MANAGEMENT_QUARTERLY_Q4] = bool(user_input.get(CONF_MANAGEMENT_QUARTERLY_Q4, False))
                self._sync_legacy_management_fields(current)
                self._save_options(current)
                if bool(user_input.get("send_test_now", False)):
                    if not self._management_default_email(current):
                        errors["base"] = "management_email_missing"
                        return self.async_show_form(step_id="management_quarterly", data_schema=self._management_quarterly_schema(current), errors=errors)
                    try:
                        from . import _async_send_management_report, _management_recipient
                        await _async_send_management_report(self.hass, self._config_entry, manual=True, interval=INTERVAL_QUARTERLY, recipient=_management_recipient(current), quarter=test_quarter)
                    except HomeAssistantError:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_quarterly", data_schema=self._management_quarterly_schema(current), errors=errors)
                    except Exception:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_quarterly", data_schema=self._management_quarterly_schema(current), errors=errors)
                self._update_options_keep_open(current)
                return await self.async_step_management_options()
        return self.async_show_form(step_id="management_quarterly", data_schema=self._management_quarterly_schema(current), errors=errors)

    def _management_quarterly_schema(self, current: dict[str, Any]) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_MANAGEMENT_QUARTERLY_ENABLED, default=bool(current.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False))): bool,
            vol.Required(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, default=current.get(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, "08:00")): selector.TimeSelector(),
            vol.Required(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, default=int(current.get(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_MANAGEMENT_QUARTERLY_MODE, default=current.get(CONF_MANAGEMENT_QUARTERLY_MODE, QUARTER_MODE_START)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=QUARTER_MODE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_MANAGEMENT_QUARTERLY_Q1, default=bool(current.get(CONF_MANAGEMENT_QUARTERLY_Q1, True))): bool,
            vol.Required(CONF_MANAGEMENT_QUARTERLY_Q2, default=bool(current.get(CONF_MANAGEMENT_QUARTERLY_Q2, True))): bool,
            vol.Required(CONF_MANAGEMENT_QUARTERLY_Q3, default=bool(current.get(CONF_MANAGEMENT_QUARTERLY_Q3, True))): bool,
            vol.Required(CONF_MANAGEMENT_QUARTERLY_Q4, default=bool(current.get(CONF_MANAGEMENT_QUARTERLY_Q4, True))): bool,
            vol.Optional("test_quarter", default="1"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=REPORT_TEST_QUARTER_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional("send_test_now", default=False): bool,
        })

    async def async_step_management_yearly(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        errors: dict[str, str] = {}
        if user_input is not None:
            send_time = _clean_time(user_input.get(CONF_MANAGEMENT_YEARLY_SEND_TIME, "08:00"))
            if not TIME_RE.match(send_time):
                errors[CONF_MANAGEMENT_YEARLY_SEND_TIME] = "invalid_time"
            day = int(user_input.get(CONF_MANAGEMENT_YEARLY_MONTHDAY, 1))
            month = int(user_input.get(CONF_MANAGEMENT_YEARLY_MONTH, 1))
            if not 1 <= day <= 31:
                errors[CONF_MANAGEMENT_YEARLY_MONTHDAY] = "invalid_monthday"
            if not 1 <= month <= 12:
                errors[CONF_MANAGEMENT_YEARLY_MONTH] = "invalid_month"
            if not errors:
                current[CONF_MANAGEMENT_YEARLY_ENABLED] = bool(user_input.get(CONF_MANAGEMENT_YEARLY_ENABLED, False))
                current[CONF_MANAGEMENT_YEARLY_EMAIL] = ""
                current[CONF_MANAGEMENT_YEARLY_SEND_TIME] = send_time
                current[CONF_MANAGEMENT_YEARLY_MONTHDAY] = day
                current[CONF_MANAGEMENT_YEARLY_MONTH] = month
                self._sync_legacy_management_fields(current)
                self._save_options(current)
                if bool(user_input.get("send_test_now", False)):
                    if not self._management_default_email(current):
                        errors["base"] = "management_email_missing"
                        return self.async_show_form(step_id="management_yearly", data_schema=self._management_yearly_schema(current), errors=errors)
                    try:
                        from . import _async_send_management_report, _management_recipient
                        await _async_send_management_report(self.hass, self._config_entry, manual=True, interval=INTERVAL_YEARLY, recipient=_management_recipient(current))
                    except HomeAssistantError:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_yearly", data_schema=self._management_yearly_schema(current), errors=errors)
                    except Exception:
                        errors["base"] = "send_failed"
                        return self.async_show_form(step_id="management_yearly", data_schema=self._management_yearly_schema(current), errors=errors)
                self._update_options_keep_open(current)
                return await self.async_step_management_options()
        return self.async_show_form(step_id="management_yearly", data_schema=self._management_yearly_schema(current), errors=errors)

    def _management_yearly_schema(self, current: dict[str, Any]) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_MANAGEMENT_YEARLY_ENABLED, default=bool(current.get(CONF_MANAGEMENT_YEARLY_ENABLED, False))): bool,
            vol.Required(CONF_MANAGEMENT_YEARLY_SEND_TIME, default=current.get(CONF_MANAGEMENT_YEARLY_SEND_TIME, "08:00")): selector.TimeSelector(),
            vol.Required(CONF_MANAGEMENT_YEARLY_MONTHDAY, default=int(current.get(CONF_MANAGEMENT_YEARLY_MONTHDAY, 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_MANAGEMENT_YEARLY_MONTH, default=str(current.get(CONF_MANAGEMENT_YEARLY_MONTH, 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=MONTH_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional("send_test_now", default=False): bool,
        })

    def _sync_legacy_management_fields(self, current: dict[str, Any]) -> None:
        intervals: list[str] = []
        if current.get(CONF_MANAGEMENT_MONTHLY_ENABLED):
            intervals.append(INTERVAL_MONTHLY)
        if current.get(CONF_MANAGEMENT_QUARTERLY_ENABLED):
            intervals.append(INTERVAL_QUARTERLY)
        if current.get(CONF_MANAGEMENT_YEARLY_ENABLED):
            intervals.append(INTERVAL_YEARLY)
        current[CONF_MANAGEMENT_INTERVALS] = intervals or [INTERVAL_MONTHLY]
        current[CONF_MANAGEMENT_INTERVAL] = current[CONF_MANAGEMENT_INTERVALS][0]
        current[CONF_MANAGEMENT_EMAIL] = str(current.get(CONF_MANAGEMENT_DEFAULT_EMAIL, current.get(CONF_MANAGEMENT_EMAIL, "")) or "")
        current[CONF_MANAGEMENT_SEND_TIME] = str(current.get(CONF_MANAGEMENT_MONTHLY_SEND_TIME, current.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
        current[CONF_MANAGEMENT_MONTHDAY] = int(current.get(CONF_MANAGEMENT_MONTHLY_MONTHDAY, current.get(CONF_MANAGEMENT_MONTHDAY, 1)) or 1)
        current[CONF_MANAGEMENT_MONTH] = int(current.get(CONF_MANAGEMENT_YEARLY_MONTH, current.get(CONF_MANAGEMENT_MONTH, 1)) or 1)

    async def async_step_add_berth(self, user_input: dict[str, Any] | None = None):
        options = self._options()
        if user_input is not None:
            berth = _normalize_berth(user_input)
            errors = _validate_berth(berth)
            if any(b.get("berth_id") == berth["berth_id"] for b in options[CONF_BERTHS]):
                errors["berth_id"] = "already_exists"
            if not errors:
                options[CONF_BERTHS].append(berth)
                options[CONF_BERTHS].sort(key=lambda item: _natural_sort_key(item.get("berth_id", "")))
                self._update_options_keep_open(options)
                return await self.async_step_manage_objects()
            return self.async_show_form(step_id="add_berth", data_schema=_berth_schema(self.hass, user_input), errors=errors)
        return self.async_show_form(step_id="add_berth", data_schema=_berth_schema(self.hass, _default_new_berth(options)))

    async def async_step_edit_berth(self, user_input: dict[str, Any] | None = None):
        options = self._options()
        if not options.get(CONF_BERTHS):
            return self.async_show_form(step_id="no_berths", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
        if user_input is not None:
            self._selected_berth_id = str(user_input["berth_id"])
            return await self.async_step_edit_berth_data()
        return self.async_show_form(step_id="edit_berth", data_schema=self._berth_select_schema())

    async def async_step_edit_berth_data(self, user_input: dict[str, Any] | None = None):
        options = self._options()
        old_id = self._selected_berth_id
        existing = next((b for b in options[CONF_BERTHS] if b.get("berth_id") == old_id), None)
        if existing is None:
            return self.async_show_form(step_id="no_berths", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
        if user_input is not None:
            berth = _normalize_berth(user_input, existing)
            errors = _validate_berth(berth)
            if berth["berth_id"] != old_id and any(b.get("berth_id") == berth["berth_id"] for b in options[CONF_BERTHS]):
                errors["berth_id"] = "already_exists"
            if not errors:
                options[CONF_BERTHS] = [b for b in options[CONF_BERTHS] if b.get("berth_id") != old_id]
                options[CONF_BERTHS].append(berth)
                options[CONF_BERTHS].sort(key=lambda item: _natural_sort_key(item.get("berth_id", "")))
                self._update_options_keep_open(options)
                return await self.async_step_manage_objects()
            return self.async_show_form(step_id="edit_berth_data", data_schema=_berth_schema(self.hass, user_input, edit=True), errors=errors)
        return self.async_show_form(step_id="edit_berth_data", data_schema=_berth_schema(self.hass, existing, edit=True))

    async def async_step_remove_object(self, user_input: dict[str, Any] | None = None):
        options = self._options()
        if not options.get(CONF_BERTHS):
            return self.async_show_form(step_id="no_berths", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
        if user_input is not None:
            berth_id = str(user_input["berth_id"])
            options[CONF_BERTHS] = [b for b in options[CONF_BERTHS] if b.get("berth_id") != berth_id]
            self._update_options_keep_open(options)
            return await self.async_step_manage_objects()
        return self.async_show_form(step_id="remove_object", data_schema=self._berth_select_schema())

    async def async_step_test_mail(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            email = str(user_input.get(CONF_EMAIL, "")).strip()
            if not EMAIL_RE.match(email):
                errors[CONF_EMAIL] = "invalid_email"
            else:
                try:
                    from . import _async_send_test_mail
                    await _async_send_test_mail(self.hass, self._config_entry, email)
                    return self.async_show_form(step_id="test_mail_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
                except (HomeAssistantError, Exception):
                    errors["base"] = "send_failed"
        return self.async_show_form(step_id="test_mail", data_schema=vol.Schema({vol.Required(CONF_EMAIL): str}), errors=errors)

    async def async_step_test_berth_mail(self, user_input: dict[str, Any] | None = None):
        options = self._options()
        if not options.get(CONF_BERTHS):
            return self.async_show_form(step_id="no_berths", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
        errors: dict[str, str] = {}
        if user_input is not None:
            berth_id = str(user_input.get("berth_id", "")).strip()
            berth = next((b for b in options[CONF_BERTHS] if b.get("berth_id") == berth_id), None)
            if not berth:
                errors["base"] = "not_found"
            else:
                if not str(berth.get(CONF_EMAIL, "")).strip():
                    errors["base"] = "email_missing"
                else:
                    try:
                        from . import _async_send_berth_mail
                        await _async_send_berth_mail(self.hass, self._config_entry, berth, manual=True)
                        return self.async_show_form(step_id="test_berth_mail_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
                    except (HomeAssistantError, Exception):
                        errors["base"] = "send_failed"
        return self.async_show_form(step_id="test_berth_mail", data_schema=self._berth_select_schema(), errors=errors)

    async def async_step_send_management_report(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                from . import _async_send_management_report
                await _async_send_management_report(self.hass, self._config_entry, manual=True)
                return self.async_show_form(step_id="management_report_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))
            except (HomeAssistantError, Exception):
                errors["base"] = "send_failed"
        return self.async_show_form(
            step_id="send_management_report",
            data_schema=vol.Schema({vol.Required("send_now", default=True): bool}),
            errors=errors,
        )


    async def async_step_billing_pdf(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._billing_scope = str(user_input.get(FORM_SCOPE, user_input.get("scope", BILLING_SCOPE_SHORT_TERM)))
            return await self.async_step_billing_pdf_details()
        return self.async_show_form(
            step_id="billing_pdf",
            data_schema=vol.Schema({
                vol.Required(FORM_SCOPE, default=BILLING_SCOPE_SHORT_TERM): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=BILLING_SCOPE_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
                ),
            }),
        )

    async def async_step_billing_pdf_details(self, user_input: dict[str, Any] | None = None):
        current = self._options()
        errors: dict[str, str] = {}
        scope = getattr(self, "_billing_scope", BILLING_SCOPE_SHORT_TERM)
        rental_filter = RENTAL_TYPE_SHORT_TERM if scope == BILLING_SCOPE_SHORT_TERM else RENTAL_TYPE_PERMANENT
        if user_input is not None:
            try:
                from . import _async_create_billing_pdf_and_mail
                raw_price = user_input.get(FORM_PRICE_KWH, user_input.get(CONF_DEFAULT_KWH_PRICE, current.get(CONF_DEFAULT_KWH_PRICE, 0.0)))
                try:
                    price = float(str(raw_price or 0).replace(",", "."))
                except Exception:
                    price = float(current.get(CONF_DEFAULT_KWH_PRICE, 0.0) or 0.0)
                object_id_value = str(user_input.get(FORM_OBJECT_ID, user_input.get("object_id", ""))).strip()
                if not object_id_value:
                    errors["base"] = "billing_object_required"
                    raise HomeAssistantError("billing_object_required")
                pdf_url = await _async_create_billing_pdf_and_mail(
                    self.hass,
                    self._config_entry,
                    start_date=str(user_input.get(FORM_START_DATE, user_input.get("start_date", ""))).strip(),
                    end_date=str(user_input.get(FORM_END_DATE, user_input.get("end_date", ""))).strip(),
                    price_kwh=price,
                    scope=scope,
                    object_id=object_id_value,
                )
                self._last_pdf_url = pdf_url
                try:
                    from homeassistant.components import persistent_notification

                    persistent_notification.async_create(
                        self.hass,
                        f"Die PDF-Abrechnung wurde erstellt und per E-Mail versendet.\n\n"
                        f"PDF öffnen: {pdf_url}\n\n"
                        f"Hinweis: Falls der normale Klick zum Dashboard führt, bitte Rechtsklick oder lange drücken und im neuen Tab öffnen.\n\n"
                        f"Direkter Link zum Kopieren: `{pdf_url}`",
                        title="Liegenschafts Mailer - PDF-Abrechnung",
                        notification_id="liegenschafts_mailer_billing_pdf",
                    )
                except Exception:
                    pass
                return self.async_show_form(
                    step_id="billing_pdf_done",
                    data_schema=vol.Schema({
                        vol.Required("back", default=True): bool,
                    }),
                    description_placeholders={
                        "pdf_url": pdf_url,
                        "pdf_link": f"PDF öffnen: {pdf_url}",
                    },
                )
            except HomeAssistantError:
                if "base" not in errors:
                    errors["base"] = "billing_failed"
            except Exception:
                errors["base"] = "billing_failed"
        return self.async_show_form(
            step_id="billing_pdf_details",
            data_schema=vol.Schema({
                vol.Required(FORM_OBJECT_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=self._billing_object_options(rental_type=rental_filter), mode=selector.SelectSelectorMode.DROPDOWN)
                ),
                vol.Required(FORM_START_DATE, default=(date.today() - timedelta(days=1)).isoformat()): selector.DateSelector(),
                vol.Required(FORM_END_DATE, default=date.today().isoformat()): selector.DateSelector(),
                vol.Optional(FORM_PRICE_KWH, default=str(current.get(CONF_DEFAULT_KWH_PRICE, 0.0) or 0.0)): str,
            }),
            errors=errors,
        )


    async def async_step_list_berths(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        options = self._options()
        return self.async_show_form(
            step_id="list_berths",
            data_schema=vol.Schema({vol.Required("back", default=True): bool}),
            description_placeholders={"berth_table": _berths_markdown_table(options)},
        )

    async def async_step_no_berths(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(step_id="no_berths", data_schema=vol.Schema({vol.Required("back", default=True): bool}))

    async def async_step_test_mail_done(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(step_id="test_mail_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))

    async def async_step_test_berth_mail_done(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(step_id="test_berth_mail_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))

    async def async_step_management_report_done(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(step_id="management_report_done", data_schema=vol.Schema({vol.Required("back", default=True): bool}))

    async def async_step_export_csv_done(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_csv_mail_sent_done(user_input)

    async def async_step_export_csv_mail_done(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_csv_mail_sent_done(user_input)

    async def async_step_csv_mail_done(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_csv_mail_sent_done(user_input)

    async def async_step_billing_pdf_done(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        pdf_url = getattr(self, "_last_pdf_url", "")
        if pdf_url:
            return self.async_show_form(
                step_id="billing_pdf_done",
                data_schema=vol.Schema({
                    vol.Required("back", default=True): bool,
                }),
                description_placeholders={
                    "pdf_url": pdf_url,
                    "pdf_link": f"PDF öffnen: {pdf_url}",
                },
            )
        return self.async_show_form(step_id="billing_pdf_done", data_schema=vol.Schema({
            vol.Required("back", default=True): bool,
        }))

    async def async_step_csv_mail_sent_done(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(
            step_id="csv_mail_sent_done",
            data_schema=vol.Schema({
                vol.Required("back", default=True): bool,
            }),
        )
