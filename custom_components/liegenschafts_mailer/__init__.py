"""Liegenschafts Mailer integration for Home Assistant."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timedelta
import calendar
import csv
import io
import math
import os
import html
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADMIN_PASSWORD,
    CONF_ADMIN_PASSWORD_ENABLED,
    CONF_ADMIN_PASSWORD_DISABLED,
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
    DEFAULT_RENTAL_TYPE,
    DEFAULT_SEND_MODE,
    DEFAULT_TENANT_SALUTATION,
    DOMAIN,
    INTERVAL_DAILY,
    INTERVAL_MONTHLY,
    INTERVAL_QUARTERLY,
    INTERVAL_WEEKLY,
    INTERVAL_YEARLY,
    INTERVALS,
    PROPERTY_TYPE_DEFAULTS,
    RENTAL_TYPE_PERMANENT,
    RENTAL_TYPE_SHORT_TERM,
    SERVICE_ADD_UPDATE_BERTH,
    SERVICE_REMOVE_BERTH,
    SERVICE_SEND_ALL_NOW,
    SERVICE_SEND_MANAGEMENT_REPORT_NOW,
    SERVICE_SEND_NOW,
    SERVICE_SEND_TEST_MAIL,
    SERVICE_EXPORT_CURRENT_CSV,
    SERVICE_SEND_CSV_TO_MANAGEMENT,
    SERVICE_SEND_BILLING_PDF_TO_MANAGEMENT,
    SEND_MODE_TARGET,
    TENANT_SALUTATION_MR,
    TENANT_SALUTATION_MS,
    QUARTER_MODE_START,
    QUARTER_MODE_END,
    BILLING_SCOPE_SHORT_TERM,
    BILLING_SCOPE_LONG_TERM,
    BILLING_SCOPE_ALL,
    BILLING_SCOPE_OBJECT,
)

_LOGGER = logging.getLogger(__name__)

DATA_UNSUB = "unsub"
PLATFORMS: list[Platform] = [Platform.SENSOR]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

ADD_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required("object_id"): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_TENANT_SALUTATION, default=DEFAULT_TENANT_SALUTATION): vol.In([TENANT_SALUTATION_MR, TENANT_SALUTATION_MS]),
        vol.Required("tenant_name"): cv.string,
        vol.Optional(CONF_EMAIL, default=""): cv.string,
        vol.Optional(CONF_RENTAL_TYPE, default=DEFAULT_RENTAL_TYPE): vol.In([RENTAL_TYPE_PERMANENT, RENTAL_TYPE_SHORT_TERM]),
        vol.Required("meter_sensor"): cv.entity_id,
        vol.Required("interval", default=INTERVAL_MONTHLY): vol.In(INTERVALS),
        vol.Required("send_time", default="08:00"): cv.string,
        vol.Optional("weekday", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=7)),
        vol.Optional("monthday", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
        vol.Optional("month", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
        vol.Optional("enabled", default=True): cv.boolean,
    }
)

REMOVE_SCHEMA = vol.Schema({vol.Required("object_id"): cv.string})
SEND_NOW_SCHEMA = vol.Schema({vol.Required("object_id"): cv.string})
SEND_ALL_NOW_SCHEMA = vol.Schema({})
SEND_TEST_MAIL_SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): cv.string})
SEND_MANAGEMENT_REPORT_NOW_SCHEMA = vol.Schema({})
EXPORT_CURRENT_CSV_SCHEMA = vol.Schema({})
BILLING_PDF_SCHEMA = vol.Schema({
    vol.Required("start_date"): cv.string,
    vol.Required("end_date"): cv.string,
    vol.Optional("price_kwh"): vol.Coerce(float),
    vol.Optional("scope", default=BILLING_SCOPE_SHORT_TERM): vol.In([BILLING_SCOPE_SHORT_TERM, BILLING_SCOPE_LONG_TERM, BILLING_SCOPE_ALL, BILLING_SCOPE_OBJECT]),
    vol.Optional("object_id", default=""): cv.string,
})


def _property_defaults(options: dict[str, Any]) -> tuple[str, str, str]:
    property_type = str(options.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    default_name, default_single, default_plural = PROPERTY_TYPE_DEFAULTS.get(
        property_type, PROPERTY_TYPE_DEFAULTS[DEFAULT_PROPERTY_TYPE]
    )
    single = str(options.get(CONF_OBJECT_LABEL, default_single) or default_single).strip()
    plural = str(options.get(CONF_OBJECT_LABEL_PLURAL, default_plural) or default_plural).strip()
    return default_name, single, plural


def _entry_options(entry: ConfigEntry) -> dict[str, Any]:
    """Return a mutable copy of entry options with defaults."""
    options = deepcopy(dict(entry.options or {}))
    options.setdefault(CONF_NOTIFY_SERVICE, entry.data.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE))
    options.setdefault(CONF_SEND_MODE, SEND_MODE_TARGET)
    options.setdefault(CONF_BERTHS, [])
    legacy_password = str(entry.data.get(CONF_ADMIN_PASSWORD, "") or "").strip()
    option_password = str(options.get(CONF_ADMIN_PASSWORD, "") or "").strip()
    raw_enabled = options.get(CONF_ADMIN_PASSWORD_ENABLED, entry.data.get(CONF_ADMIN_PASSWORD_ENABLED, None))
    raw_disabled = options.get(CONF_ADMIN_PASSWORD_DISABLED, entry.data.get(CONF_ADMIN_PASSWORD_DISABLED, None))
    if raw_enabled is None:
        password_enabled = bool((option_password or legacy_password) and not bool(raw_disabled))
    else:
        password_enabled = bool(raw_enabled)
    if password_enabled:
        options[CONF_ADMIN_PASSWORD] = option_password or legacy_password
        options[CONF_ADMIN_PASSWORD_ENABLED] = True
        options[CONF_ADMIN_PASSWORD_DISABLED] = False
    else:
        options[CONF_ADMIN_PASSWORD] = ""
        options[CONF_ADMIN_PASSWORD_ENABLED] = False
        options[CONF_ADMIN_PASSWORD_DISABLED] = True
    options.setdefault(CONF_PROPERTY_TYPE, entry.data.get(CONF_PROPERTY_TYPE, DEFAULT_PROPERTY_TYPE))
    _, single, plural = _property_defaults(options)
    options.setdefault(CONF_OBJECT_LABEL, single)
    options.setdefault(CONF_OBJECT_LABEL_PLURAL, plural)
    options.setdefault(CONF_MANAGEMENT_EMAIL, entry.data.get(CONF_MANAGEMENT_EMAIL, ""))
    options.setdefault(CONF_MANAGEMENT_INTERVAL, entry.data.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY))
    options.setdefault(CONF_MANAGEMENT_INTERVALS, _management_intervals_from_options(options, entry.data))
    options.setdefault(CONF_MANAGEMENT_SEND_TIME, entry.data.get(CONF_MANAGEMENT_SEND_TIME, "08:00"))
    options.setdefault(CONF_MANAGEMENT_MONTHDAY, int(entry.data.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_MONTH, int(entry.data.get(CONF_MANAGEMENT_MONTH, 1) or 1))
    options.setdefault(CONF_DEFAULT_KWH_PRICE, float(entry.data.get(CONF_DEFAULT_KWH_PRICE, 0.0) or 0.0))
    default_mgmt_email = str(options.get(CONF_MANAGEMENT_EMAIL, entry.data.get(CONF_MANAGEMENT_EMAIL, "")) or "")
    options.setdefault(CONF_MANAGEMENT_DEFAULT_EMAIL, default_mgmt_email)
    intervals = _management_intervals_from_options(options, entry.data)
    options.setdefault(CONF_MANAGEMENT_MONTHLY_ENABLED, INTERVAL_MONTHLY in intervals)
    options.setdefault(CONF_MANAGEMENT_MONTHLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_MONTHLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_MONTHLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_ENABLED, INTERVAL_QUARTERLY in intervals)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_MODE, QUARTER_MODE_START)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q1, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q2, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q3, True)
    options.setdefault(CONF_MANAGEMENT_QUARTERLY_Q4, True)
    options.setdefault(CONF_MANAGEMENT_YEARLY_ENABLED, INTERVAL_YEARLY in intervals)
    options.setdefault(CONF_MANAGEMENT_YEARLY_EMAIL, "")
    options.setdefault(CONF_MANAGEMENT_YEARLY_SEND_TIME, str(options.get(CONF_MANAGEMENT_SEND_TIME, "08:00")))
    options.setdefault(CONF_MANAGEMENT_YEARLY_MONTHDAY, int(options.get(CONF_MANAGEMENT_MONTHDAY, 1) or 1))
    options.setdefault(CONF_MANAGEMENT_YEARLY_MONTH, int(options.get(CONF_MANAGEMENT_MONTH, 1) or 1))
    return options


def _natural_sort_key(value: str) -> tuple[str, int]:
    text = str(value or "").strip()
    match = re.search(r"^(.*?)[\s_-]*0*(\d+)$", text, re.IGNORECASE)
    if match:
        return (match.group(1).strip().lower(), int(match.group(2)))
    return (text.lower(), 0)


def _get_single_entry(hass: HomeAssistant) -> ConfigEntry:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Liegenschafts Mailer ist noch nicht eingerichtet.")
    return entries[0]


def _clean_time(value: Any) -> str:
    send_time = str(value or "").strip()
    if len(send_time) == 8 and send_time.endswith(":00"):
        send_time = send_time[:5]
    return send_time


def _normalize_berth(data: dict[str, Any]) -> dict[str, Any]:
    berth_id = str(data.get("object_id") or data.get("berth_id") or "").strip()
    if not berth_id:
        raise HomeAssistantError("object_id darf nicht leer sein.")
    email = str(data.get(CONF_EMAIL, "")).strip()
    if email and not EMAIL_RE.match(email):
        raise HomeAssistantError(f"Ungueltige E-Mail-Adresse: {email}")
    send_time = _clean_time(data.get("send_time", "08:00"))
    if not TIME_RE.match(send_time):
        raise HomeAssistantError("send_time muss im Format HH:MM angegeben werden, z. B. 08:00.")
    interval = data.get("interval", INTERVAL_MONTHLY)
    if interval not in INTERVALS:
        raise HomeAssistantError("Ungueltiges Intervall.")
    return {
        "berth_id": berth_id,
        CONF_NAME: str(data[CONF_NAME]).strip(),
        CONF_TENANT_SALUTATION: str(data.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION)),
        "tenant_name": str(data["tenant_name"]).strip(),
        CONF_EMAIL: email,
        CONF_RENTAL_TYPE: str(data.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE) or DEFAULT_RENTAL_TYPE),
        "meter_sensor": str(data["meter_sensor"]).strip(),
        "interval": interval,
        "send_time": send_time,
        "weekday": int(data.get("weekday", 1)),
        "monthday": int(data.get("monthday", 1)),
        "month": int(data.get("month", 1)),
        "enabled": bool(data.get("enabled", True)),
    }


def _effective_monthday(year: int, month: int, day: int) -> int:
    return min(int(day), calendar.monthrange(year, month)[1])


def _due_today_for_interval(interval: str, now: datetime, *, weekday: int = 1, monthday: int = 1, month: int = 1) -> bool:
    if interval == INTERVAL_DAILY:
        return True
    if interval == INTERVAL_WEEKLY:
        return now.isoweekday() == int(weekday)
    if interval == INTERVAL_MONTHLY:
        return now.day == _effective_monthday(now.year, now.month, int(monthday))
    if interval == INTERVAL_QUARTERLY:
        # Jan/Apr/Jul/Oct by default, shifted by configured start month.
        return ((now.month - int(month)) % 3 == 0) and now.day == _effective_monthday(now.year, now.month, int(monthday))
    if interval == INTERVAL_YEARLY:
        return now.month == int(month) and now.day == _effective_monthday(now.year, now.month, int(monthday))
    return False


def _due_today(berth: dict[str, Any], now: datetime) -> bool:
    return _due_today_for_interval(
        str(berth.get("interval", INTERVAL_MONTHLY)),
        now,
        weekday=int(berth.get("weekday", 1)),
        monthday=int(berth.get("monthday", 1)),
        month=int(berth.get("month", 1)),
    )


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
    valid = [item for item in intervals if item in (INTERVAL_MONTHLY, INTERVAL_QUARTERLY, INTERVAL_YEARLY)]
    return valid or [INTERVAL_MONTHLY]


def _admin_due_today_for_interval(entry: ConfigEntry, now: datetime, interval: str) -> bool:
    options = _entry_options(entry)
    return _due_today_for_interval(
        interval,
        now,
        monthday=int(options.get(CONF_MANAGEMENT_MONTHDAY, 1)),
        month=int(options.get(CONF_MANAGEMENT_MONTH, 1)),
    )


def _admin_due_today(entry: ConfigEntry, now: datetime) -> bool:
    options = _entry_options(entry)
    return _due_today_for_interval(
        str(options.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY)),
        now,
        monthday=int(options.get(CONF_MANAGEMENT_MONTHDAY, 1)),
        month=int(options.get(CONF_MANAGEMENT_MONTH, 1)),
    )


def _management_recipient(options: dict[str, Any], specific_key: str | None = None) -> str:
    """Return the central management recipient.

    Per-report recipient fields are intentionally ignored. Management reports always
    go to the configured standard management email address.
    """
    return str(options.get(CONF_MANAGEMENT_DEFAULT_EMAIL) or options.get(CONF_MANAGEMENT_EMAIL) or "").strip()


def _quarter_from_month(options: dict[str, Any], month: int) -> int | None:
    mode = str(options.get(CONF_MANAGEMENT_QUARTERLY_MODE, QUARTER_MODE_START))
    if mode == QUARTER_MODE_END:
        mapping = {3: 1, 6: 2, 9: 3, 12: 4}
    else:
        mapping = {1: 1, 4: 2, 7: 3, 10: 4}
    return mapping.get(int(month))


def _quarter_enabled(options: dict[str, Any], quarter: int) -> bool:
    return bool(options.get({1: CONF_MANAGEMENT_QUARTERLY_Q1, 2: CONF_MANAGEMENT_QUARTERLY_Q2, 3: CONF_MANAGEMENT_QUARTERLY_Q3, 4: CONF_MANAGEMENT_QUARTERLY_Q4}[quarter], True))


def _quarterly_due_today(options: dict[str, Any], now: datetime) -> int | None:
    if not options.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False):
        return None
    quarter = _quarter_from_month(options, now.month)
    if quarter is None or not _quarter_enabled(options, quarter):
        return None
    monthday = int(options.get(CONF_MANAGEMENT_QUARTERLY_MONTHDAY, 1) or 1)
    if now.day != _effective_monthday(now.year, now.month, monthday):
        return None
    return quarter


def _management_manual_plans(options: dict[str, Any]) -> list[tuple[str, str, int | None]]:
    plans: list[tuple[str, str, int | None]] = []
    if options.get(CONF_MANAGEMENT_MONTHLY_ENABLED, False):
        plans.append((INTERVAL_MONTHLY, _management_recipient(options, CONF_MANAGEMENT_MONTHLY_EMAIL), None))
    if options.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False):
        for quarter in (1, 2, 3, 4):
            if _quarter_enabled(options, quarter):
                plans.append((INTERVAL_QUARTERLY, _management_recipient(options, CONF_MANAGEMENT_QUARTERLY_EMAIL), quarter))
    if options.get(CONF_MANAGEMENT_YEARLY_ENABLED, False):
        plans.append((INTERVAL_YEARLY, _management_recipient(options, CONF_MANAGEMENT_YEARLY_EMAIL), None))
    if not plans:
        # Backwards-compatible fallback.
        for interval in _management_intervals_from_options(options):
            plans.append((interval, _management_recipient(options, CONF_MANAGEMENT_EMAIL), None))
    return plans


def _already_sent_today(item: dict[str, Any], now: datetime, key: str = "last_sent_date") -> bool:
    return item.get(key) == now.date().isoformat()


def _notify_service(entry: ConfigEntry) -> tuple[str, str]:
    options = _entry_options(entry)
    service_name = str(options.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)).strip()
    if service_name.startswith("notify."):
        service_name = service_name.split(".", 1)[1]
    service_name = service_name.strip().lower().replace(" ", "_").replace("-", "_")
    if not service_name:
        service_name = DEFAULT_NOTIFY_SERVICE.split(".", 1)[1]
    return "notify", service_name


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    async def async_add_update_berth(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        berth = _normalize_berth(dict(call.data))
        options = _entry_options(target_entry)
        berths = [b for b in options[CONF_BERTHS] if b.get("berth_id") != berth["berth_id"]]
        existing = next((b for b in options[CONF_BERTHS] if b.get("berth_id") == berth["berth_id"]), None)
        if existing:
            for key in ("last_sent_date", "last_sent_at", CONF_LAST_BILLING_PDF_URL, CONF_LAST_BILLING_PDF_PATH, CONF_LAST_BILLING_PDF_FILENAME, CONF_LAST_BILLING_AT, CONF_LAST_BILLING_SCOPE, CONF_LAST_BILLING_START_DATE, CONF_LAST_BILLING_END_DATE):
                if key in existing:
                    berth[key] = existing[key]
        berths.append(berth)
        berths.sort(key=lambda item: _natural_sort_key(item.get("berth_id", "")))
        options[CONF_BERTHS] = berths
        hass.config_entries.async_update_entry(target_entry, options=options)
        await hass.config_entries.async_reload(target_entry.entry_id)
        _LOGGER.info("Object %s saved", berth["berth_id"])

    async def async_remove_berth(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        berth_id = str(call.data.get("object_id") or call.data.get("berth_id") or "").strip()
        options = _entry_options(target_entry)
        before = len(options[CONF_BERTHS])
        options[CONF_BERTHS] = [b for b in options[CONF_BERTHS] if b.get("berth_id") != berth_id]
        if len(options[CONF_BERTHS]) == before:
            raise HomeAssistantError(f"Objekt {berth_id} wurde nicht gefunden.")
        hass.config_entries.async_update_entry(target_entry, options=options)
        await hass.config_entries.async_reload(target_entry.entry_id)
        _LOGGER.info("Object %s removed", berth_id)

    async def async_send_now(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        berth_id = str(call.data.get("object_id") or call.data.get("berth_id") or "").strip()
        options = _entry_options(target_entry)
        berth = next((b for b in options[CONF_BERTHS] if b.get("berth_id") == berth_id), None)
        if not berth:
            raise HomeAssistantError(f"Objekt {berth_id} wurde nicht gefunden.")
        await _async_send_berth_mail(hass, target_entry, berth, manual=True)

    async def async_send_all_now(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        options = _entry_options(target_entry)
        for berth in options[CONF_BERTHS]:
            if str(berth.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) == RENTAL_TYPE_SHORT_TERM:
                continue
            if berth.get("enabled", True):
                if not str(berth.get(CONF_EMAIL, "")).strip():
                    _LOGGER.info("Skipping %s because no tenant email is configured", berth.get("berth_id"))
                    continue
                await _async_send_berth_mail(hass, target_entry, berth, manual=True)

    async def async_send_test_mail(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        await _async_send_test_mail(hass, target_entry, str(call.data[CONF_EMAIL]).strip())

    async def async_send_management_report_now(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        options = _entry_options(target_entry)
        for interval, recipient, quarter in _management_manual_plans(options):
            await _async_send_management_report(hass, target_entry, manual=True, interval=interval, recipient=recipient, quarter=quarter)

    async def async_export_current_csv(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        path = await _async_export_current_csv_and_mail(hass, target_entry)
        _LOGGER.info("Exported current readings CSV and sent it by mail: %s", path)

    async def async_send_billing_pdf(call: ServiceCall) -> None:
        target_entry = _get_single_entry(hass)
        start_date = str(call.data.get("start_date", "")).strip()
        end_date = str(call.data.get("end_date", "")).strip()
        price = call.data.get("price_kwh")
        await _async_create_billing_pdf_and_mail(hass, target_entry, start_date=start_date, end_date=end_date, price_kwh=price, scope=str(call.data.get("scope", BILLING_SCOPE_SHORT_TERM)), object_id=str(call.data.get("object_id", "")))

    hass.services.async_register(DOMAIN, SERVICE_ADD_UPDATE_BERTH, async_add_update_berth, schema=ADD_UPDATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_BERTH, async_remove_berth, schema=REMOVE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_NOW, async_send_now, schema=SEND_NOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_ALL_NOW, async_send_all_now, schema=SEND_ALL_NOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_TEST_MAIL, async_send_test_mail, schema=SEND_TEST_MAIL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_MANAGEMENT_REPORT_NOW, async_send_management_report_now, schema=SEND_MANAGEMENT_REPORT_NOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_CURRENT_CSV, async_export_current_csv, schema=EXPORT_CURRENT_CSV_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_CSV_TO_MANAGEMENT, async_export_current_csv, schema=EXPORT_CURRENT_CSV_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_BILLING_PDF_TO_MANAGEMENT, async_send_billing_pdf, schema=BILLING_PDF_SCHEMA)

    @callback
    def _minute_tick(now: datetime) -> None:
        hass.async_create_task(_async_check_due(hass, entry, now))

    unsub: Callable[[], None] = async_track_time_change(hass, _minute_tick, second=0)
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB] = unsub

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, {})
    if unsub := entry_data.get(DATA_UNSUB):
        unsub()
    if not hass.data.get(DOMAIN):
        for service in (
            SERVICE_ADD_UPDATE_BERTH,
            SERVICE_REMOVE_BERTH,
            SERVICE_SEND_NOW,
            SERVICE_SEND_ALL_NOW,
            SERVICE_SEND_TEST_MAIL,
            SERVICE_SEND_MANAGEMENT_REPORT_NOW,
            SERVICE_EXPORT_CURRENT_CSV,
    SERVICE_SEND_CSV_TO_MANAGEMENT,
    SERVICE_SEND_BILLING_PDF_TO_MANAGEMENT,
        ):
            hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)
    return True


async def _async_check_due(hass: HomeAssistant, entry: ConfigEntry, now: datetime | None = None) -> None:
    now = now or dt_util.now()
    current_time = now.strftime("%H:%M")
    options = _entry_options(entry)

    for berth in options[CONF_BERTHS]:
        if str(berth.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) == RENTAL_TYPE_SHORT_TERM:
            continue
        if not berth.get("enabled", True):
            continue
        if berth.get("send_time") != current_time:
            continue
        if not _due_today(berth, now):
            continue
        if _already_sent_today(berth, now):
            continue
        try:
            await _async_send_berth_mail(hass, entry, berth, manual=False)
        except HomeAssistantError as err:
            _LOGGER.error("Could not send meter mail for object %s: %s", berth.get("berth_id"), err)

    # Monthly management report
    monthly_recipient = _management_recipient(options, CONF_MANAGEMENT_MONTHLY_EMAIL)
    monthly_time = _clean_time(options.get(CONF_MANAGEMENT_MONTHLY_SEND_TIME, "08:00"))
    if options.get(CONF_MANAGEMENT_MONTHLY_ENABLED, False) and monthly_recipient and current_time == monthly_time:
        monthday = int(options.get(CONF_MANAGEMENT_MONTHLY_MONTHDAY, 1) or 1)
        last_key = "last_management_report_date_monthly"
        if now.day == _effective_monthday(now.year, now.month, monthday) and not _already_sent_today(options, now, key=last_key):
            try:
                await _async_send_management_report(hass, entry, manual=False, interval=INTERVAL_MONTHLY, recipient=monthly_recipient)
            except HomeAssistantError as err:
                _LOGGER.error("Could not send monthly management report: %s", err)

    # Quarterly management report
    quarterly_recipient = _management_recipient(options, CONF_MANAGEMENT_QUARTERLY_EMAIL)
    quarterly_time = _clean_time(options.get(CONF_MANAGEMENT_QUARTERLY_SEND_TIME, "08:00"))
    if options.get(CONF_MANAGEMENT_QUARTERLY_ENABLED, False) and quarterly_recipient and current_time == quarterly_time:
        quarter = _quarterly_due_today(options, now)
        if quarter is not None:
            last_key = f"last_management_report_date_quarterly_q{quarter}"
            if not _already_sent_today(options, now, key=last_key):
                try:
                    await _async_send_management_report(hass, entry, manual=False, interval=INTERVAL_QUARTERLY, recipient=quarterly_recipient, quarter=quarter)
                except HomeAssistantError as err:
                    _LOGGER.error("Could not send quarterly management report: %s", err)

    # Yearly management report
    yearly_recipient = _management_recipient(options, CONF_MANAGEMENT_YEARLY_EMAIL)
    yearly_time = _clean_time(options.get(CONF_MANAGEMENT_YEARLY_SEND_TIME, "08:00"))
    if options.get(CONF_MANAGEMENT_YEARLY_ENABLED, False) and yearly_recipient and current_time == yearly_time:
        month = int(options.get(CONF_MANAGEMENT_YEARLY_MONTH, 1) or 1)
        monthday = int(options.get(CONF_MANAGEMENT_YEARLY_MONTHDAY, 1) or 1)
        last_key = "last_management_report_date_yearly"
        if now.month == month and now.day == _effective_monthday(now.year, month, monthday) and not _already_sent_today(options, now, key=last_key):
            try:
                await _async_send_management_report(hass, entry, manual=False, interval=INTERVAL_YEARLY, recipient=yearly_recipient)
            except HomeAssistantError as err:
                _LOGGER.error("Could not send yearly management report: %s", err)


async def _async_export_current_csv(hass: HomeAssistant, entry: ConfigEntry) -> tuple[str, str]:
    """Export all current object meter readings to /config/www/liegenschafts_mailer."""
    options = _entry_options(entry)
    now = dt_util.now()
    export_dir = hass.config.path("www", "liegenschafts_mailer")

    def _ensure_export_dir() -> None:
        os.makedirs(export_dir, exist_ok=True)

    await hass.async_add_executor_job(_ensure_export_dir)
    filename = f"zaehlerstaende_aktuell_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    latest_filename = "zaehlerstaende_aktuell.csv"
    path = os.path.join(export_dir, filename)
    latest_path = os.path.join(export_dir, latest_filename)

    rows: list[dict[str, Any]] = []
    for berth in options.get(CONF_BERTHS, []):
        sensor_entity = str(berth.get("meter_sensor", ""))
        state = hass.states.get(sensor_entity)
        if state is None:
            value = ""
            unit = ""
            status = "Sensor fehlt"
        else:
            value = str(state.state)
            unit = str(state.attributes.get("unit_of_measurement", "") or "")
            status = "ok" if state.state not in ("unknown", "unavailable", None) else str(state.state)
        rows.append({
            "Objekt": str(berth.get(CONF_NAME) or berth.get("berth_id") or ""),
            "Objekt-ID": str(berth.get("berth_id") or ""),
            "Mieter": str(berth.get("tenant_name") or ""),
            "Mieter-E-Mail": str(berth.get(CONF_EMAIL) or ""),
            "Zähler-Sensor": sensor_entity,
            "Zählerstand": value,
            "Einheit": unit,
            "Exportzeitpunkt": now.strftime("%Y-%m-%d %H:%M:%S"),
        })

    fieldnames = [
        "Objekt", "Objekt-ID", "Mieter", "Mieter-E-Mail", "Zähler-Sensor",
        "Zählerstand", "Einheit", "Exportzeitpunkt",
    ]

    def _write_csv(target: str) -> None:
        with open(target, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    await hass.async_add_executor_job(_write_csv, path)
    await hass.async_add_executor_job(_write_csv, latest_path)
    return path, f"/local/liegenschafts_mailer/{filename}"




async def _async_export_current_csv_and_mail(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Export all current readings and send the CSV to the standard management email."""
    options = _entry_options(entry)
    recipient = _management_recipient(options)
    if not EMAIL_RE.match(recipient):
        raise HomeAssistantError("Keine gueltige Standard-Verwaltungsmail-Adresse hinterlegt.")

    path, url = await _async_export_current_csv(hass, entry)

    def _read_csv() -> str:
        with open(path, "r", encoding="utf-8-sig") as file:
            return file.read()

    csv_content = await hass.async_add_executor_job(_read_csv)
    now = dt_util.now()
    filename = os.path.basename(path)
    _, _, plural = _property_defaults(options)

    if _is_german_lang(hass):
        title = f"CSV-Export aktuelle Zählerstände {plural} - {now.strftime('%d.%m.%Y')}"
        message = (
            "CSV-Export der aktuellen Zählerstände\n"
            f"Datum: {now.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"Anzahl {plural}: {len(options.get(CONF_BERTHS, []))}\n"
            f"Datei: {filename}\n\n"
            "Die CSV-Datei befindet sich im Anhang dieser E-Mail."
        )
        html_message = _html_page(
            title,
            ""
            f"<p style='font-size:14px;color:#475569;margin:0 0 14px 0;'>Erstellt am {html.escape(now.strftime('%d.%m.%Y %H:%M:%S'))}</p>"
            f"<p style='font-size:14px;margin:0 0 14px 0;'>Die CSV-Datei <strong>{html.escape(filename)}</strong> wurde erzeugt und an die Verwaltung gesendet.</p>"
            f"<p style='font-size:13px;color:#64748b;margin:0 0 16px 0;'>Die CSV-Datei befindet sich im Anhang dieser E-Mail.</p>"
        )
    else:
        title = f"CSV export current meter readings {plural} - {now.strftime('%Y-%m-%d')}"
        message = (
            "CSV export of current meter readings\n"
            f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Number of {plural}: {len(options.get(CONF_BERTHS, []))}\n"
            f"File: {filename}\n\n"
            "The CSV file is attached to this email."
        )
        html_message = _html_page(
            title,
            ""
            f"<p style='font-size:14px;color:#475569;margin:0 0 14px 0;'>Created {html.escape(now.strftime('%Y-%m-%d %H:%M:%S'))}</p>"
            f"<p style='font-size:14px;margin:0 0 14px 0;'>The CSV file <strong>{html.escape(filename)}</strong> was created and sent to management.</p>"
            f"<p style='font-size:13px;color:#64748b;margin:0 0 16px 0;'>The CSV file is attached to this email.</p>"
        )

    # Home Assistant SMTP notify supports file attachments through the
    # data.images key. The name is historical; SMTP attaches the files by
    # their basename. Do not use custom keys like attachments/attachment here:
    # they are ignored by the SMTP notify platform.
    await _async_send_raw_mail(
        hass,
        entry,
        title=title,
        message=message,
        recipient=recipient,
        data={
            "images": [path],
        },
        # Keep the CSV export mail plain text so the file is attached as a
        # separate attachment instead of being treated as inline HTML content.
        html_message=None,
    )
    return path




