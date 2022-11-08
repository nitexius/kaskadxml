import logging
import pathlib
import zipfile
from django.http import HttpResponse
from io import BytesIO
from typing import Iterable, List
from dataclasses import dataclass
from django.shortcuts import render
from .forms import KlogicForm
from .kaskad_xml import AlarmsXML, KloggerXML, KlogicXML, ErrorMissingNofflTag, ErrorMissingProduct
from .models import HistoryAttr, Tag, Alarm, Cutout

logger = logging.getLogger(__name__)


class KlogicBadFormatError(Exception):
    """Klogic XML: Неправильный формат"""


class KloggerBadFormatError(Exception):
    """Klogger XML: Неправильный формат"""


class AlarmsBadFormatError(Exception):
    """Klogger XML: Неправильный формат"""


class NotEnoughVar(Exception):
    """В группе Alarms у централи добавлены не все переменные"""


class NewTagsError(Exception):
    """Новые переменные"""


class DefaultAlarmError(Exception):
    """Шаблон Alarm XML не найден"""


@dataclass
class OutputFiles:
    name: str
    file: bytes


@dataclass
class kargs:
    form: KlogicForm
    klogic_xml: KlogicXML
    station_id: int


def shift_create(klogic_xml: KlogicXML) -> BytesIO:
    """Подсчет смещения адресов контроллеров"""
    shift_attr = klogic_xml.shift()
    txt = BytesIO()

    for l in shift_attr.all_lens:
        address = 0
        for i, _ in enumerate(shift_attr.all_attrs):
            if shift_attr.all_attrs[i].len_group != l:
                continue
            current_shift = (
                float(shift_attr.all_attrs[i].addr) - address
                if i and address else 0
            )
            address = float(shift_attr.all_attrs[i].addr)
            new_str = f'Кол-во переменных = {l}. {shift_attr.all_attrs[i].name}. Смещение = {current_shift} \n'
            txt.write(bytes(new_str, encoding='utf-8'))
    return txt


def get_checkboxes(form):
    return form.cleaned_data['bd'], form.cleaned_data['alarm']


def get_klogic_input_file(form):
    PROT_CODE = '244'
    xml_file = form.cleaned_data['klogic_file']
    xml_file_read = xml_file.read()
    klogic_input_file = BytesIO(xml_file_read)
    klogic_input_file.seek(0)
    return KlogicXML(klogic_input_file, PROT_CODE, xml_file.name)


def get_klogger_input_file(args):
    klogger_xml_file = args.form.cleaned_data['klogger_file']
    klogger_xml_file_read = klogger_xml_file.read()
    klogger_input_file = BytesIO(klogger_xml_file_read)
    klogger_input_file.seek(0)
    return KloggerXML(klogger_input_file, args.klogic_xml.klogic_tree_find(), args.station_id, klogger_xml_file.name)


def get_default_alarm_xml_path() -> pathlib.Path:
    try:
        default_alarm_xml_path = Alarm.objects.get(gm='default_alarm_xml').xml.path
    except (Alarm.DoesNotExist, FileNotFoundError):
        raise DefaultAlarmError('Шаблон Alarm XML не найден')
    return default_alarm_xml_path


def get_alarms_input_file(args):
    return AlarmsXML(get_default_alarm_xml_path(), args.klogic_xml.klogic_tree_find(), args.station_id,
                     Cutout.get_products_values())


def get_new_tags(klogic_xml):
    try:
        klogic_xml.find_module()
        logger.debug(klogic_xml.module.tag)
        klogic_xml.h_remove(HistoryAttr.get_h_attrs())
        Tag.delete_new_tags()
        new_tags = klogic_xml.set_new_tags(Tag.get_tags_values())
        if new_tags == -1:
            raise NotEnoughVar('В группе Alarms у централи добавлены не все переменные')
        return new_tags
    except AttributeError:
        raise KlogicBadFormatError('Klogic XML: Неправильный формат')


def save_new_tags(new_tags):
    for tag in new_tags:
        new_tag = Tag(id=tag.tag_id, name=tag.tag_name, controller=tag.controller, tag_type='3')
        new_tag.save()


def create_output_file(kaskad_module: KlogicXML or AlarmsXML or KloggerXML) -> OutputFiles:
    output_file = BytesIO()
    kaskad_module.write(output_file)
    return OutputFiles(
        name=kaskad_module.xml_file_name,
        file=output_file.getbuffer()
    )


def create_shift_output_file(klogic_xml):
    return OutputFiles(
        name='Смещение.txt',
        file=shift_create(klogic_xml).getbuffer()
    )


def update_klogic_xml(klogic_xml: KlogicXML):
    new_tags = get_new_tags(klogic_xml)
    if len(new_tags):
        save_new_tags(new_tags)
        raise NewTagsError(f'Новые переменные: {len(new_tags)}')
    else:
        klogic_xml.delete_empty_groups()
        klogic_xml.delete_tags(Tag.get_bad_tags())
        klogic_xml.add_comment()
        klogic_xml.set_noffl(Tag.get_tags_values())
        return create_output_file(klogic_xml), create_shift_output_file(klogic_xml)


def update_klogger_xml(klogger_xml: KloggerXML, args):
    klogger_xml.delete_old_config()
    try:
        logger.debug(klogger_xml.db_version.tag)
        klogger_xml.set_klogger_xml(args.klogic_xml.module, Tag.get_bdtp_tags())
        return create_output_file(klogger_xml)
    except AttributeError:
        raise KloggerBadFormatError('Klogger XML: Неправильный формат')


def update_alarms_xml(alarm_xml: AlarmsXML, args):
    try:
        logger.debug(alarm_xml.group_item.tag)
        alarm_xml.set_alarm_xml(args.klogic_xml.module, Tag.get_tags_values())
        return create_output_file(alarm_xml)
    except AttributeError:
        raise AlarmsBadFormatError('Alarm XML: Неправильный формат')


def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
    for file in files:
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr(file.name, file.file)
    return zip_buffer


def get_files(input_file, output_file, args):
    file = input_file(args)
    return output_file(file, args)


def index(request):
    output_files = []

    if request.method == 'POST':
        form = KlogicForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            station_id = form.cleaned_data['station']
            bdtp_checkbox, alarm_checkbox = get_checkboxes(form)
            klogic_xml = get_klogic_input_file(form)
            print(klogic_xml)
            gm = str(klogic_xml.klogic_tree_find().gm.text)
            try:
                output_files.extend(update_klogic_xml(klogic_xml))

                params = kargs(
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
