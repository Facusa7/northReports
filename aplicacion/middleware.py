from aplicacion.views import loginView
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib import auth

__author__ = 'Basa'



class AutoLogout:
  def process_request(self, request):
    if not request.user.is_authenticated():
      #Can't log out if not logged in
      #No puedo desloguearse un usuario sin loguearse
      return loginView(request)

    try:
      if datetime.now() - request.session['last_touch'] > timedelta( 0, settings.AUTO_LOGOUT_DELAY * 60, 0):
        auth.logout(request)
        del request.session['last_touch']
        return loginView(request)
    except KeyError:
      pass

    request.session['last_touch'] = datetime.now()