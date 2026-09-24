import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.utils import timezone

from .models import Usuario, validar_celular, validar_dni


def solo_digitos(texto):
    return re.sub(r'\D', '', texto or '')


class RegistroForm(forms.ModelForm):
    # Se aceptan espacios o guiones al escribir ("987 654 321"); se guardan solo los dígitos
    celular = forms.CharField(
        label='Celular (WhatsApp)', max_length=15,
        widget=forms.TextInput(attrs={'autocomplete': 'tel', 'inputmode': 'numeric', 'placeholder': '9XX XXX XXX'}),
    )
    dni = forms.CharField(
        label='DNI', max_length=12,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'placeholder': '8 dígitos'}),
    )
    password1 = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Mínimo 8 caracteres. Evita contraseñas muy comunes o solo con números.',
    )
    password2 = forms.CharField(
        label='Repite tu contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    codigo_referida = forms.CharField(
        label='¿Te invitó una amiga? Escribe su código (opcional)', required=False, max_length=20,
        help_text='Cuando compres tu primer paquete desde Atempo 5, las dos recibirán 1 crédito extra.',
        widget=forms.TextInput(attrs={'placeholder': 'Por ejemplo: MARIA-7K3Q', 'autocapitalize': 'characters'}),
    )
    acepto_privacidad = forms.BooleanField(
        required=True,
        error_messages={'required': 'Para crear tu cuenta necesitas aceptar la política de privacidad.'},
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'email', 'celular', 'dni']
        widgets = {
            'nombre': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'apellido': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }
        error_messages = {
            'email': {'unique': 'Ya existe una cuenta con este correo. ¿Quieres iniciar sesión?'},
            'celular': {'unique': 'Ya existe una cuenta con este celular. ¿Quieres iniciar sesión?'},
            'dni': {'unique': 'Ya existe una cuenta con este DNI.'},
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(self._meta.error_messages['email']['unique'])
        return email

    def clean_celular(self):
        celular = solo_digitos(self.cleaned_data.get('celular'))
        validar_celular(celular)
        if Usuario.objects.filter(celular=celular).exists():
            raise forms.ValidationError(self._meta.error_messages['celular']['unique'])
        return celular

    def clean_dni(self):
        dni = solo_digitos(self.cleaned_data.get('dni'))
        validar_dni(dni)
        if Usuario.objects.filter(dni=dni).exists():
            raise forms.ValidationError(self._meta.error_messages['dni']['unique'])
        return dni

    def clean_codigo_referida(self):
        from compras.referidas import buscar_por_codigo

        codigo = self.cleaned_data.get('codigo_referida', '').strip()
        if not codigo:
            return None
        invitadora = buscar_por_codigo(codigo)
        if invitadora is None:
            raise forms.ValidationError('No encontramos ese código. Revisa que esté bien escrito.')
        return invitadora

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password1', error)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        usuario.acepto_privacidad = timezone.now()
        usuario.referida_por = self.cleaned_data.get('codigo_referida')
        if commit:
            usuario.save()
        return usuario


class IngresarForm(AuthenticationForm):
    username = forms.CharField(
        label='Correo o celular',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    error_messages = {
        'invalid_login': 'El correo, el celular o la contraseña no son correctos. Revísalos e inténtalo de nuevo.',
        'inactive': 'Esta cuenta está desactivada.',
    }


class RecuperarForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))


class NuevaClaveForm(SetPasswordForm):
    """Igual que el de Django, con etiquetas en nuestro tono."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Nueva contraseña'
        self.fields['new_password1'].help_text = 'Mínimo 8 caracteres. Evita contraseñas muy comunes o solo con números.'
        self.fields['new_password2'].label = 'Repite tu nueva contraseña'
