from django.db import models
from .kaskad_xml import alrm, xo_choices

TAG_TYPES = (
    ('1', 'good_tag'),
    ('2', 'bad_tag'),
    ('3', 'new_tag'),
)


class Alarm(models.Model):
    """Xml Аварии ИС Диспетчеризация ХО"""
    gm = models.CharField(max_length=100, verbose_name='Код ГМ', unique=True)
    xml = models.FileField(upload_to='media/alarms')

    class Meta:
        ordering = ['gm']
        verbose_name = 'Alarm'
        verbose_name_plural = 'Alarms'

    def __str__(self):
        return self.gm


class Cutout(models.Model):
    """Уставки для продуктов (Контроль уставок)"""
    name = models.CharField(max_length=100, verbose_name='Наименование продукта', unique=True)
    cutout = models.IntegerField(default=-50, verbose_name='Уставка')
    xo_type = models.CharField(max_length=100, default='None', verbose_name='Серверная/Машзал/Камеры', choices=xo_choices)

    class Meta:
        ordering = ['name']
        verbose_name = 'Контроль уставок'
        verbose_name_plural = 'Контроль уставок'

    @classmethod
    def get_products_values(cls):
        return list(cls.objects.values('name', 'cutout', 'xo_type'))

    def __str__(self):
        return self.name


class HistoryAttr(models.Model):
    """Служебные символы в названии переменной"""
    h_attr = models.CharField(max_length=30)

    class Meta:
        ordering = ['h_attr']
        verbose_name = '[H_   ]'
        verbose_name_plural = '[H_   ]'

    @classmethod
    def get_h_attrs(cls):
        result = []
        for h in cls.objects.all():
            attr = h.h_attr
            attr = attr.replace('"', "")
            result.append(attr)
        return result

    def __str__(self):
        return self.h_attr


class Tag(models.Model):
    """Используемые переменные"""
    name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)                #
    tag_type = models.CharField(
        max_length=100,
        verbose_name='Тип переменной',
        choices=TAG_TYPES
    )
    alarm_id = models.CharField(max_length=100, default='None', verbose_name='Код аварии', choices=alrm)    #
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')
    controller = models.CharField(max_length=100, default="", verbose_name='Название контроллера')

    class Meta:
        ordering = ['name']
        verbose_name = 'Переменная'
        verbose_name_plural = 'Переменные'

    @classmethod
    def get_tags_names(cls):
        return cls.objects.exclude(tag_type='3').values('id', 'name')

    @classmethod
    def get_noffl_tags(cls):
        return cls.objects.filter(noffl='1').values('name')

    @classmethod
    def get_alarm_tags(cls):
        return cls.objects.exclude(alarm_id__in=['0', 'None']).values('name', 'alarm_id')

    @classmethod
    def get_bdtp_tags(cls):
        return cls.objects.filter(bdtp='1').values()

    @classmethod
    def get_bad_tags(cls):
        return cls.objects.filter(tag_type='2').values()

    def __str__(self):
        return self.name

