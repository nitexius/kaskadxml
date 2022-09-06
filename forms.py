from django import forms


class KlogicForm(forms.Form):
    gm = forms.CharField(label='Код ГМ')
