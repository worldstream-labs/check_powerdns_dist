![GitHub release](https://img.shields.io/github/release/worldstream-labs/check_powerdns_dist.svg) 
![GitHub](https://img.shields.io/github/license/worldstream-labs/check_powerdns_dist.svg?color=blue) 
![python 2.7](https://img.shields.io/badge/python-2.7-blue.svg)
![python 3.x](https://img.shields.io/badge/python-3-blue.svg)

# PowerDNS Dist (Balancer) check

Icinga/Nagios plugin, interned to check PowerDNS Dist status using the API.
A non-zero exit code is generated if the numbers of DNS queries per seconds exceeds
warning/critical

## Installation and requirements

*   Python 2.7 or Python 3.x
*   [PowerDNS Dist API](https://dnsdist.org/guides/webserver.html).  
*   [monitoring-plugins](https://github.com/monitoring-plugins/monitoring-plugins)  
    On debian-based systems you need the package `nagios-plugins` or the package `monitoring-plugins`


## Usage

For example: check the statistics using the API running on 127.0.0.1:8083 using key "myapikey".
```sh
./check_powerdns_dist.py -A 127.0.0.1 -P 8083 -k myapikey -p
```
Use --help argument for a description of all arguments. 
```sh
./check_powerdns_dist.py --help
```

## License

PowerDNS Authoritative check is licensed under the terms of the GNU
General Public License Version 3.
