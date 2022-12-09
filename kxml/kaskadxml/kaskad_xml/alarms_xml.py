import logging
import pathlib
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .klogic_xml import KlogicAttrs
from .alrm import alrm, stations
from .indices import indices as i, constants as c, xo_types, sensor_error_indices as se_i
from .exceptions import ErrorMissingProduct


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


def get_child_group(child_group: str, text):
	child = ElementTree.Element(child_group)
	if text:
		child.text = text
	return child


def get_measure_units(in_out: Element):
	""" Получение единицы измерения переменной """
	try:
		measure_units = in_out.attrib['MeasU']
	except KeyError:
		measure_units = False
	return measure_units


def get_klogic_id(tag_settings: Element) -> str:
	""" Получение адреса переменной """
	kid = ''
	for setting in tag_settings.iter('KId'):
		kid = setting.text
	return kid


def get_value_type(tag_settings: Element) -> int:
	""" Получение типа переменной """
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
		group.insert(i.group_alarms, get_child_group('tempAlarms', False))


def get_measure_units_index(alarm_tag: AlarmTagAttrs) -> int:
	"""Получение индекса для группы MeasureUnits"""
	return (
		i.me_not_exist
		if not get_measure_units(alarm_tag.in_out) else i.me_exist
	)


def get_central_tags(tags: Iterable) -> list:
	""" Получение переменных, для проверки контроллера централи """
	return [tag for tag in tags if tag['alarm_id'] == 'central']


def server_cutout(xo_type: str) -> str:
	""" Получение уставки для Серверной/Маш-зала """
	return c.server_cutout


