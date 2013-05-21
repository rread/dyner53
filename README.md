# Dynamic Route53 DNS Updater #

This is is a quick and dirty script to manage a domain name on Route 53.
The basic idea is to use the AWS Route 53 api to get the same functionality offered
by Dynamic DNS.  This is still a work in progress, particularly the daemon option.

These examples assume you have configured your environment to use the boto library to accesss AWS,
and your account is currently hosting a domain on Route 53. 

Examples:

    dyner53.py --domain example.com --subdomain myhost  check

This will lookup (using Route53) the current IP address for myhost.example.com, and compare it 
with the publicly visible IP address of the current host, and report what it finds.  No changes are 
made.


    dyner53.py --domain example.com --subdomain myhost  update

This will perform the same check as above, and update if needed.  This will create subdomain if it 
does not already existing.
 
    dyner53.py --domain example.com --subdomain myhost  --ip 123.123.123.0 update

Updates the given subdomain (creating if necessary) to the given IP address.  Useful for testing or
for simple domain management. 
  
    dyner53.py --domain example.com --subdomain myhost daemon

EXPERIMENTAL mode that will run as a daemon (in the background) that will check current public IP every 10 minutes and update if needed. 
