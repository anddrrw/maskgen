import numpy as np
import cv2
from subprocess import call,Popen, PIPE
import os
import json
from datetime import datetime

def otsu(hist):
  total = sum(hist)
  sumB = 0
  wB = 0
  maximum = 0.0
  sum1 = np.dot( np.asarray(range(256)), hist)
  for ii in range(256):
    wB = wB + hist[ii]
    if wB == 0:
        continue
    wF = total - wB
    if wF == 0:
        break
    sumB = sumB +  ii * hist[ii]
    mB = sumB / wB
    mF = (sum1 - sumB) / wF
    between = wB * wF * (mB - mF) * (mB - mF)
    if between >= maximum:
        level = ii
        maximum = between
  return level

#def findRange(hist,perc):
#  maxvalue = hist[0]
#  maxpos = 0
#  maxdiff = 0
#  lastv = hist[0]
#  for i in range(1,256):
#    diff = abs(hist[i]-lastv)
#    if (diff > maxdiff):
#      maxdiff = diff
#    if hist[i] > maxvalue:
#      maxvalue = hist[i]
#      maxpos = i
#  i = maxpos-1
#  lastv = maxvalue
#  while i>0:
#    diff = abs(hist[i]-lastv)
#    if diff <= maxdiff:
#      break
#    lastv=hist[i]
#    i-=1
#  bottomRange = i
#  i = maxpos+1
#  lastv = maxvalue
#  while i<256:
#    diff = abs(hist[i]-lastv)
#    if diff <= maxdiff:
#      break
#    lastv=hist[i]
#    i+=1
#  topRange = i
#  return bottomRange,topRange


def _buildHist(filename):
  cap = cv2.VideoCapture(filename)
  hist = np.zeros(256).astype('int64')
  bins=np.asarray(range(257))
  pixelCount = 0.0
  while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
      break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pixelCount+=(gray.shape[0]*gray.shape[1])
    hist += np.histogram(gray,bins=bins)[0]
  cap.release()
  return hist,pixelCount

def _buildMasks(filename,histandcount):
  maskprefix = filename[0:filename.rfind('.')]
  histnorm = histandcount[0]/histandcount[1]
  values=np.where((histnorm<=0.95) & (histnorm>(256/histandcount[1])))[0]
  cap = cv2.VideoCapture(filename)
  while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
      break
    gray = _grayToRGB(frame)
    result = np.ones(gray.shape)*255
    totalMatch = 0
    for value in values: 
       matches = gray==value
       totalMatch+=sum(sum(matches))
       result[matches]=0
    if totalMatch>0:
       elapsed_time = cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
       cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time) + '.png',gray)      
       break
  cap.release()

def buildMasksFromCombinedVideoOld(filename):
  h,pc = _buildHist(filename)
  hist = h/pc
  return _buildMasks(filename,hist)

def buildMasksFromCombinedVideo(filename,codec='mp4v',suffix='mp4',startSegment=None, endSegment=None, startTime=0):
  maskprefix = filename[0:filename.rfind('.')]
  capIn = cv2.VideoCapture(filename)
  capOut = None
  try:
    ranges= []
    start = None
    fourcc = cv2.cv.CV_FOURCC(*codec)
    count = 0
    fgbg = cv2.BackgroundSubtractorMOG2()
    first = True
    sample = None
    kernel = np.ones((5,5),np.uint8)
    while(capIn.isOpened()):
      ret, frame = capIn.read()
      if sample is None:
        sample = np.ones(frame[:,:,0].shape)*255
      if not ret:
        break
      elapsed_time = capIn.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
      if startSegment and startSegment > elapsed_time:
        continue
      if endSegment and endSegment < elapsed_time:
        break
      thresh = fgbg.apply(frame)
      if first:
        first = False
        continue
#      gray = frame[:,:,1]
#      laplacian = cv2.Laplacian(frame,cv2.CV_64F)
#      thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 11, 1)
#      ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
      result = thresh.copy()
      result[:,:]=0
      result[abs(thresh)>0.000001] = 255 
      opening = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
      closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
      totalMatch = sum(sum(closing))
      result = closing
      if totalMatch>0:
        count+=1
        if start is None:
          start = elapsed_time + startTime
          sample = result
          capOut = cv2.VideoWriter(_composeMaskName(maskprefix,start,suffix), fourcc, capIn.get(cv2.cv.CV_CAP_PROP_FPS),(result.shape[1],result.shape[0]),False)
        capOut.write(_grayToRGB(result))
      else:
        if start is not None:
          ranges.append({'starttime':start,'endtime':elapsed_time+startTime,'frames':count,'mask':sample,'videosegment':os.path.split(_composeMaskName(maskprefix,start,suffix))[1]})
          capOut.release()
          count = 0
        start = None
        capOut = None
    if start is not None:
      ranges.append({'starttime':start,'endtime':elapsed_time+startTime,'frames':count,'mask':sample,'videosegment':os.path.split(_composeMaskName(maskprefix,start,suffix))[1]})
      capOut.release()
  finally:
    capIn.release()
    if capOut:
      capOut.release()
  return ranges

