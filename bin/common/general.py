#!/usr/bin/env python
'''
General python functions that don't fit in it's own file.

'''

__author__ = "daniel.lindh@cybercow.se"
__copyright__ = "Copyright 2011, The System Console project"
__maintainer__ = "Daniel Lindh"
__email__ = "syco@cybercow.se"
__credits__ = ["???"]
__license__ = "???"
__version__ = "1.0.0"
__status__ = "Production"

import glob
import os
import re
import shutil
import stat
import string
import subprocess
import time
import sys
from random import choice
from socket import *

import app

def install_and_import_pexpect():
  '''
  Import the pexpect module, will be installed if not already done.

  '''
  try:
    import pexpect
    return pexpect
  except:
    subprocess.Popen("yum -y install pexpect", shell=True)
    time.sleep(2)

pexpect = install_and_import_pexpect()

def remove_file(path):
  '''
  Remove file(s) in path, can use wildcard.

  Example
  remove_file('/var/log/libvirt/qemu/%s.log*')

  '''
  for file_name in glob.glob(path):
    app.print_verbose('Remove file %s' % file_name)
    os.remove('%s' % file_name)

def grep(file_name, pattern):
  '''
  Return true if regexp pattern is included in the file.

  '''
  prog = re.compile(pattern)
  for line in open(file_name):
    if prog.search(line):
      return True
  return False

def delete_install_dir():
  '''
  Delete the folder where installation files are stored during installation.

  '''
  app.print_verbose("Delete " + app.INSTALL_DIR + " used during installation.")
  shutil.rmtree(app.INSTALL_DIR, ignore_errors=True)
  pass

