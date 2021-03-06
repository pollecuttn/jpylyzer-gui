#! /usr/bin/env python
#
#
#
# jpylyzer
#
# Requires: Python 2.7 (older versions won't work) OR Python 3.2 or more recent
#  (Python 3.0 and 3.1 won't work either!)
#
# Copyright (C) 2011, 2012 Johan van der Knijff, Koninklijke Bibliotheek -
#  National Library of the Netherlands
#
# Contributors: Rene van der Ark (refactoring of original code), Lars Buitinck 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ISSUES:
# 1. Using wildcards on the command line doesn't result in the expected
# behaviour under Linux! Workaround: wrap them in quotes, e.g:
#
#  jpylyzer.py *  -- only processes 1st encountered file!
#  jpylyzer.py "*" -- results in correct behaviour
#

import sys
import os
import time
import imp
import glob
import struct
import argparse
import config
import etpatch as ET
from boxvalidator import BoxValidator
from byteconv import bytesToText
from shared import printWarning
from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import askdirectory
scriptPath, scriptName = os.path.split(sys.argv[0])

__version__= "1.8.2"

def main_is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
        hasattr(sys, "importers") # old py2exe
        or imp.is_frozen("__main__")) # tools/freeze

def get_main_dir():
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])

def readFileBytes(file):
    # Read file, return contents as a byte object
    
    # Open file
    f = open(file,"rb")
    
    # Put contents of file into a byte object.
    fileData=f.read()
    f.close()
    
    return(fileData)

