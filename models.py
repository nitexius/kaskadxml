from django.db import models


class klogic(models.Model):
    '''xml klogic ИС Диспетчеризация ХО'''
    gm = models.CharField(max_length=100, verbose_name='Код ГМ', unique=True)
    xml = models.FileField(upload_to='media/klogic')

    class Meta:
        ordering = ['gm']
        verbose_name = 'Klogic XML'
        verbose_name_plural = 'Klogic XML'

    def __str__(self):
        return self.gm


class history_tags(models.Model):
    '''Служебные символы в названии переменной'''
    htags = models.CharField(max_length=30)

    class Meta:
        ordering = ['htags']
        verbose_name = '[H_   ]'
        verbose_name_plural = '[H_   ]'

    @classmethod
    def get_htagsall(cls):
        result = []
        for h in cls.objects.all():
            tag = h.htags
            tag = tag.replace('"', "")
            result.append(tag)
        return result

    def __str__(self):
        return self.htags


class GoodTags(models.Model):
    '''Используемые переменные'''
    Name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)
    alarm_id = models.IntegerField(default='0', verbose_name='Код аварии')
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')

    class Meta:
        ordering = ['Name']
        verbose_name = 'Используемая переменная'
        verbose_name_plural = 'Используемые переменные'

    @classmethod
    def get_GoodTagsall(cls):
        GoodTag = GoodTags.objects.all()
        return GoodTag

    @classmethod
    def get_noffl_tags(cls):
        nofflTag = GoodTags.objects.filter(noffl='1')
        return nofflTag

    def __str__(self):
        return self.Name


class BadTags(models.Model):
    '''Удаляемые переменные'''
    Name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)

    class Meta:
        ordering = ['Name']
        verbose_name = 'Удаляемая переменная'
        verbose_name_plural = 'Удаляемые переменные'

    @classmethod
    def get_BadTagsall(cls):
        BadTag = BadTags.objects.all()
        return BadTag

    def __str__(self):
        return self.Name


class NewTags(models.Model):
    '''Новые переменные, отсутсвующие в GoodTags, BadTags'''
    Name = models.CharField(max_length=100, verbose_name='Название переменной')
    Controller = models.CharField(max_length=100, default="", verbose_name='Название контроллера')

    class Meta:
        verbose_name = 'Новая переменная'
        verbose_name_plural = 'Новые переменные'

    @classmethod
    def delete_NewTagsall(cls):
        NewTag = NewTags.objects.all()
        NewTag.delete()

    def __str__(self):
        return self.Name
