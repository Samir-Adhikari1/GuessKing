from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_game, name='start'),
    path('rules/', views.rules_page, name='rules'),
    path('play/', views.play_game, name='play'),
]