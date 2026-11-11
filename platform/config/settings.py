"""Configuration Django de SYSTEM-C Platform.

Toutes les valeurs sensibles ou propres à un environnement viennent des
variables d'environnement (voir ``.env.example``). Aucun secret n'est versionné.
"""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from .env import env, env_bool, env_int, env_list, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR / ".env")

DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Clé de développement uniquement : jamais acceptée hors mode DEBUG.
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY est obligatoire quand DJANGO_DEBUG est désactivé.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.partners",
    "apps.bots",
    "apps.academy",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.OrganizationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.platform",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "systemc"),
        "USER": env("POSTGRES_USER", "systemc"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        "OPTIONS": {"connect_timeout": 10},
    }
}

# Cache partagé en base : fonctionne avec plusieurs processus sans service externe.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "systemc_cache",
    }
}

AUTH_USER_MODEL = "core.User"
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Limitation des tentatives de connexion.
LOGIN_MAX_ATTEMPTS_PER_ACCOUNT = env_int("LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", 5)
LOGIN_MAX_ATTEMPTS_PER_IP = env_int("LOGIN_MAX_ATTEMPTS_PER_IP", 20)
LOGIN_LOCKOUT_SECONDS = env_int("LOGIN_LOCKOUT_SECONDS", 15 * 60)

# Internationalisation : français par défaut, anglais disponible.
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", _("French")), ("en", _("English"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "systemc_language"
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_HTTPONLY = True
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions et cookies.
SESSION_COOKIE_AGE = env_int("SESSION_COOKIE_AGE", 8 * 60 * 60)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# En-têtes de sécurité (complétés par apps.core.middleware.SecurityHeadersMiddleware).
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    LANGUAGE_COOKIE_SECURE = True
    SESSION_COOKIE_NAME = "__Host-sessionid"
    CSRF_COOKIE_NAME = "__Host-csrftoken"
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    if env_bool("DJANGO_BEHIND_TLS_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Journalisation : sortie console, sans corps de requête ni donnée de formulaire.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
        # Les 403/404 sont des refus attendus : pas de trace détaillée dans les journaux.
        "django.request": {"level": "ERROR"},
    },
}

# Valeurs par défaut propres à la plateforme.
SYSTEMC_DEFAULT_CURRENCY = env("SYSTEMC_DEFAULT_CURRENCY", "USD")

# Fichiers privés (ressources payantes d'Academy) : hors du code source et des
# fichiers statiques, sans URL publique. Ils ne seront servis que par une vue
# qui vérifie les droits d'accès.
SYSTEMC_PRIVATE_MEDIA_ROOT = Path(env("SYSTEMC_PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))
