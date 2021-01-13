#!/usr/bin/env python
# encoding: utf-8

# Remi Frenay, WorldStream B.V., 2020
# <rf@worldstream.nl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import object
__author__ = 'Remi Frenay <rf@worldstream.nl>'
__version__ = '1.0.0'
__plugin_name__ = 'check_powerdns_dist.py'

import os
import pickle
import requests
import json
import sys
import tempfile
import time


querylist = ['queries']

avglist = querylist + ['responses', 'cache-hits', 'cache-misses', 'latency-slow', 'latency0-1', 'latency1-10',
                       'latency10-50', 'latency50-100', 'latency100-1000', 'frontend-nxdomain', 'frontend-servfail',
                       'frontend-noerror', 'acl-drops', 'rule-drop', 'downstream-timeouts', 'downstream-send-errors']
watchlist = avglist + ['latency-avg10000', 'security-status']


class MyPdnsError(Exception):
    pass


# noinspection PyTypeChecker
def parse_args():
    # Build argument list
    try:
        import argparse
    except ImportError:
        print('Error importing library python-argparse')
        sys.exit(MStatus().UNKNOWN)

    tempdir = tempfile.gettempdir()
    parser = argparse.ArgumentParser(
        prog=__plugin_name__,
        description='Icinga/Nagios plugin, interned to check PowerDNS status using the API.'
                    'A non-zero exit code is generated, if the numbers of DNS queries per seconds exceeds'
                    ' warning/critical values. Additionally the plugin checks for the security-status of PowerDNS. ',
        epilog='This program is free software: you can redistribute it and/or modify '
               'it under the terms of the GNU General Public License as published by '
               'the Free Software Foundation, either version 3 of the License, or '
               'at your option) any later version. Author: ' + __author__)

    parser.add_argument('-A', '--api-host', help='PowerDNS API host (default 127.0.0.1)', type=str, default='127.0.0.1')
    parser.add_argument('-T', '--test', help='Test case; Use fake data', action='store_true')
    parser.add_argument('-P', '--api-port', help='PowerDNS API port (default 8083)', type=int, default=8083)
    parser.add_argument('-k', '--api-key', help='PowerDNS API key', type=str, default='')
    parser.add_argument('-n', '--config-name', help='Name of PowerDNS virtual configuration', type=str)
    parser.add_argument('-w', '--warning', help='Warning threshold (Queries/s)', type=str, default='0')
    parser.add_argument('-c', '--critical', help='Critical threshold (Queries/s)', type=str, default='0')
    parser.add_argument('-s', '--scratch',
                        help="Scratch/temp directory. (Default %s)" % tempdir, type=str, default=tempdir)
    parser.add_argument('-p', '--perfdata', help='Print performance data, (default: off)', action='store_true')
    parser.add_argument('--skipsecurity', help='Skip PowerDNS security status, (default: off)', action='store_true')
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
    return parser.parse_args()


class MStatus(object):
    """Monitoring status enum"""

    def __init__(self):
        self.OK = 0
        self.WARNING = 1
        self.CRITICAL = 2
        self.UNKNOWN = 3


class Monitoring(object):
    """"Monitoring"""

    def __init__(self):
        self.status = MStatus().UNKNOWN
        self.message = "Unknown Status"
        self.perfdata = []

    def set_status(self, _status):
        if _status == MStatus().UNKNOWN:
            return
        if self.status == MStatus().CRITICAL:
            return
        if _status == MStatus().CRITICAL:
            self.status = _status
            return
        if self.status == MStatus().WARNING:
            return
        self.status = _status

    def set_message(self, _message):
        self.message = _message

    def set_perfdata(self, _label, _value, _warning, _critical):
        self.perfdata.append([_label, _value, _warning, _critical])

    def report(self):
        if self.status == MStatus().OK:
            code = "OK"
        elif self.status == MStatus().WARNING:
            code = "WARNING"
        elif self.status == MStatus().CRITICAL:
            code = "CRITICAL"
        else:
            code = "UNKNOWN"
        output = code + ' - ' + self.message
        if len(self.perfdata) > 0:
            output += '|'
            for measurement in self.perfdata:
                output += (" '%s'=%d;%s;%s;0;" % (measurement[0], measurement[1], measurement[2], measurement[3]))
        print(output)
        sys.exit(self.status)


class PowerDnsApi(object):
    """PowerDNS API"""

    def __init__(self, api_host, api_port, api_key):
        self.api_host = api_host
        self.api_port = api_port
        self.api_key = api_key

    def statistics(self):
        data = dict()
        json_object = self.execute('/api/v1/servers/localhost/statistics')
        for val in json_object:
            if ('type' in val) and ('name' in val) and ('value' in val) and (val['type'] == 'StatisticItem'):
                data[val['name']] = int(val['value'])
        return data

    def execute(self, path):
        """Connect with PowerDNS API to execute request"""

        url = "http://%s:%d%s" % (self.api_host, self.api_port, path)
        headers = {'X-API-Key': self.api_key}
        try:
            get_result = requests.get(url, headers=headers, verify=False)
            if get_result.status_code == 401:
                raise MyPdnsError("Incorrect API Key!")
            if get_result.status_code != 200:
                raise MyPdnsError("API unexpected result code %d" % get_result.status_code)
            json_object = json.loads(get_result.content.decode('utf-8'))
            return json_object
        except requests.exceptions.ConnectionError:
            raise MyPdnsError("Error connecting to %s" % url)


