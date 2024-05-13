import os, imutils, shutil
import PyPDF2, cv2, time
import glob, re
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
from pytesseract import TesseractError
import numpy as np
import pandas as pd
from skimage import filters, exposure
from sqlalchemy import create_engine
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


##############################################################################
##                                                                          ##
##                       Paths to folders containing:                       ##
##                                                                          ##
##                             1. Raw PDF Files                             ##
##                             2. Identified PDF                            ##
##                            3. Unidentified PDF                           ##
##                                                                          ##
##############################################################################


currPath = f'{os.getcwd()}' 
pathPDF = f'{currPath}\\Files\\'
scannedPDF = f'{pathPDF}Scanned'
notscanPDF = f'{pathPDF}Not-Scanned'


##############################################################################
##                                                                          ##
##                             SQL Configuration                            ##
##                                                                          ##
##############################################################################


usr = 'read_only'
pwd = 'Neustar01'
srvr = 'unifin-sql'
db = 'tiger'
drvr = 'ODBC+Driver+17+for+SQL+Server'

config = f"mssql+pyodbc://{usr}:{pwd}@{srvr}/{db}?driver={drvr}"
engine = create_engine(config)


##############################################################################
##                                                                          ##
##        Functions to fetch first and Last names of Unifin Accounts        ##
##                                                                          ##
##############################################################################


def FirstName(unifinID):

    unifinID = "'" + unifinID + "'"

    query = "SELECT IIF(CHARINDEX(',',REVERSE(ADR.ADR_NAME))>0, \
            RIGHT(ADR.ADR_NAME,CHARINDEX(',',REVERSE(ADR.ADR_NAME))-1), '') \
            as 'FIRST NAME' FROM CDS.DBR INNER JOIN UFN.[01.ADR] \
            ADR on ADR_DBR_NO = DBR_NO INNER JOIN CDS.CLT on \
            CLT_NO = DBR_CLIENT where dbr_no in (" + unifinID + ")"

    firstName = pd.read_sql(query, engine, dtype=str)

    return firstName.iloc[0, 0]


def LastName(unifinID):

    unifinID = "'" + unifinID + "'"

    query = "SELECT IIF(CHARINDEX(',',ADR.ADR_NAME)>0, \
             LEFT(ADR.ADR_NAME,CHARINDEX(',',ADR.ADR_NAME)-1), ADR.ADR_NAME) \
             as 'LAST NAME'FROM CDS.DBR INNER JOIN UFN.[01.ADR] \
             ADR on ADR_DBR_NO = DBR_NO INNER JOIN CDS.CLT \
             on CLT_NO = DBR_CLIENT where dbr_no in (" + unifinID + ")"

    lastName = pd.read_sql(query, engine, dtype=str)

    return lastName.iloc[0, 0]


##############################################################################
##                                                                          ##
##                     This function takes text of img                      ##
##                     and returns reference Number if                      ##
##                     text matches pattern else False                      ##
##                                                                          ##
##############################################################################


def Text(img, angle):

    if angle:

        img = RotateImage(img, angle)

    # extract text from images
        
    text = pytesseract.image_to_string(img)

    return text


def Reference(text):

    # raw string for patterns

    pattern1 = r'00\d{8}.{1,25}Quie|00\d{8}.{1,25}uier|00\d{8}.{1,30}iero'
    pattern2 = r'00\d{8}.{5,20}este|00\d{8}.{10,25}form|00\d{8}.{10,25}mular'
    pattern3 = r'encl.{1,80}00\d{8}|closed.{1,80}00\d{8}|refer.{5,15}num.{1,10}00\d{8}'
    refPattern = r"00\d{8}"

    # re.compile with DOTALL enables 
    # '.' to include next line too.

    regex1 = re.compile(pattern1, re.DOTALL)
    regex2 = re.compile(pattern2, re.DOTALL)
    regex3 = re.compile(pattern3, re.DOTALL)

    match1 = re.search(regex1, text)
    match2 = re.search(regex2, text)
    match3 = re.search(regex3, text)

    if match1 or match2 or match3:
        
        if match1:
    
            matchedText = match1.group(0)
    
        elif match2:
    
            matchedText = match2.group(0)

        elif match3:

            matchedText = match3.group(0)
            
        referenceMatch = re.search(refPattern, matchedText)
            
        referenceNo = referenceMatch.group(0)

        return referenceNo

    else:

        return False


