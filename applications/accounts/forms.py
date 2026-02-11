from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Nama Depan", max_length=100, required=True)
    last_name = forms.CharField(label="Nama Belakang", max_length=100, required=False)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')