def _parse_date(value: str, *, end: bool = False) -> datetime:
    """Parse YYYY-MM-DD to local datetime boundary."""
    text = str(value or "").strip()
    try:
        date = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as err:
        raise HomeAssistantError("Datum muss im Format YYYY-MM-DD angegeben werden.") from err
    if end:
        return dt_util.as_local(datetime.combine(date, datetime.max.time()).replace(microsecond=0))
    return dt_util.as_local(datetime.combine(date, datetime.min.time()))


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return None
        text = str(value).replace(",", ".").strip()
        result = float(text)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


async def _async_get_daily_stat_value(
    hass: HomeAssistant,
    entity_id: str,
    target: datetime,
    *,
    prefer_before: bool,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> tuple[float | None, str]:
    """Return a robust meter value for a billing boundary.

    For billing we need the value at the beginning/end of a period, not the
    current state. The lookup order is therefore:
      1. daily/long-term statistics in the complete billing period
      2. recorder history in the complete billing period
      3. current state only as explicit last resort
    """
    entity_id = str(entity_id or "").strip()
    if not entity_id:
        return None, "kein Sensor"

    period_start = period_start or target
    period_end = period_end or target
    query_start = min(period_start, target) - timedelta(days=2)
    query_end = max(period_end, target) + timedelta(days=2)

    def _choose_candidate(candidates: list[tuple[datetime, float]], source_label: str) -> tuple[float | None, str] | None:
        if not candidates:
            return None
        normalized = sorted((dt_util.as_local(dt), value) for dt, value in candidates if value is not None)
        if not normalized:
            return None
        if prefer_before:
            before = [item for item in normalized if item[0] <= target]
            chosen = max(before, key=lambda item: item[0]) if before else min(normalized, key=lambda item: item[0])
        else:
            after = [item for item in normalized if item[0] >= target]
            chosen = min(after, key=lambda item: item[0]) if after else max(normalized, key=lambda item: item[0])
        return chosen[1], f"{source_label} {chosen[0].strftime('%d.%m.%Y %H:%M')}"

    # 1) Prefer Home Assistant statistics over raw recorder history.
    try:
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import statistics_during_period

        def _stats_job():
            return statistics_during_period(
                hass,
                query_start,
                query_end,
                [entity_id],
                "day",
                None,
                {"state", "sum", "mean"},
                True,
            )

        stats = await get_instance(hass).async_add_executor_job(_stats_job)
        rows = list((stats or {}).get(entity_id, []) or [])
        candidates: list[tuple[datetime, float]] = []
        for row in rows:
            row_start = row.get("start") or row.get("start_time")
            if row_start is None:
                continue
            if isinstance(row_start, str):
                try:
                    row_start = dt_util.parse_datetime(row_start)
                except Exception:
                    continue
            row_dt = dt_util.as_local(row_start)
            value = _to_float(row.get("state"))
            if value is None:
                value = _to_float(row.get("sum"))
            if value is None:
                value = _to_float(row.get("mean"))
            if value is not None:
                candidates.append((row_dt, value))
        chosen = _choose_candidate(candidates, "Langzeitstatistik")
        if chosen is not None:
            return chosen
    except Exception as err:
        _LOGGER.debug("Could not read daily statistics for %s: %s", entity_id, err)

    # 2) Recorder history fallback. This is essential when the entity has no
    # long-term statistics yet but the normal HA history graph already contains
    # the required values.
    try:
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder import history as recorder_history

        def _extract_history_items(raw: Any) -> list[Any]:
            if isinstance(raw, dict):
                return list(raw.get(entity_id, []) or [])
            if isinstance(raw, list):
                return raw
            return []

        def _history_job():
            try:
                return recorder_history.get_significant_states(
                    hass,
                    query_start,
                    query_end,
                    [entity_id],
                    significant_changes_only=False,
                    minimal_response=False,
                    no_attributes=True,
                )
            except TypeError:
                try:
                    return recorder_history.get_significant_states(
                        hass,
                        query_start,
                        query_end,
                        [entity_id],
                        None,
                        True,
                        False,
                        False,
                    )
                except TypeError:
                    try:
                        return recorder_history.state_changes_during_period(
                            hass,
                            query_start,
                            query_end,
                            entity_id,
                            include_start_time_state=True,
                        )
                    except TypeError:
                        return recorder_history.get_significant_states(hass, query_start, query_end, [entity_id])

        raw_history = await get_instance(hass).async_add_executor_job(_history_job)
        candidates: list[tuple[datetime, float]] = []
        for item in _extract_history_items(raw_history):
            if isinstance(item, dict):
                value = _to_float(item.get("state"))
                stamp = item.get("last_updated") or item.get("last_changed") or item.get("last_reported")
                if isinstance(stamp, str):
                    stamp = dt_util.parse_datetime(stamp)
            else:
                value = _to_float(getattr(item, "state", None))
                stamp = getattr(item, "last_updated", None) or getattr(item, "last_changed", None)
            if value is None or stamp is None:
                continue
            candidates.append((dt_util.as_local(stamp), value))
        chosen = _choose_candidate(candidates, "Recorder-Historie")
        if chosen is not None:
            return chosen
    except Exception as err:
        _LOGGER.debug("Could not read recorder history for %s: %s", entity_id, err)

    # 3) Explicit last resort only. This keeps the PDF creation working, but the
    # source string makes the fallback visible in logs if needed.
    state = hass.states.get(entity_id)
    value = _to_float(state.state if state else None)
    if value is not None:
        return value, "Fallback aktueller Zustand"
    return None, "kein Wert gefunden"


def _format_de_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return ""
    text = f"{value:.{decimals}f}"
    return text.replace(".", ",")


def _pdf_escape_text(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_simple_pdf(path: str, *, title: str, lines: list[str]) -> None:
    """Write a minimal PDF without external dependencies."""
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= 42:
            pages.append(current)
            current = []
    if current or not pages:
        pages.append(current)

    objects: list[bytes] = []
    font_obj = 3
    pages_obj = 2
    catalog_obj = 1
    kids: list[int] = []

    # placeholders for catalog/pages/font are inserted first
    objects.append(b"")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    for page_lines in pages:
        content_lines = ["BT", "/F1 16 Tf", "50 800 Td", f"({_pdf_escape_text(title)}) Tj", "/F1 9 Tf", "0 -24 Td"]
        for line in page_lines:
            content_lines.append(f"({_pdf_escape_text(line[:125])}) Tj")
            content_lines.append("0 -14 Td")
        content_lines.append("ET")
        content = "\n".join(content_lines).encode("cp1252", "replace")
        content_obj_num = len(objects) + 1
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
        page_obj_num = len(objects) + 1
        kids.append(page_obj_num)
        page = f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj_num} 0 R >>".encode()
        objects.append(page)

    objects[0] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
    kids_refs = " ".join(f"{kid} 0 R" for kid in kids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_refs}] /Count {len(kids)} >>".encode()

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects)+1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    with open(path, "wb") as file:
        file.write(out.getvalue())


