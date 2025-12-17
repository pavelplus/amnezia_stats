from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('stats/', views.stats, name='stats'),
    
    # Django auth
    # https://docs.djangoproject.com/en/5.2/topics/auth/default/#module-django.contrib.auth.views
    # path('accounts/', include('django.contrib.auth.urls')),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]