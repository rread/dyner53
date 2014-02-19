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

def sys_is_osx_lion():
    import platform

    if platform.platform()[0:6] == 'Darwin':
        (major, minor, patch) = platform.mac_ver()[0].split(".")
        if major == '10' and minor in ['7', '8', '9']:
            return True
    return False


def init_logging(daemon=False):
    """
    Send logs to syslog.

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
            # syslog_address = ('localhost', logging.handlers.SYSLOG_UDP_PORT)
            syslog_address = '/dev/log'
        syslog = logging.handlers.SysLogHandler(address=syslog_address,
                                                facility='daemon')
        syslog = logging.handlers.SysLogHandler()
        syslog.setFormatter(formatter)
        syslog.setLevel(logging.INFO)
        logger.addHandler(syslog)

class DynDomain:
    def __init__(self, subdomain, domain):
        self.domain = domain
        self.dyn_domain = ".".join([subdomain, domain])
        self.route53 = boto.connect_route53()
        self.zone = self.route53.get_zone(domain)


    def check(self, ip):
        check_ip = ip or get_public_ip()
        rec = self.zone.get_a(self.dyn_domain)
        if rec is not None:
            logger.info("Current IP is %s, %s = %s" % (check_ip, self.dyn_domain, rec.resource_records))
            if check_ip in rec.resource_records:
                logger.debug("Dynamic address is current.")
                return True
            else:
                logger.debug('Need to update %s' % self.dyn_domain)
                return False
        else:
            logger.debug("Domain %s does not exist." % self.dyn_domain)
            return False

    def update(self, ip):
        my_ip = ip or get_public_ip()
        zone = self.route53.get_zone(self.domain)
        rec = zone.get_a(self.dyn_domain)
        if rec is None:
            zone.add_a(self.dyn_domain, my_ip, ttl=60)
        elif my_ip not in rec.resource_records:
            logger.warn('updating %s from %s -> %s' % (self.dyn_domain, rec.resource_records, my_ip))
            zone.update_a(self.dyn_domain, my_ip, ttl=60)
        else:
            logger.debug("No update needed.")

    def delete(self):
        zone = self.route53.get_zone(self.domain)
        rec = zone.get_a(self.dyn_domain)
        if rec is None:
            logger.debug("%s: Domain not found", self.dyn_domain)
        else:
            zone.delete_a(rec.name, rec.identifier)


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
    dd = DynDomain(args.subdomain, args.domain)
    dd.check(args.ip)

def do_update(args):
    init_logging()
    dd = DynDomain(args.subdomain, args.domain)
    dd.update(args.ip)


def do_delete(args):
    init_logging()
    dd = DynDomain(args.subdomain, args.domain)
    dd.delete()

def do_daemon(args):
    """

    :param args:
    """
    with daemon.DaemonContext():
        init_logging(True)
        run_daemon(args)


def run_daemon(args):
    logger.warn("Dynamic route53 updater started for: %s" %
                get_dyn_domain(args.subdomain, args.domain))


    while True:
        try:
            dd = DynDomain(args.subdomain, args.domain)
        except Exception, e:
            logging.warn('Unable to connect to route53: %s', e)
            continue

        try:
            dd.update(args.ip)
        except Exception, e:
            logger.warn("Unable to update zone: %s", e)
        time.sleep(300)


def main():
    args = get_args()
    args.func(args)


if __name__ == '__main__':
  main()
