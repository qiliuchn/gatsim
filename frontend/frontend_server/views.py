# frontend_server/views.py
import os
import json
import subprocess
from django.conf import settings
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed
)
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Folder where gatsim/cache lives
CACHE_DIR = os.path.abspath(
    os.path.join(settings.BASE_DIR, os.pardir, 'gatsim', 'cache')
)

def index(request):
    """
    Render the main frontend page (index.html).
    """
    return render(request, 'index.html')

@csrf_exempt
def submit_simulation(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        payload = json.loads(request.body)
        fork_name       = payload.get('fork_name', '')
        simulation_name = payload['simulation_name']
        command         = payload.get('command', '')
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON payload')

    try:
        subprocess.check_call([
            'python',
            os.path.join(settings.BASE_DIR, 'setup_backend.py'),
            '--fork', fork_name,
            '--name', simulation_name,
            '--cmd',  command
        ])
    except subprocess.CalledProcessError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({
        'status':  'success',
        'message': f'Simulation "{simulation_name}" configured'
    })

@csrf_exempt
def start_simulation(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        subprocess.check_call([
            'python',
            os.path.join(settings.BASE_DIR, 'backend_wrapper.py'),
            '--start'
        ])
    except subprocess.CalledProcessError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'success', 'message': 'Simulation started'})

@csrf_exempt
def stop_simulation(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        subprocess.check_call([
            'python',
            os.path.join(settings.BASE_DIR, 'backend_wrapper.py'),
            '--stop'
        ])
    except subprocess.CalledProcessError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'success', 'message': 'Simulation stopped'})

def get_simulation_data(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    def load(fname):
        with open(os.path.join(CACHE_DIR, fname), 'r') as f:
            return json.load(f)
    try:
        meta      = load('curr_meta.json')
        movements = load('curr_movements.json')
        plans     = load('curr_plans.json')
        messages  = load('curr_messages.json')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({
        'meta':            meta,
        'mobility_events': movements.get('mobility_events', {}),
        'queues':          movements.get('queues', {}),
        'curr_plans':      plans,
        'curr_messages':   messages,
    })
