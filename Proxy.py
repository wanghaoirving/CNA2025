# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)


# Helper functions
def find_max_age(text:str) -> None | int:
    # Use regular expressions to match the max-age=xxx pattern
    pattern = r"max-age=(\d+)[\s,;]?[\r\n]?"
    match = re.search(pattern, text)
    
    if match:
        return int(match.group(1))
    else:
        return None

def parse_date(date_string:str) -> datetime:
  try:
    date_string = date_string.split(':', 1)[1].strip()
    format = "%a, %d %b %Y %H:%M:%S %Z"
    res = datetime.strptime(date_string, format).replace(tzinfo=timezone.utc)
    return res
  except:
    return None

def is_valid_cache(date:datetime, max_age:int):
  expire_date = date + timedelta(seconds=max_age)
  current_date = datetime.now(timezone.utc)
  return current_date <= expire_date


# Create a server socket, bind it to a port and start listening
try:
  # Create a server socket.
  # ~~~~ INSERT CODE ~~~~
  server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # ~~~~ END CODE INSERT ~~~~
  print ('Created socket')
except:
  print ('Failed to create socket')
  sys.exit()

try:
  # Bind the the server socket to a host and port
  # ~~~~ INSERT CODE ~~~~
  server_sock.bind((proxyHost , proxyPort))
  # ~~~~ END CODE INSERT ~~~~
  print ('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  # Listen on the server socket
  # ~~~~ INSERT CODE ~~~~
  server_sock.listen(30)
  # ~~~~ END CODE INSERT ~~~~
  print ('Listening to socket')
except:
  print ('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  # Accept connection from client and store in the clientSocket
  try:
    # ~~~~ INSERT CODE ~~~~
    clientSocket, client_addr = server_sock.accept()#implement client connection acceptance
    # ~~~~ END CODE INSERT ~~~~
    print ('Received a connection')
  except:
    print ('Failed to accept connection')
    sys.exit()

  # Get HTTP request from client
  # and store it in the variable: message_bytes
  # ~~~~ INSERT CODE ~~~~
  message_bytes=clientSocket.recv(BUFFER_SIZE)
  # ~~~~ END CODE INSERT ~~~~
  message = message_bytes.decode('utf-8')
  print ('Received request:')
  print ('< ' + message)

  # Extract the method, URI and version of the HTTP client request 
  requestParts = message.split()
  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print ('Method:\t\t' + method)
  print ('URI:\t\t' + URI)
  print ('Version:\t' + version)
  print ('')

  # Get the requested resource from URI
  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)

  # Remove parent directory changes - security
  URI = URI.replace('/..', '')

  # Split hostname from resource name
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/'

  if len(resourceParts) == 2:
    # Resource is absolute URI with hostname and resource
    resource = resource + resourceParts[1]

  print ('Requested Resource:\t' + resource)

  # Check if resource is in cache
  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print ('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    
    # Check wether the file is currently in the cache
    cacheFile = open(cacheLocation, "r")
    cacheData = cacheFile.readlines()

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    # ProxyServer finds a cache hit
    # Send back response to client 
    # ~~~~ INSERT CODE ~~~~
    # Test if cache is valid: cache-control: max-age=xxx
    max_age = None
    cache_date = None
    for line in cacheData:
      line = line.lower()
      if line.startswith('cache-control'):
        max_age = find_max_age(text=line)
      if line.startswith('date'):
        cache_date = parse_date(date_string=line)
      
    if cache_date is not None and max_age is not None:
      if not is_valid_cache(cache_date, max_age):
        # raise an error, make request to origin server
        raise IOError()

    clientSocket.sendall(''.join(cacheData).encode())
    # ~~~~ END CODE INSERT ~~~~
    cacheFile.close()
    print ('Sent to the client:')
    print ('> ' + ''.join(cacheData))
  except:
    # cache miss.  Get resource from origin server
    originServerSocket = None
    # Create a socket to connect to origin server
    # and store in originServerSocket
    # ~~~~ INSERT CODE ~~~~
    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # ~~~~ END CODE INSERT ~~~~

    print ('Connecting to:\t\t' + hostname + '\n')
    try:
      # Get the IP address for a hostname
      address = socket.gethostbyname(hostname)
      # Connect to the origin server
      # ~~~~ INSERT CODE ~~~~
      parsed = urlparse('http://' + URI)

      port = parsed.port if parsed.port else 80
      originServerSocket.connect((hostname, port))
      # ~~~~ END CODE INSERT ~~~~
      print ('Connected to origin Server')

      originServerRequest = ''
      originServerRequestHeader = ''
      # Create origin server request line and headers to send
      # and store in originServerRequestHeader and originServerRequest
      # originServerRequest is the first line in the request and
      # originServerRequestHeader is the second line in the request
      # ~~~~ INSERT CODE ~~~~
       # I don't know whether to send the client's request header directly to the server or let us customize the request header
      originServerRequest = f"{method} {resource} {version}"
      originServerRequestHeader = f"Host: {hostname}\r\n"
      # originServerRequestHeader += "Accept: */*\r\n"
      # originServerRequestHeader += "Connection: close\r\n"


      # ~~~~ END CODE INSERT ~~~~

      # Construct the request to send to the origin server
      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

      # Request the web resource from origin server
      print ('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print ('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        print ('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      # Get the response from the origin server
      # ~~~~ INSERT CODE ~~~~
      data = originServerSocket.recv(BUFFER_SIZE)
      # ~~~~ END CODE INSERT ~~~~

      # Send the response to the client
      # ~~~~ INSERT CODE ~~~~
      clientSocket.sendall(data)
      
      # Test if the response shoud be cache
      cache_response = True
      responseLines = data.decode().split('\r\n')
      
      
      # Test Cache-Control: public | max-age
      for line in responseLines:
        line = line.strip().lower()
        if line.startswith('cache-control'):
          cache_response = False
          if line.find('public') != -1 or line.find('max-age') != -1:
            cache_response = True
            break
        if line == '':
          break
        
      # http status code != 404/301/302
      statusLine = responseLines[0]
      if statusLine.find('404') != -1 or \
        statusLine.find('301') != -1 or \
          statusLine.find('302') != -1:
            cache_response = False
      

          
      
      if not cache_response:
        try:
          clientSocket.shutdown(socket.SHUT_WR)
          clientSocket.close()
        except:
          print ('Failed to close client socket')
        continue

      # ~~~~ END CODE INSERT ~~~~

      # Create a new file in the cache for the requested file.
      cacheDir, file = os.path.split(cacheLocation)
      print ('cached directory ' + cacheDir)
      if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
      cacheFile = open(cacheLocation, 'wb')

      # Save origin server response in the cache file
      # ~~~~ INSERT CODE ~~~~
      cacheFile.write(data)
      # ~~~~ END CODE INSERT ~~~~
      cacheFile.close()
      print ('cache file closed')

      # finished communicating with origin server - shutdown socket writes
      print ('origin response received. Closing sockets')
      originServerSocket.close()
       
      clientSocket.shutdown(socket.SHUT_WR)
      print ('client socket shutdown for writing')
    except OSError as err:
      print ('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    print ('Failed to close client socket')
