#! /usr/bin/env python

import os
import sys
import re
import time
import shutil
import commands

try:
    from PIL import Image
except ImportError:
    print "Python Imaging Library (PIL) is REQUIRED to generate thumbnails."
    sys.exit(1)

try:
    import tornado.ioloop
    import tornado.web
except ImportError:
    print "Tornado Web Server is REQUIRED"
    sys.exit(1)

PICS_TEMPLATE = """
<style>
body { text-align:center; }
.s { border:4px solid red; }
img {
  border:4px solid #fff;
  margin:auto;
  margin-bottom:2px;
}
#menu {
  position:fixed;
  right:0;
  bottom:0;
  padding:15px;
  width:200px;
  background:#666;
  cursor:pointer;
  color:#fff;
}
</style>
<script type="text/javascript" 
 src="http://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.min.js">
</script>
<script>
$(document).ready(function() {
  
  $(".i").click(function() {
     var isSelected = $(this).hasClass('s');
     var src = $(this).attr('src');
     var action = null;

     if (isSelected) {
       $(this).removeClass('s');
       action = 'delete';
     } else {
       $(this).addClass('s');
       action = 'add'
     }

     var success = function(data, textStatus, jqXHR) {
     };

     $.post('http://localhost:8888/', 
            {thumbnail: src, action: action},
            success);
   });
});
</script>

<!-- <img class="i" src="0000.jpg" /> -->
"""

# Get all the JPEG images under PicsDir.
def allpics(picsdir):
    pics = []
    for dirpath, dirnames, filenames in os.walk(picsdir):
        for f in filenames:
            if re.search('[.]jpe?g$', f, re.I):
                pics.append(os.path.join(dirpath, f))
    print "got %d images" % len(pics)
    return pics

# Create thumbnails for all the pics and place them under Thumbnails_Dir.
# The thumbnails are named like so: "00001.jpg", "00002.jpg", ...
# Creates Mapping_Path file, which contains a mapping from
# the newly named thumbnail to the location of the full-size image.
# There is one mapping per line:
#  "00001.jpg Path-To-Original"
def resize(pics, thumbnails_dir, mapping_path, size=(320, 320)):
    if os.path.exists(mapping_path):
        print 'skipping resizing since %s exists' % mapping_path
        return
    print 'resizing %d images' % len(pics)
    start = time.time()
    print_lines = 10
    log_every = len(pics) / print_lines
    f = open(mapping_path, 'w')
    for i, p in enumerate(pics):
        im = Image.open(p)
        im.thumbnail(size)
        base = '%05d.jpg' % i
        newname = os.path.join(thumbnails_dir, base)
        f.write(base + ' ' + p + '\n')
        if i % log_every == 0 and i > 0:
            print '(%d/%d) created %d thumbnails' % (
                i/log_every, print_lines, log_every)
        im.save(newname, 'JPEG')
    f.close()
    end = time.time()
    print "creating %d thumbnails took %.f seconds" % (len(pics), end-start)

# Generate a HTML file that contains all the thumbnails in IMG tags.
def gen_html(thumbnails_dir, index):
    print 'generating html'
    i = 0
    pics = []
    while True:
        base = "%05d.jpg" % i
        name = os.path.join(thumbnails_dir, base)
        if not os.path.exists(name):
            break
        html = '<img class="i" src="%s" />' % base
        pics.append(html)
        i += 1
    final = PICS_TEMPLATE + "\n".join(pics)
    with open(index, 'w') as f:
        f.write(final)

# Open the HTML file that's on the disk in the default browser. 
# Google Chrome is recommended.
def launch_local_url(url, size):
    print 'launching ' + url
    print '*** NOTE: DOESNT WORK UNDER FIREFOX'
    print 'remember to make browser fullscreen: '
    print ' - Shift-Cmd-F in Google Chrome (the same to return to normal)'
    print
    print '%s of thumbnails will open in your browser' % size
    print 'click on each image to select them'
    raw_input('HIT ENTER TO CONTINUE, or Ctrl-C to cancel\n')
    commands.getoutput('open "%s"' % url)
    time.sleep(2)

