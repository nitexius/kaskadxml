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
    return (
        KlogicXML(klogic_input_file, prot_code=PROT_CODE),
        xml_file.name
    )


def get_klogger_input_file(form, klogic_xml: KlogicXML, station_id: int):
    klogger_xml_file = form.cleaned_data['klogger_file']
    klogger_xml_file_read = klogger_xml_file.read()
    klogger_input_file = BytesIO(klogger_xml_file_read)
    klogger_input_file.seek(0)
    return (
        KloggerXML(klogger_input_file, klogic_xml.klogic_tree_find(), station_id),
        klogger_xml_file.name
    )


def get_default_alarm_xml_path() -> pathlib.Path:
    try:
        default_alarm_xml_path = Alarm.objects.get(gm='default_alarm_xml').xml.path
    except (Alarm.DoesNotExist, FileNotFoundError):
        raise DefaultAlarmError('Шаблон Alarm XML не найден')
    return default_alarm_xml_path


def get_alarms_input_file(klogic_xml: KlogicXML, station_id: int):
    return (
        AlarmsXML(get_default_alarm_xml_path(), klogic_xml.klogic_tree_find(), station_id,
                  Cutout.get_products_values()),
        'Alarms.xml'
    )


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
    raise NewTagsError(f'Новые переменные: {len(new_tags)}')


def create_output_file(kaskad_module: KlogicXML or AlarmsXML or KloggerXML, filename: str) -> OutputFiles:
    output_file = BytesIO()
    kaskad_module.write(output_file)
    return OutputFiles(
            name=filename,
            file=output_file.getbuffer()
        )


def create_shift_output_file(klogic_xml):
    return OutputFiles(
        name='Смещение.txt',
        file=shift_create(klogic_xml).getbuffer()
    )


def update_klogic_xml(klogic_xml):
    klogic_xml.delete_empty_groups()
    klogic_xml.delete_tags(Tag.get_bad_tags())
    klogic_xml.add_comment()
    klogic_xml.set_noffl(Tag.get_tags_values())


def update_klogger_xml(klogger_xml: KloggerXML, klogic_xml: KlogicXML) -> str:
    logger.debug(klogger_xml.db_version.tag)
    klogger_xml.delete_old_config()
    return klogger_xml.set_klogger_xml(klogic_xml.module, Tag.get_bdtp_tags())


def update_alarms_xml(alarm_xml: AlarmsXML, klogic_xml: KlogicXML) -> str:
    logger.debug(alarm_xml.group_item.tag)
    return alarm_xml.set_alarm_xml(klogic_xml.module, Tag.get_tags_values())


def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
    for file in files:
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr(file.name, file.file)
    return zip_buffer


def index(request):
    output_files = []

    if request.method == 'POST':
        form = KlogicForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            context['text_error'] = False
            station_id = form.cleaned_data['station']
            bdtp_checkbox, alarm_checkbox = get_checkboxes(form)
            klogic_xml, xml_filename = get_klogic_input_file(form)
            gm = str(klogic_xml.klogic_tree_find().gm.text)
            try:
                new_tags = get_new_tags(klogic_xml)
                if len(new_tags):
                    save_new_tags(new_tags)
                else:
                    update_klogic_xml(klogic_xml)
                    output_files.append(create_output_file(klogic_xml, xml_filename))
                    output_files.append(create_shift_output_file(klogic_xml))
                    context['text_kl'] = "klogic XML: Обработка завершена"
                    if bdtp_checkbox:
                        logger.debug('bdtp_checkbox:')
                        logger.debug(bdtp_checkbox)
                        klogger_xml, klogger_xml_filename = get_klogger_input_file(form, klogic_xml, station_id)
                        try:
                            context['text_bdtp'] = update_klogger_xml(klogger_xml, klogic_xml)
                            output_files.append(create_output_file(klogger_xml, klogger_xml_filename))
                        except AttributeError:
                            raise KloggerBadFormatError('Klogger XML: Неправильный формат')
                    if alarm_checkbox:
                        logger.debug('alarm_checkbox:')
                        logger.debug(alarm_checkbox)
                        alarm_xml, alarm_xml_filename = get_alarms_input_file(klogic_xml, station_id)
                        try:
                            context['text_al'] = update_alarms_xml(alarm_xml, klogic_xml)
                            output_files.append(create_output_file(alarm_xml, alarm_xml_filename))
                        except AttributeError:
                            raise AlarmsBadFormatError('Alarm XML: Неправильный формат')
                        except ErrorMissingProduct as e:
                            context['text_error'] = e

                    logger.debug(context)

            except (
                    KlogicBadFormatError,
                    KloggerBadFormatError,
                    AlarmsBadFormatError,
                    DefaultAlarmError,
                    IndexError,
                    NotEnoughVar,
                    ErrorMissingNofflTag,
                    NewTagsError
            ) as msg:
                context['text_error'] = msg

            if not context['text_error']:
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
