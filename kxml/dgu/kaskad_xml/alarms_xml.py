import logging
import pathlib
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from .alrm import alrm, stations
from .indices import indices as i, constants as c
from .klogic_xml import KlogicXML
from kaskadxml.kaskad_xml import  (
    KlogicAttrs,
    AlarmTagAttrs,
    AlarmAttrs,
)


class AlarmTag:
    """ Класс для аварийного параметра"""
    def __init__(self, alarm_tag_attrs: AlarmTagAttrs):
        self.alarm_tag_attr = alarm_tag_attrs


def get_child_group(child_group: str, text) -> Element:
    """ Поиск группы для вставки """
    child = ElementTree.Element(child_group)
    if text:
        child.text = text
    return child


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
        if setting.attrib['MIBType'] == '1':
            value_type = 2
    return value_type


def get_measure_units_index(alarm_tag: AlarmTagAttrs) -> int:
    """ Получение индекса для группы MeasureUnits """
    return (
        i.me_not_exist
        if not get_measure_units(alarm_tag.in_out) else i.me_exist
    )


def set_group_element(element, name: str):
    """ Получение группы искомой GroupItem """
    group_items = element.findall('.//GroupItem')
    for group_item in group_items:
        if group_item[i.group_name].text == name:
            return group_item


def set_tag_full_name(alarm_tag):
    tag_full_name = ''
    for setting in alarm_tag.in_out[i.settings].iter('Description'):
        tag_full_name = setting.text
    return tag_full_name


