from django import forms

from .models import Cita


class FichaNutricionForm(forms.Form):
    """
    Ficha breve que se pide al agendar una evaluación. La nutricionista completa el resto en la cita.
    Son datos de salud (datos sensibles, Ley N.° 29733): se pide consentimiento expreso.
    """
    objetivo = forms.ChoiceField(label='¿Cuál es tu objetivo principal?', choices=[('', 'Elige una opción')] + Cita.OBJETIVOS)
    alergias = forms.CharField(
        label='Alergias o restricciones alimentarias', max_length=200,
        help_text='Por ejemplo: "lactosa", "vegetariana". Si no tienes, escribe "Ninguna".')
    condiciones = forms.CharField(
        label='Condiciones de salud que la nutricionista deba saber (opcional)', max_length=300, required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Por ejemplo: hipertensión, diabetes, tiroides. Puedes dejarlo vacío y conversarlo en la cita.')
    consentimiento = forms.BooleanField(
        label='Autorizo a Atempo a usar estos datos de salud solo para mi asesoría nutricional.',
        error_messages={'required': 'Para agendar la evaluación necesitamos tu autorización para usar estos datos.'})
