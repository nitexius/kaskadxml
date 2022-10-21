import logging
import datetime
import os
import zipfile
from django.http import FileResponse
from pathlib import Path
from io import BytesIO
from typing import Iterable
from django.shortcuts import render
from .forms import KlogicForm
from .kaskad_xml import AlarmsXML, KloggerXML, KlogicXML, ErrorMissingNofflTag
from .models import HistoryAttr, GoodTags, BadTags, Alarms, Cutout, NewTags


def set_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = f'{base_dir}/kaskadxml/logs/{datetime.date.today()}'
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    log_path = f'{log_dir}/views_logging.log'
    logger_handler = logging.FileHandler(log_path)
    logger_handler.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter('%(asctime)s %(message)s')
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)
    return logger


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


def index(request):
    logger = set_logging()
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
            klogic_xml.find_module()
            logger.debug(klogic_xml.module.tag)
            klogic_xml.h_remove(HistoryAttr.get_h_attrs())
            NewTags.delete_new_tags_all()
            new_tags = klogic_xml.set_new_tags(get_tags())
        except AttributeError:
            context['text_kl'] = "Klogic XML: Неправильный формат"

        if new_tags == -1:
            context['text'] = "В группе Alarms у централи добавлены не все переменные"
        else:
            if len(new_tags):
                for tag in new_tags:
                    new_tag = NewTags(id=tag.tag_id, name=tag.tag_name, Controller=tag.controller)
                    new_tag.save()
                context['text'] = "Новые переменные:"
                context['len_new_tags'] = len(new_tags)
            else:
                context['text_kl'] = "Klogic XML: Обработка завершена"
                klogic_xml.delete_empty_groups()
                klogic_xml.delete_tags(BadTags.get_bad_tags_values())
                klogic_xml.add_comment()
                gm = klogic_xml.klogic_tree_find().gm.text
                try:
                    klogic_xml.set_noffl(GoodTags.get_good_tags_values())
                except ErrorMissingNofflTag:
                    context['text_kl'] = 'Klogic XML: У контроллеров не заданы параметры для ФБ noffl'

                klogic_output_file = BytesIO()
                klogic_xml.write(klogic_output_file)

                with zipfile.ZipFile(f'{gm}.zip', 'a') as zip_file:
                    zip_file.writestr(xml_filename, klogic_output_file.getbuffer())

                shift = shift_create(klogic_xml)
                with zipfile.ZipFile(f'{gm}.zip', 'a') as zip_file:
                    zip_file.writestr('Смещение.txt', shift.getbuffer())

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
                        with zipfile.ZipFile(f'{gm}.zip', 'a') as zip_file:
                            zip_file.writestr(klogger_xml_filename, klogger_output_file.getbuffer())
                    except AttributeError:
                        context['text_bdtp'] = "Klogger XML: Неправильный формат"
                if alarm_checkbox:
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
                            with zipfile.ZipFile(f'{gm}.zip', 'a') as zip_file:
                                zip_file.writestr('Alarms.xml', new_alarm_xml.getbuffer())
                        except AttributeError:
                            context['text_al'] = "Alarm XML: Неправильный формат"
                    except (Alarms.DoesNotExist, FileNotFoundError):
                        context['text_al'] = "Alarm XML не найден"

                return FileResponse(open(f'{gm}.zip', 'rb'), as_attachment=True)

    return render(request, 'xoxml/index.html', context)