USER_SELECTIONS_PATH = None

# After the local HTML file is opened in browser,
# any user selections will be handled by this
# web server.
class MainHandler(tornado.web.RequestHandler):
    def post(self):
        action = self.get_argument("action", "")
        thumbnail = self.get_argument("thumbnail", "")
        if action and thumbnail:
            USER_SELECTIONS_PATH.write(action + ' ' + thumbnail + '\n')
            USER_SELECTIONS_PATH.flush()
        print("%s %s" % (action, thumbnail))
        self.write("")

# Launch the above server and write the selections to a file.
def start_server(user_selections_path):
    global USER_SELECTIONS_PATH
    try:
        print "starting server...to capture user selections"
        print "Hit Ctrl-C when you are done selecting the images"
        print "=" * 60
        USER_SELECTIONS_PATH = open(user_selections_path, 'w')
        application = tornado.web.Application([(r"/", MainHandler)])
        application.listen(8888)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        USER_SELECTIONS_PATH.close()
        print

# Size of the thumbnails directory.
def report_thumbnails_dir_size(d):
    size = commands.getoutput('du -hs ' + d).split()[0]
    print "size of thumbnails dir: " + size
    return size

# Copy the user selections into a directory.
# User_Selections_Path has a bunch of commands:
#   add 00001.jpg
#   add 00002.jpg
#   delete 00001.jpg   # user unselected 00001.jpg
# Get a list of the added thumbnails. Get the paths to
# the original image. And copy those images to a "selections-N"
# directory under the Thumbnails_Dir.
def copy_selections(thumbnails_dir, user_selections_path, mapping_path):
    selections = {}
    allthumbs = []
    with open(user_selections_path) as f:
        for line in f:
            action, thumb = line.strip().split(None, 1)
            allthumbs.append(thumb)
            if action == 'add':
                selections[thumb] = True
            else:
                selections[thumb] = False
    mappings = {}
    with open(mapping_path) as f:
        for line in f:
            thumb, original = line.strip().split(None, 1)
            mappings[thumb] = original
    # Order by user's 1st selection, 2nd selection, ...
    seen = set()
    originals = []
    for t in allthumbs:
        if selections[t]:
            if t in seen:
                continue
            seen.add(t)
            originals.append(mappings[t])
    selections_dir = None
    for i in range(1000):
        p = os.path.join(thumbnails_dir, 'selections-' + str(i))
        try:
            os.mkdir(p)
            selections_dir = p
            break
        except OSError:
            continue
    assert selections_dir
    for i, path in enumerate(originals):
        base = '%05d.jpg' % i
        newname = os.path.join(selections_dir, base)
        print "copying %s <= %s" % (base, path)
        shutil.copyfile(path, newname)
    print "all selections have been copied to", selections_dir
    commands.getoutput('open ' + selections_dir)

def main():
    # Locations of all the pictures
    pics_dir = os.path.expanduser('~/Pictures')
    # When do you want to put the thumbnails;
    # default: the thumbs directory, in the current directory.
    thumbnails_dir = 'thumbs'
    # The local HTML file.
    index = os.path.join(thumbnails_dir, 'index.html')
    # Maps each thumbnail to their original path.
    mapping_path = os.path.join(thumbnails_dir, 'mapping.txt')
    # All the images clicked on by the user.
    user_selections_path = os.path.join(thumbnails_dir, 'selections.txt')
    # Local URL from the browser to open
    local_url = 'file://' + os.path.abspath(index)
    if not os.path.exists(thumbnails_dir):
        os.mkdir(thumbnails_dir)

    print 'thumbnails will be create under %s/' % thumbnails_dir
    pics = allpics(pics_dir)
    resize(pics, thumbnails_dir, mapping_path)
    size = report_thumbnails_dir_size(thumbnails_dir)
    gen_html(thumbnails_dir, index)
    launch_local_url(local_url, size)
    start_server(user_selections_path)
    copy_selections(thumbnails_dir, user_selections_path, mapping_path)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
