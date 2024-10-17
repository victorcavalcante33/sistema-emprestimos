
import os
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações de segurança
SECRET_KEY = "django-inseguro-27g&wn&vru!2==ms!=1c2kjycjl^*l(bns0(@*&km0yij*-q6k"
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.0.23:8000', '192.168.0.23', 'vito9621.pythonanywhere.com']

# Aplicações instaladas
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'PELFCRED',
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Configuração de URLs
ROOT_URLCONF = "myproject.urls"

# Configuração dos templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'PELFCRED' / 'templates'],  # Diretório de templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'PELFCRED.context_processors.admin_status',
            ],
        },
    },
]

# Configuração WSGI
WSGI_APPLICATION = "myproject.wsgi.application"

# Configuração do banco de dados
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # Banco de dados SQLite
    }
}

# Validação de senhas
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internacionalização
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Arquivos estáticos
STATIC_URL = '/static/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'myproject/static')]  # Apontando para a pasta static principal

STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para coletar os arquivos estáticos em produção

# Tipo de chave primária padrão
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirecionamento após login e logout
LOGIN_REDIRECT_URL = 'PELFCRED:home'
LOGOUT_REDIRECT_URL = 'PELFCRED:login'

API_PIX_URL = 'https://api.exemplo.com/pix'
API_PIX_KEY = 'sua_chave_de_api'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'PELFCRED': {  # Nome do app ou qualquer outro que você deseja monitorar
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# settings.py

# Certifique-se de que o backend de sessão está configurado corretamente
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # ou 'signed_cookies', conforme apropriado
SESSION_COOKIE_AGE = 1209600  # Duração da sessão em segundos (2 semanas por padrão)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Sessão não deve expirar quando o navegador for fechado
SESSION_COOKIE_SECURE = False  # Defina como True se estiver usando HTTPS