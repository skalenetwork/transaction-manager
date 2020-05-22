""" SKALE test utilities """

import json


def get_bp_data(bp, request, params=None):
    data = bp.get(request, query_string=params).data
    return json.loads(data.decode('utf-8'))['data']


def post_bp_data(bp, request, params=None):
    data = bp.post(request, json=params).data
    return json.loads(data.decode('utf-8'))['data']