def _short_text(value: Any, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)] + "…"


def _pdf_content_line(text: str) -> bytes:
    return f"({_pdf_escape_text(text)}) Tj".encode("cp1252", "replace")


def _billing_pdf_cell(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    return _pdf_escape_text(text)


def _write_billing_pdf(path: str, *, title: str, meta_lines: list[str], rows: list[dict[str, Any]], totals: list[str], sources: list[str] | None = None) -> None:
    """Write a clean customer-facing billing PDF.

    The document intentionally hides all internal Home Assistant entity IDs and
    shows only accounting-relevant data.
    """
    page_w, page_h = 595, 842
    margin_x = 38
    y_start = 790
    row_h = 22
    header_h = 24
    col_x = [38, 125, 215, 275, 335, 407, 475]
    col_w = [87, 90, 60, 60, 72, 68, 80]
    headers = ["Objekt", "Mieter", "Beginn", "Ende", "Verbrauch", "Preis/kWh", "Betrag"]

    def money(value: Any) -> str:
        return _format_de_number(value, 2) + " EUR"

    table_rows: list[list[str]] = []
    for row in rows:
        table_rows.append([
            _short_text(row.get("object", ""), 18),
            _short_text(row.get("tenant", ""), 18),
            _format_de_number(row.get("start"), 2),
            _format_de_number(row.get("end"), 2),
            _format_de_number(row.get("consumption"), 2),
            _format_de_number(row.get("price"), 4),
            money(row.get("amount")),
        ])

    pages: list[list[list[str]]] = []
    current: list[list[str]] = []
    rows_per_page = 22
    for row in table_rows:
        current.append(row)
        if len(current) >= rows_per_page:
            pages.append(current)
            current = []
    if current or not pages:
        pages.append(current)

    objects: list[bytes] = []
    font_obj = 3
    pages_obj = 2
    catalog_obj = 1
    kids: list[int] = []
    objects.append(b"")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    for page_idx, page_rows in enumerate(pages, start=1):
        content = bytearray()
        def cmd(text: str) -> None:
            content.extend(text.encode("ascii"))
            content.extend(b"\n")
        def text_at(x: int, y: int, size: int, value: Any) -> None:
            cmd("BT")
            cmd(f"/F1 {size} Tf")
            cmd(f"{x} {y} Td")
            content.extend(f"({_billing_pdf_cell(value)}) Tj".encode("cp1252", "replace"))
            content.extend(b"\nET\n")
        def rect(x: int, y: int, w: int, h: int, gray: float | None = None) -> None:
            if gray is not None:
                cmd(f"{gray:.2f} g")
            cmd(f"{x} {y} {w} {h} re f")
            cmd("0 g")
        def stroke_rect(x: int, y: int, w: int, h: int) -> None:
            cmd("0.75 w")
            cmd("0.70 G")
            cmd(f"{x} {y} {w} {h} re S")
            cmd("0 G")

        # Header block
        rect(0, page_h - 72, page_w, 72, 0.93)
        text_at(margin_x, 792, 18, title)
        y = 760
        for meta in meta_lines[:4]:
            text_at(margin_x, y, 10, meta)
            y -= 14

        # Table header
        table_y = 650
        rect(margin_x, table_y, 520, header_h, 0.88)
        stroke_rect(margin_x, table_y, 520, header_h)
        for i, head in enumerate(headers):
            text_at(col_x[i] + 4, table_y + 8, 9, head)

        y = table_y - row_h
        for idx, row in enumerate(page_rows):
            if idx % 2 == 1:
                rect(margin_x, y, 520, row_h, 0.97)
            stroke_rect(margin_x, y, 520, row_h)
            for i, value in enumerate(row):
                text_at(col_x[i] + 4, y + 7, 8, value)
            y -= row_h

        # Totals block on last page
        if page_idx == len(pages):
            y -= 12
            rect(margin_x, y - 46, 520, 52, 0.94)
            stroke_rect(margin_x, y - 46, 520, 52)
            text_at(margin_x + 10, y - 6, 11, "Zusammenfassung")
            ty = y - 23
            for total in totals:
                text_at(margin_x + 10, ty, 10, total)
                ty -= 14
            hint_y = 62
            text_at(margin_x, hint_y, 8, "Hinweis: Die Abrechnung nutzt bevorzugt Tages-/Langzeitwerte der kWh-Zählerstände.")
            text_at(margin_x, hint_y - 12, 8, "Interne Sensor-IDs werden in dieser Abrechnung bewusst nicht angezeigt.")

        text_at(510, 30, 8, f"Seite {page_idx} von {len(pages)}")

        content_obj_num = len(objects) + 1
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + bytes(content) + b"\nendstream")
        page_obj_num = len(objects) + 1
        kids.append(page_obj_num)
        page = f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {page_w} {page_h}] /Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj_num} 0 R >>".encode()
        objects.append(page)

    objects[0] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
    kids_refs = " ".join(f"{kid} 0 R" for kid in kids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_refs}] /Count {len(kids)} >>".encode()

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects)+1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    with open(path, "wb") as file:
        file.write(out.getvalue())


