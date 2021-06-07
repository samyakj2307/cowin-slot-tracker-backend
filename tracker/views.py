from django.shortcuts import render
from django.http import JsonResponse
from . import track_runner
from . import cleanFCM

# Create your views here.

def index(request):
    track_runner.my_cowin_runner.delay()
    return JsonResponse({"status": "Message sending Started"})
    

def clean(request):
    cleanFCM.cleanFunc()
    return JsonResponse({"status":"Hello"})
