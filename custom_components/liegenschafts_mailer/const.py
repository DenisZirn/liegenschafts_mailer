"""Constants for Liegenschafts Mailer."""
from __future__ import annotations

DOMAIN = "liegenschafts_mailer"

CONF_NOTIFY_SERVICE = "notify_service"
CONF_BERTHS = "berths"
CONF_SEND_MODE = "send_mode"
CONF_ADMIN_PASSWORD = "admin_password"
CONF_ADMIN_PASSWORD_ENABLED = "admin_password_enabled"
CONF_ADMIN_PASSWORD_DISABLED = "admin_password_disabled"
CONF_PROPERTY_TYPE = "property_type"
CONF_OBJECT_LABEL = "object_label"
CONF_OBJECT_LABEL_PLURAL = "object_label_plural"
CONF_MANAGEMENT_EMAIL = "management_email"
CONF_MANAGEMENT_INTERVAL = "management_interval"
CONF_MANAGEMENT_INTERVALS = "management_intervals"
CONF_MANAGEMENT_SEND_TIME = "management_send_time"
CONF_MANAGEMENT_MONTHDAY = "management_monthday"
CONF_MANAGEMENT_MONTH = "management_month"
CONF_DEFAULT_KWH_PRICE = "default_kwh_price"
CONF_HA_BASE_URL = "ha_base_url"
CONF_RENTAL_TYPE = "rental_type"

CONF_LAST_BILLING_PDF_URL = "last_billing_pdf_url"
CONF_LAST_BILLING_PDF_PATH = "last_billing_pdf_path"
CONF_LAST_BILLING_PDF_FILENAME = "last_billing_pdf_filename"
CONF_LAST_BILLING_AT = "last_billing_at"
CONF_LAST_BILLING_SCOPE = "last_billing_scope"
CONF_LAST_BILLING_START_DATE = "last_billing_start_date"
CONF_LAST_BILLING_END_DATE = "last_billing_end_date"

CONF_MANAGEMENT_DEFAULT_EMAIL = "management_default_email"
CONF_MANAGEMENT_MONTHLY_ENABLED = "management_monthly_enabled"
CONF_MANAGEMENT_MONTHLY_EMAIL = "management_monthly_email"
CONF_MANAGEMENT_MONTHLY_SEND_TIME = "management_monthly_send_time"
CONF_MANAGEMENT_MONTHLY_MONTHDAY = "management_monthly_monthday"
CONF_MANAGEMENT_QUARTERLY_ENABLED = "management_quarterly_enabled"
CONF_MANAGEMENT_QUARTERLY_EMAIL = "management_quarterly_email"
CONF_MANAGEMENT_QUARTERLY_SEND_TIME = "management_quarterly_send_time"
CONF_MANAGEMENT_QUARTERLY_MONTHDAY = "management_quarterly_monthday"
CONF_MANAGEMENT_QUARTERLY_MODE = "management_quarterly_mode"
CONF_MANAGEMENT_QUARTERLY_Q1 = "management_quarterly_q1"
CONF_MANAGEMENT_QUARTERLY_Q2 = "management_quarterly_q2"
CONF_MANAGEMENT_QUARTERLY_Q3 = "management_quarterly_q3"
CONF_MANAGEMENT_QUARTERLY_Q4 = "management_quarterly_q4"
CONF_MANAGEMENT_YEARLY_ENABLED = "management_yearly_enabled"
CONF_MANAGEMENT_YEARLY_EMAIL = "management_yearly_email"
CONF_MANAGEMENT_YEARLY_SEND_TIME = "management_yearly_send_time"
CONF_MANAGEMENT_YEARLY_MONTHDAY = "management_yearly_monthday"
CONF_MANAGEMENT_YEARLY_MONTH = "management_yearly_month"

QUARTER_MODE_START = "quarter_start"
QUARTER_MODE_END = "quarter_end"
QUARTER_MODES = [QUARTER_MODE_START, QUARTER_MODE_END]
CONF_TENANT_SALUTATION = "tenant_salutation"

SEND_MODE_TARGET = "target"
SEND_MODE_DEFAULT_RECIPIENT = "default_recipient"
SEND_MODES = [SEND_MODE_TARGET, SEND_MODE_DEFAULT_RECIPIENT]

