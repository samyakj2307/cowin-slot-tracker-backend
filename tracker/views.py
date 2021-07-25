from django.shortcuts import render
from django.http import JsonResponse
from . import track_runner
from . import cleanFCM
from . import tracker_2_0

# Create your views here.

def index(request):
    track_runner.my_cowin_runner.delay()
    return JsonResponse({"status": "Message sending Started"})

def index_2_0(request):
    # tracker_2_0.my_cowin_runner.delay()
    tracker_2_0.my_cowin_runner()
    return JsonResponse({"status": "Message sending Started"})
    

def clean(request):
    cleanFCM.cleanFunc()
    return JsonResponse({"status":"Hello"})
