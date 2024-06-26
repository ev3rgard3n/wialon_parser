"""
URL configuration for wialonparser project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from project import views, apis


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_index, name='home_index'),
    path('logout/', views.logout_user, name='logout'),

    path("api/wialon/sensors/<int:object_id>", views.get_sensors_statistics, name="sensors"),
    path("api/wialon/feul_report/<int:object_id>", views.fuel_report, name="fuel_report"),
    path("api/wialon/feul_report/all/", views.fuel_report_for_all, name="fuel_report_for_all"),


    path('wialon_send_auth/', views.wialon_send_auth, name='wialon_send_auth'),
    path('wialon_recv_auth/', views.wialon_recv_auth),

    path('api/wialon/get_last_events/', apis.api_wialon_get_last_events),
    path('api/first_init/', apis.first_init)
]
