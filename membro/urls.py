from django.urls import path

from membro import views

urlpatterns = [
    path('', views.membru_list, name='membru-list'),
    path('foun/', views.membru_create, name='membru-create'),
    path('hein-konfirmasaun/', views.pending_konfirma, name='pending-konfirma'),
    path('hein-aprovasaun/', views.pending_aprova, name='pending-aprova'),
    path('kargu/', views.kargu_list, name='kargu-list'),
    path('kargu/foun/', views.kargu_create, name='kargu-create'),
    path('kargu/<int:pk>/remata/', views.kargu_end, name='kargu-end'),
    path('<uuid:public_id>/', views.membru_detail, name='membru-detail'),
    path('<uuid:public_id>/edita/', views.membru_edit, name='membru-edit'),
    path('<uuid:public_id>/hamoos/', views.membru_delete, name='membru-delete'),
    path('<uuid:public_id>/foto/', views.membru_foto, name='membru-foto'),
    path('<uuid:public_id>/konfirma/', views.membru_konfirma, name='membru-konfirma'),
    path('<uuid:public_id>/aprova/', views.membru_aprova, name='membru-aprova'),
]