async def _async_create_billing_pdf(hass: HomeAssistant, entry: ConfigEntry, *, start_date: str, end_date: str, price_kwh: Any = None, scope: str = BILLING_SCOPE_SHORT_TERM, object_id: str = "") -> tuple[str, str]:
    options = _entry_options(entry)
    start_dt = _parse_date(start_date, end=False)
    end_dt = _parse_date(end_date, end=True)
    if end_dt <= start_dt:
        raise HomeAssistantError("Enddatum muss nach dem Beginndatum liegen.")
    default_price = _to_float(options.get(CONF_DEFAULT_KWH_PRICE, 0.0)) or 0.0
    price = _to_float(price_kwh) if price_kwh not in (None, "") else default_price
    if price is None:
        price = 0.0

    export_dir = hass.config.path("www", "liegenschafts_mailer", "abrechnungen")
    await hass.async_add_executor_job(lambda: os.makedirs(export_dir, exist_ok=True))
    now = dt_util.now()
    filename = f"abrechnung_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(export_dir, filename)

    _, single, plural = _property_defaults(options)
    all_berths = list(options.get(CONF_BERTHS, []))
    if scope == BILLING_SCOPE_SHORT_TERM:
        selected_berths = [
            b for b in all_berths
            if str(b.get("berth_id", "")) == str(object_id or "")
            and str(b.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) == RENTAL_TYPE_SHORT_TERM
        ]
        if not selected_berths:
            raise HomeAssistantError("Ausgewaehltes Kurzzeitobjekt wurde nicht gefunden.")
    elif scope == BILLING_SCOPE_LONG_TERM:
        selected_berths = [
            b for b in all_berths
            if str(b.get("berth_id", "")) == str(object_id or "")
            and str(b.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) != RENTAL_TYPE_SHORT_TERM
        ]
        if not selected_berths:
            raise HomeAssistantError("Ausgewaehltes Langzeitobjekt wurde nicht gefunden.")
    elif scope == BILLING_SCOPE_OBJECT:
        selected_berths = [b for b in all_berths if str(b.get("berth_id", "")) == str(object_id or "")]
        if not selected_berths:
            raise HomeAssistantError("Ausgewaehltes Objekt wurde nicht gefunden.")
    elif scope == BILLING_SCOPE_ALL:
        selected_berths = all_berths
    else:
        selected_berths = []

    rows: list[dict[str, Any]] = []
    total_kwh = 0.0
    total_amount = 0.0
    for berth in selected_berths:
        sensor_entity = str(berth.get("meter_sensor", ""))
        start_value, start_source = await _async_get_daily_stat_value(
            hass,
            sensor_entity,
            start_dt,
            prefer_before=False,
            period_start=start_dt,
            period_end=end_dt,
        )
        end_value, end_source = await _async_get_daily_stat_value(
            hass,
            sensor_entity,
            end_dt,
            prefer_before=True,
            period_start=start_dt,
            period_end=end_dt,
        )
        consumption = None
        amount = None
        if start_value is not None and end_value is not None:
            consumption = max(0.0, end_value - start_value)
            amount = consumption * price
            total_kwh += consumption
            total_amount += amount
        rows.append({
            "object": str(berth.get(CONF_NAME) or berth.get("berth_id") or ""),
            "tenant": str(berth.get("tenant_name") or ""),
            "sensor": sensor_entity,
            "start": start_value,
            "end": end_value,
            "consumption": consumption,
            "amount": amount,
            "price": price,
            "start_source": start_source,
            "end_source": end_source,
        })

    scope_label = "Kurzzeitmiete" if scope == BILLING_SCOPE_SHORT_TERM else ("Langzeitmiete" if scope == BILLING_SCOPE_LONG_TERM else ("Alle Objekte" if scope == BILLING_SCOPE_ALL else "Einzelobjekt"))
    title = f"Abrechnungsübersicht {plural} - {scope_label}"
    meta_lines = [
        f"Zeitraum: {start_dt.strftime('%d.%m.%Y')} bis {end_dt.strftime('%d.%m.%Y')}",
        f"Preis pro kWh: {_format_de_number(price, 4)} EUR",
        f"Erstellt am: {now.strftime('%d.%m.%Y %H:%M:%S')}",
        f"Abrechnungsart: {scope_label}",
        f"Anzahl {plural}: {len(rows)}",
    ]
    totals = [
        f"Summe Verbrauch: {_format_de_number(total_kwh)} kWh",
        f"Summe Betrag: {_format_de_number(total_amount)} EUR",
    ]
    await hass.async_add_executor_job(lambda: _write_billing_pdf(path, title=title, meta_lines=meta_lines, rows=rows, totals=totals, sources=None))
    return path, f"/local/liegenschafts_mailer/abrechnungen/{filename}"