class AlarmsXML:
    """ Класс для  AlarmsXML"""

    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int):
        self.xml_path = xml_path
        self.xml_file_name = 'Alarms.xml'
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.temp_groups = ElementTree.parse(self.xml_path)
        self.temp_xmls = {}
        self.alarm_root = self.parsed_xml.getroot()
        self.group_item = self.parsed_xml.find('.//GroupItem')
        self.group_gm = None
        self.group_ids = set()
        self.station_id = station_id
        self.klogic_name = kl_find.klogic_name
        self.protocol_name = kl_find.protocol_name
        self.syst_num = kl_find.syst_num
        self.tag_id_in_alarms = 1
        self.all_tag_alrm_id = []
        self.station_name = self.get_station_name()
        self.logger = logging.getLogger(__name__)
        self.protocol_name = ''
        self.module_name = ''
        self.ibp_number = ''
        self.ibp_type = ''
        self.group_status = None
        self.group_offline = None
        self.alarm_group_find = False
   
    def set_group_ids(self):
        """ Получение всех id групп """
        self.group_ids = set()
        group_id_elements = self.parsed_xml.findall('.//GroupID')
        for group_id in group_id_elements:
            self.group_ids.add(group_id.text)

    def get_station_name(self) -> str:
        """ Получение названия станции """
        station_name = ''
        for station in stations:
            if self.station_id == station[i.alrm_code]:
                station_name = station[i.alrm_text]
        return f'{station_name}\\{self.klogic_name.text}'

    def get_tag_alarm_attrs(self, alarm_tag: AlarmTagAttrs) -> AlarmAttrs:
        """Получение необходимых атрибутов аварийной группы: определение в какую группу добавить тег"""
        tag_alarm = ''
        for group in alrm:
            if group[i.alrm_code] == 'ИБП':
                for alarm in group[i.alrm_text]:
                    if alarm_tag.tag['alarm_id'] == alarm[i.alrm_code]:
                        tag_alarm = alarm[i.alrm_text]
            else:
                if alarm_tag.tag['alarm_id'] == group[i.alrm_code]:
                    tag_alarm = group[i.alrm_text]
        tag_alarm = f'{tag_alarm}{self.ibp_type} {self.ibp_number}'
        tag_alarm_id = alarm_tag.tag['alarm_id']
        return AlarmAttrs(
            id=tag_alarm_id + self.ibp_type + self.ibp_number,
            text=tag_alarm
        )

    def insert_alarms_group(self, group: Element, attrs: AlarmAttrs):
        """Добавление группы Alarms с идентификатором аварии"""
        if group[i.group_alarms].tag != f'{attrs.id}Alarms':
            self.alarm_group_find = True
            group.insert(i.group_alarms, get_child_group(f'{attrs.id}Alarms', False))
            self.all_tag_alrm_id.append(attrs.id)

    def check_group_item(self, group: Element, attrs: AlarmAttrs):
        """Поиск аварийной группы"""
        self.alarm_group_find = False
        if group[i.group_name].text == attrs.text:
            self.insert_alarms_group(group, attrs)

    def set_alarm_tag(self, group: int, in_out: Element, tag: dict) -> AlarmTagAttrs:
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
        self.tag_id_in_alarms += 1
        return alarm_tag_attrs

    def alarm_insert(self, alarm_tag: AlarmAttrs, prot_number):
        """Вставка строк в alarms.xml"""
        measure_units = get_measure_units(alarm_tag.in_out)
        mu_index = get_measure_units_index(alarm_tag)
        alarm_tag_full_name = set_tag_full_name(alarm_tag)
        kid = get_klogic_id(alarm_tag.tag_settings)
        value_type = get_value_type(alarm_tag.tag_settings)
        alarm_tag.tag_name = alarm_tag.in_out.attrib['Name']
        tag_path_map = {
            'upsBasicBatteryStatus': f'{c.ups_klogic_path}\\upsBattery\\upsBasicBattery',
            'upsBasicOutputStatus': f'{c.ups_klogic_path}\\upsOutput\\upsBasicOutput',
            'upsAdvBatteryReplaceIndicator': f'{c.ups_klogic_path}\\upsBattery\\upsAdvBattery',
            'Отсутствие связи': 'Служебные теги'
        }
        tag_path = tag_path_map.get(alarm_tag.tag_name, '')
        string_id = f'Kl\\st{self.station_id}\\Cn{self.syst_num.text}\\{self.protocol_name}\\{self.module_name}\\{tag_path}\\\\{alarm_tag.tag_name}'
        alarm_attrs = self.get_tag_alarm_attrs(alarm_tag)

        group_item = self.temp_xmls[prot_number].findall('.//GroupItem')
        for group in group_item:
            self.check_group_item(group, alarm_attrs)
            if self.alarm_group_find:
                self.logger.debug(alarm_attrs.text)
                self.logger.debug(string_id)
                if not self.temp_xmls[prot_number].find(f'.//{alarm_attrs.id}Alarms/Alarm'):
                    self.temp_xmls[prot_number].find(f'.//{alarm_attrs.id}Alarms').insert(i.alarm_index, get_child_group('Alarm', False))
                    parent_group = self.temp_xmls[prot_number].find(f'.//{alarm_attrs.id}Alarms/Alarm')
                    parent_group.insert(i.alarm_id, get_child_group('ID', f'{alarm_tag.id}'))
                    parent_group.insert(i.group_name, get_child_group('Name', f'{alarm_tag.tag_name}'))
                    parent_group.insert(i.full_name, get_child_group('FullName', f'{alarm_tag_full_name}'.replace('\\', '.')))
                    if measure_units:
                        parent_group.insert(mu_index, get_child_group('MeasureUnits', f'{measure_units}'))
                    parent_group.insert(mu_index + 1, get_child_group('ZoneName', f'{self.klogic_name.text}'))
                    parent_group.insert(mu_index + 2, get_child_group('StationName', f'{self.station_name}'))
                    parent_group.insert(mu_index + 3, get_child_group('Passport', False))
                    passport_group = self.temp_xmls[prot_number].find(f'.//{alarm_attrs.id}Alarms/Alarm/Passport')
                    passport_group.insert(i.station_id, get_child_group('StationID', f'{self.station_id}'))
                    passport_group.insert(i.passport_type, get_child_group('PassportType', '222'))
                    passport_group.insert(i.group_id, get_child_group('GroupID', f'{self.syst_num.text}'))
                    passport_group.insert(i.passport_id, get_child_group('PassportID', f'{kid}'))
                    passport_group.insert(i.value_type, get_child_group('ValueType', f'{value_type}'))
                    parent_group.insert(mu_index + 4, get_child_group('StringID', f'{string_id}'))

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

    def remove_attr(self, parent_group: str, group_name: str, iterables: Iterable):
        """Удаление служебных символов в названии групп"""
        for index in iterables:
            for parent in self.parsed_xml.findall(parent_group):
                for child in parent:
                    child.tag = child.tag.replace(f'{index}{group_name}', f'{group_name}')
                    child.tag = child.tag.replace(f'{group_name}{index}', f'{group_name}')
                    child.tag = child.tag.replace('tempAlarms', 'Alarms')

    def generate_group_id(self, new_group_ids: Iterable) -> int:
        """Получение нового id"""
        group_id = 1
        while any([
            group_id in new_group_ids,
            group_id in self.group_ids
        ]):
            group_id += 1
        return group_id
    
    def set_module_atrrs(self, module: Element):
        """ Поучение информации по текущему модулю """
        self.module_name = module[i.settings][i.name].text
        self.ibp_number = self.module_name.split(' ')[i.ibp_number]
        self.ibp_type = self.module_name.split(' ')[i.ibp_type]
    
    def insert_new_gm_group(self, prot_number: int):
        """ Добавление готовой папки по ГМ в alarms.xml """
        all_group_item = self.parsed_xml.findall('.//GroupItem')
        for group_item in all_group_item:
            if group_item[i.group_name].text == 'ИБП ГМ':
            
                all_temp_group = self.temp_xmls[prot_number].findall('.//GroupItem')
                for temp_group in all_temp_group:
                    if temp_group[i.group_name].text == 'ГМ':
                        temp_group[i.group_name].text = self.protocol_name
                        group_item[2].insert(prot_number, temp_group)
    
    def remove_template_group(self):
        """ Удаление шаблона """
        groups = self.alarm_root.findall('.//GroupItem')
        for main_group in groups:
            if main_group[i.group_name].text == 'ИБП ГМ':
                for gmgroup in main_group[2]:
                    if gmgroup[i.group_name].text == 'ГМ':
                        main_group[2].remove(gmgroup)
    
    def remove_service_attrs(self):
        for attr in self.all_tag_alrm_id:
            while any([
                self.parsed_xml.find(f'.//GroupItem{attr}') is not None,
                self.parsed_xml.find(f'.//Children{attr}') is not None,
                self.parsed_xml.find(f'.//Alarms{attr}') is not None,
                self.parsed_xml.find(f'.//{attr}Alarms') is not None,
                self.parsed_xml.find(f'.//GroupID{attr}') is not None,
                self.parsed_xml.find(f'.//GroupName{attr}') is not None,
            ]):
            
                for group_name in [
                    ['.//Children', 'GroupItem'],
                    ['.//GroupItem', 'Children'],
                    ['.//GroupItem', 'Alarms'],
                    ['.//GroupItem', 'GroupID'],
                    ['.//GroupItem', 'GroupName'],
                ]:
                    self.remove_attr(group_name[0], group_name[1], self.all_tag_alrm_id)
    
    def set_alarm_xml(self, klogic_xml: KlogicXML, tags: Iterable):
        """Формирование alarms.xml"""
        self.group_gm = set_group_element(self.temp_groups, 'ГМ')
        self.group_status = set_group_element(self.temp_groups, 'Статусы')
        self.group_offline = set_group_element(self.temp_groups, 'Нет связи')
        self.set_group_ids()

        for prot_number in range(1, klogic_xml.prot_number):
            self.temp_xmls[prot_number] = ElementTree.parse(self.xml_path)
            self.protocol_name = klogic_xml.protocols[prot_number][i.protocol][i.settings][i.name].text

            modules = klogic_xml.protocols[prot_number][i.protocol].findall('.//Module')
            for module in modules:
                self.set_module_atrrs(module)
                all_inout = module.findall('.//InOut')
                for in_out in all_inout:
                    for tag in tags:
                        if in_out.attrib['Name'] == tag['name']:
                            alarm_tag = self.set_alarm_tag(module, in_out, tag)
                            self.alarm_insert(alarm_tag, prot_number)
                
                self.insert_new_gm_group(prot_number)

        self.remove_template_group()
        self.remove_service_attrs()

    def write(self, xml_path):
        self.parsed_xml.write(xml_path, encoding='UTF-8')
