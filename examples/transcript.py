# Usage: mitmdump -s "transcript.py outfile"
# or better yet:
# mitmproxy -n -r a_previously_recorded_mitmdump_output_file -s 'transcript.py outfile'
# Records a highly readable transcript of all requests 
# paired with responses for easy analysis of an API protocol

from libmproxy.protocol.http import decoded
import json
import pprint
import re
import urlparse

of = None 
trans_num = 0

# Same as parse_qs except it does not convert
# scalar values into arrays of one element like the
# annoyng parse_qs does.
def parse_qs_right(qs):
    params = urlparse.parse_qs(qs)
    for k in params.keys():
      if len(params[k]) == 1:
        params[k] = params[k][0]
    return params

def print_json(json_text):
    obj = json.loads(json_text)
    of.write(json.dumps(obj, sort_keys=True, indent=2, separators=(',', ': ')))
    of.write("\n")

def print_request(req):
    global trans_num
    of.write( ("========== REQUEST #%d ==========\n" % (trans_num)) )
    of.write(req.url)
    of.write("\n")
    pprint.pprint(req.headers, stream = of)
    parsed_url = urlparse.urlparse(req.url)
    if parsed_url.query > '':
        print >> of, "parsed query:\n"
        of.write(json.dumps(parse_qs_right(parsed_url.query), sort_keys=True, indent=2, separators=(',', ': ')))
        of.write("\n")
    if 'content-type' in req.headers:
      if re.search('json', req.headers['content-type'][0]):
        print >> of, "parsed content:\n"
        print_json(req.content)
      elif re.search('urlencoded', req.headers['content-type'][0]): 
        of.write(json.dumps(parse_qs_right(req.content), sort_keys=True, indent=2, separators=(',', ': ')))
        of.write("\n")
    else:
      pprint.pprint(req.content,stream = of)

def print_response(response):
    global trans_num
    of.write( ("========== RESPONSE #%d ==========\n" % (trans_num)) )
    pprint.pprint(response.headers,stream=of)
    if re.search('json', response.headers['content-type'][0]) or (re.search('text/html', response.headers['content-type'][0]) and re.search('^{.*}$',response.content)):
      print_json(response.content)
    else:
      pprint.pprint(response.content,stream=of)


def start(context, argv):
    if len(argv) != 2:
        raise ValueError('Usage: -s "transcript.py outfile"')
    global of
    of = open(argv[1], 'w')

def response(context, flow):
    global trans_num
    trans_num += 1
    print_request(flow.request)
    with decoded(flow.response):  # automatically decode gzipped responses.
      print_response(flow.response)