def _absolute_local_url(hass: HomeAssistant, entry: ConfigEntry, relative_url: str) -> str:
    """Return a full Home Assistant URL for a /local/... path."""
    rel = str(relative_url or "").strip()
    if rel.startswith("http://") or rel.startswith("https://"):
        return rel
    if not rel.startswith("/"):
        rel = "/" + rel
    options = _entry_options(entry)
    configured = str(options.get(CONF_HA_BASE_URL, "") or "").strip().rstrip("/")
    if configured:
        return configured + rel
    base_url = ""
    try:
        from homeassistant.helpers.network import get_url

        base_url = str(get_url(hass, allow_internal=True, allow_external=True) or "").rstrip("/")
    except Exception:
        pass
    if not base_url:
        for attr in ("external_url", "internal_url"):
            try:
                value = getattr(hass.config, attr, None)
                if value:
                    base_url = str(value).rstrip("/")
                    break
            except Exception:
                pass
    return (base_url + rel) if base_url else rel


def _remember_last_billing_pdf(hass: HomeAssistant, entry: ConfigEntry, *, object_id: str, full_url: str, path: str, scope: str, start_date: str, end_date: str) -> None:
    """Store the last generated billing PDF on the matching object for dashboard links."""
    obj_id = str(object_id or "").strip()
    if not obj_id:
        return
    options = _entry_options(entry)
    changed = False
    updated_berths: list[dict[str, Any]] = []
    for berth in options.get(CONF_BERTHS, []):
        item = dict(berth)
        if str(item.get("berth_id", "")) == obj_id:
            item[CONF_LAST_BILLING_PDF_URL] = str(full_url or "")
            item[CONF_LAST_BILLING_PDF_PATH] = str(path or "")
            item[CONF_LAST_BILLING_PDF_FILENAME] = os.path.basename(path) if path else ""
            item[CONF_LAST_BILLING_AT] = dt_util.now().isoformat()
            item[CONF_LAST_BILLING_SCOPE] = str(scope or "")
            item[CONF_LAST_BILLING_START_DATE] = str(start_date or "")
            item[CONF_LAST_BILLING_END_DATE] = str(end_date or "")
            changed = True
        updated_berths.append(item)
    if changed:
        options[CONF_BERTHS] = updated_berths
        hass.config_entries.async_update_entry(entry, options=options)

