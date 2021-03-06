Pymailheaders
=============

Pymailheaders is a small GTK+ program which displays mail headers in your mail
box.  It was innovated by xmailheaders, with a few more handy features like new
mail highlighting, multi-language support, lauching regardless of network
connection status and auto-reconnecting.  Pymailheaders was written from scratch
in Python for portability and easiness reasons.  IMAP4, POP3 protocols and XML
feeds are supported now.

If you find any bugs, you can either write me an "E-mail"
[mailto://zeegeek@gmail.com] or submit a bug report at "bug report page"
[http://sourceforge.net/tracker/?atid=929414&group_id=189460&func=browse].  For
feature requests, you can submit them at "feature request page"
[http://sourceforge.net/tracker/?atid=929417&group_id=189460&func=browse].
Thank you.


REQUIREMENTS
============

You need the following packages install on your system in order to run
Pymailheaders,

* Python 2.4 (or above) [http://www.python.org/download/]
* PyGTK 2.6 (or above) [http://pygtk.org/downloads.html]
* GTK 2.6 (or above) [http://gtk.org/download/]

For *ubuntu users, all you need to do is to install python-gtk2 package.  And
then all the dependencies will be met by the package management system.  You can
simply type the following command in a terminal to get it done.

> sudo apt-get install python-gtk2 python-glade2 python-gobject

It should be similar in other distributions.


INSTALL
=======

You do not need to install this program, just run pymailheaders.py.


USAGE
=====

Recommended: Simply run pymailheaders.py without any arguments on the command
prompt.

Advanced: Pymailheaders will look for a configuration file called
.pymailheadersrc in your home directory unless you use command line argument
'-f' to specify another file explicitly.  If you do not have a configuration
file yet, Pymailheaders will create one for you in your home directory.  If you
already have one, you can still use command line arguments to overwrite the
options in the configuration file.  If mandatory options like server type,
server address, user name and password are not provided in command line
arguments nor in the configuration file, Pymailheaders will tell you which
options are missing by popping the settings dialog up.

Use 'pymailheaders.py -h' for full argument list.

On the first time running Pymailheaders, you have to provide all mandatory
options, namely server type, server address, user name and password (if
required), or the settings dialog will pop up to ask for them.

> pymailheaders.py -t imap -s express.cites.uiuc.edu -a -u zeegeek \
  -p classified -e

After successfully launching Pymailheaders, you can omit all arguments except
for '-c' if you use another configuration file in future launches.  Everything
else can be set using Pymailheaders' GTK+ settings dialog by right clicking on
Pymailheaders' window.  Add a '&' mark at the end of the command to make it run
in background.

> pymailheaders.py

The following demonstrates how to run Pymailheaders for different protocols on command line.

For IMAP4 mailboxes, you need to set server type as imap and provide server URL,
username and password.  If your server supports encrypted connection, you also
have to set the ssl option.  The following example establishes a secured
connection with '-e' argument,

> pymailheaders.py -t imap -s express.cites.uiuc.edu -a -u zeegeek \
  -p classified -e -i 60

To use pymailheaders with POP3 mailbox, it is basically the same as doing it
with IMAP4 mailbox.  The only thing you need to change is server type.  For
example,

> pymailheaders.py -t pop -s express.cites.uiuc.edu -a -u zeegeek \
  -p classified -e -i 60

If you have a Gmail account and you want to check for new mails, just set server
type to feed and server to gmail.  Then you need to give your username and
password.  Here is an example,

> pymailheaders.py -t feed -s gmail -a -u zeegeek -p classified -i 60

You can also use pymailheaders to check for XML feeds in the formats of RSS 1.0,
2.0 and Atom 0.3, 1.0.  If your feed provider does not require authentication,
you do not need to provide username and password.  Example,

> pymailheaders.py -t feed -s http://feedparser.org/docs/examples/atom10.xml


DOWNLOAD
========

* Pymailheaders - stable version [http://sourceforge.net/project/platformdownload.php?group_id=189460]
* Pymailheaders - development snapshot [http://github.com/zeegeek/pymailheaders/tarball/master]

I'm not keeping the under-development code in SourceForge's Subversion
repository any more.  All the code has been moved to a "GIT repository"
[http://github.com/zeegeek/pymailheaders].
