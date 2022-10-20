import pathlib
from typing import Iterable, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .indices import indices as i, constants as c, smart_divide_all_n


@dataclass
class NewTagAttrs:
    tag_id: int
    controller: str
    tag_name: str


@dataclass
class GroupAttr:
    name: str
    len_group: int
    addr: int


@dataclass
class ShiftAttrs:
    all_attrs: List[GroupAttr]
    all_lens: set


@dataclass
class KlogicAttrs:
    danfoss: Element
    protocol_name: Element
    gm: Element
    Groups: Element
    fsection: Element
    task_name: Element
    te: Element
    klogic_name: Element
    syst_num: Element


class ErrorCentralAlarm(Exception):
    """ Исключение при отсутствующих авариях у централей 351, 551"""


class ErrorMissingNofflTag(Exception):
    """ Исключение при отсутствующих тегах nofll у контроллера"""


class Tag:
    """ Класс для параметра"""

    def __init__(self, new_tag_attrs: NewTagAttrs):
        self.tag_attr = new_tag_attrs


def get_tag_value_list(source_tag: Iterable, attr: str):
    for tag in source_tag:
        yield tag[attr]


def get_group_tags(tag_groups: Element) -> List[str]:
    """Получение всех переменных контроллера"""
    group_tag_names = []
    if tag_groups.attrib['Name'] == 'Alarms' and len(tag_groups) > c.central_alarm_len:
        for alarm_number in range(len(tag_groups))[i.first_tag:]:
            try:
                group_tag_names.append(
                    tag_groups[alarm_number].attrib['Name'].split(f'{alarm_number}_')[i.alarm_split])
            except IndexError:
                raise ErrorCentralAlarm('В группе Alarms у централи добавлены не все переменные')
    else:
        group_tag_names.append(tag_groups.attrib['Name'])
    return group_tag_names


def check_noffl_input(noffl_input: Element) -> bool:
    return not noffl_input.attrib['Name'] in ['N', 'T', 'pOffline']


def tree_insert(parent_group: Element, insert_index: int, child_group: str, text: str):
    child = ElementTree.Element(child_group)
    if text:
        child.text = text
    parent_group.insert(insert_index, child)


def update_inout_setting(inout: Element, setting_tag: str, text: str):
    for setting in inout[i.settings].iter(setting_tag):
        setting.text = text
        print(setting.tag, text)


def get_node(group: Element) -> str:
    """Получение адреса контроллера"""
    node = 0
    for setting in group[i.first_tag].iter('PropList'):
        node = setting.attrib['Node']
    return node


def get_all_input_number(fb_input: int, noffl_number: int) -> int:
    """Получение текущего номера входа ФБ noffl, с учетом всех ФБ noffl"""
    return fb_input + c.num_of_inputs * noffl_number


def filter_smart_divide_out(inout: Element) -> bool:
    return (True
            if inout.attrib['Name'] == smart_divide_all_n else False
            )