##############################################################################
##                                                                          ##
##                     This function take img as input                      ##
##                     reads it in OSD mode and return                      ##
##                     an angle by which img should be                      ##
##                                 rotated.                                 ##
##                                                                          ##
##############################################################################


def RotationAngle(rawIMG):
    
    try:
        
        results = pytesseract.image_to_osd(rawIMG, output_type=Output.DICT)\
        
        return results['rotate']
    
    except TesseractError as e:
        
        return -1


##############################################################################
##                                                                          ##
##                  This function take image and rotation                   ##
##                    angle as input and returns rotated                    ##
##                              image as output.                            ##
##                                                                          ##
##############################################################################


def RotateImage(rawIMG, rotation):
    
    rotated = imutils.rotate_bound(rawIMG, angle=rotation)
    
    return rotated


def RefiningImage(img):

    # refines image

    enhanced_image = exposure.adjust_gamma(img, gamma=0.5)
    
    return enhanced_image


##############################################################################
##                                                                          ##
##                  This function takes text in image and                   ##
##                  matches it with first & Last name from                  ##
##                   from SQL & returns a similarity score                  ##
##                                                                          ##
##############################################################################


def NameMatching(text, name):

    word_list = text.split()
    
    # Calculate similarity scores for each word
    
    similarity_scores = [(word, fuzz.token_set_ratio(name, word)) for word in word_list]

    # Sort the words by similarity score (highest to lowest)
    
    sorted_words = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

    # Get the most similar word
    
    most_similar_word = sorted_words[0][0]
    similarity_score = sorted_words[0][1]

    return most_similar_word, similarity_score


##############################################################################
##                                                                          ##
##                    This function takes List of images                    ##
##                    of each pdf and saves image if ref                    ##
##                    number found and returns true. Ref                    ##
##                    number image not found then return                    ##
##                                  False.                                  ##
##                                                                          ##
##############################################################################


def ImageSelection(imgList):
    
    # Default value of found set to False

    found = False

    # List of angles on which image will be OCR'ed

    angles = [0, 90, 180, 270]

    for img in imgList:

        img = RefiningImage(img)

        for angle in angles:

            text = Text(img, angle)

            reference = Reference(text)

            if reference:

                firstName = FirstName(reference)
                lastName = LastName(reference)

                firstFound, firstScore = NameMatching(text, firstName)
                lastFound, lastScore = NameMatching(text, lastName)

                if ((firstScore + lastScore) / 2) >= 80.00:

                    found = True
                    break

        if found: break
    
    return found, reference


def PDFtoImg(path1, path2, path3):

    # Creates Scanned and unscanned folder

    if not os.path.exists(path2): os.makedirs(path2)
    if not os.path.exists(path3): os.makedirs(path3)
    
    # Total PDF count

    PDFcount1 = 0

    # Identified PDF count

    PDFcount2 = 0

    # List for Unifin IDs

    unifinIDs = []
    
    os.chdir(path1)
    
    pattern = path1 + '*.pdf'

    pdfNames = glob.glob(pattern)
    
    for file in pdfNames:

        PDFcount1 += 1

        # Gets a list of PIL images of each pdf page
        
        images = convert_from_path(file)

        # Converts each PIL Image to np.array first
        # Convert np.array to cv2 n-dimension array
        # Also Converts RGB to Gray Scale.
        # Adds each image to images List.

        imgList = []
        
        for img in images:

            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

            imgList.append(gray)
        
        found, reference = ImageSelection(imgList)

        if found:

            unifinIDs.append(reference)

            PDFcount2 += 1

            name = reference + '.pdf'

            newPath = os.path.join(path2, name)

            shutil.move(file, newPath)
        
        else:

            newPath = os.path.join(path3, file.split('\\')[-1])

            shutil.move(file, newPath)

    # return PDFcount1, PDFcount2

    return PDFcount1, PDFcount2, unifinIDs


##############################################################################
##############################################################################
##############################################################################
####                                                                      ####
####                              Processing                              ####
####                                                                      ####
##############################################################################
##############################################################################
##############################################################################


total, identified, accIDs = PDFtoImg(pathPDF, scannedPDF, notscanPDF)

filePath = f'{currPath}\\DisputeAccounts.txt'

data = '\n' + '\n'.join(accIDs)

with open(filePath, 'a') as file:

    file.write(data)

    