from django.urls import path

from . import views

urlpatterns = [
    path('message/like/', views.handle_like, name='message_like'),
    path('get_csrf_token/', views.get_csrf_token, name='get_csrf_token'),
]