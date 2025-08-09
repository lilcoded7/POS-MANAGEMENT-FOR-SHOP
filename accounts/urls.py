from django.urls import path
from accounts.views import *


urlpatterns = [
    path('login/user/', login_view, name='login_view'),
    path('logout/', logout_view, name='logout_out')

]