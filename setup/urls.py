from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rota Vagas (DM-19 e DM-20)
    path('api/vagas', views.vagas_list_create, name='vagas_list_create'),
    path('api/vagas/', views.vagas_list_create, name='vagas_list_create_slash'),
    path('api/vagas/<int:vaga_id>', views.vaga_detail, name='vaga_detail'),
    path('api/vagas/<int:vaga_id>/', views.vaga_detail, name='vaga_detail_slash'),

    # Rota Dashboard (DM-21)
    path('api/dashboard', views.dashboard_indicadores, name='dashboard_indicadores'),
    path('api/dashboard/', views.dashboard_indicadores, name='dashboard_indicadores_slash'),
    path('api/dashboard/indicadores', views.dashboard_indicadores, name='dashboard_indicadores_sub'),
    path('api/dashboard/indicadores/', views.dashboard_indicadores, name='dashboard_indicadores_sub_slash'),
]