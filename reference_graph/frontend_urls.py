"""
Frontend URL configuration for reference_graph project.
"""
from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', views.home, name='home'),
    path('graph/', views.reference_graph, name='reference_graph'),
    path('paper/<uuid:paper_id>/', views.paper_detail, name='paper_detail'),
    path('upload/', views.upload_paper, name='upload_paper'),
    path('test-graph/', views.test_graph, name='test_graph'),
    path('chatbot-test/', views.chatbot_test, name='chatbot_test'),
    path('login/', RedirectView.as_view(pattern_name='accounts:login', permanent=False), name='login_page'),
    path('signup/', RedirectView.as_view(pattern_name='accounts:signup', permanent=False), name='signup_page'),
]