class PowerDnsFake(object):
    """PowerDNS Fake class for testing"""

    def __init__(self):
        pass

    @staticmethod
    def get_data_ok():
        data = {'queries': 0, 'responses': 0, 'cache-hits': 0, 'cache-misses': 0, 'latency-slow': 0, 'latency0-1': 0,
                'latency1-10': 0, 'latency10-50': 0, 'latency50-100': 0, 'latency100-1000': 0, 'frontend-nxdomain': 0,
                'frontend-servfail': 0, 'frontend-noerror': 0, 'acl-drops': 0, 'rule-drop': 0, 'downstream-timeouts': 0,
                'downstream-send-errors': 0, 'latency-avg10000': 0, 'security-status': 1}

        return data


def get_fname(_path_base, _config):
    # returns cache file name
    if _config:
        return os.path.join(_path_base, 'monitor-pdns-dist-' + _config)
    else:
        return os.path.join(_path_base, 'monitor-pdns-dist')


def load_measurement(_filename):
    fd = open(_filename, 'rb')
    _data_old = pickle.load(fd)
    fd.close()
    return _data_old


def save_measurement(_filename, _data_new):
    try:
        fd = open(_filename, 'wb')
        pickle.dump(_data_new, fd)
        fd.close()
    except IOError:
        raise MyPdnsError("Could not write measurement to %s" % _filename)


def filter_data(_data_raw, _watchlist):
    _data_new = dict()
    for _key in _data_raw:
        if _key in _watchlist:
            _data_new[_key] = _data_raw[_key]
    return _data_new


def calc_avgps(_data_old, _data_new):
    _data_avg = dict()
    _queries = 0

    try:
        elapsed = _data_new['epoch'] - _data_old['epoch']
        for _label, _value in list(_data_old.items()):
            if (_label in _data_new) and (_label in avglist):
                delta = _data_new[_label] - _value
                _data_avg[_label] = round(delta/elapsed)
                if delta < 0:
                    return dict(), 0
                if _label in querylist:
                    _queries += delta
        _queries /= elapsed
        return _data_avg, round(_queries)
    except KeyError:
        return dict(), 0
    except ZeroDivisionError:
        return dict(), 0


# main
if __name__ == '__main__':

    monitor = Monitoring()

    try:
        args = parse_args()

        if args.test:
            pdns = PowerDnsFake()
            result = pdns.get_data_ok()
        elif args.api_host:
            pdns = PowerDnsApi(args.api_host, args.api_port, args.api_key)
            result = pdns.statistics()
        else:
            raise MyPdnsError("No hosts specified")

        # Keep items defined in watchlist
        data_new = dict()
        for key in result:
            if key in watchlist:
                data_new[key] = result[key]
        if len(data_new) == 0:
            raise MyPdnsError("No data available")
        data_new['epoch'] = int(time.time())
        if args.test:
            data_old = data_new.copy()
            data_old['epoch'] -= 1
        else:
            filename = get_fname(args.scratch, args.config_name)
            try:
                data_old = load_measurement(filename)
            except IOError:
                data_old = dict()
            save_measurement(filename, data_new)
        (data_avg, queries) = calc_avgps(data_old, data_new)

        if ('security-status' in data_new) and (args.skipsecurity == 0):
            if data_new['security-status'] == 0:
                monitor.set_status(MStatus().CRITICAL)
                security = 'NXDOMAIN or resolution failure.'
            elif data_new['security-status'] == 1:
                monitor.set_status(MStatus().OK)
                security = 'PowerDNS running.'
            elif data_new['security-status'] == 2:
                monitor.set_status(MStatus().WARNING)
                security = 'PowerDNS upgrade recommended.'
            elif data_new['security-status'] == 3:
                monitor.set_status(MStatus().CRITICAL)
                security = 'PowerDNS upgrade mandatory.'
            else:
                monitor.set_status(MStatus().CRITICAL)
                security = "PowerDNS unexpected security-status %d." % data_new['security-status']
        else:
            security = ''

        # support for 'less than' thresholds expressed by trailing ':'
        if args.warning:
            warning = int(args.warning.split(':')[0])
            if args.warning.endswith(":"):
                if (queries < warning):
                    monitor.set_status(MStatus().WARNING)
            elif (queries >= warning):
                monitor.set_status(MStatus().WARNING)

        if args.critical:
            critical = int(args.critical.split(':')[0])
            if args.critical.endswith(":"):
                if (queries < critical):
                    monitor.set_status(MStatus().CRITICAL)
            elif (queries >= critical):
                monitor.set_status(MStatus().CRITICAL)

        monitor.set_status(MStatus().OK)
        monitor.set_message("%s Queries: %d/s." % (security, queries))
        if args.perfdata:
            for label, value in sorted(data_avg.items()):
                monitor.set_perfdata(label, value, args.warning, args.critical)
    except MyPdnsError as e:
        monitor.set_message(str(e))
    monitor.report()