async def _async_create_billing_pdf_and_mail(hass: HomeAssistant, entry: ConfigEntry, *, start_date: str, end_date: str, price_kwh: Any = None, scope: str = BILLING_SCOPE_SHORT_TERM, object_id: str = "") -> str:
    options = _entry_options(entry)
    recipient = _management_recipient(options)
    if not EMAIL_RE.match(recipient):
        raise HomeAssistantError("Keine gueltige Standard-Verwaltungsmail-Adresse hinterlegt.")
    path, url = await _async_create_billing_pdf(hass, entry, start_date=start_date, end_date=end_date, price_kwh=price_kwh, scope=scope, object_id=object_id)
    full_url = _absolute_local_url(hass, entry, url)
    _remember_last_billing_pdf(hass, entry, object_id=object_id, full_url=full_url, path=path, scope=scope, start_date=start_date, end_date=end_date)
    filename = os.path.basename(path)
    start_dt = _parse_date(start_date, end=False)
    end_dt = _parse_date(end_date, end=True)
    start_display = start_dt.strftime('%d.%m.%Y')
    end_display = end_dt.strftime('%d.%m.%Y')
    title = f"PDF-Abrechnung Zählerstände - {start_display} bis {end_display}"
    message = (
        "PDF-Abrechnung der Zählerstände\n"
        f"Zeitraum: {start_display} bis {end_display}\n"
        f"Datei: {filename}\n"
        f"Link: {full_url}\n\n"
        "Die PDF-Datei befindet sich im Anhang dieser E-Mail."
    )
    await _async_send_raw_mail(
        hass,
        entry,
        title=title,
        message=message,
        recipient=recipient,
        data={"images": [path]},
        html_message=None,
    )
    return full_url


