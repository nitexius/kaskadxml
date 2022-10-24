import io
import logging
import datetime
import os
import zipfile
from django.http import FileResponse, HttpResponse
from pathlib import Path
from io import BytesIO
from typing import Iterable, List
from dataclasses import dataclass
from django.shortcuts import render
from .forms import KlogicForm
from .kaskad_xml import AlarmsXML, KloggerXML, KlogicXML, ErrorMissingNofflTag, ErrorMissingProduct
from .models import HistoryAttr, GoodTags, BadTags, Alarms, Cutout, NewTags


@dataclass
class OutputFiles:
    name: str
    file: bytes


def get_tags() -> Iterable:
    exist_tags = []
    for tag in GoodTags.get_good_tags_values():
        exist_tags.append(tag)
    for tag in BadTags.get_bad_tags_values():
        tag['alarm_id'] = 'None'
        tag['bdtp'] = False
        tag['noffl'] = False
        exist_tags.append(tag)
    return exist_tags


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


def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
    for file in files:
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr(file.name, file.file)
    return zip_buffer


def index(request):
    logger = logging.getLogger(__name__)
    output_files = []
    form = KlogicForm()
    context = {'form': form}

    if request.method == 'POST':
        station_id = request.POST.get('station')
        xml_file = request.FILES['klogic_file'].read()
        xml_filename = request.FILES['klogic_file'].name
        bdtp_checkbox = request.POST.get('bd')
        alarm_checkbox = request.POST.get('alarm')

        klogic_input_file = BytesIO(xml_file)
        klogic_input_file.seek(0)

        klogic_xml = KlogicXML(klogic_input_file, prot_code='244')
        try:
            context['text_error'] = False
            klogic_xml.find_module()
            logger.debug(klogic_xml.module.tag)
            klogic_xml.h_remove(HistoryAttr.get_h_attrs())
            NewTags.delete_new_tags_all()
            new_tags = klogic_xml.set_new_tags(get_tags())
        except AttributeError:
            context['text_kl'] = "Klogic XML: Неправильный формат"

        if new_tags == -1:
            context['text_error'] = "В группе Alarms у централи добавлены не все переменные"
        else:
            if len(new_tags):
                for tag in new_tags:
                    new_tag = NewTags(id=tag.tag_id, name=tag.tag_name, Controller=tag.controller)
                    new_tag.save()
                context['text'] = "Новые переменные:"
                context['len_new_tags'] = len(new_tags)
            else:
                klogic_xml.delete_empty_groups()
                klogic_xml.delete_tags(BadTags.get_bad_tags_values())
                klogic_xml.add_comment()
                gm = klogic_xml.klogic_tree_find().gm.text
                try:
                    klogic_xml.set_noffl(GoodTags.get_good_tags_values())
                    context['text_kl'] = "klogic XML: Обработка завершена"
                except ErrorMissingNofflTag as e:
                    context['text_error'] = e
                klogic_output_file = BytesIO()
                klogic_xml.write(klogic_output_file)
                output_files.append(OutputFiles(
                    name=xml_filename,
                    file=klogic_output_file.getbuffer()
                ))

                shift = shift_create(klogic_xml)
                output_files.append(OutputFiles(
                    name='Смещение.txt',
                    file=shift.getbuffer()
                ))
                if bdtp_checkbox:
                    klogger_xml_file = request.FILES['klogger_file'].read()
                    klogger_xml_filename = request.FILES['klogger_file'].name
                    logger.debug('bdtp_checkbox:')
                    logger.debug(bdtp_checkbox)
                    klogger_input_file = BytesIO(klogger_xml_file)
                    klogger_input_file.seek(0)
                    klogger_xml = KloggerXML(klogger_input_file, klogic_xml.klogic_tree_find(), station_id)
                    try:
                        logger.debug(klogger_xml.db_version.tag)
                        klogger_xml.delete_old_config()
                        context['text_bdtp'] = klogger_xml.set_klogger_xml(klogic_xml.module,
                                                                           GoodTags.get_bdtp_tags())
                        klogger_output_file = BytesIO()
                        klogger_xml.write(klogger_output_file)
                        output_files.append(OutputFiles(
                            name=klogger_xml_filename,
                            file=klogger_output_file.getbuffer()
                        ))
                    except AttributeError:
                        context['text_bdtp'] = "Klogger XML: Неправильный формат"
                if alarm_checkbox:
                    context['text_al'] = False
                    logger.debug('alarm_checkbox:')
                    logger.debug(alarm_checkbox)
                    try:
                        default_alarm_xml_path = Alarms.objects.get(gm='default_alarm_xml').xml.path
                        alarm_xml = AlarmsXML(
                            default_alarm_xml_path,
                            klogic_xml.klogic_tree_find(),
                            station_id,
                            Cutout.get_products_values()
                        )
                        try:
                            logger.debug(alarm_xml.group_item.tag)
                            context['text_al'] = alarm_xml.set_alarm_xml(klogic_xml.module,
                                                                         GoodTags.get_good_tags_values())
                            new_alarm_xml = BytesIO()
                            alarm_xml.write(new_alarm_xml)
                            output_files.append(OutputFiles(
                                name='Alarms.xml',
                                file=new_alarm_xml.getbuffer()
                            ))
                        except AttributeError:
                            context['text_al'] = "Alarm XML: Неправильный формат"
                        except ErrorMissingProduct as e:
                            context['text_error'] = e
                    except (Alarms.DoesNotExist, FileNotFoundError):
                        context['text_al'] = "Alarm XML не найден"

                logger.debug(context)
                if not context['text_error']:
                    zip_buffer = set_arch(BytesIO(), output_files)
                    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=output.zip'
                    return response

    return render(request, 'xoxml/index.html', context)
