#!/usr/bin/env python3

from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import signal
import sys
import urllib.parse
import subprocess
from subprocess import PIPE
import os
# https://docs.python.org/3/library/ipaddress.html
import ipaddress


class requestHandler(BaseHTTPRequestHandler):
    # This sould be defined from outside before passing this class to HTTPServer
    usage_info = ''
    entry_timeout = 0
    set_name = ''
    whitelist = []

    def do_GET(self):

        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if 'add_ip' not in params:
            self.send_response(code=400)
            self.end_headers()
            self.wfile.write(bytes(self.usage_info, 'utf8'))
            return
        else:
            ip = params['add_ip'][0]

        if 'set_name' in params:
            self.set_name = params['set_name'][0]

        if 'timeout' in params:
            self.entry_timeout = params['timeout'][0]

        try:
            ipaddress.ip_address(ip)
        except ValueError:
            self.send_response(code=500)
            self.end_headers()
            self.wfile.write(bytes('Failed to parse IP: ' + ip + '\n', 'utf8'))
            return

        for net in self.whitelist:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(net):
                self.send_response(code=304, message='Skip whitelisted IP')
                self.end_headers()
                return

        # ipset options: -exist - no error if entry is already in the set
        cmd = ['ipset', 'add', '-exist', self.set_name,
               ip, 'timeout', str(self.entry_timeout)]
        result = subprocess.run(cmd, stdout=PIPE, stderr=PIPE)

        if result.returncode == 0:
            self.send_response(code=200)
            # self.send_header('Content-type', 'text-plain; charset=utf-8')
            self.end_headers()
            return
        else:
            self.send_response(code=500)
            self.end_headers()
            self.wfile.write(result.stderr)
            print(result.stderr)
            return


def sigterm_handler(sig, frame):
    print('Exiting')
    sys.exit(0)


# Forking version of HTTPServer
class ForkingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    pass


def run():
    # Locale settings for all programs we call
    os.environ['LC_ALL'] = 'POSIX'

    api_help = 'HTTP params: add_ip=ip[&set=set_name][&timeout=n]\n'

    parser = ArgumentParser(epilog=api_help)
    parser.add_argument('--port', type=int, default=9000,
                        help='tcp port to listen on, default 9000')
    parser.add_argument('--set-name', default='block',
                        help='ipset set name, default "block"')
    parser.add_argument('--timeout', type=int, default=120,
                        help='timeout for added ipset entry, default 120')
    parser.add_argument('--whitelist', default='',
                        help='networks to whitelist, separated by comma')
    args = parser.parse_args()

    # if os.geteuid() != 0:
    #     print('This program should be started from root')
    #     sys.exit(1)

    # Exclude '' entries
    whitelist = [i for i in str(args.whitelist).split(',') if i != '']

    for net in whitelist:
        try:
            ipaddress.ip_network(net)
            print('Whitelist: ' + net)
        except ValueError:
            print('Failed to parse whitelist network entry: ' + str(net))
            sys.exit(1)

    # Correct exit on TERM and keyboard interrupt
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    requestHandler.whitelist = whitelist
    requestHandler.usage_info = api_help
    requestHandler.entry_timeout = args.timeout
    requestHandler.set_name = args.set_name

    # httpd = HTTPServer( ('0.0.0.0', args.port), requestHandler)
    print('Starting server on port ' + str(args.port))
    httpd = ForkingHTTPServer(('0.0.0.0', args.port), requestHandler)

    httpd.serve_forever()


if __name__ == '__main__':
    run()
