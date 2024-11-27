
import os
from pathlib import Path
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from decouple import config
import pg8000

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações de segurança
SECRET_KEY = "django-inseguro-27g&wn&vru!2==ms!=1c2kjycjl^*l(bns0(@*&km0yij*-q6k"
DEBUG = True
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'potent-plasma-441522-u7.rj.r.appspot.com',
    '35.199.83.2',
    'pelfcred.com',
]
  # Aplicações instaladas
INSTALLED_APPS = [
      'django.contrib.admin',
      'django.contrib.auth',
      'django.contrib.contenttypes',
      'django.contrib.sessions',
      'django.contrib.messages',
      'django.contrib.staticfiles',
      'PELFCRED_APP',
  ]

if DEBUG:
    INSTALLED_APPS.append('sslserver')  # Adicionado para suportar HTTPS no desenvolvimento
    
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

ROOT_URLCONF = "PELFCRED.urls"



# Configuração dos templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'PELFCRED_APP' / 'templates'],  # Diretório de templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'PELFCRED_APP.context_processors.admin_status',
            ],
        },
    },
]

# Configuração WSGI
WSGI_APPLICATION = "PELFCRED.wsgi.application"

if os.getenv('GAE_ENV', '').startswith('standard'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': '/cloudsql/{}'.format(config('INSTANCE_CONNECTION_NAME')),
            'PORT': '5432',
        }
    }
else:
    # Executando localmente (desenvolvimento) usando SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Arquivos estáticos
STATIC_URL = '/static/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'PELFCRED_APP', 'static')]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Para coletar os arquivos estáticos em produção

# Tipo de chave primária padrão
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirecionamento após login e logout
LOGIN_REDIRECT_URL = 'PELFCRED_APP:home'
LOGOUT_REDIRECT_URL = 'PELFCRED_APP:login'

API_PIX_URL = 'https://api.exemplo.com/pix'
API_PIX_KEY = 'sua_chave_de_api'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False