DEFAULT_NOTIFY_SERVICE = "notify.mail_ha"
DEFAULT_SEND_MODE = SEND_MODE_TARGET
DEFAULT_PROPERTY_TYPE = "marina"
DEFAULT_OBJECT_LABEL = "Liegeplatz"
DEFAULT_OBJECT_LABEL_PLURAL = "Liegeplätze"

TENANT_SALUTATION_MR = "mr"
TENANT_SALUTATION_MS = "ms"
TENANT_SALUTATIONS = [TENANT_SALUTATION_MR, TENANT_SALUTATION_MS]
DEFAULT_TENANT_SALUTATION = TENANT_SALUTATION_MR

RENTAL_TYPE_PERMANENT = "permanent"
RENTAL_TYPE_SHORT_TERM = "short_term"
RENTAL_TYPES = [RENTAL_TYPE_PERMANENT, RENTAL_TYPE_SHORT_TERM]
DEFAULT_RENTAL_TYPE = RENTAL_TYPE_PERMANENT

PROPERTY_TYPE_MARINA = "marina"
PROPERTY_TYPE_APARTMENTS = "apartments"
PROPERTY_TYPE_GARAGES = "garages"
PROPERTY_TYPE_CAMPING = "camping"
PROPERTY_TYPE_EBIKE = "ebike"
PROPERTY_TYPE_LAUNDRY = "laundry"
PROPERTY_TYPE_CUSTOM = "custom"
PROPERTY_TYPES = [
    PROPERTY_TYPE_MARINA,
    PROPERTY_TYPE_APARTMENTS,
    PROPERTY_TYPE_GARAGES,
    PROPERTY_TYPE_CAMPING,
    PROPERTY_TYPE_EBIKE,
    PROPERTY_TYPE_LAUNDRY,
    PROPERTY_TYPE_CUSTOM,
]

PROPERTY_TYPE_DEFAULTS = {
    PROPERTY_TYPE_MARINA: ("Yachthafen", "Liegeplatz", "Liegeplätze"),
    PROPERTY_TYPE_APARTMENTS: ("Mietwohnungen", "Wohnung", "Wohnungen"),
    PROPERTY_TYPE_GARAGES: ("Garagen", "Garage", "Garagen"),
    PROPERTY_TYPE_CAMPING: ("Campingplätze", "Stellplatz", "Stellplätze"),
    PROPERTY_TYPE_EBIKE: ("E-Bike-Ladeplätze", "E-Bike-Platz", "E-Bike-Plätze"),
    PROPERTY_TYPE_LAUNDRY: ("Waschmaschinenplätze", "Waschmaschinenplatz", "Waschmaschinenplätze"),
    PROPERTY_TYPE_CUSTOM: ("Liegenschaft", "Einheit", "Einheiten"),
}

INTERVAL_DAILY = "daily"
INTERVAL_WEEKLY = "weekly"
INTERVAL_MONTHLY = "monthly"
INTERVAL_QUARTERLY = "quarterly"
INTERVAL_YEARLY = "yearly"
INTERVALS = [INTERVAL_DAILY, INTERVAL_WEEKLY, INTERVAL_MONTHLY, INTERVAL_QUARTERLY, INTERVAL_YEARLY]
MANAGEMENT_INTERVALS = [INTERVAL_MONTHLY, INTERVAL_QUARTERLY, INTERVAL_YEARLY]

SERVICE_ADD_UPDATE_BERTH = "add_update_object"
SERVICE_REMOVE_BERTH = "remove_object"
SERVICE_SEND_NOW = "send_object_now"
SERVICE_SEND_ALL_NOW = "send_all_now"
SERVICE_SEND_TEST_MAIL = "send_test_mail"
SERVICE_SEND_MANAGEMENT_REPORT_NOW = "send_management_report_now"
SERVICE_EXPORT_CURRENT_CSV = "export_current_csv"
SERVICE_SEND_CSV_TO_MANAGEMENT = "send_csv_to_management"
SERVICE_SEND_BILLING_PDF_TO_MANAGEMENT = "send_billing_pdf_to_management"

BILLING_SCOPE_SHORT_TERM = "short_term"
BILLING_SCOPE_LONG_TERM = "long_term"
BILLING_SCOPE_ALL = "all"
BILLING_SCOPE_OBJECT = "object"
BILLING_SCOPES = [BILLING_SCOPE_SHORT_TERM, BILLING_SCOPE_LONG_TERM, BILLING_SCOPE_ALL, BILLING_SCOPE_OBJECT]
