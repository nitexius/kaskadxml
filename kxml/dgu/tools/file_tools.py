import pathlib
from dataclasses import dataclass
from typing import Callable
from io import BytesIO
from kaskadxml.tools import OutputFiles, get_input_file
from kaskadxml.kaskad_xml import DefaultAlarmError
from dgu.models import Alarm_dgu
from dgu.kaskad_xml import KlogicXML, AlarmsXML


# @dataclass
# class OutputFiles:
#     name: str
#     file: bytes


# def get_input_file(file):
#     """ Получение исходного файла в виде BytesIO """
#     input_file = BytesIO(file)
#     input_file.seek(0)
#     return input_file


def set_klogic_xml(form):
    """ Создание класса KlogicXML """
    xml_file = form.cleaned_data['klogic_file']
    protocols = form.cleaned_data['protocol_name']
    PROT_CODE = '78'
    input_file = get_input_file(
        file=xml_file.read()
    )
    return KlogicXML(input_file, PROT_CODE, protocols, xml_file.name)


def get_default_alarm_xml_path() -> pathlib.Path:
    """ Получение пути к шаблону аварий """
    try:
        default_alarm_xml_path = Alarm_dgu.objects.get(gm='default_alarm_xml').xml.path
    except (Alarm_dgu.DoesNotExist, FileNotFoundError):
        raise DefaultAlarmError('Шаблон Alarm XML не найден')
    return default_alarm_xml_path


def set_alarms_xml(args):
    """ Создание класса AlarmsXML """
    return AlarmsXML(get_default_alarm_xml_path(), args.klogic_xml.klogic_tree_find(), args.station_id)


# def create_output_file(kaskad_module: KlogicXML) -> OutputFiles:
#     """ Получение готовых файлов """
#     output_file = BytesIO()
#     kaskad_module.write(output_file)
#     return OutputFiles(
#         name=kaskad_module.xml_file_name,
#         file=output_file.getbuffer()
#     )
#
#
# def transform_file(in_file_handler: Callable, output_file_handler: Callable, params):
#     """ Преобразование файлов конфигураций """
#     file = in_file_handler(params)
#     return output_file_handler(file, params)
