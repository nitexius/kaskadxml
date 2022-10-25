from django.db import models
from .kaskad_xml import alrm, xo_choices


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
    xo_type = models.CharField(max_length=100, default='None', verbose_name='Серверная/Машзал', choices=xo_choices)

    class Meta:
        ordering = ['name']
        verbose_name = 'Контроль уставок'
        verbose_name_plural = 'Контроль уставок'

    @classmethod
    def get_products_values(cls):
        products = list(cls.objects.all().values())
        return products

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
    name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)

    class Meta:
        abstract = True
        ordering = ['name']

    @classmethod
    def get_tags_values(cls):
        tags = list(cls.objects.all().values())
        return tags


class GoodTag(Tag):
    """Используемые переменные"""
    alarm_id = models.CharField(max_length=100, default='None', verbose_name='Код аварии', choices=alrm)
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')

    class Meta(Tag.Meta):
        verbose_name = 'Используемая переменная'
        verbose_name_plural = 'Используемые переменные'

    @classmethod
    def get_bdtp_tags(cls):
        bdtp_tags = list(cls.objects.filter(bdtp='1').values())
        return bdtp_tags

    def __str__(self):
        return self.name


class BadTag(Tag):
    """Удаляемые переменные"""

    class Meta(Tag.Meta):
        verbose_name = 'Удаляемая переменная'
        verbose_name_plural = 'Удаляемые переменные'

    def __str__(self):
        return self.name


class NewTag(Tag):
    """Новые переменные, отсутсвующие в GoodTags, BadTags"""
    controller = models.CharField(max_length=100, default="", verbose_name='Название контроллера')
    alarm_id = models.CharField(max_length=100, default='None', verbose_name='Код аварии', choices=alrm)
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')

    class Meta:
        verbose_name = 'Новая переменная'
        verbose_name_plural = 'Новые переменные'

    @classmethod
    def delete_new_tags_all(cls):
        new_tag = cls.objects.all()
        new_tag.delete()

    def __str__(self):
        return self.name