def generatePropertiesRemapTable():

    # Generates nested dictionary which is used to map 'raw' property values
    # (mostly integer values) to corresponding text descriptions

    # Master dictionary for mapping of text descriptions to enumerated values
    # Key: corresponds to parameter tag name
    # Value: sub-dictionary with mappings for all property values
    enumerationsMap={}

    # Sub-dictionaries for individual properties

    # Generic 0 = no, 1=yes mapping (used for various properties)
    yesNoMap={}
    yesNoMap[0]="no"
    yesNoMap[1]="yes"

    # Bits per component: sign (Image HeaderBox, Bits Per Component Box, SIZ header
    # in codestream)
    signMap={}
    signMap[0]="unsigned"
    signMap[1]="signed"

    # Compression type (Image Header Box)
    cMap={}
    cMap[7]="jpeg2000"

    # meth (Colour Specification Box)
    methMap={}
    methMap[1]="Enumerated"
    methMap[2]="Restricted ICC"
    methMap[3]="Any ICC"  # JPX only
    methMap[4]="Vendor Colour" # JPX only

    # enumCS (Colour Specification Box)
    enumCSMap={}
    enumCSMap[16]="sRGB"
    enumCSMap[17]="greyscale"
    enumCSMap[18]="sYCC"
    
    # Profile Class (ICC)
    profileClassMap={}
    profileClassMap[b'scnr']="Input Device Profile"
    profileClassMap[b'mntr']="Display Device Profile"
    profileClassMap[b'prtr']="Output Device Profile"
    profileClassMap[b'link']="DeviceLink Profile"
    profileClassMap[b'spac']="ColorSpace Conversion Profile"
    profileClassMap[b'abst']="Abstract Profile"
    profileClassMap[b'nmcl']="Named Colour Profile"
    
    # Primary Platform (ICC)
    primaryPlatformMap={}
    primaryPlatformMap[b'APPL']="Apple Computer, Inc."
    primaryPlatformMap[b'MSFT']="Microsoft Corporation"
    primaryPlatformMap[b'SGI']="Silicon Graphics, Inc."
    primaryPlatformMap[b'SUNW']="Sun Microsystems, Inc."
    
    # Transparency (ICC)
    transparencyMap={}
    transparencyMap[0]="Reflective"
    transparencyMap[1]="Transparent"
    
    # Glossiness (ICC)
    glossinessMap={}
    glossinessMap[0]="Glossy"
    glossinessMap[1]="Matte"
    
    # Polarity (ICC)
    polarityMap={}
    polarityMap[0]="Positive"
    polarityMap[1]="Negative"
    
    # Colour (ICC)
    colourMap={}
    colourMap[0]="Colour"
    colourMap[1]="Black and white"
    
    # Rendering intent (ICC)
    renderingIntentMap={}
    renderingIntentMap[0]="Perceptual"
    renderingIntentMap[1]="Media-Relative Colorimetric"
    renderingIntentMap[2]="Saturation"
    renderingIntentMap[3]="ICC-Absolute Colorimetric"
    
    # mTyp (Component Mapping box)
    mTypMap={}
    mTypMap[0]="direct use"
    mTypMap[1]="palette mapping"
    
    # Channel type (Channel Definition Box)
    cTypMap={}
    cTypMap[0]="colour"
    cTypMap[1]="opacity"
    cTypMap[2]="premultiplied opacity"
    cTypMap[65535]="not specified"

    # Channel association (Channel Definition Box)
    cAssocMap={}
    cAssocMap[0]="all colours"
    cAssocMap[65535]="no colours"

    # Decoder capabilities, rsiz (Codestream, SIZ)
    rsizMap={}
    rsizMap[0]="ISO/IEC 15444-1" # Does this correspiond to Profile 2??
    rsizMap[1]="Profile 0"
    rsizMap[2]="Profile 1"

    # Progression order (Codestream, COD)
    orderMap={}
    orderMap[0]="LRCP"
    orderMap[1]="RLCP"
    orderMap[2]="RPCL"
    orderMap[3]="PCRL"
    orderMap[4]="CPRL"

    # Transformation type (Codestream, COD)
    transformationMap={}
    transformationMap[0]="9-7 irreversible"
    transformationMap[1]="5-3 reversible"
    
    # Quantization style (Codestream, QCD)
    qStyleMap={}
    qStyleMap[0]="no quantization"
    qStyleMap[1]="scalar derived"
    qStyleMap[2]="scalar expounded"
    
    # Registration value (Codestream, COM)
    registrationMap={}
    registrationMap[0]="binary"
    registrationMap[1]="ISO/IEC 8859-15 (Latin)"

    # Add sub-dictionaries to master dictionary, using tag name as key
    enumerationsMap['unkC']=yesNoMap
    enumerationsMap['iPR']=yesNoMap
    enumerationsMap['profileClass']=profileClassMap
    enumerationsMap['primaryPlatform']=primaryPlatformMap
    enumerationsMap['embeddedProfile']=yesNoMap
    enumerationsMap['profileCannotBeUsedIndependently']=yesNoMap
    enumerationsMap['transparency']=transparencyMap
    enumerationsMap['glossiness']=glossinessMap
    enumerationsMap['polarity']=polarityMap
    enumerationsMap['colour']=colourMap
    enumerationsMap['renderingIntent']=renderingIntentMap
    enumerationsMap['bSign']=signMap
    enumerationsMap['mTyp']=mTypMap
    enumerationsMap['precincts']=yesNoMap
    enumerationsMap['sop']=yesNoMap
    enumerationsMap['eph']=yesNoMap
    enumerationsMap['multipleComponentTransformation']=yesNoMap
    enumerationsMap['codingBypass']=yesNoMap
    enumerationsMap['resetOnBoundaries']=yesNoMap
    enumerationsMap['termOnEachPass']=yesNoMap
    enumerationsMap['vertCausalContext']=yesNoMap
    enumerationsMap['predTermination']=yesNoMap
    enumerationsMap['segmentationSymbols']=yesNoMap
    enumerationsMap['bPCSign']=signMap
    enumerationsMap['ssizSign']=signMap
    enumerationsMap['c']=cMap
    enumerationsMap['meth']=methMap
    enumerationsMap['enumCS']=enumCSMap
    enumerationsMap['cTyp']=cTypMap
    enumerationsMap['cAssoc']=cAssocMap
    enumerationsMap['order']=orderMap
    enumerationsMap['transformation']=transformationMap
    enumerationsMap['rsiz']=rsizMap
    enumerationsMap['qStyle']=qStyleMap
    enumerationsMap['rcom']=registrationMap

    return(enumerationsMap)

