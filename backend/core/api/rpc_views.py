import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .rpc_dispatcher import rpc_dispatcher

@csrf_exempt
def json_rpc_view(request):
    """
    JSON-RPC 2.0 Handler Endpoint for Django.
    Accessible at: /api/rpc/
    """
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    if request.method != "POST":
        return JsonResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "JSON-RPC endpoint only accepts POST requests."},
            "id": None
        }, status=405)

    response_data = rpc_dispatcher.dispatch(
        raw_body=request.body,
        request_meta=request.META,
        request_obj=request
    )

    response = JsonResponse(response_data)
    response["Access-Control-Allow-Origin"] = "*"
    return response
