import shutil
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from xml.etree import ElementTree
from .models import history_tags, GoodTags, BadTags, NewTags, klogic, klogger, alarms, Cutout, Shift
from .forms import KlogicForm
from .fb_noffl import nfb
from .alrm import alrm, stations


def indent(elem, level=0):
    '''создает xml c отступами'''
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def h_remove(xml):
    '''удлаение служебных символов'''
    with open(xml, 'rt', encoding='cp1251') as file:
        x = file.read()
    with open(xml, 'wt', encoding='cp1251') as file:
        all_h = history_tags.get_htagsall()
        for tag in all_h:
            x = x.replace(str(tag), "")
        file.write(x)


def check_new_tag(child, tags, all_id):
    '''Поиск параметра среди используемых и удаляемых'''
    k = 0
    for tag in tags:
        all_id.add(tag.id)
        if child != tag.Name:
            k = k + 1
    return k


def append_new_tag(new_tags, controller, name, bad_tags, good_tags, all_id):
    m = 0
    for p in new_tags:
        if name != p['Name']:
            m = m + 1
    if m == len(new_tags):
        if check_new_tag(name, bad_tags, all_id) == len(bad_tags):
            if check_new_tag(name, good_tags, all_id) == len(good_tags):
                print('Новый параметр:', controller, name)
                new_tags.append({'Controller': controller, 'Name': name})


def new_tags(Module, bad_tags):
    '''Проверка на новые переменные'''
    NewTags.delete_NewTagsall()
    good_tags = GoodTags.get_GoodTagsall()
    new_tags = []
    all_id = set()

    for contr in range(len(Module))[3:]:
        controller = Module[contr].attrib['Name']
        for child in Module[contr][1:]:
            if child.attrib['Name'] == 'Alarms' and len(child) > 35:
                for al in range(len(child))[1:]:
                    if child[al].attrib['Name'].split(str(al) + "_")[1] != 'Not used':
                        tag_name = child[al].attrib['Name'].split(str(al) + "_")[1]
                        append_new_tag(new_tags, controller, tag_name, bad_tags, good_tags, all_id)
            else:
                append_new_tag(new_tags, controller, child.attrib['Name'], bad_tags, good_tags, all_id)

    print(len(new_tags))
    if len(new_tags) > 0:
        for tag in new_tags:
            new_id = 1
            while new_id in all_id:
                new_id = new_id + 1
            all_id.add(new_id)
            new_tag = NewTags(id=new_id, Name=tag['Name'], Controller=tag['Controller'])
            new_tag.save()
    return len(new_tags)


def delete_tags(Module, bad_tags):
    '''Удаление ненужных переменных'''
    for Group in Module[1:]:
        if len(Group) < 2:
            print("Удалена пустая группа:", Group.attrib['Name'])
            Module.remove(Group)
        for tag in bad_tags:
            for InOut in Group[1:]:
                if InOut.attrib['Name'] == str(tag):
                    if len(InOut) < 35:
                        print(Group.attrib['Name'], InOut.attrib['Name'], len(InOut))
                        Group.remove(InOut)


def add_comment(Module):
    '''Добавление комментария для оборудования'''
    for Group in Module[3:]:
        comm = Group.attrib['Name'].replace('__', '..')
        Settings = Group[0]
        UserComment = Settings[1]
        for comment in UserComment.iter('UserComment'):
            comment.text = str(comm)


def klogic_tree_find(tree):
    '''Получение необходимых атрибутов из klogic.xml'''
    kl_find = {}
    kl_find['danfoss'] = tree.find('.//TasksGroup1/Protocol/Settings/Name')
    kl_find['gm'] = tree.find('.//TasksGroup1/Protocol/Module/Settings/Name')
    kl_find['Groups'] = tree.find('.//TasksGroup1/Protocol/Module')
    kl_find['fsection'] = tree.find('.//UserTask')
    kl_find['task_name'] = tree.find('.//UserTask/Settings/Name')
    kl_find['te'] = tree.find('.//TasksGroup0/UserTask/Settings')
    kl_find['klogic_name'] = tree.find('.//Controller/Settings/Name')
    kl_find['syst_num'] = tree.find('.//Controller/Settings/SystNum')
    return kl_find


