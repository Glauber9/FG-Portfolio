from django.urls import path
from . import views

app_name = 'contatos'

urlpatterns = [
    path('opt-out/<uuid:token>/', views.opt_out, name='opt_out'),
    path('api/importar/', views.importar_contatos_api, name='importar_contatos_api'),
]