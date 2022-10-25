import logging
import pathlib
import datetime
import os
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .klogic_xml import KlogicAttrs
from .alrm import alrm, stations
from .indices import indices as i, constants as c, xo_types


@dataclass
class CutoutAttrs:
    cutout: str
    xo_type: str


@dataclass
class AlarmTagAttrs:
    group: int
    in_out: Element
    tag: dict
    id: int
    alarm_flag: bool
    alarm_number: int
    tag_settings: Element
    tag_name: str
    contr: str
    tag_full_name: str


@dataclass
class AlarmAttrs:
    id: str
    text: str


class AlarmTag:
    """ Класс для аварийного параметра"""

    def __init__(self, alarm_tag_attrs: AlarmTagAttrs):
        self.alarm_tag_attr = alarm_tag_attrs


class ErrorMissingProduct(Exception):
    """ Исключение при отсутствующих тегах nofll у контроллера"""


def tree_insert(parent_group: Element, insert_index: int, child_group: str, text):
    child = ElementTree.Element(child_group)
    if text:
        child.text = text
    parent_group.insert(insert_index, child)


def get_measure_units(in_out: Element):
    try:
        measure_units = in_out.attrib['MeasU']
    except KeyError:
        measure_units = False
    return measure_units


def get_klogic_id(tag_settings: Element) -> str:
    kid = ''
    for setting in tag_settings.iter('KId'):
        kid = setting.text
    return kid


def get_value_type(tag_settings: Element) -> int:
    value_type = 1
    for setting in tag_settings.iter('PropList'):
        if setting.attrib['TagType'] == 'B':
            value_type = 2
    return value_type


def mark_group_not_for_del(group: Element):
    """Добавление исключения для не удаления пустой группы"""
    if all([
        group[i.group_name].text == 'Авария всех компрессоров',
        group[i.group_alarms].tag != f'tempAlarms'
    ]):
        tree_insert(group, i.group_alarms, 'tempAlarms', False)


def get_measure_units_index(alarm_tag: AlarmTag) -> int:
    """Получение индекса для группы MeasureUnits"""
    index = 3
    if not get_measure_units(alarm_tag.alarm_tag_attr.in_out):
        index = 2
    return index


def get_central_tags(tags: Iterable) -> list:
    central_tags = []
    for tag in tags:
        if tag['alarm_id'] == 'central':
            central_tags.append(tag)
    return central_tags