async def _async_send_raw_mail(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    title: str,
    message: str,
    recipient: str,
    data: dict[str, Any] | None = None,
    html_message: str | None = None,
) -> None:
    email = str(recipient).strip()
    if not EMAIL_RE.match(email):
        raise HomeAssistantError(f"Ungueltige E-Mail-Adresse: {email}")
    domain, service = _notify_service(entry)
    if not hass.services.has_service(domain, service):
        raise HomeAssistantError(
            f"Notify-Dienst notify.{service} wurde nicht gefunden. Bitte exakt den Dienstnamen aus Entwicklerwerkzeuge > Aktionen verwenden."
        )
    mail_data = dict(data or {})
    if html_message:
        # For SMTP notify, HTML is passed through the generic notify data block.
        # If a notify provider rejects this extended payload, the code below falls
        # back to a plain notify call so mail delivery still works.
        mail_data["html"] = html_message

    payload: dict[str, Any] = {"title": title, "message": message, "target": [email]}
    if mail_data:
        payload["data"] = mail_data

    _LOGGER.info("Calling notify.%s with target=%s", service, email)
    try:
        await hass.services.async_call(domain, service, payload, blocking=True)
        return
    except Exception as err:
        if not mail_data:
            _LOGGER.error("notify.%s failed for %s: %s", service, email, err)
            raise
        _LOGGER.warning(
            "notify.%s rejected the extended mail payload for %s (%s). Retrying without HTML/data.",
            service,
            email,
            err,
        )

    fallback_payload: dict[str, Any] = {"title": title, "message": message, "target": [email]}
    await hass.services.async_call(domain, service, fallback_payload, blocking=True)


async def _async_send_test_mail(hass: HomeAssistant, entry: ConfigEntry, recipient: str) -> None:
    now = dt_util.now()
    await _async_send_raw_mail(
        hass,
        entry,
        title="Liegenschafts Mailer Testmail",
        message=(
            "Dies ist eine Testmail vom Liegenschafts Mailer.\n\n"
            f"Notify-Service: {_notify_service(entry)[0]}.{_notify_service(entry)[1]}\n"
            f"Empfänger: {recipient}\n"
            f"Zeitpunkt: {now.strftime('%d.%m.%Y %H:%M:%S')}"
        ),
        recipient=recipient,
    )


def _is_german_lang(hass: HomeAssistant) -> bool:
    return str(getattr(hass.config, "language", "de") or "de").lower().startswith("de")


def _tenant_greeting(hass: HomeAssistant, salutation: str, tenant_name: str) -> str:
    salutation = str(salutation or DEFAULT_TENANT_SALUTATION)
    tenant_name = str(tenant_name or "").strip()
    if _is_german_lang(hass):
        title = "Frau" if salutation == TENANT_SALUTATION_MS else "Herr"
        return f"Sehr geehrte {title} {tenant_name}" if salutation == TENANT_SALUTATION_MS else f"Sehr geehrter {title} {tenant_name}"
    title = "Ms" if salutation == TENANT_SALUTATION_MS else "Mr"
    return f"Dear {title} {tenant_name}"




def _html_page(title: str, body: str) -> str:
    esc_title = html.escape(str(title))
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <div style="max-width:920px;margin:0 auto;padding:24px;">
      <div style="background:#ffffff;border:1px solid #d8dee6;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(15,23,42,0.08);">
        <div style="background:#0b74c7;color:#ffffff;padding:18px 22px;">
          <h1 style="margin:0;font-size:22px;font-weight:700;">{esc_title}</h1>
        </div>
        <div style="padding:22px;">
          {body}
        </div>
        <div style="background:#f8fafc;border-top:1px solid #e5e7eb;padding:12px 22px;color:#64748b;font-size:12px;">
          Automatisch erstellt durch Home Assistant · Liegenschafts Mailer
        </div>
      </div>
    </div>
  </body>
