from django.shortcuts import render
from xml.etree import ElementTree
from .models import history_tags, GoodTags, BadTags, NewTags, klogic
from .forms import KlogicForm
from .fb_noffl import nfb


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
    k = 0
    for tag in tags:
        all_id.add(tag.id)
        if child.attrib['Name'] != tag.Name:
            k = k + 1
    return k


def new_tags(Module, bad_tags):
    '''Проверка на ноыве переменные'''
    NewTags.delete_NewTagsall()
    good_tags = GoodTags.get_GoodTagsall()
    new_tags = []
    all_id = set()

    for contr in range(len(Module))[3:]:
        for child in Module[contr][1:]:
            m = 0
            for p in new_tags:
                if child.attrib['Name'] != p['Name']:
                    m = m + 1
            if m == len(new_tags):
                if check_new_tag(child, bad_tags, all_id) == len(bad_tags):
                    if check_new_tag(child, good_tags, all_id) == len(good_tags):
                        print('Новый параметр:', Module[contr].attrib['Name'], child.attrib['Name'])
                        new_tags.append({'Controller': Module[contr].attrib['Name'], 'Name': child.attrib['Name']})
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


def noffl(tree):
    '''Привязка входов к функциональном блокам noffl'''
    root = tree.getroot()
    danfoss = tree.find('.//TasksGroup1/Protocol/Settings/Name')
    gm = tree.find('.//TasksGroup1/Protocol/Module/Settings/Name')
    Groups = tree.find('.//TasksGroup1/Protocol/Module')
    fsection = tree.find('.//UserTask')
    teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'
    task_name = tree.find('.//UserTask/Settings/Name')

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
    te = tree.find('.//TasksGroup0/UserTask/Settings')
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


def index(request):
    form = KlogicForm()
    context = {'form': form}
    if request.method == 'POST':
        gmget = request.POST.get('gm')
        context['gm'] = gmget
        xml = klogic.objects.get(gm=gmget).xml.path
        h_remove(xml)
        tree = ElementTree.parse(xml)
        Module = tree.find('.//Module')
        bad_tags = BadTags.get_BadTagsall()
        len_new_tags = new_tags(Module, bad_tags)
        if len_new_tags > 0:
            context['text'] = "Новые переменные:"
            context['len_new_tags'] = len_new_tags
        else:
            delete_tags(Module, bad_tags)
            add_comment(Module)
            noffl(tree)
            tree.write(xml)
            context['text'] = "Обработка завершена"

    return render(request, 'xoxml/index.html', context)