class AlarmsXML:
    """ Класс для  AlarmsXML"""

    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int, products: Iterable):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.alarm_root = self.parsed_xml.getroot()
        self.group_item = self.parsed_xml.find('.//GroupItem')
        self.station_id = station_id
        self.products = products
        self.klogic_name = kl_find.klogic_name
        self.protocol_name = kl_find.protocol_name
        self.gm = kl_find.gm
        self.syst_num = kl_find.syst_num
        self.tag_id_in_alarms = 1
        self.central_contr = False
        self.new_product = set()
        self.all_tag_alrm_id = []
        self.station_name = self.get_station_name()
        self.logger = logging.getLogger(__name__)

    def rename_main_group(self):
        """Переименование корневой группы"""
        all_group_name = self.parsed_xml.findall('.//GroupName')
        for group in all_group_name:
            if group.text == 'gm_name_insert':
                group.text = f'{self.gm.text}'

    def check_cutout(self, product_name: str) -> str:
        """Получение значения уставки для продукта"""
        cutout = ''
        for product in self.products:
            if product_name == product['name']:
                cutout = product['cutout']
                break
            else:
                cutout = str(c.new_product_cutout)
        return cutout

    def cutout(self, contr: str) -> CutoutAttrs:
        """Получение значения уставки и типа оборудования для контроллера"""
        result = CutoutAttrs(
            cutout=str(c.new_product_cutout),
            xo_type='None'
        )
        name = contr.split('__')[i.contr_name]
        try:
            result.xo_type = name.split('_')[i.xo_type]
            product = name.split('_')[i.product]
            if result.xo_type in xo_types.nt:
                result.cutout = str(c.nt_cutout)
            else:
                for prod in self.products:
                    if name == prod['name']:
                        result.cutout = prod['cutout']
                        break
                    else:
                        if result.xo_type in xo_types.stk:
                            result.cutout = str(c.stk_cutout)
                        else:
                            if result.xo_type in xo_types.ceh:
                                result.cutout = str(c.ceh_cutout)
                            else:
                                result.cutout = self.check_cutout(product)
        except IndexError:
            for prod in self.products:
                if name == prod['name']:
                    result = CutoutAttrs(
                        cutout=str(c.server_cutout),
                        xo_type=prod['xo_type']
                    )
        return result

    def check_central(self, element: Element, central_tags: list):
        """Определение контроллера, как контроллер централи"""
        self.central_contr = False
        for in_out in element[i.first_tag:]:
            if self.central_contr:
                break
            else:
                for central_tag in central_tags:
                    if in_out.attrib['Name'] == central_tag['name']:
                        self.central_contr = True
                        break

    def get_station_name(self) -> str:
        """Получение названия станции"""
        station_name = ''
        for station in stations:
            if self.station_id == station[i.alrm_code]:
                station_name = station[i.alrm_text]
        return f'{station_name}\\{self.klogic_name.text}'

    def set_tag_full_name(self, module: Element, attrs: AlarmTagAttrs) -> str:
        """Формирование строки FullName"""
        in_out = attrs.in_out
        if not attrs.alarm_flag:
            attrs.contr = str(module[attrs.group].attrib['Name'])
            attrs.tag_name = attrs.in_out.attrib['Name']
        else:
            attrs.tag_settings = in_out[attrs.alarm_number][i.settings]
            attrs.tag_name = in_out[attrs.alarm_number].attrib['Name']
            attrs.contr = str(module[attrs.group].attrib['Name'] + '\\' + 'Alarms')
        attrs.tag_full_name = f'{self.klogic_name.text}.{self.protocol_name.text}.{self.gm.text}.{attrs.contr}.{attrs.tag_name}'
        return attrs.tag_full_name

    def get_tag_alarm_attrs(self, alarm_tag: AlarmTag) -> AlarmAttrs:
        """Получение необходимых атрибутов аварийной группы: определение в какую группу добавить тег"""
        tag_alarm = ''
        for group in alrm:
            if any([
                group[i.alrm_code] == 'Уставки',
                group[i.alrm_code] == 'Потребители',
                group[i.alrm_code] == 'Централи'
            ]):
                for alarm in group[i.alrm_text]:
                    if alarm_tag.alarm_tag_attr.tag['alarm_id'] == alarm[i.alrm_code]:
                        tag_alarm = alarm[i.alrm_text]
            else:
                if alarm_tag.alarm_tag_attr.tag['alarm_id'] == group[i.alrm_code]:
                    tag_alarm = group[i.alrm_text]

        tag_alarm_id = alarm_tag.alarm_tag_attr.tag['alarm_id']
        xo_type = self.cutout(alarm_tag.alarm_tag_attr.contr).xo_type
        if all([
            tag_alarm_id == 'A1',
            xo_type in xo_types.a1k
        ]):
            tag_alarm = 'A1. Высокая температура К'
            tag_alarm_id = f'{tag_alarm_id}K'

        if tag_alarm_id == 'Cutout':
            cutout = self.cutout(alarm_tag.alarm_tag_attr.contr).cutout
            tag_alarm = f'{cutout}c'
            tag_alarm_id = f'{tag_alarm_id}{tag_alarm}'
            if cutout == str(c.new_product_cutout):
                self.new_product.add(alarm_tag.alarm_tag_attr.contr)
        else:
            if tag_alarm_id == 'A13-high-lim-air':
                cutout = self.cutout(alarm_tag.alarm_tag_attr.contr).cutout
                tag_alarm = f'{cutout}a'
                tag_alarm_id = f'{tag_alarm_id}{tag_alarm}'
                if cutout == str(c.new_product_cutout):
                    self.new_product.add(alarm_tag.alarm_tag_attr.contr)

        return AlarmAttrs(
            id=tag_alarm_id,
            text=tag_alarm
        )

    def insert_alarms_group(self, group: Element, attrs: AlarmAttrs):
        """Добавление группы Alarms с идентификатором аварии"""
        if group[i.group_alarms].tag != f'{attrs.id}Alarms':
            tree_insert(group, i.group_alarms, f'{attrs.id}Alarms', False)
            self.all_tag_alrm_id.append(attrs.id)

    def check_group_item(self, group: Element, attrs: AlarmAttrs) -> bool:
        """Поиск аварийной группы"""
        alarm_group_find = False
        if group[i.group_name].text == attrs.text:
            alarm_group_find = True
            self.insert_alarms_group(group, attrs)
        return alarm_group_find

    def set_alarm_tag(self, group: int, in_out: Element, tag: dict) -> AlarmTag:
        """Создание аварийного тега"""
        alarm_tag_attrs = AlarmTagAttrs(
            group=group,
            in_out=in_out,
            tag=tag,
            id=self.tag_id_in_alarms,
            alarm_flag=False,
            alarm_number=0,
            tag_settings=in_out[i.settings],
            tag_name='',
            contr='',
            tag_full_name=''
        )
        alarm_tag = AlarmTag(alarm_tag_attrs)
        self.tag_id_in_alarms += 1
        return alarm_tag

    def alarm_insert(self, module: Element, alarm_tag: AlarmTag):
        """Вставка строк в alarms.xml"""
        measure_units = get_measure_units(alarm_tag.alarm_tag_attr.in_out)
        mu_index = get_measure_units_index(alarm_tag)
        alarm_tag_full_name = self.set_tag_full_name(module, alarm_tag.alarm_tag_attr)
        kid = get_klogic_id(alarm_tag.alarm_tag_attr.tag_settings)
        value_type = get_value_type(alarm_tag.alarm_tag_attr.tag_settings)
        string_id = f'Kl\\st{self.station_id}\\Cn{self.syst_num.text}\\{self.protocol_name.text}\\{self.gm.text}\\{alarm_tag.alarm_tag_attr.contr}\\\\{alarm_tag.alarm_tag_attr.tag_name}'
        alarm_attrs = self.get_tag_alarm_attrs(alarm_tag)

        group_item = self.parsed_xml.findall('.//GroupItem')
        for group in group_item:
            mark_group_not_for_del(group)
            if self.check_group_item(group, alarm_attrs):
                self.logger.debug(alarm_attrs.text)
                self.logger.debug(string_id)
                tree_insert(self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms'), i.alarm_index, 'Alarm',
                            False)
                parent_group = self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms/Alarm')
                tree_insert(parent_group, i.alarm_id, 'ID', f'{alarm_tag.alarm_tag_attr.id}')
                tree_insert(parent_group, i.group_name, 'Name', f'{alarm_tag.alarm_tag_attr.tag_name}')
                tree_insert(parent_group, i.full_name, 'FullName',
                            f'{alarm_tag_full_name}'.replace('\\', '.'))
                if measure_units:
                    tree_insert(parent_group, mu_index, 'MeasureUnits', f'{measure_units}')
                tree_insert(parent_group, mu_index + 1, 'ZoneName', f'{self.klogic_name.text}')
                tree_insert(parent_group, mu_index + 2, 'StationName', f'{self.station_name}')
                tree_insert(parent_group, mu_index + 3, 'Passport', False)
                passport_group = self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms/Alarm/Passport')
                tree_insert(passport_group, i.station_id, 'StationID', f'{self.station_id}')
                tree_insert(passport_group, i.passport_type, 'PassportType', '222')
                tree_insert(passport_group, i.group_id, 'GroupID', f'{self.syst_num.text}')
                tree_insert(passport_group, i.passport_id, 'PassportID', f'{kid}')
                tree_insert(passport_group, i.value_type, 'ValueType', f'{value_type}')
                tree_insert(parent_group, mu_index + 4, 'StringID', f'{string_id}')

    def delete_empty_groups(self):
        """Удаление пустых групп"""
        alarms_groups = self.alarm_root.findall('.//Children')
        for group in alarms_groups:
            item = 0
            while item < len(group):
                if len(group[item]) < i.empty_group_len:
                    group.remove(group[item])
                else:
                    item += 1

    def remove_service_attrs(self, parent_group: str, group_name: str, iterables: Iterable):
        """Удаление служебных символов в названии групп"""
        for index in iterables:
            for parent in self.parsed_xml.findall(parent_group):
                for child in parent:
                    child.tag = child.tag.replace(f'{index}{group_name}', f'{group_name}')
                    child.tag = child.tag.replace('tempAlarms', 'Alarms')

    def set_alarm_xml(self, module: Element, tags: Iterable):
        """Формирование alarms.xml"""
        self.rename_main_group()
        central_tags = get_central_tags(tags)
        for group in range(len(module))[i.first_contr:]:
            cutout_flag = False
            self.check_central(module[group], central_tags)
            for in_out in module[group][i.first_tag:]:
                for tag in tags:

                    if in_out.attrib['Name'] == 'Alarms':
                        for alarm_number in range(len(in_out))[i.first_tag:]:
                            if all([
                                in_out[alarm_number].attrib['Name'].split(f'{alarm_number}_')[i.alarm_split] == tag[
                                    'name'],
                                tag['alarm_id'] != 'None',
                                tag['alarm_id'] != '0'
                            ]):
                                alarm_tag = self.set_alarm_tag(group, in_out, tag)
                                alarm_tag.alarm_tag_attr.alarm_flag = True
                                alarm_tag.alarm_tag_attr.alarm_number = alarm_number
                                self.alarm_insert(module, alarm_tag)

                    if all([
                        in_out.attrib['Name'] == tag['name'],
                        tag['alarm_id'] != 'None',
                        tag['alarm_id'] != '0'
                    ]):
                        alarm_tag = self.set_alarm_tag(group, in_out, tag)
                        if tag['alarm_id'] == 'r12':
                            if self.central_contr:
                                self.alarm_insert(module, alarm_tag)
                        else:
                            if tag['alarm_id'] == 'A03-alarm-delay':
                                if not self.central_contr:
                                    self.alarm_insert(module, alarm_tag)
                            else:
                                if tag['alarm_id'] == 'Cutout' and not cutout_flag:
                                    self.alarm_insert(module, alarm_tag)
                                    cutout_flag = True
                                else:
                                    if tag['alarm_id'] != 'Cutout':
                                        self.alarm_insert(module, alarm_tag)

        self.delete_empty_groups()
        self.remove_service_attrs('.//GroupItem', 'Alarms', self.all_tag_alrm_id)

        if len(self.new_product):
            raise ErrorMissingProduct(f'Alarm XML: Новый вид продукта: {self.new_product}')
            # return "Alarm XML: Новый вид продукта" + f'{self.new_product}'
        else:
            return "Alarm XML: Обработка завершена"

    def write(self, xml_path):
        self.parsed_xml.write(xml_path, encoding='UTF-8')
