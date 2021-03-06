from subprocess import call,Popen, PIPE
import os

def copyexif(source,target):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  try:
     call([exifcommand, '-all=', target])
     call([exifcommand, '-P', '-TagsFromFile',  source, '-all:all', '-unsafe', target])
     call([exifcommand, '-XMPToolkit=', target])
     call([exifcommand, '-Warning=', target])
     return None
  except OSError:
     return 'exiftool not installed'

def getexif(source):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  meta = {}
  try:
    p = Popen([exifcommand,source],stdout=PIPE,stderr=PIPE)
    try:
      while True:
        line = p.stdout.readline()
        try:
           line = unicode(line,'utf-8')
        except:
           try:
             line = unicode(line,'latin').encode('ascii',errors='xmlcharrefreplace')
           except:
             continue
        if line is None or len(line) == 0:
           break
        pos = line.find(': ')
        if pos > 0:
           meta[line[0:pos].strip()] = line[pos+2:].strip()
    finally:
      p.stdout.close()
      p.stderr.close()
  except OSError:
    print "Exiftool not installed"
  return meta

def _decodeStr(name,sv):
  return sv
       
def compareexif(source,target):
  metasource = getexif(source)
  metatarget = getexif(target)
  diff = {}
  for k,sv in metasource.iteritems():
     if k in metatarget:
       tv = metatarget[k]
       if tv != sv:
         diff[k] = ('change',sv,tv)
     else:
         diff[k] = ('delete',sv)
  for k,tv in metatarget.iteritems():
     if k not in metasource:
         diff[k] = ('add',tv)
  return diff