class AlarmsXML:
	""" Класс для  AlarmsXML"""
	
	def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int, products: Iterable):
		self.xml_path = xml_path
		self.xml_file_name = 'Alarms.xml'
		self.parsed_xml = ElementTree.parse(self.xml_path)
		self.alarm_root = self.parsed_xml.getroot()
		self.group_item = self.parsed_xml.find('.//GroupItem')
		self.station_id = station_id
		self.products = products
		self.klogic_name = kl_find.klogic_name
		self.protocol_name = kl_find.protocol_name
		self.gm = kl_find.gm
		self.syst_num = kl_find.syst_num
		self.contr_name = None
		self.verif_tag = None
		self.alarm_number = None
		self.tag_id_in_alarms = 1
		self.central_contr = False
		self.cutout_flag = False
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
	
	def filter_contr_name(self, product):
		""" Поиск полного названия контроллера в таблице контроля уставок """
		if self.contr_name == product['name']:
			return product
	
	def cutout(self, contr: str) -> CutoutAttrs:
		"""Получение значения уставки и типа оборудования для контроллера"""
		result = CutoutAttrs(
			cutout=str(c.new_product_cutout),
			xo_type='None'
		)
		self.contr_name = contr.split('__')[i.contr_name]
		try:
			result.xo_type = self.contr_name.split('_')[i.xo_type]
			product = self.contr_name.split('_')[i.product]
			if result.xo_type in xo_types.nt:
				result.cutout = str(c.nt_cutout)
			else:
				for prod in self.products:
					if self.contr_name == prod['name']:
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
			check_cutout_map = {
				'server': server_cutout,
				'central_room': server_cutout,
			}
			products = filter(self.filter_contr_name, self.products)
			for prod in products:
				result = CutoutAttrs(
					cutout=str(check_cutout_map.get(prod['xo_type'], self.check_cutout)(self.contr_name)),
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
			attrs.tag_settings = in_out[i.settings]
			attrs.tag_name = in_out.attrib['Name']
			attrs.contr = str(module[attrs.group].attrib['Name'] + '\\' + 'Alarms')
		attrs.tag_full_name = f'{self.klogic_name.text}.{self.protocol_name.text}.{self.gm.text}.{attrs.contr}.{attrs.tag_name}'
		return attrs.tag_full_name
	
	def get_tag_alarm_attrs(self, alarm_tag: AlarmTagAttrs) -> AlarmAttrs:
		"""Получение необходимых атрибутов аварийной группы: определение в какую группу добавить тег"""
		tag_alarm = ''
		for group in alrm:
			if any([
				group[i.alrm_code] == 'Уставки',
				group[i.alrm_code] == 'Потребители',
				group[i.alrm_code] == 'Централи'
			]):
				for alarm in group[i.alrm_text]:
					if alarm_tag.tag['alarm_id'] == alarm[i.alrm_code]:
						tag_alarm = alarm[i.alrm_text]
			else:
				if alarm_tag.tag['alarm_id'] == group[i.alrm_code]:
					tag_alarm = group[i.alrm_text]
		
		tag_alarm_id = alarm_tag.tag['alarm_id']
		xo_type = self.cutout(alarm_tag.contr).xo_type
		if all([
			tag_alarm_id == 'A1',
			xo_type in xo_types.a1k
		]):
			tag_alarm = 'A1. Высокая температура К'
			tag_alarm_id = f'{tag_alarm_id}K'
		
		if tag_alarm_id == 'Cutout':
			cutout = self.cutout(alarm_tag.contr).cutout
			tag_alarm = f'{cutout}c'
			tag_alarm_id = f'{tag_alarm_id}{tag_alarm}'
			if cutout == str(c.new_product_cutout):
				self.new_product.add(alarm_tag.contr)
		else:
			if tag_alarm_id == 'A13-high-lim-air':
				cutout = self.cutout(alarm_tag.contr).cutout
				tag_alarm = f'{cutout}a'
				tag_alarm_id = f'{tag_alarm_id}{tag_alarm}'
				if cutout == str(c.new_product_cutout):
					self.new_product.add(alarm_tag.contr)
		
		return AlarmAttrs(
			id=tag_alarm_id,
			text=tag_alarm
		)
	
	def insert_alarms_group(self, group: Element, attrs: AlarmAttrs):
		"""Добавление группы Alarms с идентификатором аварии"""
		if group[i.group_alarms].tag != f'{attrs.id}Alarms':
			group.insert(i.group_alarms, get_child_group(f'{attrs.id}Alarms', False))
			self.all_tag_alrm_id.append(attrs.id)
	
	def check_group_item(self, group: Element, attrs: AlarmAttrs) -> bool:
		"""Поиск аварийной группы"""
		alarm_group_find = False
		if group[i.group_name].text == attrs.text:
			alarm_group_find = True
			self.insert_alarms_group(group, attrs)
		return alarm_group_find
	
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
	
	def alarm_insert(self, module: Element, alarm_tag: AlarmTagAttrs):
		"""Вставка строк в alarms.xml"""
		measure_units = get_measure_units(alarm_tag.in_out)
		mu_index = get_measure_units_index(alarm_tag)
		alarm_tag_full_name = self.set_tag_full_name(module, alarm_tag)
		kid = get_klogic_id(alarm_tag.tag_settings)
		value_type = get_value_type(alarm_tag.tag_settings)
		string_id = f'Kl\\st{self.station_id}\\Cn{self.syst_num.text}\\{self.protocol_name.text}\\{self.gm.text}\\{alarm_tag.contr}\\\\{alarm_tag.tag_name}'
		alarm_attrs = self.get_tag_alarm_attrs(alarm_tag)
		
		group_item = self.parsed_xml.findall('.//GroupItem')
		for group in group_item:
			mark_group_not_for_del(group)
			if self.check_group_item(group, alarm_attrs):
				self.logger.debug(alarm_attrs.text)
				self.logger.debug(string_id)
				self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms').insert(i.alarm_index,
				                                                          get_child_group('Alarm', False))
				parent_group = self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms/Alarm')
				parent_group.insert(i.alarm_id, get_child_group('ID', f'{alarm_tag.id}'))
				parent_group.insert(i.group_name, get_child_group('Name', f'{alarm_tag.tag_name}'))
				parent_group.insert(i.full_name,
				                    get_child_group('FullName', f'{alarm_tag_full_name}'.replace('\\', '.')))
				if measure_units:
					parent_group.insert(mu_index, get_child_group('MeasureUnits', f'{measure_units}'))
				parent_group.insert(mu_index + 1, get_child_group('ZoneName', f'{self.klogic_name.text}'))
				parent_group.insert(mu_index + 2, get_child_group('StationName', f'{self.station_name}'))
				parent_group.insert(mu_index + 3, get_child_group('Passport', False))
				passport_group = self.parsed_xml.find(f'.//{alarm_attrs.id}Alarms/Alarm/Passport')
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
	
	def remove_service_attrs(self, parent_group: str, group_name: str, iterables: Iterable):
		"""Удаление служебных символов в названии групп"""
		for index in iterables:
			for parent in self.parsed_xml.findall(parent_group):
				for child in parent:
					child.tag = child.tag.replace(f'{index}{group_name}', f'{group_name}')
					child.tag = child.tag.replace('tempAlarms', 'Alarms')
	
	def r12_insert(self, module: Element, alarm_tag: AlarmTagAttrs):
		""" Вставка аварии по R12 для централи """
		if self.central_contr:
			self.alarm_insert(module, alarm_tag)
	
	def a03_insert(self, module: Element, alarm_tag: AlarmTagAttrs):
		""" Вставка аварии А03 контроллеров потребителей """
		if not self.central_contr:
			self.alarm_insert(module, alarm_tag)
	
	def get_alarms_group_tag(self, in_out):
		""" Получение аварийных переменных для централей 351, 551 """
		if in_out.tag != 'Settings':
			tag_name = in_out.attrib['Name'].split(f'{self.alarm_number}_')[i.alarm_split]
			self.alarm_number += 1
			if tag_name == self.verif_tag['name']:
				return in_out
	
	def unknown_sensor_insert(self, module: Element, group: int, in_out: Element, tag: dict, alarm_number: int):
		""" Вставка аварии неизвестного датчика по порядковому номеру """
		alarm_id = se_i.get(alarm_number)
		if alarm_id:
			alarm_tag = self.set_alarm_tag(
				group,
				in_out,
				{
					'name': 'Ошибка датчика',
					'alarm_id': se_i.get(alarm_number)
				}
			)
			alarm_tag.alarm_flag = True
			alarm_tag.alarm_number = alarm_number
			self.alarm_insert(module, alarm_tag)
	
	def central_alarms_insert(self, module: Element, group: int, in_out: Element, tag: dict, alarm_number: int):
		""" Вставка аварийного параметра централей 351, 551 """
		alarm_tag = self.set_alarm_tag(group, in_out, tag)
		alarm_tag.alarm_flag = True
		alarm_tag.alarm_number = alarm_number
		self.alarm_insert(module, alarm_tag)
	
	def cutout_insert(self, module: Element, alarm_tag: AlarmTagAttrs):
		""" Вставка аварии контроля уставок потребителей """
		if not self.cutout_flag:
			self.alarm_insert(module, alarm_tag)
			self.cutout_flag = True
	
	def set_alarm_xml(self, module: Element, tags: Iterable):
		"""Формирование alarms.xml"""
		self.rename_main_group()
		central_tags = get_central_tags(tags)
		for group, module_group in enumerate(module, i.first_contr):
			try:
				self.cutout_flag = False
				self.check_central(module[group], central_tags)
				for in_out in module[group][i.first_tag:]:
					if in_out.attrib['Name'] == 'Alarms':
						for self.verif_tag in tags:
							self.alarm_number = 1
							central_alarm_tag_insert_map = {
								'unknown_sensor_error': self.unknown_sensor_insert
							}
							central_alarms_tags = filter(self.get_alarms_group_tag, in_out)
							for central_alarms_tag in central_alarms_tags:
								args = [module, group, central_alarms_tag, self.verif_tag, self.alarm_number - 1]
								central_alarm_tag_insert_map.get(self.verif_tag['alarm_id'],
								                                 self.central_alarms_insert)(*args)
					
					for tag in tags:
						if in_out.attrib['Name'] == tag['name']:
							alarm_tag = self.set_alarm_tag(group, in_out, tag)
							args = [module, alarm_tag]
							alarm_tag_insert_map = {
								'r12': self.r12_insert,
								'A03-alarm-delay': self.a03_insert,
								'Cutout': self.cutout_insert
							}
							alarm_tag_insert_map.get(tag['alarm_id'], self.alarm_insert)(*args)
			
			except IndexError:
				break
		
		self.delete_empty_groups()
		self.remove_service_attrs('.//GroupItem', 'Alarms', self.all_tag_alrm_id)
		
		if len(self.new_product):
			raise ErrorMissingProduct(f'Alarm XML: Новый вид продукта: {self.new_product}')
		else:
			return "Alarm XML: Обработка завершена"
	
	def write(self, xml_path):
		self.parsed_xml.write(xml_path, encoding='UTF-8')