from django.conf.urls import include, url

from pretix.multidomain import event_url

from .views import back, callback

event_patterns = [
    url(r'^woopay/', include([
        
        url(r'^back/$', back, name='back'),
        url(r'w/(?P<cart_namespace>[a-zA-Z0-9]{16})/back/', back, name='back'),

        
    ])),
]


urlpatterns = [
    url(r'^woopay/callback/$', callback, name='callback'),
]
