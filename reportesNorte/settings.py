"""
Django settings for reportesNorte project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

#encoding:utf-8

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

RUTA_PROYECTO = os.path.dirname(os.path.realpath(__file__))

TEMPLATE_DIRS = (
    os.path.join(RUTA_PROYECTO,'plantillas'),
)

STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.



    os.path.join(RUTA_PROYECTO,'static'),
)



ADMINS = (
     ('Mateo', 'mateobasaldua@gmail.com'),
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'a2*$s2ghx*=m@=lu#39-ub_p*uae^(l2e)6qsyu_^t)9qvb3fd'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True



TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'aplicacion',
)



MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'aplicacion.middleware.AutoLogout',#tambien fue agregado para el autoLogout
)


ROOT_URLCONF = 'reportesNorte.urls'

WSGI_APPLICATION = 'reportesNorte.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
   'default': {
        'ENGINE': 'sqlserver_ado', #sqlserver_ado
        'NAME': 'SI_RE_PA',
        'HOST': '10.0.4.162',
        #'PORT': '1433',
        'USER': 'sa',
        'PASSWORD': 'Norte1234',
        'OPTIONS': {
            'provider': 'SQLNCLI11', #'provider': 'SQLNCLI11',
            'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'#'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'
        }
    },

     'SDCLASS': {
        'ENGINE': 'sqlserver_ado', #sqlserver_ado
        'NAME': 'SD_CLASS_SQL',
        'HOST': '10.0.4.162',
        #'PORT': '1433',
        'USER': 'sa',
        'PASSWORD': 'Norte1234',
        'OPTIONS': {
            'provider': 'SQLNCLI11', #'provider': 'SQLNCLI11',
            'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'#'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'
        }
    },

     'sqlserver2008': {
        'ENGINE': 'sqlserver_ado', #sqlserver_ado
        'NAME': 'SD_CLASS_SQL',
        #'HOST': '10.0.4.162',
        'HOST': '10.0.4.40',
        #'PORT': '1433',
        'USER': 'pasante1',
        #'USER': 'sa',
        'PASSWORD': 'Norte1234',
        'OPTIONS': {
            'provider': 'SQLNCLI11', #'provider': 'SQLNCLI11',
            'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'#'use_mars': 'DataTypeCompatibility=80;MARS Connection=True;'
        }
     }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'es-AR'

DATABASE_OPTIONS = {'charset': 'utf8'}
DEFAULT_CHARSET = 'utf-8'

TIME_ZONE = 'America/Argentina/Buenos_Aires'



USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'


#Agregado
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True #Cierra la sesion cuando se cierra el nevegador.

# Auto logout delay in minutes
AUTO_LOGOUT_DELAY = 60 #equivalent to 60 minuts


MEDIA_ROOT = 'C:/Users/Basa/Documents/Trabajo/ProyectosPython/reportesNorte/reportesNorte/static/'
MEDIA_URL = '/images/'
IMAGEN_EXCEL = 'C:/Users/Basa/Documents/Trabajo/ProyectosPython/reportesNorte/reportesNorte/static/images/headerExcel.bmp'

#Correo
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'sirepa.norte@gmail.com'
EMAIL_HOST_PASSWORD = 'Norte1234'

# EMAIL_USE_TLS = True
# EMAIL_HOST = '10.0.4.8/exchange'
# EMAIL_PORT = 25
# EMAIL_HOST_USER = 'indicador@diarionorte.com'
# EMAIL_HOST_PASSWORD = 'Pelopincho8103'


#De aca para abajo lo de Active Directory
import ldap
from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion, PosixGroupType, NestedActiveDirectoryGroupType


AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)
# Binding and connection options
AUTH_LDAP_SERVER_URI = "ldap://diarionorte.com"  
AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
AUTH_LDAP_BIND_DN = "cn=Administrador,cn=Users,DC=diarionorte,DC=com"
AUTH_LDAP_BIND_PASSWORD = "Moxtezuma100215"

# AUTH_LDAP_USER_ATTR_MAP = {"first_name": "givenName", "last_name": "sn"}
# AUTH_LDAP_PROFILE_ATTR_MAP = {"home_directory": "homeDirectory"}

AUTH_LDAP_USER_SEARCH = LDAPSearch("DC=diarionorte, DC=com", ldap.SCOPE_SUBTREE, "(&(objectClass=*)(sAMAccountName=%(user)s))")
# Para agregar el grupo permitido a acceder al sistema solo escribir algo como esto "ou=Departamento Sistemas,"
AUTH_LDAP_GROUP_SEARCH = LDAPSearch("ou=groups,dc=diarionorte, dc =com",
                                    ldap.SCOPE_SUBTREE,  # allow searching from current node to all nodes below
                                    "(objectClass=*)"  # type of object
)
AUTH_LDAP_GROUP_TYPE = PosixGroupType(name_attr="cn")  # a posixGroup is identified by the keyword "cn" into ldap server
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}
#Esto se usa para ver la respuesta del servidor Active Directory, descomentar esto cuando no responda
#import logging

#logger = logging.getLogger('django_auth_ldap')
#logger.addHandler(logging.StreamHandler())
#logger.setLevel(logging.DEBUG)
