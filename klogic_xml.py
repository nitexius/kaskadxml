import pathlib
from typing import Iterable
from xml.etree import ElementTree
#from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from .models import NewTags, KlogicAttrs, ShiftAttrs, NewTagAttrs


class KlogicXML:
    ''' Класс для  KlogicXML'''

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, xml_path: pathlib.Path):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.module = self.parsed_xml.find('.//Module')

    def h_remove(self, attrs: Iterable):
        '''удлаение служебных символов в названии параметра'''
        for group in self.module[3:]:
            for inout in group[1:]:
                for h in attrs:
                    if h in inout.attrib['Name']:
                        inout.attrib['Name'] = inout.attrib['Name'].replace(h, '')

    def generate_id(self, exist_ids: set):
        '''Получение нового id'''
        id = 1
        while any([
            id in exist_ids,
            id in self.new_ids
        ]):
            id += 1
        return id

    def check_new_tag(self, exist_tags: set) -> bool:
        '''Проверка нового параметра'''
        result = False
        if not any([
            self.new_tag_name in self.new_tag_names,
            self.new_tag_name in exist_tags
        ]):
            result = True
        return result

    def get_new_tag_attr(self, exist_ids: set):
        generated_id = self.generate_id(exist_ids)
        print('Новый параметр:', generated_id, self.new_tag_controller, self.new_tag_name)
        self.new_tag_attr = NewTagAttrs(
            tag_id=generated_id,
            controller=self.new_tag_controller,
            tag_name=self.new_tag_name
        )

    def new_tags(self, exist_tags: set, exist_ids: set):
        '''Проверка на новые переменные'''
        all_new_tags = []
        self.new_tag_names = []
        self.new_ids = []
        cental_alarms_flag = False
        for Group in range(len(self.module))[3:]:
            if not cental_alarms_flag:
                self.new_tag_controller = self.module[Group].attrib['Name']
                for tag in self.module[Group][1:]:
                    if tag.attrib['Name'] == 'Alarms' and len(tag) > 35:
                        for alarm_tag in range(len(tag))[1:]:
                            try:
                                if tag[alarm_tag].attrib['Name'].split(str(alarm_tag) + "_")[1] != 'Not used':
                                    self.new_tag_name = tag[alarm_tag].attrib['Name'].split(str(alarm_tag) + "_")[1]
                                    if self.check_new_tag(exist_tags):
                                        self.get_new_tag_attr(exist_ids)
                                        all_new_tags.append(self.new_tag_attr)
                                        self.new_tag_names.append(self.new_tag_name)
                                        self.new_ids.append(self.new_tag_attr.tag_id)
                            except IndexError:
                                cental_alarms_flag = True
                                break
                    else:
                        self.new_tag_name = tag.attrib['Name']
                        if self.check_new_tag(exist_tags):
                            self.get_new_tag_attr(exist_ids)
                            all_new_tags.append(self.new_tag_attr)
                            self.new_tag_names.append(self.new_tag_name)
                            self.new_ids.append(self.new_tag_attr.tag_id)
            else:
                break
        if not cental_alarms_flag:
            result = all_new_tags
        else:
            result = -1
        return result

    def delete_tags(self, bad_tags: QuerySet):
        '''Удаление ненужных переменных, пустых групп'''
        for Group in self.module[1:]:
            if len(Group) < 2:
                print("Удалена пустая группа:", Group.attrib['Name'])
                self.module.remove(Group)
            for tag in bad_tags:
                for InOut in Group[1:]:
                    if InOut.attrib['Name'] == str(tag):
                        if len(InOut) < 35:
                            print(Group.attrib['Name'], InOut.attrib['Name'], len(InOut))
                            Group.remove(InOut)

    def add_comment(self):
        '''Добавление комментария для оборудования'''
        for Group in self.module[3:]:
            comm = Group.attrib['Name'].replace('__', '..')
            Settings = Group[0]
            UserComment = Settings[1]
            for comment in UserComment.iter('UserComment'):
                comment.text = str(comm)

    def klogic_tree_find(self) -> KlogicAttrs:
        '''Получение необходимых атрибутов из klogic.xml'''
        kl_find = KlogicAttrs(
            danfoss=self.parsed_xml.find('.//TasksGroup1/Protocol/Settings/Name'),
            gm=self.parsed_xml.find('.//TasksGroup1/Protocol/Module/Settings/Name'),
            Groups=self.parsed_xml.find('.//TasksGroup1/Protocol/Module'),
            fsection=self.parsed_xml.find('.//UserTask'),
            task_name=self.parsed_xml.find('.//UserTask/Settings/Name'),
            te=self.parsed_xml.find('.//TasksGroup0/UserTask/Settings'),
            klogic_name=self.parsed_xml.find('.//Controller/Settings/Name'),
            syst_num=self.parsed_xml.find('.//Controller/Settings/SystNum')
        )
        return kl_find

    def shift(self) -> ShiftAttrs:
        '''Подсчет смещения адресов контроллеров'''
        shift_attr = ShiftAttrs(
            all_attrs=[],
            all_lens=set()
        )
        for Group in range(len(self.module))[1:]:
            contr_attr = []
            if self.module[Group].attrib['Name'] != 'Служебные теги' and self.module[Group].attrib['Name'] != 'Дата и время':
                contr_attr.append(self.module[Group].attrib['Name'])
                contr_attr.append(len(self.module[Group]))
                shift_attr.all_lens.add(len(self.module[Group]))
                for settings in self.module[Group][1][0]:
                    if settings.tag == 'KId':
                        contr_attr.append(self.module[Group][1].attrib['Name'])
                        contr_attr.append(settings.text)
                shift_attr.all_attrs.append(contr_attr)
        return shift_attr

    def noffl(self, noffl_tags: QuerySet):
        '''Привязка входов к функциональном блокам noffl'''
        kl_find = self.klogic_tree_find()
        danfoss = kl_find.danfoss
        gm = kl_find.gm
        Groups = kl_find.Groups
        fsection = kl_find.fsection
        teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'
        task_name = kl_find.task_name

        num_of_inputs = 10  # Количество входов в каждом Функциональном блоке noffl
        strs = []  # Список со строками, содержащими путь к переменным в xml
        tag_settings = []  # Список, содержащий данные для заполнения в группе Connected функц.блока noffl
        num_of_contr = 0  # Переменная для подсчета контроллеров, подключенных к функц.блоку noffl
        num_of_fb = 0  # Переменная для подсчета фнукц.блоков noffl

        for fb in range(len(fsection))[1:]:
            fblock = fsection[fb][0][0]  # Название функц.блока
            for h in range(0, 15):
                if fblock.text == f'noffl {h + 1}':
                    num_of_fb = num_of_fb + 1  # Подсчет функц.блоков noffl
                    for fb_input in range(len(fsection[fb]))[3:]:  # 3 входа ФБ не используются на этом этапе
                        if (fb_input + num_of_inputs * h) < len(
                                Groups):  # проверка, чтобы текущий номер входа ФБ не превышал кол-во контроллеров
                            if (fb_input + 1) == len(fsection[fb]):  # последний вход ФБ
                                continue
                            else:
                                inout = Groups[fb_input + num_of_inputs * h]
                                contr = inout.attrib['Name']
                                flag = False
                                for tag in range(len(inout))[1:]:
                                    if flag:  # проверка на тот случай, если контроллер уже добавлен в ФБ
                                        break
                                    for noffl_tag in noffl_tags:
                                        if inout[tag].attrib['Name'] == str(noffl_tag):
                                            tag_setting = inout[tag][0]
                                            tag_settings.append(tag_setting)
                                            tag_name = inout[tag].attrib['Name']
                                            st = f'{danfoss.text}.{gm.text}.{contr}.{tag_name}'
                                            strs.append(st)
                                            flag = True
                        else:
                            break

                    for v in range(len(fsection[fb]))[1:]:
                        if (num_of_contr + 3) < len(
                                Groups):  # len(Groups) - общее колличество групп в Klogic XML, включая служебные(3 шт.)
                            noffl_input = fsection[fb][v]  # Вход функционального блока noffl
                            if noffl_input.attrib['Name'] == 'N' or \
                                    noffl_input.attrib['Name'] == 'T' or \
                                    noffl_input.attrib['Name'] == 'pOffline':
                                print(fb, fsection[fb][0][0].text, 'v = ', v, noffl_input.attrib['Name'])
                            else:

                                ''' Формирование служебной строки <TaskElements> '''
                                in_name = noffl_input.attrib['Name']
                                str_link = f'{task_name.text}.{fblock.text}.{in_name}'
                                te = f'&lt;ExternalLink&gt;&lt;Path&gt;{task_name.text}.{fblock.text}.{in_name}&lt;/Path&gt;&lt;MarkerLink&gt;&lt;Link&gt;{strs[num_of_contr]}&lt;/Link&gt;&lt;showAllConnections&gt;False&lt;/showAllConnections&gt;&lt;offsetMarkerFB&gt;40&lt;/offsetMarkerFB&gt;&lt;/MarkerLink&gt;&lt;/ExternalLink&gt;'
                                teall = teall + te

                                ''' Подключение тегов на входы функционального блока '''
                                ts = tag_settings[num_of_contr]
                                Connected2 = ElementTree.Element("Connected")
                                Connected2.text = str_link
                                ts.insert(0, Connected2)
                                Connected = ElementTree.Element("Connected")
                                Connected.text = strs[num_of_contr]
                                noffl_input[0].insert(1, Connected)
                                print(fb, 'N =', (num_of_contr - num_of_inputs * (num_of_fb - 1)), str_link,
                                      strs[num_of_contr])
                                num_of_contr = num_of_contr + 1  # Подсчет контроллеров, подключенных к функц.блоку noffl
                        else:
                            break
                    N_input = fsection[fb][5][0]  # Вход ФБ с колличеством подключенных контроллеров
                    connected_inputs = num_of_contr - num_of_inputs * (num_of_fb - 1)
                    N_input.remove(N_input[3])
                    InitValue0 = ElementTree.Element("InitValue0")
                    if connected_inputs > 0:
                        print(N_input[3].text, '%.2f' % connected_inputs)
                        InitValue0.text = '%.2f' % connected_inputs
                    else:
                        InitValue0.text = '%.2f' % 0
                    N_input.insert(3, InitValue0)

                if fblock.text == 'smart divide':
                    smart_divide = fb  # Номер ФБ smart divide

        ''' Вставка строки <TaskElements> '''
        teall = teall + '&lt;/Controls&gt;&lt;/Elements&gt;'
        te = kl_find.te
        for child in range(len(te)):
            if te[child].tag == 'TaskElements':
                te.remove(te[child])
                TaskElements = ElementTree.Element("TaskElements")
                TaskElements.text = teall
                te.insert(child, TaskElements)

        ''' Вставка количества контроллеров в ФБ smart divide'''
        print('Общее количество контроллеров:', ((num_of_fb - 1) * 10) + connected_inputs, 'u=', connected_inputs)
        for t in range(len(fsection[smart_divide]))[1:]:
            if fsection[smart_divide][t].attrib['Name'] == 'Делитель 1':
                all_contr = fsection[smart_divide][t][0]
                all_contr.remove(all_contr[3])
                nall = ((num_of_fb - 1) * 10) + connected_inputs
                InitValueNAll = ElementTree.Element("InitValue0")
                InitValueNAll.text = '%.2f' % nall
                all_contr.insert(3, InitValueNAll)

    def write(self):
        self.parsed_xml.write(self.xml_path)
