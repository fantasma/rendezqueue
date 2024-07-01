from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import base64

class MyHandler(BaseHTTPRequestHandler):
  def do_PUT(self):
    # Parse query parameters
    params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

    # Extract fields
    key = params.get('key', [""])[0]
    uid = params.get('uid', [""])[0]
    ttl = params.get('ttl', ["0"])[0]
    off = params.get('off', ["0"])[0]
    values = params.get('val', [])

    try:
      key = base64.urlsafe_b64decode(key)
      uid = base64.urlsafe_b64decode(uid)
      
      tmp_values = []
      for v in values:
        tmp_values.extend(v.split(','))
      values = [
        base64.urlsafe_b64decode(v)
        for v in tmp_values
      ]
    except Exception:
      self.send_response(400)
      self.end_headers()
      self.wfile.write(b"Invalid key or uid")
      return

    # Return the same thing.
    result = {
      "key": base64.urlsafe_b64encode(key),
      "uid": base64.urlsafe_b64encode(uid),
      "ttl": ttl,
      "off": off,
      "val": [base64.urlsafe_b64encode(v) for v in values],
    }
    response_string = urllib.parse.urlencode(result)

    # Send response
    self.send_response(200)
    self.send_header('Content-type', 'application/x-www-form-urlencoded')
    self.end_headers()
    self.wfile.write(response_string.encode())


if __name__ == '__main__':
  server_address = ('', 8000)
  httpd = HTTPServer(server_address, MyHandler)
  print('Starting server...')
  httpd.serve_forever()
