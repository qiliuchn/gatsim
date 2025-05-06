# frontend_server/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Homepage: render the main index.html template
    path('',          views.index,              name='index'),
    # API endpoints for simulation control and data
    path('submit/',   views.submit_simulation,  name='submit'),
    path('run/',      views.start_simulation,   name='run'),
    path('stop/',     views.stop_simulation,    name='stop'),
    path('data/',     views.get_simulation_data, name='data'),
]