def shift(Module, gmget):
    '''Подсчет смещения адресов контроллеров'''
    try:
        old_shift = Shift.objects.get(gm=gmget)
        old_shift.delete()
    except ObjectDoesNotExist:
        pass

    all_contr = []
    sh = set()
    for Group in range(len(Module))[1:]:
        contr = []
        if Module[Group].attrib['Name'] != 'Служебные теги' and Module[Group].attrib['Name'] != 'Дата и время':
            contr.append(Module[Group].attrib['Name'])
            contr.append(len(Module[Group]))
            sh.add(len(Module[Group]))
            for settings in Module[Group][1][0]:
                if settings.tag == 'KId':
                    contr.append(Module[Group][1].attrib['Name'])
                    contr.append(settings.text)
            all_contr.append(contr)

    Shift.objects.create(gm=gmget, txt="media/shift/" + str(gmget) + ".txt")
    txt = Shift.objects.get(gm=gmget).txt.path
    file = open(str(txt), "w+")
    for s in sh:
        address = 0
        for n in range(len(all_contr)):
            if all_contr[n][1] == s:
                if address == 0:
                    q = 0
                    address = float(all_contr[n][3])
                else:
                    q = float(all_contr[n][3]) - address
                    address = float(all_contr[n][3])
                file.write(('Кол-во переменных = ' + str(s) + '. ' + str(all_contr[n][0]) + '. Смещение = ' + str(q) + '\n'))
    file.close()


