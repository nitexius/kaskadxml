# import pathlib
# import zipfile
# from dataclasses import dataclass
# from typing import List, Callable
# from io import BytesIO
# from kaskadxml.models import Alarm, Cutout
# from kaskadxml.kaskad_xml import KlogicXML, KloggerXML, AlarmsXML, DefaultAlarmError, c
# from .shift_tools import shift_create
#
#
# @dataclass
# class OutputFiles:
#     name: str
#     file: bytes
#
#
# def get_input_file(file):
#     """ Получение исходного файла в виде BytesIO """
#     input_file = BytesIO(file)
#     input_file.seek(0)
#     return input_file
#
#
# def set_klogic_xml(form):
#     """ Создание класса KlogicXML """
#     xml_file = form.cleaned_data['klogic_file']
#     PROT_CODE = '244'
#     input_file = get_input_file(
#         file=xml_file.read()
#     )
#     return KlogicXML(input_file, PROT_CODE, xml_file.name)
#
#
# def set_klogger_xml(args):
#     """ Создание класса KloggerXML """
#     klogger_xml_file = args.form.cleaned_data['klogger_file']
#     klogger_input_file = get_input_file(
#         file=klogger_xml_file.read()
#     )
#     return KloggerXML(klogger_input_file, args.klogic_xml.klogic_tree_find(), args.station_id, klogger_xml_file.name)
#
#
# def get_default_alarm_xml_path() -> pathlib.Path:
#     """ Получение пути к шаблону аварий """
#     try:
#         default_alarm_xml_path = Alarm.objects.get(gm='default_alarm_xml').xml.path
#     except (Alarm.DoesNotExist, FileNotFoundError):
#         raise DefaultAlarmError('Шаблон Alarm XML не найден')
#     return default_alarm_xml_path
#
#
# def set_alarms_xml(args):
#     """ Создание класса AlarmsXML """
#     return AlarmsXML(get_default_alarm_xml_path(), args.klogic_xml.klogic_tree_find(), args.station_id,
#                      Cutout.get_products_values())
#
#
# def create_output_file(kaskad_module: KlogicXML or AlarmsXML or KloggerXML) -> OutputFiles:
#     """ Получение готовых файлов """
#     output_file = BytesIO()
#     kaskad_module.write(output_file)
#     return OutputFiles(
#         name=kaskad_module.xml_file_name,
#         file=output_file.getbuffer()
#     )
#
#
# def create_shift_output_file(klogic_xml):
#     """ Получение готового файла со смещениями адресов контроллеров """
#     return OutputFiles(
#         name=c.shift_file_name,
#         file=shift_create(klogic_xml).getbuffer()
#     )
#
#
# def transform_file(in_file_handler: Callable, output_file_handler: Callable, params):
#     """ Преобразование файлов конфигураций """
#     file = in_file_handler(params)
#     return output_file_handler(file, params)
#
#
# def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
#     """ Создание архива готовых файлов """
#     for file in files:
#         with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
#             zip_file.writestr(file.name, file.file)
#     return zip_buffer


import pathlib
import zipfile
from dataclasses import dataclass
from typing import List, Callable
from io import BytesIO
from kaskadxml.models import Alarm, Cutout
from kaskadxml.kaskad_xml import KlogicXML, KloggerXML, AlarmsXML, DefaultAlarmError, c
from .shift_tools import shift_create


@dataclass
class OutputFiles:
    name: str
    file: bytes


def get_input_file(file):
    """ Получение исходного файла в виде BytesIO """
    input_file = BytesIO(file)
    input_file.seek(0)
    return input_file


def set_klogic_xml(form):
    """ Создание класса KlogicXML """
    xml_file = form.cleaned_data['klogic_file']
    PROT_CODE = '244'
    input_file = get_input_file(
        file=xml_file.read()
    )
    return KlogicXML(input_file, PROT_CODE, xml_file.name)


def set_klogger_xml(args):
    """ Создание класса KloggerXML """
    klogger_xml_file = args.form.cleaned_data['klogger_file']
    klogger_input_file = get_input_file(
        file=klogger_xml_file.read()
    )
    return KloggerXML(klogger_input_file, args.klogic_xml.klogic_tree_find(), args.station_id, klogger_xml_file.name)


def get_default_alarm_xml_path() -> pathlib.Path:
    """ Получение пути к шаблону аварий """
    try:
        default_alarm_xml_path = Alarm.objects.get(gm='default_alarm_xml').xml.path
    except (Alarm.DoesNotExist, FileNotFoundError):
        raise DefaultAlarmError('Шаблон Alarm XML не найден')
    return default_alarm_xml_path


def set_alarms_xml(args):
    """ Создание класса AlarmsXML """
    return AlarmsXML(get_default_alarm_xml_path(), args.klogic_xml.klogic_tree_find(), args.station_id,
                     Cutout.get_products_values())


def create_output_file(kaskad_module: KlogicXML or AlarmsXML or KloggerXML) -> OutputFiles:
    """ Получение готовых файлов """
    output_file = BytesIO()
    kaskad_module.write(output_file)
    return OutputFiles(
        name=kaskad_module.xml_file_name,
        file=output_file.getbuffer()
    )


def create_shift_output_file(klogic_xml):
    """ Получение готового файла со смещениями адресов контроллеров """
    return OutputFiles(
        name=c.shift_file_name,
        file=shift_create(klogic_xml).getbuffer()
    )


def transform_file(in_file_handler: Callable, output_file_handler: Callable, params):
    """ Преобразование файлов конфигураций """
    file = in_file_handler(params)
    return output_file_handler(file, params)


def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
    """ Создание архива готовых файлов """
    for file in files:
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr(file.name, file.file)
    return zip_buffer
