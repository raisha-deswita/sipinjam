from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.accounts'

    def ready(self):
        import applications.accounts.signals