def noffl(tree):
    '''Привязка входов к функциональном блокам noffl'''
    root = tree.getroot()
    kl_find = klogic_tree_find(tree)
    danfoss = kl_find['danfoss']
    gm = kl_find['gm']
    Groups = kl_find['Groups']
    fsection = kl_find['fsection']
    teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'
    task_name = kl_find['task_name']

    noffl_tags = GoodTags.get_noffl_tags()
    fb = nfb
    j = 10
    strs = []
    tag_settings = []
    w = -1
    n = 0
    u = 0
    y = 1

    for i in range(len(fsection))[1:]:
        fblock = fsection[i][0][0]
        for h in range(len(fb)):
            if fblock.text == fb[h]:
                n = n + 1
                for x in range(len(fsection[i]))[3:]:
                    if (x + j * h) < len(Groups):
                        if (x + 1) == len(fsection[i]):
                            next
                        else:
                            inout = Groups[x + j * h]
                            contr = inout.attrib['Name']
                            flag = False
                            for b in range(len(inout))[1:]:
                                if flag:
                                    break
                                for tag in noffl_tags:
                                    if inout[b].attrib['Name'] == str(tag):
                                        tag_setting = inout[b][0]
                                        tag_settings.append(tag_setting)
                                        tag = inout[b].attrib['Name']
                                        st = f'{danfoss.text}.{gm.text}.{contr}.{tag}'
                                        strs.append(st)
                                        flag = True
                    else:
                        break

                for v in range(len(fsection[i]))[1:]:
                    if (w + 4) < len(Groups):
                        var = fsection[i][v]
                        if var.attrib['Name'] == 'N' or var.attrib['Name'] == 'T' or var.attrib['Name'] == 'pOffline':
                            print(i, fsection[i][0][0].text, 'v = ', v, var.attrib['Name'])
                        else:
                            w = w + 1

                            ''' Формирование служебной строки <TaskElements> '''
                            in_name = var.attrib['Name']
                            str_link = f'{task_name.text}.{fblock.text}.{in_name}'
                            te = f'&lt;ExternalLink&gt;&lt;Path&gt;{task_name.text}.{fblock.text}.{in_name}&lt;/Path&gt;&lt;MarkerLink&gt;&lt;Link&gt;{strs[w]}&lt;/Link&gt;&lt;showAllConnections&gt;False&lt;/showAllConnections&gt;&lt;offsetMarkerFB&gt;40&lt;/offsetMarkerFB&gt;&lt;/MarkerLink&gt;&lt;/ExternalLink&gt;'
                            teall = teall + te

                            ''' Подключение тегов на входы функционального блока '''
                            ts = tag_settings[w]
                            Connected2 = ElementTree.Element("Connected")
                            Connected2.text = str_link
                            ts.insert(0, Connected2)
                            Connected = ElementTree.Element("Connected")
                            Connected.text = strs[w]
                            var[0].insert(1, Connected)
                            indent(root)
                            print(i, 'N =', (w + 1) - j * (n - 1), str_link, strs[w])
                    else:
                        break
                N = fsection[i][5][0]
                u = (w + 1) - j * (n - 1)
                N.remove(N[3])
                InitValue0 = ElementTree.Element("InitValue0")
                if ((w + 1) - j * (n - 1)) > 0:
                    print(N[3].text, '%.2f' % u)
                    InitValue0.text = '%.2f' % u
                else:
                    InitValue0.text = '%.2f' % 0
                N.insert(3, InitValue0)

            else:
                next
            if fblock.text == 'smart divide':
                y = i
            else:
                next

    ''' Вставка строки <TaskElements> '''
    teall = teall + '&lt;/Controls&gt;&lt;/Elements&gt;'
    te = kl_find['te']
    te.remove(te[7])
    TaskElements = ElementTree.Element("TaskElements")
    TaskElements.text = teall
    te.insert(7, TaskElements)

    ''' Вставка количества контроллеров в ФБ '''
    print('Общее количество контроллеров:', ((n - 1) * 10) + u, 'y=', y, 'u=', u)
    for t in range(len(fsection[y]))[1:]:
        if fsection[y][t].attrib['Name'] == 'Делитель 1':
            all_contr = fsection[y][t][0]
            all_contr.remove(all_contr[3])
            nall = ((n - 1) * 10) + u
            InitValueNAll = ElementTree.Element("InitValue0")
            InitValueNAll.text = '%.2f' % nall
            all_contr.insert(3, InitValueNAll)


def tree_insert(tree, tree_group, child_str, num, txt):
    '''шаблон добавления строки в xml'''
    child = ElementTree.Element(child_str)
    if txt is not False:
        child.text = txt
    tr = tree.find(tree_group)
    tr.insert(num, child)


