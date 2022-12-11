from django.http import HttpResponse
from io import BytesIO
from django.shortcuts import render
from .forms import DguForm
from .tools import (
    set_klogic_xml,
    set_alarms_xml,
    set_mnemolist_xml,
    update_klogic_xml,
    update_alarms_xml,
    update_mnemolist_xml,
)
from kaskadxml.views import RequestParams
from kaskadxml.tools import set_arch, transform_file
from kaskadxml.kaskad_xml import NewTagsError, KlogicBadFormatError, AlarmsBadFormatError, DefaultAlarmError
from kaskadxml.log_utils import logger
from .kaskad_xml import generate_mnemo_id


def get_checkboxes(form):
    return form.cleaned_data['alarm'], form.cleaned_data['mnemolist']


def index(request):
    output_files = []
    generate_mnemo_id()

    if request.method == 'POST':
        form = DguForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            station_id = form.cleaned_data['station']
            alarm_checkbox, mnemolist_checkbox = get_checkboxes(form)
            klogic_xml = set_klogic_xml(form)
            try:
                update_klogic_xml(klogic_xml)

                params = RequestParams(
                    form=form,
                    klogic_xml=klogic_xml,
                    station_id=station_id
                )

                handlers = (
                    (set_alarms_xml, update_alarms_xml) if alarm_checkbox else None,
                    (set_mnemolist_xml, update_mnemolist_xml) if mnemolist_checkbox else None,
                )

                for getter_func, update_func in filter(None, handlers):
                    output_files.append(transform_file(getter_func, update_func, params))

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
