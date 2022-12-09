from django.http import HttpResponse
from io import BytesIO
from django.shortcuts import render
from .forms import DguForm
from .tools import (
    set_klogic_xml,
    set_alarms_xml,
    update_klogic_xml,
    update_alarms_xml,
)
from kaskadxml.views import RequestParams
from kaskadxml.tools import set_arch
from kaskadxml.kaskad_xml import NewTagsError, KlogicBadFormatError, AlarmsBadFormatError, DefaultAlarmError
from kaskadxml.log_utils import logger


def get_checkbox(form):
    return form.cleaned_data['alarm']


def index(request):
    output_files = []

    if request.method == 'POST':
        form = DguForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            station_id = form.cleaned_data['station']
            alarm_checkbox = get_checkbox(form)
            klogic_xml = set_klogic_xml(form)
            try:
                update_klogic_xml(klogic_xml)

                params = RequestParams(
                    form=form,
                    klogic_xml=klogic_xml,
                    station_id=station_id
                )

                if alarm_checkbox:
                    alarms_xml = set_alarms_xml(params)
                    output_files.append(update_alarms_xml(alarms_xml, params))

                logger.debug(context)

            except (
                    KlogicBadFormatError,
                    AlarmsBadFormatError,
                    DefaultAlarmError,
                    IndexError,
                    NewTagsError,
            ) as msg:
                context['text_error'] = msg

            if 'text_error' not in context:
                zip_name = 'DGU_output'
                zip_buffer = set_arch(BytesIO(), output_files)
                response = HttpResponse(
                    zip_buffer.getvalue(),
                    headers={
                        'content_type': 'application/zip',
                        'Content-Disposition': f'attachment; filename={zip_name}.zip'
                    }
                )
                return response
    else:
        form = DguForm()
        context = {'form': form}
    return render(request, 'dguxml/index.html', context)
