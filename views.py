import shutil, pathlib
from django.shortcuts import render
from django.db.models.query import QuerySet
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import ElementTree as ET_class
from .models import history_attr, GoodTags, BadTags, klogic, klogger, alarms, Cutout, NewTags, Shift
from .forms import KlogicForm
from .alrm import alrm, stations
from .klogic_xml import KlogicXML


def get_tags() -> set:
    exist_tags = set()
    for tag in GoodTags.get_GoodTagsall():
        exist_tags.add(tag.Name)
    for tag in BadTags.get_BadTagsall():
        exist_tags.add(tag.Name)
    return exist_tags


def get_tags_ids() -> set:
    '''Получение всех id из GoodTags, BadTags, NewTags'''
    exist_ids = set()
    for id in GoodTags.get_all_id() | BadTags.get_all_id():
        exist_ids.add(id)
    return exist_ids


def shift_create(klogic_xml: KlogicXML, gmget: str):
    '''Подсчет смещения адресов контроллеров'''
    try:
        old_shift = Shift.objects.get(gm=gmget)
        old_shift.delete()
    except Shift.DoesNotExist:
        pass
    shift_attr = klogic_xml.shift()
    Shift.objects.create(gm=gmget, txt="media/shift/" + str(gmget) + ".txt")
    txt = Shift.objects.get(gm=gmget).txt.path
    file = open(str(txt), "w+")
    for l in shift_attr.all_lens:
        address = 0
        for a in range(len(shift_attr.all_attrs)):
            if shift_attr.all_attrs[a][1] == l:
                if address == 0:
                    current_shift = 0
                    address = float(shift_attr.all_attrs[a][3])
                else:
                    current_shift = float(shift_attr.all_attrs[a][3]) - address
                    address = float(shift_attr.all_attrs[a][3])
                file.write(('Кол-во переменных = ' + str(l) + '. ' +
                            str(shift_attr.all_attrs[a][0]) + '. Смещение = ' + str(current_shift) + '\n'))
    file.close()


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
                NewTags.delete_NewTagsall()
                new_tags = klogic_xml.new_tags(get_tags(), get_tags_ids())
            except AttributeError:
                context['text_kl'] = "Klogic XML: Неправильный формат"
        except (klogic.DoesNotExist, FileNotFoundError):
            context['text_kl'] = "Klogic XML не найден"

        if len(new_tags) > 0:
            for tag in new_tags:
                new_tag = NewTags(id=tag.tag_id, Name=tag.tag_name, Controller=tag.controller)
                new_tag.save()
            context['text'] = "Новые переменные:"
            context['len_new_tags'] = len(new_tags)
        else:
            if new_tags == -1:
                context['text'] = "В группе Alarms у централи добавлены не все переменные"
            else:
                klogic_xml.delete_tags(BadTags.get_BadTagsall())
                klogic_xml.add_comment()
                klogic_xml.noffl(GoodTags.get_noffl_tags())
                klogic_xml.write()
                shift_create(klogic_xml, gmget)
                #klogic_xml.shift(gmget)
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
