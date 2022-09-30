import shutil, pathlib
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import ElementTree as ET_class
from .models import history_attr, GoodTags, klogic, klogger, alarms, Cutout
from .forms import KlogicForm
from .alrm import alrm, stations
from .klogic_xml import KlogicXML


def index(request):
    form = KlogicForm()
    context = {'form': form}
    if request.method == 'POST':
        gmget = request.POST.get('gm')
        context['gm'] = gmget
        try:
            xml_path = klogic.objects.get(gm=gmget).xml.path
            klogic_xml = KlogicXML(xml_path)
            klogic_xml.h_remove(history_attr.get_h_attrs())
            # bdtp_checkbox = request.POST.get('bd')
            # alarm_checkbox = request.POST.get('alarm')
            # tree = ElementTree.parse(xml_path)
            # Module = tree.find('.//Module')
            try:
                print(klogic_xml.module.tag)
                len_new_tags = klogic_xml.new_tags()
            except AttributeError:
                context['text_kl'] = "Klogic XML: Неправильный формат"
        except (ObjectDoesNotExist, FileNotFoundError):
            context['text_kl'] = "Klogic XML не найден"

        if len_new_tags > 0:
            context['text'] = "Новые переменные:"
            context['len_new_tags'] = len_new_tags
        else:
            if len_new_tags == -1:
                context['text'] = "В группе Alarms у централи добавлены не все переменные"
            else:
                klogic_xml.delete_tags()
                klogic_xml.add_comment()
                klogic_xml.noffl()
                klogic_xml.write()
                klogic_xml.shift(gmget)
                # if bdtp_checkbox:
                #     print('bdtp_checkbox:', bdtp_checkbox)
                #     try:
                #         klogger_xml = klogger.objects.get(gm=gmget).xml.path
                #         klogger_tree = ElementTree.parse(klogger_xml)
                #         DBVersion = klogger_tree.find('.//DBVersion')
                #         try:
                #             print(DBVersion.tag)
                #             #context['text_bdtp'] = bdtp(gmget, tree, Module, klogger_xml, klogger_tree)
                #         except AttributeError:
                #             context['text_bdtp'] = "Klogger XML: Неправильный формат"
                #     except (ObjectDoesNotExist, FileNotFoundError):
                #         context['text_bdtp'] = "Klogger XML не найден"
                # if alarm_checkbox:
                #     print('alarm_checkbox:', alarm_checkbox)
                #     try:
                #         alarm_xml = alarms.objects.get(gm='default_alarm_xml').xml.path
                #         alarm_tree = ElementTree.parse(alarm_xml)
                #         GroupItem = alarm_tree.find('.//GroupItem')
                #         try:
                #             print(GroupItem.tag)
                #             #context['text_al'] = alarm(gmget, tree, Module, alarm_xml)
                #         except AttributeError:
                #             context['text_al'] = "Alarm XML: Неправильный формат"
                #     except (ObjectDoesNotExist, FileNotFoundError):
                #         context['text_al'] = "Alarm XML не найден"

                context['text_kl'] = "Klogic XML: Обработка завершена"

    return render(request, 'xoxml/index.html', context)
