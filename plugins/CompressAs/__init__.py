"""
Andrew Smith
PAR Government Systems
7/15/2016

compress_as takes in two JPEG images, and compresses the first with the q tables of the second
possible future features:
-create/compress thumbnail as well

"""

import os
import tempfile
from PIL import Image
from bitstring import BitArray
from subprocess import call,Popen, PIPE

def parse_tables(imageFile):
    """
    Grab all quantization tables from jpg header
    :param imageFile: string containing jpg image filename
    :return: list of lists of unsorted quantization tables
    """

    # open the image and scan for q table marker "FF DB"
    s = open(imageFile, 'rb')
    b = BitArray(s)
    ffdb = b.findall('0xffdb', bytealigned=True)

    # grab the tables, based on format
    tables = []
    for start in ffdb:
        subset = b[start + 5 * 8:start + 134 * 8]
        check = subset.find('0xff', bytealigned=True)
        if check:
            subsubset = subset[0:check[0]]
            tables.append(subsubset)
        else:
            tables.append(subset[0:64 * 8])
            tables.append(subset[65 * 8:])

    # concatenate the tables, and convert them from bitarray to list
    finalTable = []
    for table in tables:
        tempTable = []

        bi = table.bin
        for i in xrange(0, len(bi), 8):
            byte = bi[i:i + 8]
            val = int(byte, 2)
            tempTable.append(val)
        finalTable.append(tempTable)
    s.close()
    return finalTable

def sort_tables(tablesList):
    """
    Un-zigzags a list of quantization tables
    :param tablesList: list of lists of unsorted quantization tables
    :return: list of lists of sorted quantization tables
    """

    # hardcode order, since it will always be length 64
    indices = [0,1,5,6,14,15,27,28,2,4,7,13,16,26,29,42,3,8,12,17,25,30,41,43,
               9,11,18,24,31,40,44,53,10,19,23,32,39,45,52,54,20,22,33,38,46,
               51,55,60,21,34,37,47,50,56,59,61,35,36,48,49,57,58,62,63]

    newTables = []
    for listIdx in xrange(len(tablesList)):
        if len(tablesList[listIdx]) == 64:
            tempTable = []
            for elmIdx in xrange(0,64):
                tempTable.append(tablesList[listIdx][indices[elmIdx]])
            newTables.append(tempTable)
    return newTables

def runexiftool(args):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  command = [exifcommand]
  command.extend(args)
  try:
    p = Popen(command,stdout=PIPE,stderr=PIPE)
    try:
      while True:
        line = p.stdout.readline()  
        if line is None or len(line) == 0:
           break
        print line
    finally:
      p.stdout.close()
      p.stderr.close()
  except OSError as e:
    print "Exiftool not installed"
    raise e


def save_as(source, target, qTables):
    """
    Saves image file using quantization tables
    :param imageFile: string filename of image
    :param qTables: list of lists containing jpg quantization tables
    """

    # much of the time, images will have thumbnail tables included.
    # from what I've seen the thumbnail tables always come first...
    thumbTable = []
    if len(qTables) > 2:
        thumbTable = qTables[0:2]
        finalTable = qTables[-2:]
    elif len(qTables) < 2:
        finalTable = [qTables, qTables]
    else:
        finalTable = qTables

    # write jpeg with specified tables
    im = Image.open(source)
    im.save(target, subsampling=1, qtables=finalTable)
    if thumbTable:
        im.thumbnail((128,128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        try:
            im.save(tempFile, subsampling=1, qtables=thumbTable)
        except OverflowError:
            thumbTable[:] = [[(x - 128) for x in row] for row in thumbTable]
            im.save(tempFile, subsampling=1, qtables=thumbTable)
        try:
          runexiftool(['-overwrite_original','-P','-m','-"ThumbnailImage<=' + tempFile + '"',target])
          runexiftool(['exiftool', '-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
        finally:
          os.close(fd)
          os.remove(tempFile)
    im.close()


def transform(img,source,target, **kwargs):

    donor = kwargs['donor']
    tables_zigzag = parse_tables(donor[1])
    tables_sorted = sort_tables(tables_zigzag)
    save_as(source, target, tables_sorted)
    
    return False
    
def operation():
    return ['AntiForensicExifQuantizationTable','AntiForensicExif', 
            'Save as a JPEG using original tables', 'PIL', '1.1.7']
    
def args():
    return [('donor', None, 'JPEG with donor QT')]

def suffix():
    return '.jpg'
