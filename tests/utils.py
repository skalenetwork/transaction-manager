""" SKALE test utilities """

import json


def get_bp_data(bp, request, params=None, plain_response=False, **kwargs):
    response = bp.get(request, query_string=params, **kwargs)
    if plain_response:
        return response

    return json.loads(response.data.decode('utf-8'))


def post_bp_data(bp, request, params=None, plain_response=False, **kwargs):
    response = bp.post(request, json=params)
    if plain_response:
        return response
    return json.loads(response.data.decode('utf-8'))