def _rgbToGray(frame):
   """
     returnp  green only
   """
#  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   return frame[:,:,1]

def _grayToRGB(frame):
   """
     project gray into Green
   """
#  cv2.cvtColor(result, cv2.COLOR_GRAY2BGR))
   result = np.zeros((frame.shape[0],frame.shape[1],3))
   result[:,:,1] = frame
   return result.astype('uint8')

def _composeMaskName(maskprefix,starttime,suffix):
   return maskprefix + '_mask_' + str(starttime) + '.' + suffix 

def _invertSegment(dir,segmentFileName, prefix,starttime,codec='mp4v'):
   """
    Invert a single video file (gray scale)
    """
   suffix = segmentFileName[segmentFileName.rfind('.')+1:]
   maskFileName = _composeMaskName(prefix,str(starttime),suffix)
   capIn = cv2.VideoCapture(os.path.join(dir,segmentFileName))
   fourcc = capIn.get(cv2.cv.CV_CAP_PROP_FOURCC)
   if fourcc == 0:
     fourcc = cv2.cv.CV_FOURCC(*codec)
   capOut = cv2.VideoWriter(os.path.join(dir,maskFileName), fourcc, \
             capIn.get(cv2.cv.CV_CAP_PROP_FPS), \
             (int(capIn.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),int(capIn.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))), \
             False)
   try:
     ret = True
     while(ret and  capIn.isOpened()):
       ret, frame = capIn.read()
       if ret:
          result = _rgbToGray(frame)
          result = abs(result - np.ones(result.shape)*255)
          capOut.write(_grayToRGB(result))
   finally:
     capIn.release()
     if capOut:
       capOut.release()
   return maskFileName
   
def invertVideoMasks(dir,videomasks,start,end):
   """
   Invert black/white for the video masks.
   Save to a new files for the given start and end node names.
   """
   if videomasks is None:
     return
   prefix = start + '_' + end
   result = []
   for maskdata in videomasks:
     maskdata = maskdata.copy()
     maskdata['videosegment'] = _invertSegment(dir,maskdata['videosegment'], prefix, maskdata['starttime'])
     result.append(maskdata)
   return result


def addToMeta(meta,prefix,line,split=True):
   parts = line.split(',') if split else [line]
   for part in parts:
     pair = [x.strip().lower() for x in part.split(': ')]
     if len(pair)>1 and pair[1] != '':
       if prefix != '':
         meta[prefix + '.' + pair[0]] = pair[1]
       else:
         meta[pair[0]] = pair[1]
   
def getStreamId(line):
   start = line.find('#')
   if start > 0:
     end = line.find('(',start)
     end = min(end,line.find(': ',start))
     return line[start:end]
   return ''

def processMeta(stream):
   meta = {}
   prefix = ''
   while True:
     line = stream.readline()   
     if line is None or len(line) == 0:
         break
     if 'Stream' in line:
         prefix=getStreamId(line)
         splitPos = line.find(': ')
         meta[line[0:splitPos].strip()] = line[splitPos+2:].strip()
         continue
     if 'Duration' in line:
       addToMeta(meta,prefix, line)
     else:
       addToMeta(meta,prefix, line, split=False)
   return meta

def sortFrames(frames):
   for k,v in frames.iteritems():
    frames[k] = sorted(v,key=lambda meta: meta['pkt_pts_time'])

def _addMetaToFrames(frames,meta):
   if len(meta) > 0 and 'stream_index' in meta:
      index = meta['stream_index']
      if index not in frames:
         frames[index] = []
      frames[index].append(meta)
      meta.pop('stream_index')

def processFrames(stream):
   frames = {}
   meta = {}
   while True:
     line = stream.readline()  
     if line is None or len(line) == 0:
         break
     if '[/FRAME]' in line:
        _addMetaToFrames(frames,meta)
        meta = {}
     else:
         parts = line.split('=')
         if len(parts)>1:
            meta[parts[0].strip()] = parts[1].strip()
   _addMetaToFrames(frames,meta)
   return frames
