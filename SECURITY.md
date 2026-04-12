# Security Policy

## Supported Versions

| Version             | Supported          |
| ------------------- | ------------------ |
| main branch         | :white_check_mark: |
| most recent release | :white_check_mark: |
| older releases      | :x:                |

## Scope

 - **Denial of Service (DoS):** We consider DoS vectors to be ordinary bugs and not security vulnerabilities.
   You may post them openly on the issue tracker. We will not issue any advisories or CVEs for them.
   The reasoning here is that mitmproxy is an interactive inspection tool, not a web server for high volume traffic.
   It can typically be overwhelmed by sending too many requests; any DoS is just a variation of this.
 - **All other vulnerabilities:** Please report them using the process below.

## Reporting a Vulnerability

We ask that you do not report security issues to our normal GitHub issue tracker.

If you believe you've identified a security issue with mitmproxy,
please report it to [@mhils](https://github.com/mhils), [@Kriechi](https://github.com/Kriechi), and/or [@cortesi](https://github.com/cortesi) 
via the email addresses listed on their GitHub profiles.

Once you've submitted an issue via email, 
you should receive an acknowledgment within 48 hours, and depending on the action to be taken, you may receive further follow-up emails.
