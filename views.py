from dataclasses import dataclass
from django.http import HttpResponse
from io import BytesIO
from django.shortcuts import render
from .forms import KlogicForm
from .kaskad_xml import KlogicXML
from .files_tools import get_klogic_input_file, get_klogger_input_file, get_alarms_input_file, get_files, set_arch
from .update_xmls_tools import update_klogic_xml, update_klogger_xml, update_alarms_xml
from .log_utils import logger
from .kaskad_xml import (
    ErrorMissingProduct,
    ErrorMissingNofflTag,
    KlogicBadFormatError,
    KloggerBadFormatError,
    AlarmsBadFormatError,
    NotEnoughVar,
    NewTagsError,
    DefaultAlarmError
)


@dataclass
class RequestParams:
    form: KlogicForm
    klogic_xml: KlogicXML
    station_id: int


def get_checkboxes(form):
    return form.cleaned_data['bd'], form.cleaned_data['alarm']


def index(request):
    output_files = []

    if request.method == 'POST':
        form = KlogicForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            station_id = form.cleaned_data['station']
            bdtp_checkbox, alarm_checkbox = get_checkboxes(form)
            klogic_xml = get_klogic_input_file(form)
            gm = str(klogic_xml.klogic_tree_find().gm.text)
            try:
                output_files.extend(update_klogic_xml(klogic_xml))

                params = RequestParams(
                    form=form,
                    klogic_xml=klogic_xml,
                    station_id=station_id
                )

                handlers = (
                    (get_klogger_input_file, update_klogger_xml) if bdtp_checkbox else None,
                    (get_alarms_input_file, update_alarms_xml) if alarm_checkbox else None
                )

                for getter_func, update_func in filter(None, handlers):
                    output_files.append(get_files(getter_func, update_func, params))

                logger.debug(context)

            except (
                    KlogicBadFormatError,
                    KloggerBadFormatError,
                    AlarmsBadFormatError,
                    DefaultAlarmError,
                    IndexError,
                    NotEnoughVar,
                    ErrorMissingNofflTag,
                    NewTagsError,
                    ErrorMissingProduct
            ) as msg:
                context['text_error'] = msg

            if 'text_error' not in context:
                zip_name = gm.split('(')[1].replace(')', '')
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
        form = KlogicForm()
        context = {'form': form}

    return render(request, 'xoxml/index.html', context)