#   sortFrames(frames)
   
def getMeta(file,withFrames=False):
   ffmpegcommand = os.getenv('MASKGEN_FFPROBETOOL','ffprobe')
   p = Popen([ffmpegcommand,file, '-show_frames'] if withFrames else ['ffprobe',file],stdout=PIPE,stderr=PIPE)
   try:
     frames= processFrames(p.stdout) if withFrames else {}
     meta = processMeta(p.stderr) 
   finally:
     p.stdout.close()
     p.stderr.close()
   return meta,frames

# str(ffmpeg.compareMeta({'f':1,'e':2,'g':3},{'f':1,'y':3,'g':4}))=="{'y': ('a', 3), 'e': ('d', 2), 'g': ('c', 4)}"
def compareMeta(oneMeta,twoMeta,skipMeta=None):
  diff = {}
  for k,v in oneMeta.iteritems():
    if skipMeta is not None and k in skipMeta:
      continue
    if k in twoMeta and twoMeta[k] != v:
      diff[k] = ('change',v, twoMeta[k])
    if k not in twoMeta:
      diff[k] = ('delete',v)
  for k,v in twoMeta.iteritems():
    if k not in oneMeta:
      diff[k] = ('add',v)
  return diff

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compareStream(a,b,orderAttr='pkt_pts_time',skipMeta=None):
  """
    Compare to lists of hash maps, generating 'add', 'delete' and 'change' records.
    An order attribute (time stamp) is provided as the orderAttr, to identify each individual record.
    The order attribute is required to identify sequence of added or removed hashes.
    The order attribute serves as unique id of each hash.
    The order attribute is a mandatory key in the hash.
  """  
  apos = 0
  bpos = 0
  diff = []
  start=0
  while apos < len(a) and bpos < len(b):
    apacket = a[apos]
    if orderAttr not in apacket:
      apos+=1
      continue 
    aptime = float(apacket[orderAttr])
    bpacket = b[bpos]
    if orderAttr not in bpacket:
      bpos+=1
      continue 
    try:
      bptime = float(bpacket[orderAttr])
    except ValueError as e:
      print bpacket
      raise e
    if aptime==bptime:
      metaDiff = compareMeta(apacket,bpacket,skipMeta=skipMeta)
      if len(metaDiff)>0:
        diff.append(('change',apos,bpos,aptime,metaDiff))
      apos+=1
      bpos+=1
    elif aptime < bptime:
      start = aptime
      c = 0
      while aptime < bptime and apos < len(a):
         end = aptime
         apos+=1
         c+=1
         if apos < len(a):
           apacket = a[apos]
           aptime = float(apacket[orderAttr])
      diff.append(('delete',start,end,c))
    elif aptime > bptime:
      start = bptime
      c = 0
      while aptime > bptime and bpos < len(b):
          end = bptime
          c+=1
          bpos+=1
          if bpos < len(b):
            bpacket = b[bpos]
            bptime = float(bpacket[orderAttr])
      diff.append(('add',start,end,c))
  if apos < len(a):
    start = float(a[apos][orderAttr])
    c = len(a)-apos
    apacket = a[len(a)-1]
    aptime = float(apacket[orderAttr])
    diff.append(('delete',start,aptime,c))
  elif bpos < len(b):
    start = float(b[bpos][orderAttr])
    c = len(b)-bpos
    bpacket = b[len(b)-1]
    bptime = float(bpacket[orderAttr])
    diff.append(('add',start,bptime,c))
  return diff

def compareFrames(oneFrames,twoFrames,skipMeta=None):
  diff = {}
  for streamId, packets in oneFrames.iteritems():
    if streamId in twoFrames:
       diff[streamId] = ('change',compareStream(packets, twoFrames[streamId],skipMeta=skipMeta))
    else:
       diff[streamId] = ('delete',[])
  for streamId, packets in twoFrames.iteritems():
    if streamId not in oneFrames:
       diff[streamId] = ('add',[])
  return diff
    
#video_tools.formMetaDataDiff('/Users/ericrobertson/Documents/movie/videoSample.mp4','/Users/ericrobertson/Documents/movie/videoSample1.mp4')
def formMetaDataDiff(fileOne, fileTwo):
  """
  Obtaining frame and video meta-data, compare the two videos, identify changes, frame additions and frame removals
  """
  oneMeta,oneFrames = getMeta(fileOne,withFrames=True)
  twoMeta,twoFrames = getMeta(fileTwo,withFrames=True)
  metaDiff = compareMeta(oneMeta,twoMeta)
  frameDiff = compareFrames(oneFrames, twoFrames, skipMeta=['pkt_pos','pkt_size'])
  return metaDiff,frameDiff

