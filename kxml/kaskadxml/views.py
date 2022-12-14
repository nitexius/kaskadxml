from dataclasses import dataclass
from django.http import HttpResponse
from io import BytesIO
from django.shortcuts import render
from .forms import KlogicForm
from .kaskad_xml import KlogicXML, MnemoListXML
from .tools import (
    set_klogic_xml,
    set_klogger_xml,
    set_alarms_xml,
    transform_file,
    set_arch,
    update_klogic_xml,
    update_klogger_xml,
    update_alarms_xml,
    set_mnemolist_xml,
    update_mnemolist_xml,
    set_gm_mnemo_xml,
    update_gm_mnemo_xml
)
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
    return form.cleaned_data['bd'], form.cleaned_data['alarm'], form.cleaned_data['mnemolist']


def get_zip_name(gm: str) ->str:
    try:
        zip_name = gm.split('(')[1].replace(')', '')
    except IndexError:
        zip_name = 'output'
    return zip_name


def index(request):
    output_files = []

    if request.method == 'POST':
        form = KlogicForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            station_id = form.cleaned_data['station']
            bdtp_checkbox, alarm_checkbox, mnemolist_checkbox = get_checkboxes(form)
            klogic_xml = set_klogic_xml(form)

            gm = str(klogic_xml.klogic_tree_find().gm.text)
            try:
                output_files.extend(update_klogic_xml(klogic_xml))

                params = RequestParams(
                    form=form,
                    klogic_xml=klogic_xml,
                    station_id=station_id,
                )

                handlers = (
                    (set_klogger_xml, update_klogger_xml) if bdtp_checkbox else None,
                    (set_alarms_xml, update_alarms_xml) if alarm_checkbox else None,
                )

                for getter_func, update_func in filter(None, handlers):
                    output_files.append(transform_file(getter_func, update_func, params))

                if mnemolist_checkbox:
                    mnemolist_xml = set_mnemolist_xml(params)
                    output_files.append(update_mnemolist_xml(mnemolist_xml, params))
                    
                    gm_mnemo_xml = set_gm_mnemo_xml(params)
                    output_files.extend(update_gm_mnemo_xml(gm_mnemo_xml, params, mnemolist_xml))

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
                zip_buffer = set_arch(BytesIO(), output_files)
                response = HttpResponse(
                    zip_buffer.getvalue(),
                    headers={
                        'content_type': 'application/zip',
                        'Content-Disposition': f'attachment; filename={get_zip_name(gm)}.zip'
                    }
                )
                return response
    else:
        form = KlogicForm()
        context = {'form': form}

    return render(request, 'xoxml/index.html', context)
