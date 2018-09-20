import json
import logging
from .models import ReferencedWoopayObject
from .payment import Woopay
from django.contrib import messages
from django.core import signing
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pretix.base.models import Order, Quota, RequiredAction
from pretix.base.payment import PaymentException
from pretix.base.services.orders import mark_order_paid
from pretix.control.permissions import event_permission_required
from pretix.multidomain.urlreverse import eventreverse


logger = logging.getLogger('pretix.plugins.woopay')


def back(request, *args, **kwargs):
    if request.GET.get('order'):
        try:
            order = Order.objects.get(code=request.GET.get('order'))
        except:
            order = None
    else:
        order = None
    if order:
        return redirect(eventreverse(request.event, 'presale:event.order', kwargs={
            'order': order.code,
            'secret': order.secret
        }) + ('?paid=yes' if order.status == Order.STATUS_PAID else ''))
    else:
        return redirect(eventreverse(request.event,'presale:event.checkout.start'))
def callback(request, *args, **kwargs):
    if request.GET.get('key'):
        key=request.GET.get('key')
        logger.info("woopay callback data {0}"+key)
        woopay=ReferencedWoopayObject.objects.filter(key=key).first()
        if woopay:
            if(woopay.order.status!=Order.STATUS_PAID):
                mark_order_paid(woopay.order, 'woopay', key)
            return HttpResponse('{"data":1}')
        else:
            response = HttpResponse()
            response.status_code=404
            return response
    else:
        response = HttpResponse()
        response.status_code=404
        return response