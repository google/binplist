<font size='4'><font color='red'><b>NOTE:</b></font> the commandline utility installed alongside the python module has been renamed to <b>plist.py</b>.</font>


Download the latest source version on the [Downloads](https://code.google.com/p/binplist/downloads/list) section and then:

```
$ tar zxf binplist-X.X.X.tar.gz
$ cd binplist-X.X.X
$ python setup.py install
```


This also installs a **plist.py** (previously binplist) command that you can use to show the contents of plists.


```
$ xxd -l 16 ~/Library/Preferences/com.apple.mail.plist
0000000: 6270 6c69 7374 3030 d901 0203 0405 0607  bplist00........
$ plist.py ~/Library/Preferences/com.apple.mail.plist 
{
    'AccountsVersion': 1,
    'EnableBundles': True,
    'AddInvitationsToICalAutomatically': False,
    'MailAccounts': [{
        'DraftsMailboxName': 'Drafts',
        'SentMessagesMailboxName': 'Sent Messages',
        'AccountPath': '~/Library/Mail/RSS',
        'AccountType': 'RSSAccount',
        'uniqueId': 'd8280167-594d-46be-a978-13deabaa2962'
    }, {
        'AccountPath': '~/Library/Mail/Mailboxes',
        'uniqueId': '7c4fe635-2f58-4893-8801-a72064374251',
        'NotesMailboxName': 'Notes',
        'SentMessagesMailboxName': 'Sent Messages',
        'AccountType': 'LocalAccount',
        'DraftsMailboxName': 'Drafts',
        'IsSyncable': True
    }],
    'IMAPServerPrefixesMirrorFilesystem': True,
    'MessageTracerInfo': {
        'RecordedPlugins': [],
        'MessageCompatibilityUUID': '1C58722D-AFBD-464E-81BB-0E05C108BE06',
        'MailCompatibilityUUID': '9049EF7D-5873-4F54-A447-51D722009310'
    },
    'junkMailTrustHeaders': True,
    'ActiveEditors': [],
    'BundleCompatibilityVersion': 1
}
```

As of version 0.1.4 Unicode strings should be printed gracefully on any console that supports utf-8 output. I.e:

```
$ plist.py ~/Downloads/UTFS.plist 
{
    'Globtroter.pl - serwis podróżnicz': '神木新闻网--中国神木欢迎您！'
}
```


**WINDOWS users:** You're a bit out of luck here. If you select a proper TrueType font for your console and change the default codepage to 65001 (chcp 65001) you will almost get the output right. Otherwise, just redirect the default output of plist.py to a file and open it with your preferred text editor.


You can also change the preferred encoding for both of strings (-e) in a plist and plist.py's output (-E) if you wish. By default, the encoding for plist strings is handled by a """smart""" decoder that attempts to only decode printable ASCII-characters and escape the rest, which is most probably what you want by default.

Otherwise, feel free to play with the encodings.