import json
import logging
import urllib.parse
import requests
import random, string
import xml.dom.minidom
from collections import OrderedDict
from pprint import pprint

from django import forms
from django.contrib import messages
from django.core import signing
from django.template.loader import get_template
from django.template.loader import render_to_string
from django.utils.translation import ugettext as __, ugettext_lazy as _

from bs4 import BeautifulSoup
from pretix.base.decimal import round_decimal
from pretix.base.models import Order, Quota, RequiredAction
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.services.mail import SendMailException
from pretix.base.services.orders import mark_order_paid, mark_order_refunded
from pretix.helpers.urls import build_absolute_uri as build_global_uri
from pretix.multidomain.urlreverse import build_absolute_uri
from .models import ReferencedWoopayObject
from .models import SessionWoopayObject
from pretix.base.settings import SettingsSandbox
logger = logging.getLogger('pretix.plugins.woopay')

WOOPAY_TEST_URL = 'https://www.test.wooppay.com/api/wsdl?ws=1'
WOOPAY_PRODUCTION_URL='https://www.wooppay.com/api/wsdl?ws=1'
WOOPAY_TEST_USER = 'test_merch'
WOOPAY_TEST_PASSWORD = 'A12345678a'

class Woopay(BasePaymentProvider):
    identifier = 'woopay'
    verbose_name = _('Wooppay')
    payment_form_fields = OrderedDict([
    ])
    

    @property
    def settings_form_fields(self):
        d = OrderedDict(
        [
                ('server',
                 forms.ChoiceField(
                     label=_('Server'),
                     initial='test',
                     choices=(
                         ('live', _('Live')),
                         ('test', _('Test')),
                     ),
                 )),
                 ('login',
                 forms.CharField(
                     label=_('Login'),
                     max_length=80,
                     initial=WOOPAY_TEST_USER
                 )),
                ('password',
                 forms.CharField(
                     label=_('Password'),
                     max_length=80,
                     widget = (forms.PasswordInput()),
                     initial = WOOPAY_TEST_PASSWORD
                    
                 )),
                 ('site_url',
                 forms.CharField(
                     label=_('Site URL'),
                     max_length=80,
                 ))
            ] +list(super().settings_form_fields.items())
        )
        d.move_to_end('_enabled', last=False)
        return d
    def payment_is_valid_session(self, request):
        return True

    def payment_form_render(self, request) -> str:
        template = get_template('woopay/checkout_payment_form.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)


    def checkout_confirm_render(self,request):

        return None
    def get_payment_status(self,order):
        woop=ReferencedWoopayObject.objects.get(order=order)
        if(self.settings.get('server')=='test'):
            url=WOOPAY_TEST_URL
        else: 
            url=WOOPAY_PRODUCTION_URL
        template = get_template('woopay/cash_getOperationData.xml')
        ctx={'code':woop.reference}
        db_session=SessionWoopayObject.objects.get(id=1)
        body=template.render(ctx)
    
        headers={'Content-Type':'application/xml','Cookie':'session='+db_session.session+';'}
        r = requests.post(url, data=body,headers=headers)
        
        soup = BeautifulSoup(r.text,"lxml")

        if(soup.error_code.text!='0'):
            self._woopay_login()
            self.get_payment_status(woop.order)
        else:
            print(soup.status.text)
            if(soup.status.text=='3'):
                order.status=Order.STATUS_CANCELED
                order.save()
            
            if(soup.status.text=='4'):
                mark_order_paid(order, 'woopay')
        
        

    def order_pending_render(self, request, order) -> str:
        
        woop=ReferencedWoopayObject.objects.get(order=order)
        if(order.status!=Order.STATUS_PAID):
            self.get_payment_status(order)
        template = get_template('woopay/pending.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings,
             'order': order,'status':order.status,'link':woop.url}
        return template.render(ctx)

    def _woopay_login(self):

        template = get_template('woopay/login.xml')
        ctx={
            'login':self.settings.get('login'),
            'password':self.settings.get('password')
        }
        body=template.render(ctx)
        
        if(self.settings.get('server')=='test'):
            url=WOOPAY_TEST_URL
        else: 
            url=WOOPAY_PRODUCTION_URL
        
        headers={'Content-Type':'application/xml'}
        r = requests.post(url, data=body,headers=headers)
        
        soup = BeautifulSoup(r.text,"lxml")
        print(soup)
        
        if(soup.error_code.text=='0'):
            db_item=SessionWoopayObject.objects.get_or_create(id=1)
            if db_item:
                db_item=SessionWoopayObject.objects.get(id=1)
                db_item.session=soup.session.text
                db_item.save()
            
        return None
    def generate_random_key(self):
        rand_str = lambda n: ''.join([random.choice(string.ascii_lowercase) for i in xrange(n)])
        key=rand_str(15)
        m=ReferencedWoopayObject.objects.filter(key=key).first()
        if m:
            self.generate_random_key()
        else:
            return key


    def payment_perform(self, request, order) -> str:
        
        kwargs = {}
        if request.resolver_match and 'cart_namespace' in request.resolver_match.kwargs:
            kwargs['cart_namespace'] = request.resolver_match.kwargs['cart_namespace']
        if(self.settings.get('server')=='test'):
            url=WOOPAY_TEST_URL
        else: 
            url=WOOPAY_PRODUCTION_URL
        url_back=self.settings.get('site_url')+'/'+order.event.organizer.slug+'/'+order.event.slug+'/woopay/'
        
       
        self._woopay_login()
        template = get_template('woopay/cash_createInvoice.xml')
        key=self.generate_random_key()
        ctx={
            'referenceId':order.code,
            'backUrl':url_back+'back?order='+order.code,
            'requestUrl':url_back+'callback?key='+key,
            'amount':int(order.total),
        }
        db_session=SessionWoopayObject.objects.get(id=1)
        body=template.render(ctx)
        
        headers={'Content-Type':'application/xml','Cookie':'session='+db_session.session+';'}
        r = requests.post(url, data=body,headers=headers)
        
        soup = BeautifulSoup(r.text,"lxml")
        print(soup)
        
        if(soup.error_code.text=='0'):
            logger.info("woopay  data {0}"+soup.operationid.text+" url "+soup.operationurl.text)
            pay=ReferencedWoopayObject.objects.get_or_create(order=order, reference=soup.operationid.text,url=soup.operationurl.text,key=key)
            return  soup.operationurl.text
        
        return None