def checkOneFile(file):
    # Process one file and return analysis result as text string (which contains
    # formatted XML)
    
    fileData = readFileBytes(file)
    isValidJP2, tests, characteristics = BoxValidator("JP2", fileData).validate() #validateJP2(fileData)
    
    # Generate property values remap table
    remapTable = generatePropertiesRemapTable()

    # Create printable version of tests and characteristics tree
    tests.makeHumanReadable()
    characteristics.makeHumanReadable(remapTable)
    
    # Create output elementtree object
    root=ET.Element('jpylyzer')

    # Create elements for storing tool and file meta info
    toolInfo=ET.Element('toolInfo')
    fileInfo=ET.Element('fileInfo')
    
    # File name and path may contain non-ASCII characters, decoding to Latin should
    # (hopefully) prevent any Unicode decode errors. Elementtree will then deal with any non-ASCII
    # characters by replacing them with numeric entity references
    try:
        # This works in Python 2.7, but raises error in 3.x (no decode attribute for str type!)
        fileName=os.path.basename(file).decode("iso-8859-15","strict")
        filePath=os.path.abspath(file).decode("iso-8859-15","strict")
    except AttributeError:
        # This works in Python 3.x, but goes wrong withh non-ASCII chars in 2.7
        fileName=os.path.basename(file)
        filePath=os.path.abspath(file)
        
    # Produce some general tool and file meta info
    toolInfo.appendChildTagWithText("toolName", scriptName)
    toolInfo.appendChildTagWithText("toolVersion", __version__)
    fileInfo.appendChildTagWithText("fileName", fileName)
    fileInfo.appendChildTagWithText("filePath", filePath)
    fileInfo.appendChildTagWithText("fileSizeInBytes", str(os.path.getsize(file)))
    fileInfo.appendChildTagWithText("fileLastModified", time.ctime(os.path.getmtime(file)))

    # Append to root
    root.append(toolInfo)
    root.append(fileInfo)

    # Add validation outcome
    root.appendChildTagWithText("isValidJP2", str(isValidJP2))

    # Append test results and characteristics to root
    root.append(tests)
    root.append(characteristics)

    # Result as XML
    result=root.toxml().decode("ascii")

    return(result)
    
def checkFiles(images):
    if len(images) == 0:
        printWarning("no images to check!")

    for image in images:
            thisFile = image

            isFile = os.path.isfile(thisFile)

            if isFile:
                # Analyse file
                result=checkOneFile(thisFile)
                
                # Write output to stdout
                sys.stdout.write(result)

def parseCommandLine():
    # Create parser
    parser = argparse.ArgumentParser(description="JP2 image validator and properties extractor",version=__version__)

    # Add arguments
    parser.add_argument('jp2In', action="store", help="input JP2 image(s)")
    parser.add_argument('--verbose', action="store_true", dest="outputVerboseFlag", default=False, help="report test results in verbose format")

    # Parse arguments
    args=parser.parse_args()

    return(args)

def main():
    # Get input from command line
    args=parseCommandLine()
    jp2In=args.jp2In
    
    # Storing this to 'config.outputVerboseFlag' makes this value available to any module
    # that imports 'config.py' (here: 'boxvalidator.py')
    config.outputVerboseFlag=args.outputVerboseFlag

    # Input images as file list
    imagesIn=glob.glob(jp2In)
    
    # Check file
    checkFiles(imagesIn)

def selectJptwoFile():
    jp2filename.set('')
    nofilechosen.set('')
    xmlfilenamepath.set('')
    nofileordirchosen.set('')
    """ Returns selected JP2 file path and name """
    jp2file = askopenfilename(filetypes=[("jp2",".jp2"),("All files","*.*")])
    if jp2file:
        lblJp2Name.pack(padx=5, pady=5)
        lblJp2.pack()
        setJp2FileNameLabel(jp2file)
        return jp2file
    else:
        nofilechosen.set("You haven't selected a JP2 file to validate."
                         +"\nClick the button above to select a JP2 file to validate"
                         +"\nor"
                         +"\nClose this window")
        lblNofilechosen.pack()
    