def bdtp(gmget, tree, Module, klogger_xml, klogger_tree):
    '''Формирование klogger.xml'''
    klogger_root = klogger_tree.getroot()

    try:
        old_groups = klogger_tree.find('.//Groups')
        print('len(old_groups)=', len(old_groups))
        if len(old_groups) > 0:
            klogger_root.remove(old_groups)
            #indent(klogger_root)
            klogger_tree.write(klogger_xml, encoding='UTF-8')
    except (TypeError) as e:
        print('Конфигурация БДТП пуста')
        pass

    kl_find = klogic_tree_find(tree)
    klogic_name = kl_find['klogic_name']
    danfoss = kl_find['danfoss']
    gm = kl_find['gm']
    syst_num = kl_find['syst_num']
    bdtpTags = GoodTags.get_bdtp_tags()
    Gr = ElementTree.Element("Groups")
    klogger_root.insert(37, Gr)
    bdtp_id = 1
    all_bdtp_tags = {}
    all_groups = []
    for Group in range(len(Module))[1:]:
        if Module[Group].attrib['Name'] != 'Служебные теги' and Module[Group].attrib['Name'] != 'Дата и время':
            all_groups.append(Group)
            tree_insert(klogger_tree, './/Groups', 'Grp' + str(Group), Group, False)
            contr = Module[Group].attrib['Name']
            tree_insert(klogger_tree, './/Grp' + str(Group), 'Name', 0, contr)
            tree_insert(klogger_tree, './/Grp' + str(Group), 'OwnCfg', 1, 'false')
            tree_insert(klogger_tree, './/Grp' + str(Group), 'Params' + str(Group), 2, False)
            i = 0
            group_tags = {}

            for InOut in Module[Group][1:]:
                for bdtptag in bdtpTags:
                    tag = {}
                    if InOut.attrib['Name'] == str(bdtptag):
                        tag_name = InOut.attrib['Name']
                        tag['Name'] = tag_name
                        for settings in InOut[0]:
                            if settings.tag == 'KId':
                                tag['KId'] = settings.text
                            else:
                                if settings.tag == 'PropList':
                                    tag['PropList'] = settings.attrib['TagType']
                        tag['st'] = f'{klogic_name.text}.{danfoss.text}.{gm.text}.{contr}.{tag_name}'
                        group_tags[i] = tag
                        i = i + 1
            all_bdtp_tags[Group] = group_tags

    all_par = set()
    for grp in all_groups:
        for par in range(len(all_bdtp_tags[grp])):
            all_par.add(par)
            tree_insert(klogger_tree, './/Params' + str(grp), 'Par' + str(par), par, False)
            str_par = './/Params' + str(grp) + '/Par' + str(par)
            tree_insert(klogger_tree, str_par, 'Zone', 0, str(klogic_name.text))
            tree_insert(klogger_tree, str_par, 'ParID', 1, str(bdtp_id))
            bdtp_id = bdtp_id + 1
            tree_insert(klogger_tree, str_par, 'StId', 2, str(klogic.objects.get(gm=gmget).station_id))
            tree_insert(klogger_tree, str_par, 'Type', 3, '222')
            tree_insert(klogger_tree, str_par, 'GrId', 4, str(syst_num.text))
            tree_insert(klogger_tree, str_par, 'PsId', 5, all_bdtp_tags[grp][par]['KId'])
            if all_bdtp_tags[grp][par]['PropList'] == 'B':
                ValType = '2'
                TypeName = 'Дискретный вход (Логический)'
            else:
                ValType = '1'
                if all_bdtp_tags[grp][par]['PropList'] == 'F':
                    TypeName = 'Аналоговый вход (Вещественный)'
                else:
                    if all_bdtp_tags[grp][par]['PropList'] == 'W':
                        TypeName = 'Аналоговый выход (Целочисленный)'
                    else:
                        TypeName = ''
            tree_insert(klogger_tree, str_par, 'ValType', 6, ValType)
            tree_insert(klogger_tree, str_par, 'TypeName', 7, TypeName)
            tree_insert(klogger_tree, str_par, 'Cipher', 8, str(all_bdtp_tags[grp][par]['Name']))
            tree_insert(klogger_tree, str_par, 'Name', 9, all_bdtp_tags[grp][par]['st'])
            tree_insert(klogger_tree, str_par, 'UsePreAgr', 10, 'false')

    #indent(klogger_root)
    klogger_tree.write(klogger_xml, encoding='UTF-8')
    print(all_par)

    with open(klogger_xml, 'rt', encoding='UTF-8') as file:
        x = file.read()
    with open(klogger_xml, 'wt', encoding='UTF-8') as file:
        for grp in reversed(all_groups):
            x = x.replace('Grp'+str(grp), 'Grp')
            x = x.replace('Params' + str(grp), 'Params')
        for par in all_par:
            x = x.replace('Par' + str(par)+'>', 'Par>')
        file.write(x)

    return "Klogger XML: Обработка завершена"


def check_cutout(products, name):
    '''Получение значения уставки для продукта'''
    for pr in products:
        if name == pr.name:
            ust = pr.cutout
            break
        else:
            ust = '-50'
    return ust


