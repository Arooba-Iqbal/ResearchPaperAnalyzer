"""
URL configuration for the papers app.
"""
from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'papers'

urlpatterns = [
    path('papers/', views.PaperListView.as_view(), name='paper-list'),
    path('papers/<uuid:pk>/', views.PaperDetailView.as_view(), name='paper-detail'),
    path('papers/<uuid:pk>/references/', views.PaperReferencesView.as_view(), name='paper-references'),
    path('papers/<uuid:pk>/cited-by/', views.PaperCitedByView.as_view(), name='paper-cited-by'),
    path('papers/<uuid:pk>/chunks/', views.PaperChunksView.as_view(), name='paper-chunks'),
    path('papers/<uuid:pk>/process-references/', views.process_paper_references, name='process-paper-references'),
    path('upload/', login_required(views.PaperUploadView.as_view()), name='paper-upload'),
    path('search/', views.PaperSearchView.as_view(), name='paper-search'),
    path('graph-data/', views.GraphDataView.as_view(), name='graph-data'),
]
