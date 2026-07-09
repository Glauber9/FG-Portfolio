from django import forms


class ImportarContatosForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo',
        help_text='Envie um CSV ou XLSX com colunas como nome, telefone e email.',
    )