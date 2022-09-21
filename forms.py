from django import forms


class KlogicForm(forms.Form):
    gm = forms.CharField(label='Код ГМ')
    bd = forms.BooleanField(label='Сформировать Klogger XML', required=False)
    alarm = forms.BooleanField(label='Сформировать Alarms XML', required=False)