def cutout(contr):
    '''Получение значения уставки для контроллера'''
    products = Cutout.get_products_name()
    name = contr.split('__')[0]
    try:
        type = name.split('_')[0]
        product = name.split('_')[1]
        if type == 'Б' or type == 'НК':
            cutout = '-20'
        else:
            for pr in products:
                if name == pr.name:
                    cutout = pr.cutout
                    break
                else:
                    if type == 'СК':
                        cutout = '0'
                    else:
                        if type == 'Ц':
                            cutout = '12'
                        else:
                            cutout = check_cutout(products, product)
        result = {'cutout': cutout, 'type': type}
    except IndexError:
        if name == 'Серверная':
            type == name
        else:
            type == 'None'
        result = {'cutout': check_cutout(products, name), 'type': type}
    return result


def alarm_insert(attr):
    '''Вставка строк в alarms.xml с учетом подготовленных аттрибутов'''
    kl_find = klogic_tree_find(attr['tree'])
    klogic_name = kl_find['klogic_name']
    danfoss = kl_find['danfoss']
    gm = kl_find['gm']
    syst_num = kl_find['syst_num']
    station = klogic.objects.get(gm=attr['gmget']).station_id
    contr = str(attr['Module'][attr['Group']].attrib['Name'])
    tag_name = attr['InOut'].attrib['Name']

    for s in stations:
        if station == s[0]:
            station_str = s[1]
    StationName = str(station_str + '\\' + klogic_name.text)

    try:
        MeasureUnits = attr['InOut'].attrib['MeasU']
    except (KeyError):
        MeasureUnits = False

    if not attr['al']:
        tag_settings = attr['InOut'][0]
    else:
        tag_settings = attr['InOut'][attr['al']][0]
        tag_name = attr['InOut'][attr['al']].attrib['Name']
        contr = str(attr['Module'][attr['Group']].attrib['Name'] + '\\' + 'Alarms')
    st = f'{klogic_name.text}.{danfoss.text}.{gm.text}.{contr}.{tag_name}'

    for settings in tag_settings:
        if settings.tag == 'KId':
            KId = settings.text
        else:
            if settings.tag == 'PropList':
                if settings.attrib['TagType'] == 'B':
                    ValueType = '2'
                else:
                    ValueType = '1'
    StringID = str(
        'Kl\\St' + str(station) + '\\Cn' + str(syst_num.text) + '\\' + str(danfoss.text) + '\\' +
        str(gm.text) + '\\' + str(contr) + '\\\\' + str(tag_name))

    for a in alrm:
        if a[0] == 'Уставки' or a[0] == 'Потребители' or a[0] == 'Централи':
            for b in a[1]:
                if attr['tag'].alarm_id == b[0]:
                    tag_alarm = b[1]
        else:
            if attr['tag'].alarm_id == a[0]:
                tag_alarm = a[1]

    tag_str = attr['tag'].alarm_id
    xo_type = cutout(contr)['type']
    if attr['tag'].alarm_id == 'A1':
        if xo_type == 'СК' or xo_type == 'НК' or xo_type == 'Серверная':
            tag_alarm = 'A1. Высокая температура К'
            tag_str = str(attr['tag'].alarm_id + 'K')

    if attr['tag'].alarm_id == 'Cutout':
        ust = cutout(contr)['cutout']
        tag_alarm = str(str(ust) + 'c')
        tag_str = str(attr['tag'].alarm_id) + tag_alarm
        if ust == '-50':
            attr['new_product'].add(contr)
    else:
        if attr['tag'].alarm_id == 'A13-high-lim-air':
            ust = cutout(contr)['cutout']
            tag_alarm = str(str(ust) + 'a')
            tag_str = str(attr['tag'].alarm_id) + tag_alarm
            if ust == '-50':
                attr['new_product'].add(contr)

    GroupItem = attr['alarm_tree'].findall('.//GroupItem')
    for child in GroupItem:
        if child[1].text == 'Авария всех компрессоров':
            if child[2].tag == 'Alarms' or child[2].tag == 'temp' + 'Alarms':
                next
            else:
                Alarms = ElementTree.Element('temp' + 'Alarms')
                child.insert(2, Alarms)
        if child[1].text == tag_alarm:
            if child[2].tag == 'Alarms' or child[2].tag == str(tag_str) + 'Alarms':
                next
            else:
                Alarms = ElementTree.Element(str(tag_str) + 'Alarms')
                child.insert(2, Alarms)
                attr['tags_str'].append(tag_str)
            tree_insert(attr['alarm_tree'], './/' + str(tag_str) + 'Alarms', 'Alarm', 0, False)
            str_par = './/' + str(tag_str) + 'Alarms/Alarm'
            tree_insert(attr['alarm_tree'], str_par, 'ID', 0, str(attr['id']))
            tree_insert(attr['alarm_tree'], str_par, 'Name', 1, str(tag_name))
            tree_insert(attr['alarm_tree'], str_par, 'FullName', 2, str(st).replace('\\', '.'))
            if not MeasureUnits:
                n = 2
            else:
                n = 3
                tree_insert(attr['alarm_tree'], str_par, 'MeasureUnits', n, str(MeasureUnits))
            tree_insert(attr['alarm_tree'], str_par, 'ZoneName', n + 1, str(klogic_name.text))
            tree_insert(attr['alarm_tree'], str_par, 'StationName', n + 2, str(StationName))
            tree_insert(attr['alarm_tree'], str_par, 'Passport', n + 3, False)
            tree_insert(attr['alarm_tree'], str_par + '/Passport', 'StationID', 0, str(station))
            tree_insert(attr['alarm_tree'], str_par + '/Passport', 'PassportType', 1, str(222))
            tree_insert(attr['alarm_tree'], str_par + '/Passport', 'GroupID', 2, str(syst_num.text))
            tree_insert(attr['alarm_tree'], str_par + '/Passport', 'PassportID', 3, str(KId))
            tree_insert(attr['alarm_tree'], str_par + '/Passport', 'ValueType', 4, ValueType)
            tree_insert(attr['alarm_tree'], str_par, 'StringID', n + 4, StringID)
    return attr['tags_str']


