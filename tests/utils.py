""" SKALE test utilities """

import json


def get_bp_data(bp, request, params=None, plain_response=False, **kwargs):
    json_response = bp.get(request, query_string=params, **kwargs).data
    if plain_response:
        return json_response

    return json.loads(json_response.decode('utf-8'))


def post_bp_data(bp, request, params=None, plain_response=False, **kwargs):
    json_response = bp.post(request, json=params).data
    if plain_response:
        return json_response
    return json.loads(json_response.decode('utf-8'))
