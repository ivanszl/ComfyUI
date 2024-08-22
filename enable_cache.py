import os
import json
import nodes
import server
import logging
import traceback
from aiohttp import web
from aiohttp.typedefs import Handler

def node_info(node_class):
  obj_class = nodes.NODE_CLASS_MAPPINGS[node_class]
  info = {}
  info['input'] = obj_class.INPUT_TYPES()
  info['output'] = obj_class.RETURN_TYPES
  info['output_is_list'] = obj_class.OUTPUT_IS_LIST if hasattr(obj_class, 'OUTPUT_IS_LIST') else [False] * len(obj_class.RETURN_TYPES)
  info['output_name'] = obj_class.RETURN_NAMES if hasattr(obj_class, 'RETURN_NAMES') else info['output']
  info['name'] = node_class
  info['display_name'] = nodes.NODE_DISPLAY_NAME_MAPPINGS[node_class] if node_class in nodes.NODE_DISPLAY_NAME_MAPPINGS.keys() else node_class
  info['description'] = obj_class.DESCRIPTION if hasattr(obj_class,'DESCRIPTION') else ''
  info['python_module'] = getattr(obj_class, "RELATIVE_PYTHON_MODULE", "nodes")
  info['category'] = 'sd'
  if hasattr(obj_class, 'OUTPUT_NODE') and obj_class.OUTPUT_NODE == True:
      info['output_node'] = True
  else:
      info['output_node'] = False

  if hasattr(obj_class, 'CATEGORY'):
      info['category'] = obj_class.CATEGORY
  return info

def dynamic_object_info():
  out = {}
  for x in nodes.NODE_CLASS_MAPPINGS:
    try:
      out[x] = node_info(x)
    except Exception as e:
      logging.error(f"[ERROR] An error occurred while retrieving information for the '{x}' node.")
      logging.error(traceback.format_exc())
  os.makedirs("./.one_cache", exist_ok=True)
  with open("./.one_cache/object_info.json", 'w') as w:
    json.dump(out, w)

async def cache_object_info(request:web.Request):
  if "refresh" in request.rel_url.query:
    dynamic_object_info()
  if not os.path.exists("./.one_cache/object_info.json"):
    dynamic_object_info()
  return web.FileResponse("./.one_cache/object_info.json")

@web.middleware
async def gzip_middleware(request:web.Request, handler: Handler):
  if request.path == "/object_info" or request.path == "/api/object_info":
    handler = cache_object_info
  response = await handler(request)
  
  if not response.headers.get('Content-Encoding'):
    if response.content_length is None or response.content_length > 1000:
      response.enable_compression()
  
  return response
    

def hijack_enable_cache(server:server.PromptServer):
  server.app.middlewares.append(gzip_middleware)
  
def call_on_start(scheme, address, port):
  dynamic_object_info()