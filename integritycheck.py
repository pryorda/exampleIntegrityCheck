#!/usr/bin/python
import re
import os
import hashlib
import shelve
from optparse import OptionParser
import sys
import smtplib
import socket

exclude = re.compile('.*.git')
include = re.compile('.*php')

# Current DIct of files and hashes
current = {}
# Files that have different hashes then baseline
changed = {}
# New Files that did not exist in base line
new = {}
# Files that no loner exists
deleted = {}

#EMAIL Settings and code
hname = socket.gethostname()
sender = 'pryorda'
receivers = 'pryorda'
subject = "Subject: CMS Directory IntegrityCheck on " + hname + "\r\n"
to = "To: " + receivers + "\r\n"
whofrom = "From: " + sender + "\r\n"
message = whofrom
message += to
message += subject
message += """
The integrity of the CMS box has changed:\n
"""
sendemail = False


def hashfile(afile, hasher, blocksize=65536):
    # Creates a hash of the file
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()

def createbaseline():
    #Create Baseline
    for path, dirs, files in os.walk(dir_to_check):
      for sub_path, dirs, files in os.walk(path):
        if not re.match(exclude, sub_path):
           for entry in files:
             if re.match(include, entry):
                file = sub_path + '/' + entry
                hash = hashfile(open(file, 'rb'), hashlib.sha256())
                #print("File: {}/{} Hash: {}").format(sub_path, entry, hash)
                base.update({file:hash})
    base.sync()

def getcurrent():
    # Current File Integrity
    for path, dirs, files in os.walk(dir_to_check):
      for sub_path, dirs, files in os.walk(path):
        if not re.match(exclude, sub_path):
           for entry in files:
             if re.match(include, entry):
                file = sub_path + '/' + entry
                hash = hashfile(open(file, 'rb'), hashlib.sha256())
                #print("File: {}/{} Hash: {}").format(sub_path, entry, hash)
                current.update({file:hash})

def getchanges():
    # Find Differences
    for k, v in current.iteritems():
      if k in base.keys():
         if current[k] == base[k]:
            continue
            # print k, "exists in base with hash", v
         else:
            changed.update({k:v})
            # print "Hash for", k, "does not match base hash of", base(k)
      else:
         #Add to new file list
         new.update({k:v})
def findremovedfiles():
    # Check for removed files
    for k, v in base.iteritems():
      if k not in current.keys():
         deleted.update({k:v})


parser = OptionParser()
parser.add_option("-c", "--createbaseline", action="store_true", dest="createbase", default=False,
                  help="Creates baseline.")
parser.add_option("-i", "--integritycheck", action="store_true", dest="integritycheck", default=False,
                  help="Checks the integrity of a directory")
parser.add_option("-d", "--directory", dest="directory",
                  help="Directory to check. Example: /var/www/wordpress (Required)", metavar="directory")
parser.add_option("-b", "--baseline", dest="baseline",
                  help="Location to store baseline. Example: /root/baseline.shelf (Required)", metavar="baseline")
(options, args) = parser.parse_args()

#Create BaseLine
if options.createbase and options.directory and options.baseline:
   dir_to_check = options.directory
   baseline = options.baseline
   print "Creating baseline of", dir_to_check, "in", baseline
   base = shelve.open(baseline)
   createbaseline()

#Check Integrity
elif options.integritycheck and options.directory and options.baseline:
   dir_to_check = options.directory
   baseline = options.baseline
   print "Checking integrity of", dir_to_check, "using baseline:", baseline
   base = shelve.open(baseline)
   getcurrent()
   getchanges()
   findremovedfiles()
   if new or changed or deleted:
      sendemail = True
      if new:
         message += "New files were detected. You might need to run createbaseline\n"
         for k, v in new.iteritems():
           message += "\t" + k + " Hash:" + v + "\n"
         message += "\n\n"
      if deleted:
         message += "File Deletions were detected. You might need to run createbaseline\n"
         for k, v in deleted.iteritems():
           message += "\t" + k + " Hash:" + v + "\n"
         message += "\n\n"
      if changed:
         message += "File changes were detected. You will need to look over the files and validate that it was not compromised\n"
         for k, v in changed.iteritems():
           message += "\t" + k + " Hash:" + v + "\n"
         message += "\n\n"
   if sendemail:
      try:
         smtpObj = smtplib.SMTP('email-server')
         smtpObj.sendmail(sender, receivers.split(","), message)
      except SMTPException:
         print "Failed to send check_orgst.py email"

#Else show usage
else:
  parser.print_help()
  sys.exit()

base.close()

