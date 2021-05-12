from django.shortcuts import render
from django.http import JsonResponse
from . import track_runner

# Create your views here.

def index(request):
    track_runner.my_cowin_runner()
    return JsonResponse({"status": "Message sending Started"})