</html>"""


def _object_mail_html(hass: HomeAssistant, *, salutation: str, tenant_name: str, object_name: str, value: str, unit: str) -> str:
    greeting = html.escape(_tenant_greeting(hass, salutation, tenant_name))
    obj = html.escape(str(object_name))
    val = html.escape(str(value))
    unit_esc = html.escape(str(unit))
    if _is_german_lang(hass):
        body = f"""
          <p style="font-size:16px;line-height:1.5;margin:0 0 18px 0;">{greeting},</p>
          <p style="font-size:15px;line-height:1.5;margin:0 0 18px 0;">hier ist Ihr aktueller Zählerstand zum <strong>{obj}</strong>.</p>
          <div style="background:#f1f7fd;border-left:5px solid #0b74c7;border-radius:8px;padding:18px 20px;margin:20px 0;">
            <div style="font-size:13px;color:#475569;margin-bottom:6px;">Aktueller Zählerstand</div>
            <div style="font-size:28px;font-weight:700;color:#0f172a;">{val} <span style="font-size:18px;font-weight:600;">{unit_esc}</span></div>
          </div>
        """
    else:
        body = f"""
          <p style="font-size:16px;line-height:1.5;margin:0 0 18px 0;">{greeting},</p>
          <p style="font-size:15px;line-height:1.5;margin:0 0 18px 0;">here is your current meter reading for <strong>{obj}</strong>.</p>
          <div style="background:#f1f7fd;border-left:5px solid #0b74c7;border-radius:8px;padding:18px 20px;margin:20px 0;">
            <div style="font-size:13px;color:#475569;margin-bottom:6px;">Current meter reading</div>
            <div style="font-size:28px;font-weight:700;color:#0f172a;">{val} <span style="font-size:18px;font-weight:600;">{unit_esc}</span></div>
          </div>
        """
    return _html_page(obj, body)


def _format_admin_interval_en(interval: str) -> str:
    if interval == INTERVAL_MONTHLY:
        return "Monthly report"
    if interval == INTERVAL_QUARTERLY:
        return "Quarterly report"
    if interval == INTERVAL_YEARLY:
        return "Yearly report"
    return "Meter reading report"


def _management_report_html(
    hass: HomeAssistant,
    *,
    title: str,
    plural: str,
    rows: list[dict[str, str]],
    now: datetime,
    interval: str,
) -> str:
    esc_title = html.escape(title)
    esc_plural = html.escape(str(plural))
    if _is_german_lang(hass):
        subline = f"{esc_title} · erstellt am {html.escape(now.strftime('%d.%m.%Y %H:%M:%S'))}"
        count_label = f"Anzahl {esc_plural}"
        headers = ["Objekt", "Mieter", "Zählerstand", "E-Mail"]
    else:
        subline = f"{esc_title} · created {html.escape(now.strftime('%Y-%m-%d %H:%M:%S'))}"
        count_label = f"Number of {esc_plural}"
        headers = ["Object", "Tenant", "Meter reading", "E-Mail"]

    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;'>{html.escape(row['object'])}</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;'>{html.escape(row['tenant'])}</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:700;white-space:nowrap;'>{html.escape(row['value'])}</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;'><a href='mailto:{html.escape(row['email'])}' style='color:#0b74c7;text-decoration:none;'>{html.escape(row['email'])}</a></td>"
            "</tr>"
        )
    if not body_rows:
        colspan = len(headers)
        body_rows.append(f"<tr><td colspan='{colspan}' style='padding:16px 12px;color:#64748b;'>Keine Objekte vorhanden.</td></tr>")

    header_html = "".join(
        f"<th style='padding:11px 12px;background:#eaf3fb;border-bottom:1px solid #cbd5e1;text-align:{'right' if h in ('Zählerstand','Meter reading') else 'left'};font-size:13px;color:#0f172a;'>{html.escape(h)}</th>"
        for h in headers
    )
    body = f"""
      <p style="font-size:14px;color:#475569;margin:0 0 14px 0;">{subline}</p>
      <div style="display:inline-block;background:#eef6ff;color:#0b4e84;border:1px solid #bfdbfe;border-radius:999px;padding:6px 12px;font-size:13px;font-weight:700;margin:0 0 18px 0;">
        {count_label}: {len(rows)}
      </div>
      <table role="table" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;border:1px solid #cbd5e1;border-radius:10px;overflow:hidden;font-size:14px;">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
      <p style="font-size:12px;color:#64748b;margin:16px 0 0 0;">Betreff: {esc_title}</p>
    """
    return _html_page(title, body)
def _object_mail_text(hass: HomeAssistant, *, salutation: str, tenant_name: str, object_name: str, value: str, unit: str) -> tuple[str, str]:
    if _is_german_lang(hass):
        title = f"Zählerstand {object_name}"
        message = (
            f"{_tenant_greeting(hass, salutation, tenant_name)},\n\n"
            f"hier ist Ihr Zählerstand zum {object_name}.\n\n"
            f"Dieser beträgt aktuell: {value} {unit}"
        )
        return title, message
    title = f"Meter reading {object_name}"
    message = (
        f"{_tenant_greeting(hass, salutation, tenant_name)},\n\n"
        f"here is your current meter reading for {object_name}.\n\n"
        f"The current reading is: {value} {unit}"
    )
    return title, message


async def _async_send_berth_mail(hass: HomeAssistant, entry: ConfigEntry, berth: dict[str, Any], *, manual: bool) -> None:
    recipient = str(berth.get(CONF_EMAIL, "")).strip()
    if not recipient:
        raise HomeAssistantError("Fuer dieses Objekt ist keine Mieter-E-Mail-Adresse hinterlegt.")
    sensor_entity = berth["meter_sensor"]
    state = hass.states.get(sensor_entity)
    if state is None:
        raise HomeAssistantError(f"Zaehler-Sensor {sensor_entity} existiert nicht.")
    if state.state in ("unknown", "unavailable", None):
        raise HomeAssistantError(f"Zaehler-Sensor {sensor_entity} hat keinen gueltigen Wert.")
    unit = state.attributes.get("unit_of_measurement", "") or "kWh"
    now = dt_util.now()
    object_name = berth.get(CONF_NAME) or berth.get("berth_id")
    tenant_name = berth.get("tenant_name") or ""
    title, message = _object_mail_text(
        hass,
        salutation=berth.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION),
        tenant_name=tenant_name,
        object_name=object_name,
        value=str(state.state),
        unit=str(unit),
    )
    html_message = _object_mail_html(
        hass,
        salutation=berth.get(CONF_TENANT_SALUTATION, DEFAULT_TENANT_SALUTATION),
        tenant_name=tenant_name,
        object_name=object_name,
        value=str(state.state),
        unit=str(unit),
    )
    await _async_send_raw_mail(
        hass,
        entry,
        title=title,
        message=message,
        recipient=recipient,
        data={"object_id": berth.get("berth_id"), "manual": manual},
        html_message=html_message,
    )

    options = _entry_options(entry)
    for item in options[CONF_BERTHS]:
        if item.get("berth_id") == berth.get("berth_id"):
            item["last_sent_date"] = now.date().isoformat()
            item["last_sent_at"] = now.isoformat()
            break
    hass.config_entries.async_update_entry(entry, options=options)
    _LOGGER.info("Sent meter mail for %s to %s", berth.get("berth_id"), berth.get(CONF_EMAIL))


def _format_admin_interval(interval: str) -> str:
    if interval == INTERVAL_MONTHLY:
        return "Monatsübersicht"
    if interval == INTERVAL_QUARTERLY:
        return "Quartalsübersicht"
    if interval == INTERVAL_YEARLY:
        return "Jahresübersicht"
    return "Zählerstandsübersicht"


async def _async_send_management_report(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    manual: bool,
    interval: str | None = None,
    recipient: str | None = None,
    quarter: int | None = None,
) -> None:
    options = _entry_options(entry)
    interval = str(interval or options.get(CONF_MANAGEMENT_INTERVAL, INTERVAL_MONTHLY))
    fallback_key = {
        INTERVAL_MONTHLY: CONF_MANAGEMENT_MONTHLY_EMAIL,
        INTERVAL_QUARTERLY: CONF_MANAGEMENT_QUARTERLY_EMAIL,
        INTERVAL_YEARLY: CONF_MANAGEMENT_YEARLY_EMAIL,
    }.get(interval, CONF_MANAGEMENT_EMAIL)
    recipient = str(recipient or _management_recipient(options, fallback_key)).strip()
    if not EMAIL_RE.match(recipient):
        raise HomeAssistantError("Keine gueltige Verwaltungsmail-Adresse hinterlegt.")
    now = dt_util.now()
    _, _, plural = _property_defaults(options)

    report_rows: list[dict[str, str]] = []
    for berth in options.get(CONF_BERTHS, []):
        if str(berth.get(CONF_RENTAL_TYPE, DEFAULT_RENTAL_TYPE)) == RENTAL_TYPE_SHORT_TERM:
            continue
        sensor_entity = str(berth.get("meter_sensor", ""))
        state = hass.states.get(sensor_entity)
        if state is None:
            value = "Sensor fehlt" if _is_german_lang(hass) else "Sensor missing"
        elif state.state in ("unknown", "unavailable", None):
            value = str(state.state)
        else:
            unit = state.attributes.get("unit_of_measurement", "") or "kWh"
            value = f"{state.state} {unit}"
        report_rows.append(
            {
                "object": str(berth.get(CONF_NAME) or berth.get("berth_id") or ""),
                "tenant": str(berth.get("tenant_name") or ""),
                "email": str(berth.get(CONF_EMAIL) or ""),
                "value": value,
            }
        )

    quarter_suffix_de = f" Q{quarter}" if interval == INTERVAL_QUARTERLY and quarter else ""
    quarter_suffix_en = f" Q{quarter}" if interval == INTERVAL_QUARTERLY and quarter else ""
    if _is_german_lang(hass):
        title = f"{_format_admin_interval(interval)}{quarter_suffix_de} {plural} - {now.strftime('%d.%m.%Y')}"
        lines = [
            f"{_format_admin_interval(interval)}{quarter_suffix_de} der Zählerstände",
            f"Datum: {now.strftime('%d.%m.%Y %H:%M:%S')}",
            f"Anzahl {plural}: {len(report_rows)}",
            "",
            "Objekt | Mieter | Zählerstand | E-Mail",
            "--- | --- | --- | ---",
        ]
    else:
        title = f"{_format_admin_interval_en(interval)}{quarter_suffix_en} {plural} - {now.strftime('%Y-%m-%d')}"
        lines = [
            f"{_format_admin_interval_en(interval)}{quarter_suffix_en}",
            f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Number of {plural}: {len(report_rows)}",
            "",
            "Object | Tenant | Meter reading | E-Mail",
            "--- | --- | --- | ---",
        ]

    for row in report_rows:
        lines.append(f"{row['object']} | {row['tenant']} | {row['value']} | {row['email']}")

    message = "\n".join(lines)
    html_message = _management_report_html(
        hass,
        title=title,
        plural=plural,
        rows=report_rows,
        now=now,
        interval=interval,
    )
    await _async_send_raw_mail(
        hass,
        entry,
        title=title,
        message=message,
        recipient=recipient,
        data={"management_report": True, "manual": manual, "interval": interval, "quarter": quarter},
        html_message=html_message,
    )

    if interval == INTERVAL_QUARTERLY and quarter:
        date_key = f"last_management_report_date_quarterly_q{quarter}"
        at_key = f"last_management_report_at_quarterly_q{quarter}"
    else:
        date_key = f"last_management_report_date_{interval}"
        at_key = f"last_management_report_at_{interval}"
    options[date_key] = now.date().isoformat()
    options[at_key] = now.isoformat()
    options["last_management_report_date"] = now.date().isoformat()
    options["last_management_report_at"] = now.isoformat()
    hass.config_entries.async_update_entry(entry, options=options)
    _LOGGER.info("Sent %s management meter report to %s", interval, recipient)