#video_tools.processSet('/Users/ericrobertson/Documents/movie',[('videoSample','videoSample1'),('videoSample1','videoSample2'),('videoSample2','videoSample3'),('videoSample4','videoSample5'),('videoSample5','videoSample6'),('videoSample6','videoSample7'),('videoSample7','videoSample8'),('videoSample8','videoSample9'),('videoSample9','videoSample10'),('videoSample11','videoSample12'),('videoSample12','videoSample13'),('videoSample13','videoSample14'),('videoSample14','videoSample15')] ,'.mp4')
def processSet(dir,set,postfix):
  first = None
  for pair in set:
    print pair
    resMeta,resFrame = formMetaDataDiff(os.path.join(dir,pair[0]+postfix),os.path.join(dir,pair[1]+postfix))
    resultFile = os.path.join(dir,pair[0] + "_" + pair[1] + ".json")
    with open(resultFile, 'w') as f:
       json.dump({"meta":resMeta,"frames":resFrame},f,indent=2)


def toMilliSeconds(st):
  """
    Convert time to millisecond
  """
  if not st or len(st) == 0:
    return 0

  stdt = None
  try:
    stdt = datetime.strptime(st, '%H:%M:%S.%f')
  except ValueError:
    stdt = datetime.strptime(st, '%H:%M:%S')
  return (stdt.hour*3600 + stdt.minute*60 + stdt.second)*1000 + stdt.microsecond/1000

def getDuration(st,et):
  """
   calculation duration
  """
  stdt = None
  try:
    stdt = datetime.strptime(st, '%H:%M:%S.%f')
  except ValueError:
    stdt = datetime.strptime(st, '%H:%M:%S')

  etdt = None
  try:
    etdt = datetime.strptime(et, '%H:%M:%S.%f')
  except ValueError:
    etdt = datetime.strptime(et, '%H:%M:%S')

  delta = etdt-stdt
  if delta.days < 0:
    return None

  sec = delta.seconds
  sec+= (1 if delta.microseconds > 0 else 0)
  hr = sec/3600
  mi = sec/60 - (hr*60)
  ss = sec - (hr*3600) - mi*60
  return '{:=02d}:{:=02d}:{:=02d}'.format(hr,mi,ss)

#video_tools.formMaskDiff('/Users/ericrobertson/Documents/movie/s1/videoSample5.mp4','/Users/ericrobertson/Documents/movie/s1/videoSample6.mp4')
def formMaskDiff(fileOne, fileTwo,startSegment=None,endSegment=None,applyConstraintsToOutput=True):
   """
   Construct a diff video.  The FFMPEG provides degrees of difference by intensity variation in the green channel.
   The normal intensity is around 98.
   """
   ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL','ffmpeg')
   prefixOne = fileOne[0:fileOne.rfind('.')]
   prefixTwo = os.path.split(fileTwo[0:fileTwo.rfind('.')])[1]
   postFix = fileOne[fileOne.rfind('.'):]
   outFileName = prefixOne + '_'  + prefixTwo + postFix
   command = [ffmpegcommand, '-y']
   if startSegment:
     command.extend(['-ss',startSegment])
     if endSegment:
       command.extend(['-t', getDuration(startSegment,endSegment)])
   command.extend(['-i', fileOne])
   if startSegment and applyConstraintsToOutput:
     command.extend(['-ss',startSegment])
     if endSegment:
       command.extend(['-t', getDuration(startSegment,endSegment)])
   command.extend(['-i', fileTwo,'-filter_complex', 'blend=all_mode=difference', outFileName])
   p = Popen(command,stderr=PIPE)
   errors = []
   sendErrors = False
   try:
     while True:
       line = p.stderr.readline()  
       if line:
         errors.append(line)
       else:
         break
     sendErrors = p.wait() != 0
   except OSError as e:
     sendErrors = True
     errors.append(str(e))
   finally:
      p.stderr.close()

   if not sendErrors:
     result = buildMasksFromCombinedVideo(outFileName,startTime=toMilliSeconds(startSegment))
   else:
     result = []

   try:
     os.remove(outFileName)
   except IOError:
     print 'video diff process failed'

   return result,errors if sendErrors  else []

