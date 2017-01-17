# -*- coding: utf-8 -*-
"""Transform input to dpd compatible xml."""
from jinja2 import Environment, PackageLoader
from roulier.codec import Encoder
from datetime import datetime
from .dpd_api import DpdApi
import logging

DPD_ACTIONS = ('createShipmentWithLabels')
log = logging.getLogger(__name__)


class DpdEncoder(Encoder):
    """Transform input to dpd compatible xml."""

    def encode(self, api_input, action):
        """Transform input to dpd compatible xml."""
        if not (action in DPD_ACTIONS):
            raise Exception(
                'action %s not in %s' % (action, ', '.join(DPD_ACTIONS)))

        api = DpdApi()
        if not api.validate(api_input):
            raise Exception(
                'Input error : %s' % api.errors(api_input))
        data = api.normalize(api_input)

        # add some rules which are hard to implement with
        # cerberus.
        # TODO: add additional schemas for that
        if data['service']['product'] == 'DPD_Predict':
            if len(data['service']['dropOffLocation']) > 0:
                raise Exception(
                    "dropOffLocation can't be used with predict")
            if data['service']['notifications'] != 'Predict':
                log.info(
                    'Notification forced to predict because of product')
                data['service']['notifications'] = 'Predict'

        if data['service']['product'] == 'DPD_Classic':
            if len(data['service']['dropOffLocation']) > 0:
                raise Exception(
                    "dropOffLocation can't be used with classic")
            if data['service']['notifications'] == 'Predict':
                raise Exception(
                    "Predict notifications can't be used with classic")

        if data['service']['product'] == 'DPD_Relais':
            if len(data['service']['dropOffLocation']) < 1:
                raise Exception(
                    "dropOffLocation is mandatory for this product")
            if data['service']['notifications'] == 'Predict':
                raise Exception(
                    "Predict notifications can't be used with Relais")

        data['service']['shippingDate'] = (
            datetime
            .strptime(data['service']['shippingDate'], '%Y/%M/%d')
            .strftime('%d/%M/%Y')
        )

        if data['service']['labelFormat'] in ('PNG', 'ZPL'):
            # WS doesn't handle zpl yet, we convert it later
            # png is named Default, WTF DPD?
            data['service']['labelFormat'] = 'Default'

        env = Environment(
            loader=PackageLoader('roulier', '/carriers/dpd/templates'),
            extensions=['jinja2.ext.with_'])

        template = env.get_template("dpd_%s.xml" % action)
        return {
            "body": template.render(
                service=data['service'],
                parcel=data['parcel'],
                sender_address=data['from_address'],
                receiver_address=data['to_address']),
            "headers": data['auth']
        }

    def api(self):
        """Return API we are expecting."""
        return DpdApi().api_values()
