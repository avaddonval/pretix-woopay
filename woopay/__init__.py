from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class PluginApp(AppConfig):
    name = 'woopay'
    verbose_name = 'Woopay payment'

    class PretixPluginMeta:
        name = ugettext_lazy('Woopay payment')
        author = 'cybersec'
        description = ugettext_lazy('Short description')
        visible = True
        version = '1.0.0'

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'woopay.PluginApp'
