from platform import architecture
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.template import context
from django.urls import reverse, reverse_lazy
from .models import Target, CheckList
from .forms import ScanForm, AlertsForm, CheckTargetsForm, TargetForm
from .forms import CheckForm
from .forms import ExportForm
from decouple import config  # Allows us to read .env
from datetime import datetime
from datetime import date
from .scan_targets import main as scan
from .check_targets import main as check

from .targets import add
from .notifications import main as notify
from .inv_logging import start_logging
from .mighty import main as mighty

LOG_DIR = config('LOG_DIR')
GLOBAL_LOG_NAME = "add_web"
GLOBAL_LOG_FILE = LOG_DIR + GLOBAL_LOG_NAME + "_" + str(date.today()) + ".log"
GLOBAL_LOG_LEVEL = 'DEBUG'
GLOBAL_LOG_TO_CONSOLE = 'ON'
target_logger = start_logging(GLOBAL_LOG_LEVEL, GLOBAL_LOG_FILE, GLOBAL_LOG_NAME, GLOBAL_LOG_TO_CONSOLE) 
        
def index(request):
    context = {}
    
    add_form = ScanForm
    check_form = CheckTargetsForm
    alerts_form = AlertsForm

    forms = {
        'add_form': add_form,
        'check_form': check_form,
        'alerts_form': alerts_form
    }

    context['forms'] = forms

    return render(request, 'index.html', context)

def add_update(request):
    context = {}
    context['form'] = ScanForm()
    if request.method == 'POST':
        form = ScanForm(request.POST)

        if form.is_valid():
            target_type = form.cleaned_data.get('target_type')
            action = form.cleaned_data.get('action')
            vendor = form.cleaned_data.get('vendor')
            args_string = []

            if action == 'Add':
                args_string.append('-a')

            args_string.append('-t')
            args_string.append(target_type)
            args_string.append('-v')
            args_string.append(vendor)
            scan(args_string)
        
    else:
        form = ScanForm()

    return HttpResponseRedirect(reverse('index'))

def run_report(request):
    context = {}
    context['form'] = AlertsForm()
    if request.method == 'POST':
        form = AlertsForm(request.POST)
        if form.is_valid():
            target_type = form.cleaned_data.get('target_type')
            interval = form.cleaned_data.get('interval')
            args_string = []

            args_string.append('-t')
            args_string.append(target_type)
            args_string.append('-i')
            args_string.append(interval)
            print(args_string)
            notify(args_string)
    else:
        form = AlertsForm()

    return HttpResponseRedirect(reverse('index'))

def check_target(request):
    context = {}
    context['form'] = CheckForm()

    if request.method == 'POST':
    # create a form instance and populate it with data from the request:
        form = CheckForm(request.POST)

        if form.is_valid():
            target_type = form.cleaned_data.get('target_type')
            frequency = form.cleaned_data.get('frequency')
            vendor = form.cleaned_data.get('vendor')
            args_string = []

            args_string.append('-t')
            args_string.append(target_type)
            args_string.append('-f')
            args_string.append(frequency)
            print(args_string)
            check(args_string)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = CheckForm()

    return HttpResponseRedirect(reverse('index'))


def export_target(request):
    context = {}
    context['form'] = ExportForm()

    if request.method == 'POST':
    # create a form instance and populate it with data from the request:
        form = ScanForm(request.POST)

        if form.is_valid():
            target_type = form.cleaned_data.get('target_type')
            
            RC=mighty(target_type)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ExportForm()

    return HttpResponseRedirect(reverse('index') )

def add_target(request):
    target_instance = Target()

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # return HttpResponseRedirect('/codify_app/add_target')
        # create a form instance and populate it with data from the request:
        form = TargetForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            inventory_id = form.cleaned_data['inventory_id']
            hostname = form.cleaned_data['hostname']
            instance_name = form.cleaned_data['instance_name']
            owner = form.cleaned_data['owner']
            container = form.cleaned_data['container']
            DBID = form.cleaned_data['DBID']
            home_dir = form.cleaned_data['home_dir']
            status = form.cleaned_data['status']
            port = form.cleaned_data['port']
            target_type = form.cleaned_data['target_type']
            #target_instance.save() 
            inventory_id=add(hostname, instance_name, container, DBID, owner, home_dir, status, port, target_type, target_logger)

            return HttpResponseRedirect(reverse('index') )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = TargetForm()

    return render(request, 'target.html', {'form': form})
