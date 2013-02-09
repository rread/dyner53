#!/usr/bin/env python

import boto
import urllib
import argparse
import logging
import logging.handlers
import daemon

logger = logging.getLogger('dyner53')

def init_logging():
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)

    syslog = logging.handlers.SysLogHandler()
    syslog.setLevel(logging.INFO)
    logger.addHandler(syslog)


route53 = boto.connect_route53()

def daemonize():
    pass

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subdomain', '-s', help="Name of subdomain to be check/updated", required=True)
    parser.add_argument('--domain', '-d', help="Name of the zone.", required=True)
    parser.add_argument('--ip',
                        help='Set domain to specified IP instead of current public address',
                        default=None)
    parser.add_argument('--daemon', help="run as a daemon", action="store_true")
    subparsers = parser.add_subparsers()

    parser_check = subparsers.add_parser("check")
    parser_check.set_defaults(func=do_check)

    parser_update = subparsers.add_parser('update')
    parser_update.set_defaults(func=do_update)

    parser_update = subparsers.add_parser('delete')
    parser_update.set_defaults(func=do_delete)
    args = parser.parse_args()
    return args


def get_public_ip():
    my_ip = urllib.urlopen("http://api.exip.org/?call=ip").read()
    return my_ip


def get_dyn_domain(sub, domain):
    return ".".join([sub, domain])


def do_check(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    my_ip = args.ip or get_public_ip()
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is not None:
        print ("Current IP is %s, %s = %s" % (my_ip, dyn_domain, rec.resource_records))
        if my_ip in rec.resource_records:
            logger.debug("Dynamic address is current.")
        else:
            logger.debug('Need to update %s' % dyn_domain)
    else:
        logger.debug("Domain %s does not exist." % dyn_domain)


def do_update(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    my_ip = args.ip or get_public_ip()
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        zone.add_a(dyn_domain, my_ip, ttl=60)
    elif my_ip not in rec.resource_records:
        logger.critical('Updating %s from %s -> %s' % (dyn_domain, rec.resource_records, my_ip))
        zone.update_a(dyn_domain, my_ip, ttl=60)
    else:
        logger.debug("No update needed.")


def do_delete(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        logger.debug("%s: Domain not found", dyn_domain)
    else:
        zone.delete_a(rec.name, rec.identifier)


def main():
    args = get_args()
    if args.daemon:
        daemonize()
    init_logging()
    args.func(args)


if __name__ == '__main__':
    main()