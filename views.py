import shutil, pathlib
from pathlib import Path
from django.shortcuts import render
from django.db.models.query import QuerySet
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import ElementTree as ET_class
from .models import history_attr, GoodTags, BadTags, klogic, klogger, alarms, Cutout, NewTags, Shift
from .forms import KlogicForm
from .alrm import alrm, stations
from .klogic_xml import KlogicXML


def get_tags() -> Iterable:
    exist_tags = []
    for tag in GoodTags.get_GoodTags_values():
        exist_tags.append(tag)
    for tag in BadTags.get_BadTags_values():
        tag['alarm_id'] = 'None'
        tag['bdtp'] = False
        tag['noffl'] = False
        exist_tags.append(tag)
    return exist_tags


def shift_create(klogic_xml: KlogicXML, gmget: str):
    '''Подсчет смещения адресов контроллеров'''
    ATTR_NAME_INDEX = 0
    ATTR_LEN_INDEX = 1
    ATTR_ADR_INDEX = 3

    if Shift.objects.filter(gm=gmget).exists():
        Shift.objects.filter(gm=gmget).delete()

    shift_attr = klogic_xml.shift()
    Shift(gm=gmget, txt=f"media/shift/{gmget}.txt").save()
    txt = Shift.objects.get(gm=gmget).txt
    with open(txt.path, "w+") as file:
        for l in shift_attr.all_lens:
            address = 0
            for i, _ in enumerate(shift_attr.all_attrs):
                if shift_attr.all_attrs[i][ATTR_LEN_INDEX] != l:
                    continue
                current_shift = (
                    float(shift_attr.all_attrs[i][ATTR_ADR_INDEX]) - address
                    if i and address else 0
                )
                address = float(shift_attr.all_attrs[i][ATTR_ADR_INDEX])
                file.write(
                    f'Кол-во переменных = {l}. {shift_attr.all_attrs[i][ATTR_NAME_INDEX]}. Смещение = {current_shift} \n')


def index(request):
    form = KlogicForm()
    context = {'form': form}
    if request.method == 'POST':
        gmget = request.POST.get('gm')
        context['gm'] = gmget
        try:
            xml_path = klogic.objects.get(gm=gmget).xml.path
            klogic_xml = KlogicXML(xml_path)
            # bdtp_checkbox = request.POST.get('bd')
            # alarm_checkbox = request.POST.get('alarm')
            # tree = ElementTree.parse(xml_path)
            try:
                klogic_xml.find_danfoss_module()
                print(klogic_xml.module.tag)
                klogic_xml.h_remove(history_attr.get_h_attrs())
                NewTags.delete_NewTagsall()
                new_tags = klogic_xml.new_tags(get_tags())
                # Module = klogic_xml.module
            except AttributeError:
                context['text_kl'] = "Klogic XML: Неправильный формат"
        except (klogic.DoesNotExist, FileNotFoundError):
            context['text_kl'] = "Klogic XML не найден"

        if len(new_tags):
            for tag in new_tags:
                new_tag = NewTags(id=tag.tag_id, name=tag.tag_name, Controller=tag.controller)
                new_tag.save()
            context['text'] = "Новые переменные:"
            context['len_new_tags'] = len(new_tags)
        else:
            if new_tags == -1:
                context['text'] = "В группе Alarms у централи добавлены не все переменные"
            else:
                klogic_xml.delete_tags(BadTags.get_BadTags_values())
                klogic_xml.add_comment()
                klogic_xml.noffl(GoodTags.get_GoodTags_values())
                klogic_xml.write('')
                shift_create(klogic_xml, gmget)
                # if bdtp_checkbox:
                #     print('bdtp_checkbox:', bdtp_checkbox)
                #     try:
                #         klogger_xml = klogger.objects.get(gm=gmget).xml.path
                #         klogger_tree = ElementTree.parse(klogger_xml)
                #         DBVersion = klogger_tree.find('.//DBVersion')
                #         try:
                #             print(DBVersion.tag)
                #             context['text_bdtp'] = bdtp(gmget, tree, Module, klogger_xml, klogger_tree)
                #         except AttributeError:
                #             context['text_bdtp'] = "Klogger XML: Неправильный формат"
                #     except (klogger.DoesNotExist, FileNotFoundError):
                #         context['text_bdtp'] = "Klogger XML не найден"
                # if alarm_checkbox:
                #     print('alarm_checkbox:', alarm_checkbox)
                #     try:
                #         alarm_xml = alarms.objects.get(gm='default_alarm_xml').xml.path
                #         alarm_tree = ElementTree.parse(alarm_xml)
                #         GroupItem = alarm_tree.find('.//GroupItem')
                #         try:
                #             print(GroupItem.tag)
                #             context['text_al'] = alarm(gmget, tree, Module, alarm_xml)
                #         except AttributeError:
                #             context['text_al'] = "Alarm XML: Неправильный формат"
                #     except (alarms.DoesNotExist, FileNotFoundError):
                #         context['text_al'] = "Alarm XML не найден"

                context['text_kl'] = "Klogic XML: Обработка завершена"

    return render(request, 'xoxml/index.html', context)
