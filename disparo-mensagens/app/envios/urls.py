from django.urls import path
from . import views

app_name = 'envios'

urlpatterns = [
    path('webhook/whatsapp/', views.webhook_whatsapp, name='webhook_whatsapp'),
]