def alarm(gmget, tree, Module, alarm_xml):
    '''Формирование alarms.xml'''

    try:
        old_alarm = alarms.objects.get(gm=gmget)
        old_alarm.delete()
    except ObjectDoesNotExist:
        pass

    old_xml = alarm_xml.split('media_cdn/')[1]
    gmget_xml = old_xml.split(".")[0]+gmget+"."+old_xml.split(".")[1]
    alarms.objects.create(gm=gmget, xml=gmget_xml)
    new_xml_pass = alarm_xml.split(".")[0] + gmget + "." + alarm_xml.split(".")[1]
    shutil.copyfile(alarm_xml, new_xml_pass)

    new_xml = alarms.objects.get(gm=gmget).xml.path
    alarm_tree = ElementTree.parse(new_xml)
    alarm_root = alarm_tree.getroot()

    tags = GoodTags.get_GoodTagsall()
    central_tags = GoodTags.get_central_tag()
    tags_str = []
    new_product = set()
    id = 1

    for Group in range(len(Module))[1:]:
        central = False
        for InOut in Module[Group][1:]:
            if central:
                break
            else:
                for c_tag in central_tags:
                    if InOut.attrib['Name'] == str(c_tag.Name):
                        central = True
                        break
        for InOut in Module[Group][1:]:
            for tag in tags:
                al = False
                attr = {
                    'tree': tree,
                    'gmget': gmget,
                    'Module': Module,
                    'Group': Group,
                    'InOut': InOut,
                    'tag': tag,
                    'alarm_tree': alarm_tree,
                    'id': id,
                    'al': al,
                    'tags_str': tags_str,
                    'new_product': new_product
                }
                if InOut.attrib['Name'] == 'Alarms':
                    for al in range(len(InOut))[1:]:
                        if InOut[al].attrib['Name'].split(str(al) + "_")[1] == str(tag.Name):
                            if tag.alarm_id != 'None' and tag.alarm_id != '0':
                                alarm_insert(attr)
                                id = id + 1
                if InOut.attrib['Name'] == str(tag.Name):
                    if tag.alarm_id != 'None' and tag.alarm_id != '0':
                        if tag.alarm_id == 'r12':
                            if central:
                                alarm_insert(attr)
                        else:
                            if tag.alarm_id == 'A03-alarm-delay':
                                if not central:
                                    alarm_insert(attr)
                            else:
                                alarm_insert(attr)
                        id = id + 1

    alarms_groups = alarm_root.findall('.//Children')
    for group in alarms_groups:
        item = 0
        while item < len(group):
            if len(group[item]) < 4:
                group.remove(group[item])
            else:
                item = item + 1

    #indent(alarm_root)
    alarm_tree.write(new_xml, encoding='UTF-8')

    with open(new_xml, 'rt', encoding='UTF-8') as file:
        x = file.read()
    with open(new_xml, 'wt', encoding='UTF-8') as file:
        for a in tags_str:
            x = x.replace(str(a) + 'Alarms' + '>', 'Alarms>')
            x = x.replace('tempAlarms /', 'Alarms /')
        file.write(x)

    if len(new_product) > 0:
        return "Alarm XML: Новый вид продукта" + str(new_product)
    else:
        return "Alarm XML: Обработка завершена"


