#!/usr/bin/env python

import boto
import urllib
import argparse

route53 = boto.connect_route53()

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subdomain', '-s', help="Name of subdomain to be check/updated", required=True)
    parser.add_argument('--domain', '-d', help="Name of the zone.", required=True)
    parser.add_argument('--ip',
        help='Set domain to specified IP instead of current public address',
        default=None)
    subparsers = parser.add_subparsers()

    parser_check = subparsers.add_parser("check")
    parser_check.set_defaults(func = do_check)

    parser_update = subparsers.add_parser('update')
    parser_update.set_defaults(func = do_update)

    parser_update = subparsers.add_parser('delete')
    parser_update.set_defaults(func = do_delete)
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
        print ("Current IP is %s, %s = %s" %(my_ip, dyn_domain, rec.resource_records))
        if my_ip in rec.resource_records:
            print "Dynamic address is current."
        else:
            print('Need to update %s' % dyn_domain)
    else:
        print("Domain %s does not exist." % dyn_domain)

def do_update(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    my_ip = args.ip or get_public_ip()
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        zone.add_a(dyn_domain, my_ip, ttl=60)
    elif my_ip not in rec.resource_records:
        print('Updating %s from %s -> %s' % (dyn_domain, rec.resource_records, my_ip))
        zone.update_a(dyn_domain, my_ip, ttl=60)
    else:
        print "No update needed."

def do_delete(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        print ("%s: Domain not found", dyn_domain)
    else:
        zone.delete_a(rec.name, rec.identifier)

def main():
    args = get_args()
    args.func(args)

if __name__ == '__main__':
    main()