def chooseDir():
    xmldir.set('')
    nodirchosen.set('')
    xmlfilenamepath.set('')
    nofileordirchosen.set('')
    """ Returns a selected directory path and name """
    directory = askdirectory()
    if directory:
        lblDirName.pack(padx=5, pady=5)
        lblDir.pack()
        setDirNameLabel(directory)
        return directory
    else:
        nodirchosen.set("You haven't selected or created a folder to store your output xml file."
                         +"\nClick the button above to select or create a folder"
                         +"\nor"
                         +"\nClose this window")
        lblNodirchosen.pack()

def createXmlFileName(file, xmldirectory):
    jp2file = os.path.split(file)
    xmlfilename = jp2file[1]
    xmlfilename = xmlfilename.split('.')[0] + '.xml'
    xmlfilenameandpath = str(xmldirectory) + '/' + str(xmlfilename)
    lblXmlName.pack(padx=5, pady=5)
    lblXml.pack()
    return xmlfilenameandpath
    
def setJp2FileNameLabel(file):
    jp2filename.set(file)

def setDirNameLabel(file):
    xmldir.set(file)

def setXmlFileNameLabel(file):
    xmlfilenamepath.set(file)

def setCredits():
    credit.set("[gui by https://github.com/pollecuttn, built on jpylyzer (https://github.com/openplanets/jpylyzer)]")
    lblCredits.pack(pady=20)    

def jpylyze():
    nofilechosen.set('')
    nodirchosen.set('')
    nofileordirchosen.set('')
    """ get filename and path of jp2 file
    get directory name and path for output xml file
    if both exist
        create an xml file name and path based on the jp2 file name and the directory chosen to store the output xml file
        run the jp2 file through checkOneFile()
        print the output to the xml file
        display the xml file name and path on the gui
        display the credits on the gui
    else
        display message to choose both JP2 file and xml output directory"""
    jptwofilename = jp2filename.get()
    xmldirectory = xmldir.get()
    if jptwofilename and xmldirectory:
        xmlfilename = createXmlFileName(jptwofilename, xmldirectory)
        try:
            with open(xmlfilename, "w") as out:
                xmlObject = checkOneFile(jptwofilename)
                print(xmlObject, file=out)
        except:
            pass
        setXmlFileNameLabel(xmlfilename)
        setCredits()
    else:
        nofileordirchosen.set("Both a JP2 file and an xml folder need to be selected."
                         +"\nClick the buttons above to select both"
                         +"\nor"
                         +"\nClose this window")
        lblNofileordirchosen.pack()


app = Tk()
app.title("jpylyzer gui") 
app.geometry('700x600+200+100')

btnChooseJp2 = Button(app, text="1. Select jp2 file", command = selectJptwoFile, width=25, height=2)
btnChooseJp2.pack(pady=5)

btnChooseDir = Button(app, text="2. Select or create folder", command = chooseDir, width=25, height=2)
btnChooseDir.pack(pady=5)

btnJpylyze = Button(app, text="3. jpylyze", command = jpylyze, width=25, height=2)
btnJpylyze.pack(pady=5)

nofilechosen = StringVar()
nofilechosen.set('')

nodirchosen = StringVar()
nodirchosen.set('')

nofileordirchosen = StringVar()
nofileordirchosen.set('')

jp2filename = StringVar()
jp2filename.set('')

xmldir = StringVar()
xmldir.set('')

xmlfilenamepath = StringVar()
xmlfilenamepath.set('')

credit = StringVar()
credit.set('')

lblJp2Name = Label(app, text="JP2 file selected: ")

lblJp2 = Label(app, textvariable=jp2filename)

lblDirName = Label(app, text="Folder for output XML file selected: ")

lblDir = Label(app, textvariable=xmldir)

lblNofilechosen = Label(app, textvariable=nofilechosen, fg = "blue")

lblXmlName = Label(app, text="XML out file location: ")

lblXml = Label(app, textvariable=xmlfilenamepath)

lblNodirchosen = Label(app, textvariable=nodirchosen, fg = "blue")

lblNofileordirchosen = Label(app, textvariable=nofileordirchosen, fg = "blue")

lblCredits = Label(app, textvariable=credit)
        
app.mainloop()