def index(request):
    form = KlogicForm()
    context = {'form': form}
    if request.method == 'POST':
        gmget = request.POST.get('gm')
        context['gm'] = gmget
        try:
            xml = klogic.objects.get(gm=gmget).xml.path
            bdtp_checkbox = request.POST.get('bd')
            alarm_checkbox = request.POST.get('alarm')
            h_remove(xml)
            tree = ElementTree.parse(xml)
            Module = tree.find('.//Module')
            try:
                print(Module.tag)
                bad_tags = BadTags.get_BadTagsall()
                len_new_tags = new_tags(Module, bad_tags)
            except AttributeError:
                context['text_kl'] = "Klogic XML: Неправильный формат"
        except (ObjectDoesNotExist, FileNotFoundError):
            context['text_kl'] = "Klogic XML не найден"

        if len_new_tags > 0:
            context['text'] = "Новые переменные:"
            context['len_new_tags'] = len_new_tags
        else:
            delete_tags(Module, bad_tags)
            add_comment(Module)
            noffl(tree)
            tree.write(xml)
            shift(Module, gmget)
            if bdtp_checkbox:
                print('bdtp_checkbox:', bdtp_checkbox)
                try:
                    klogger_xml = klogger.objects.get(gm=gmget).xml.path
                    klogger_tree = ElementTree.parse(klogger_xml)
                    DBVersion = klogger_tree.find('.//DBVersion')
                    try:
                        print(DBVersion.tag)
                        context['text_bdtp'] = bdtp(gmget, tree, Module, klogger_xml, klogger_tree)
                    except AttributeError:
                        context['text_bdtp'] = "Klogger XML: Неправильный формат"
                except (ObjectDoesNotExist, FileNotFoundError):
                    context['text_bdtp'] = "Klogger XML не найден"
            if alarm_checkbox:
                print('alarm_checkbox:', alarm_checkbox)
                try:
                    alarm_xml = alarms.objects.get(gm='default_alarm_xml').xml.path
                    alarm_tree = ElementTree.parse(alarm_xml)
                    GroupItem = alarm_tree.find('.//GroupItem')
                    try:
                        print(GroupItem.tag)
                        context['text_al'] = alarm(gmget, tree, Module, alarm_xml)
                    except AttributeError:
                        context['text_al'] = "Alarm XML: Неправильный формат"
                except (ObjectDoesNotExist, FileNotFoundError):
                    context['text_al'] = "Alarm XML не найден"

            context['text_kl'] = "Klogic XML: Обработка завершена"

    return render(request, 'xoxml/index.html', context)
