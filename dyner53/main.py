import boto
import urllib2
import argparse
import logging
import logging.handlers
import daemon
import time

__author__ = 'rread'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
route53 = boto.connect_route53()


def sys_is_osx_lion():
    import platform

    if platform.platform()[0:6] == 'Darwin':
        (major, minor, patch) = platform.mac_ver()[0].split(".")
        if major == '10' and minor in ['7', '8']:
            return True
    return False


def init_logging(daemon=False):
    """

    :param daemon:
    """
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s[%(process)d]: %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    if daemon:
        # TODO: workaround MacPorts bug #37990
        if sys_is_osx_lion():
            syslog_address = '/var/run/syslog'
        else:
        #            syslog_address = ('localhost', logging.handlers.SYSLOG_UDP_PORT)
            syslog_address = '/dev/log'
        syslog = logging.handlers.SysLogHandler(address=syslog_address,
                                                facility='daemon')
        syslog.setFormatter(formatter)
        syslog.setLevel(logging.INFO)
        logger.addHandler(syslog)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subdomain', '-s', help="Name of subdomain to be check/updated", required=True)
    parser.add_argument('--domain', '-d', help="Name of the zone.", required=True)
    parser.add_argument('--ip',
                        help='Set domain to specified IP instead of current public address',
                        default=None)
    subparsers = parser.add_subparsers()

    parser_check = subparsers.add_parser("check")
    parser_check.set_defaults(func=do_check)

    parser_update = subparsers.add_parser('update')
    parser_update.set_defaults(func=do_update)

    parser_update = subparsers.add_parser('delete')
    parser_update.set_defaults(func=do_delete)

    parser_daemon = subparsers.add_parser('daemon')
    parser_daemon.set_defaults(func=do_daemon)
    args = parser.parse_args()
    return args


def get_public_ip():
    my_ip = urllib2.urlopen("http://api.exip.org/?call=ip").read()
    return my_ip


def get_dyn_domain(sub, domain):
    return ".".join([sub, domain])


def do_check(args):
    init_logging()
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    my_ip = args.ip or get_public_ip()
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is not None:
        logger.info("Current IP is %s, %s = %s" % (my_ip, dyn_domain, rec.resource_records))
        if my_ip in rec.resource_records:
            logger.debug("Dynamic address is current.")
        else:
            logger.debug('Need to update %s' % dyn_domain)
    else:
        logger.debug("Domain %s does not exist." % dyn_domain)


def do_update(args):
    init_logging()
    update(args)


def update(args):
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    my_ip = args.ip or get_public_ip()
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        zone.add_a(dyn_domain, my_ip, ttl=60)
    elif my_ip not in rec.resource_records:
        logger.warn('updating %s from %s -> %s' % (dyn_domain, rec.resource_records, my_ip))
        zone.update_a(dyn_domain, my_ip, ttl=60)
    else:
        logger.debug("No update needed.")


def do_delete(args):
    init_logging()
    dyn_domain = get_dyn_domain(args.subdomain, args.domain)
    zone = route53.get_zone(args.domain)
    rec = zone.get_a(dyn_domain)
    if rec is None:
        logger.debug("%s: Domain not found", dyn_domain)
    else:
        zone.delete_a(rec.name, rec.identifier)


def do_daemon(args):
    """

    :param args:
    """
    global route53
    route53.close()

    with daemon.DaemonContext():
        init_logging(True)
        run_daemon(args)


def run_daemon(args):
    logger.warn("Dynamic route53 updater started for: %s" %
                get_dyn_domain(args.subdomain, args.domain))
    while True:
        time.sleep(300)
        try:
            route53 = boto.connect_route53()
        except Exception, e:
            logging.warn('Unable to connect to route53: %s', e)
            continue

        try:
            update(args)
        except Exception, e:
            logger.warn("Unable to upaate zone: %s", e)

        route53.close()

def main():
    args = get_args()
    args.func(args)