class KlogicXML:
    """ Класс для  KlogicXML"""

    def __init__(self, xml_path: pathlib.Path, prot_code: str):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.prot_code = prot_code
        self.module = None
        self.new_tag_names = []
        self.new_ids = []
        self.all_new_tags_attrs = []
        self.cental_alarms_flag = False
        self.tag_noffl_flag = False
        self.tag_settings = []  # Список, содержащий данные для заполнения в группе Connected функц.блока noffl
        self.tags_path = []  # Список со строками, содержащими путь к переменным noffl в xml
        self.noffl_contr = 0  # Переменная для подсчета контроллеров, подключенных к функц.блоку noffl
        self.num_of_fb = 0
        self.connected_inputs = 0
        self.teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'
        self.checked_tag = None
        self.checked_attr = None

    def filter_noffl_tag(self, tag: Element) -> bool:
        """Фильтр параметра noffl"""
        return (True
                if self.checked_tag['noffl'] and tag.attrib['Name'] == self.checked_tag['name'] else False
                )

    def get_noffl_tag(self, inout: Element, good_tags: Iterable) -> Element:
        """Поиск параметра noffl"""
        for self.checked_tag in good_tags:
            tags = filter(self.filter_noffl_tag, inout[i.first_tag:])
            for tag in tags:
                return tag

    def filter_module(self, protocol: Element) -> Element:
        """Фильтр протокола с контроллерами"""
        for setting in protocol.iter('ProtCode'):
            if setting.text == self.prot_code:
                return protocol

    def find_module(self):
        """Поиск протокола с контроллерами"""
        protocols = filter(self.filter_module, self.parsed_xml.findall('.//Protocol'))
        for protocol in protocols:
            self.module = protocol[i.module]

    def filter_h_attrs(self, tag) -> Element:
        """Фильтр служебных символов (H_xxx)"""
        if self.checked_attr in tag.attrib['Name']:
            return tag

    def h_remove(self, attrs: Iterable):
        """Удаление служебных символов в названии параметра"""
        for group in self.module[i.first_contr:]:
            for self.checked_attr in attrs:
                tags = filter(self.filter_h_attrs, group[i.first_tag:])
                for tag in tags:
                    tag.attrib['Name'] = tag.attrib['Name'].replace(self.checked_attr, '')

    def generate_id(self, exist_tags: Iterable) -> int:
        """Получение нового id"""
        tag_id = 1
        while any([
            tag_id in get_tag_value_list(exist_tags, 'id'),
            tag_id in self.new_ids
        ]):
            tag_id += 1
        return tag_id

    def check_new_tag(self, exist_tags: Iterable, tag_name: str) -> bool:
        """Проверка нового параметра"""
        return not any([
            tag_name in self.new_tag_names,
            tag_name in get_tag_value_list(exist_tags, 'name')
        ])

    def create_new_tag(self, exist_tags: Iterable, group: Element, tag_name: str) -> Tag:
        """Создание нового тега"""
        tag_attrs = NewTagAttrs(
            tag_id=self.generate_id(exist_tags),
            controller=group.attrib['Name'],
            tag_name=tag_name
        )
        print('Новый параметр:', tag_attrs.tag_id, tag_attrs.controller, tag_attrs.tag_name)
        return Tag(tag_attrs)

    def update_new_lists(self, new_tag: Tag):
        """Добавление информации о новом теге в соответствующие списки"""
        self.all_new_tags_attrs.append(new_tag.tag_attr)
        self.new_tag_names.append(new_tag.tag_attr.tag_name)
        self.new_ids.append(new_tag.tag_attr.tag_id)

    def get_new_tags(self, exist_tags: Iterable):
        """Проверка на новые переменные"""
        seq = (item for item in self.module[i.first_contr:]
               if not self.cental_alarms_flag)
        for group in seq:
            for tag in group[i.first_tag:]:
                for tag_name in get_group_tags(tag):
                    if tag_name != 'Not used' and self.check_new_tag(exist_tags, tag_name):
                        new_tag = self.create_new_tag(exist_tags, group, tag_name)
                        self.update_new_lists(new_tag)

    def set_new_tags(self, exist_tags: Iterable):
        """Получение новых переменных, проверка аварий централи"""
        try:
            self.get_new_tags(exist_tags)
            return self.all_new_tags_attrs
        except ErrorCentralAlarm:
            return -1

    def delete_empty_groups(self):
        """Удаление пустых групп"""
        for group in self.module[i.first_contr:]:
            if len(group) < c.empty_klogic_group_len:
                print("Удалена пустая группа:", group.attrib['Name'])
                self.module.remove(group)

    def delete_tags(self, bad_tags: Iterable):
        """Удаление ненужных переменных"""
        for group in self.module[i.first_contr:]:
            for tag in bad_tags:
                for InOut in group[i.first_tag:]:
                    if InOut.attrib['Name'] == tag['name'] and len(InOut) < c.central_alarm_len:
                        print(group.attrib['Name'], InOut.attrib['Name'], len(InOut))
                        group.remove(InOut)

    def add_comment(self):
        """Добавление комментария для оборудования"""
        for group in self.module[i.first_contr:]:
            try:
                comm = group.attrib['Name'].split('__')[i.contr_name]
            except KeyError:
                comm = group.attrib['Name']
            settings = group[i.settings]
            for comment in settings.iter('UserComment'):
                comment.text = f'{comm}..{get_node(group)}'

    def klogic_tree_find(self) -> KlogicAttrs:
        """Получение необходимых атрибутов из klogic.xml"""
        kl_find = ()
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            for setting in protocol.iter('ProtCode'):
                if setting.text == self.prot_code:
                    self.module = protocol[i.module]
                    kl_find = KlogicAttrs(
                        danfoss=protocol[i.settings][i.name],
                        protocol_name=protocol[i.settings][i.name],
                        gm=protocol[i.module][i.settings][i.name],
                        Groups=protocol[i.module],
                        fsection=self.parsed_xml.find('.//UserTask'),
                        task_name=self.parsed_xml.find('.//UserTask/Settings/Name'),
                        te=self.parsed_xml.find('.//TasksGroup0/UserTask/Settings'),
                        klogic_name=self.parsed_xml.find('.//Controller/Settings/Name'),
                        syst_num=self.parsed_xml.find('.//Controller/Settings/SystNum')
                    )
        return kl_find

    def shift(self) -> ShiftAttrs:
        """Подсчет смещения адресов контроллеров"""
        shift_attr = ShiftAttrs(
            all_attrs=[],
            all_lens=set()
        )
        for group in self.module[1:]:
            if all([
                group.attrib['Name'] != 'Служебные теги',
                group.attrib['Name'] != 'Дата и время'
            ]):
                shift_attr.all_lens.add(len(group))
                for setting in group[i.first_tag].iter('KId'):
                    contr_attr = GroupAttr(
                        name=group.attrib['Name'],
                        len_group=len(group),
                        addr=setting.text
                    )
                    shift_attr.all_attrs.append(contr_attr)
        return shift_attr

    def get_tag_path(self, tag: Element, contr: str, tag_name: str) -> str:
        """Получение пути к параметру noffl"""
        kl_find = self.klogic_tree_find()
        protocol_name = kl_find.protocol_name
        gm = kl_find.gm
        self.tag_settings.append(tag[i.settings])
        return f'{protocol_name.text}.{gm.text}.{contr}.{tag_name}'

    def append_tag_settings(self, tag: Element):
        """Обновление списка с группами настроек тегов"""
        tag_name = tag.attrib['Name']
        if tag_name:
            self.tag_settings.append(tag[i.settings])

    def append_tags_path(self, tag: Element, contr: str):
        """Обновление списка с путем всех тегов noffl в xml"""
        tag_name = tag.attrib['Name']
        if tag_name:
            self.tags_path.append(self.get_tag_path(tag, contr, tag_name))

    def get_current_inout(self, fb_input: int, fb: Element, noffl_number: int):
        """Поиск группы контроллера в Klogic XML"""
        kl_find = self.klogic_tree_find()
        groups = kl_find.Groups
        all_fb_input_number = get_all_input_number(fb_input, noffl_number)

        if fb_input + 1 == len(fb):  # последний вход ФБ
            return 'continue'
        if all_fb_input_number < len(groups):  # проверка, чтобы текущий номер входа ФБ не превышал кол-во контроллеров
            return groups[all_fb_input_number]
        else:
            return 'break'

    def create_task_elements(self, in_name: str, task_name: Element, fblock: Element):
        """ Формирование служебной строки <TaskElements> """
        te = f'&lt;ExternalLink&gt;&lt;Path&gt;{task_name.text}.{fblock.text}.{in_name}&lt;/Path&gt;&lt;MarkerLink&gt;&lt;Link&gt;{self.tags_path[self.noffl_contr]}&lt;/Link&gt;&lt;showAllConnections&gt;False&lt;/showAllConnections&gt;&lt;offsetMarkerFB&gt;40&lt;/offsetMarkerFB&gt;&lt;/MarkerLink&gt;&lt;/ExternalLink&gt;'
        self.teall = self.teall + te

    def update_noffl_n(self, fb: Element):
        """Вставка количества контроллеров в ФБ"""
        if self.connected_inputs > 0:
            setting_text = '%.2f' % self.connected_inputs
        else:
            setting_text = '%.2f' % 0
        update_inout_setting(fb[i.n_input_index], 'InitValue0', setting_text)

    def update_all_n(self, smart_divide: Element):
        """ Вставка количества контроллеров в ФБ smart divide"""
        print('Общее количество контроллеров:',
              ((self.num_of_fb - 1) * c.num_of_inputs) + self.connected_inputs)

        inout = filter(filter_smart_divide_out, smart_divide.iter('InOut'))
        update_inout_setting(next(inout), 'InitValue0',
                             '%.2f' % (((self.num_of_fb - 1) * c.num_of_inputs) + self.connected_inputs))

    def insert_task_elements(self, kl_find: KlogicAttrs):
        """ Вставка строки <TaskElements> """
        teall = self.teall + '&lt;/Controls&gt;&lt;/Elements&gt;'
        settings = kl_find.te
        for setting in settings.iter('TaskElements'):
            setting.text = teall

    def get_noffl_all_tags_info(self, fb: Element, noffl_number: int, good_tags: Iterable):
        """ Получение данных по noffl тегам """
        for fb_input in range(len(fb))[i.service_inputs:]:  # 3 входа ФБ не используются на этом этапе
            inout = self.get_current_inout(fb_input, fb, noffl_number)
            if inout == 'continue':
                continue
            if inout == 'break':
                break
            contr = inout.attrib['Name']
            noffl_tag = self.get_noffl_tag(inout, good_tags)
            self.append_tag_settings(noffl_tag)
            self.append_tags_path(noffl_tag, contr)

    def connect_noffl_tags(self, str_link: str, noffl_input: Element):
        """ Подключение тегов на входы функционального блока """
        tree_insert(self.tag_settings[self.noffl_contr], i.tag_connected, 'Connected', str_link)
        tree_insert(noffl_input[i.settings], i.fb_input_connected, 'Connected',
                    self.tags_path[self.noffl_contr])
        print(str_link, self.tags_path[self.noffl_contr])

    def set_noffl(self, good_tags: Iterable):
        """Привязка входов к функциональным блокам noffl"""
        kl_find = self.klogic_tree_find()
        groups = kl_find.Groups
        fsection = kl_find.fsection
        task_name = kl_find.task_name

        for fb in fsection[i.first_fb:]:
            fblock = fb[i.settings][i.name]  # Название функц.блока
            for noffl_number in range(0, 15):
                if fblock.text == f'noffl {noffl_number + 1}':
                    self.num_of_fb += 1  # Подсчет функц.блоков noffl
                    self.get_noffl_all_tags_info(fb, noffl_number, good_tags)
                    for noffl_input in fb[i.first_fb_input:]:
                        if self.noffl_contr + i.first_contr < len(
                                groups):  # len(groups) - общее количество групп в Klogic XML, включая служебные(3 шт.)
                            if check_noffl_input(noffl_input):
                                in_name = noffl_input.attrib['Name']
                                try:
                                    self.create_task_elements(in_name, task_name, fblock)
                                    self.connect_noffl_tags(f'{task_name.text}.{fblock.text}.{in_name}', noffl_input)
                                    self.noffl_contr += 1  # Подсчет контроллеров, подключенных к функц.блоку noffl
                                except IndexError:
                                    raise ErrorMissingNofflTag('У контроллера не заданы параметры для ФБ noffl')
                        else:
                            break
                    self.connected_inputs = self.noffl_contr - c.num_of_inputs * (self.num_of_fb - 1)
                    self.update_noffl_n(fb)

                if fblock.text == 'smart divide':
                    smart_divide = fb  # ФБ smart divide
        self.insert_task_elements(kl_find)
        self.update_all_n(smart_divide)

    def write(self, xml_path: pathlib.Path):
        if not xml_path:
            xml_path = self.xml_path
        self.parsed_xml.write(xml_path)