def create_install_dir():
  '''
  Create folder where installation files are stored during installation.

  It could be files downloaded with wget, like rpms or tar.gz files, that should
  be installed.

  '''
  if (not os.access(app.INSTALL_DIR, os.W_OK | os.X_OK)):
    os.mkdir(app.INSTALL_DIR)

  if (os.access(app.INSTALL_DIR, os.W_OK | os.X_OK)):
    os.chmod(app.INSTALL_DIR, stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
    os.chdir(app.INSTALL_DIR)
  else:
    raise Exception("Can't create install dir.")

  import atexit
  atexit.register(delete_install_dir)

def download_file(src, dst=None, user="", remote_user=None, remote_password=None):
  '''
  Download a file using wget, and place in the installation tmp folder.

  download_file("http://www.example.com/file.gz", "file.gz")

  '''
  app.print_verbose("Download: " + src)
  if (not dst):
    dst = os.path.basename(src)

  create_install_dir()
  if (not os.access(app.INSTALL_DIR + dst, os.F_OK)):
    cmd = "-O " + app.INSTALL_DIR + dst
    if (remote_user):
      cmd += " --user=" + remote_user

    if (remote_password):
      cmd += " --password=" + remote_password

    shell_exec("wget " + cmd + " " + src, user=user)
    # Looks like the file is not flushed to disk immediatley,
    # making the script not able to read the file immediatley after it's
    # downloaded. A sleep fixes this.
    time.sleep(2)

  if (not os.access(app.INSTALL_DIR + dst, os.F_OK)):
    raise Exception("Couldn't download: " + dst)

def generate_password(length=8, chars=string.letters + string.digits):
  '''Generate a random password'''
  return ''.join([choice(chars) for i in range(length)])

def is_server_alive(server, port):
  '''
  Check if port on a server is responding, this assumes the server is alive.

  '''
  try:
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(5)
    result = s.connect_ex((server, int(port)))
  finally:
    s.close()

  if (result == 0):
    return True
  return False

def wait_for_server_to_start(server, port):
  '''
  Wait until a network port is opened.

  '''
  app.print_verbose("\nWait until " + server + " on port " + port + " starts.", new_line=False)
  while(not is_server_alive(server, port)):
    app.print_verbose(".", new_line=False)
    time.sleep(5)
  app.print_verbose(".")

class syco_spawn(pexpect.spawn):
  def expect_loop(self, searcher, timeout = -1, searchwindowsize = -1):
    self.searcher = searcher

    if timeout == -1:
        timeout = self.timeout
    if timeout is not None:
        end_time = time.time() + timeout
    if searchwindowsize == -1:
        searchwindowsize = self.searchwindowsize

    try:
        incoming = self.buffer
        freshlen = len(incoming)
        while True: # Keep reading until exception or return.
            app.print_verbose(incoming[ -freshlen : ], 2, new_line=False, enable_caption=False)
            index = searcher.search(incoming, freshlen, searchwindowsize)
            if index >= 0:
                self.buffer = incoming[searcher.end : ]
                self.before = incoming[ : searcher.start]
                self.after = incoming[searcher.start : searcher.end]
                self.match = searcher.match
                self.match_index = index
                return self.match_index
            # No match at this point
            if timeout < 0 and timeout is not None:
                raise pexpect.TIMEOUT ('Timeout exceeded in expect_any().')
            # Still have time left, so read more data
            c = self.read_nonblocking (self.maxread, timeout)
            freshlen = len(c)
            time.sleep (0.0001)
            incoming = incoming + c
            if timeout is not None:
                timeout = end_time - time.time()
    except pexpect.EOF, e:
        self.buffer = ''
        self.before = incoming
        self.after = pexpect.EOF
        index = searcher.eof_index
        if index >= 0:
            self.match = pexpect.EOF
            self.match_index = index
            return self.match_index
        else:
            self.match = None
            self.match_index = None
            raise pexpect.EOF (str(e) + '\n' + str(self))
    except pexpect.TIMEOUT, e:
        self.buffer = incoming
        self.before = incoming
        self.after = pexpect.TIMEOUT
        index = searcher.timeout_index
        if index >= 0:
            self.match = pexpect.TIMEOUT
            self.match_index = index
            return self.match_index
        else:
            self.match = None
            self.match_index = None
            raise pexpect.TIMEOUT (str(e) + '\n' + str(self))
    except:
        self.before = incoming
        self.after = None
        self.match = None
        self.match_index = None
        raise

def shell_exec(command, user="", key=None, value=None, cwd=None):
  '''
  Execute a shell command using pexpect, and writing verbose affected output.

  '''
  if key is None:
      key = []
      
  if value is None:
      value = []

  if (not cwd):
    cwd = os.getcwd()

  # Build command to execute
  args=[]
  if (user):
    args.append(user)
  args.append('-c ' + command)

  app.print_verbose("Command: su " + user + " -c '" + command + "'")

  key.append("Verify the SYCO master password[:].*")
  value.append(app.get_master_password() + "\r\n\r")

  num_of_events = len(key)  

  # Timeout for ssh.expect
  key.append(pexpect.TIMEOUT)

  # When ssh.expect reaches the end of file. Probably never
  # does, is probably reaching [PEXPECT]# first.
  key.append(pexpect.EOF)

  out = syco_spawn("su", args, cwd=cwd)
  app.print_verbose("---- Result ----", 2)
  caption = True
  stdout = ""
  index = 0
  while (index < num_of_events+1):
    index = out.expect(key, timeout=3600)
    stdout += out.before      
    caption = False
    if index >= 0 and index < num_of_events:
      out.send(value[index])      
    elif index == num_of_events:
      app.print_error("Catched a timeout from pexpect.expect, lets try again.")

  if (out.exitstatus):    
    app.print_error("Invalid exitstatus %d" % out.exitstatus)

  if (out.signalstatus):
    app.print_error("Invalid signalstatus %d - %s" % out.signalstatus, out.status)

  # An extra line break for the looks.
  if (stdout and app.options.verbose >= 2):
    print("\n"),

  out.close()

  return stdout

def shell_run(command, user="root", events={}):
  '''
  Execute a shell command using pexpect.run, and writing verbose affected output.

  Use shell_exec if possible.

  #TODO: Try to replace this with shell_exec

  '''
  command = "su " + user + ' -c "' + command + '"'

  if (user != ""):
    user_password = app.get_user_password(user)
    events["(?i)Password: "] = user_password + "\n"

  app.print_verbose("Command: " + command)
  (stdout, exit_status) = pexpect.run(command,
    cwd=os.getcwd(),
    events=events,
    withexitstatus=True,
    timeout=10000
  )

  app.print_verbose("---- Result (" + str(exit_status) + ")----", 2)
  app.print_verbose(stdout, 2)

  if (exit_status == None):
    raise Exception("Couldnt execute " + command)

  return stdout

def set_config_property(file_name, search_exp, replace_exp):
  '''
  Change or add a config property to a specific value.

  #TODO: Optimize, do more then one change in the file at the same time.

  '''
  if os.path.exists(file_name):
    exist = False
    try:
      shutil.copyfile(file_name, file_name + ".bak")
      r = open(file_name + ".bak", 'r')
      w = open(file_name, 'w')
      for line in r:
        if re.search(search_exp, line):
          line = re.sub(search_exp, replace_exp, line)
          exist = True
        w.write(line)

      if exist == False:
        w.write(replace_exp + "\n")
    finally:
      r.close()
      w.close()
      os.remove(file_name + ".bak")
  else:
    w = open(file_name, 'w')
    w.write(replace_exp)
    w.close()

if __name__ == "__main__":
  command = 'echo "moo"'
  command = command.replace('\\', '\\\\')
  command = command.replace('"', r'\"')
  command = 'su -c"' + command + '"'
  print command
  print shell_exec(command)

  download_file("http://airadvice.com/buildingblog/wp-content/uploads/2010/05/hal-9000.jpg")
  os.chdir("/tmp/install")
  print shell_exec("ls -alvh")