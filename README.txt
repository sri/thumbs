I have about 2000 pictures (~4GB) under my ~/Pictures directory.
From that, I want to select a subset and copy it to a new
directory. This little script help me to do that quickly.

You use a browser to select the images. After you are done, 
those images will be copied to a directory.

Tested on Mac OS X & Python 2.6 & Google Chrome.
Requires PIL - Python Imaging Libary w/JPEG support.
Requires Tornado Web Server.

NOTE: Does NOT work with Firefox.

PIL NOTE: I had to say: `$ export ARCHFLAGS="-arch x86_64"'
          before PIL would compile correctly for me.

Released under the BSD license.
http://www.opensource.org/licenses/bsd-license.php

How It Works
=============

1. Get all JPEGs under ~/Pictures.
2. Create thumbnails for those JPEG under ./thumbs directory.
   Default thumbnail size: 320 x 320.
3. A HTML page is generated with all the thumbnails.
4. That HTML is opened by a browser. Since the browser
   opens the HTML straight from disk, it loads all
   the thumbnails very quickly.
4. A webserver starts up in the background, recording
   user selections.
5. When user is done, the selected images (the originals, 
   not the thumbnails) are copied into a new directory.
