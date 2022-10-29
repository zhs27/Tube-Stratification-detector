import sys
import cv2,imutils
import numpy as np

# Crop image to fitted size.
# Return a cropped original image, a cropped canny image, and lowest pt of the tube
def crop(imgg):
    imgg = cv2.GaussianBlur(imgg, (3, 3), 0)
    imgg = cv2.GaussianBlur(imgg, (3, 3), 0)
    canny = cv2.Canny(imgg, 100, 150)

    # find contours
    cnts = cv2.findContours(canny.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=len)

    # traverse to get longest contour and lowestpt
    length = 0
    lowestpt = 0

    midx = 0
    for counts in range(0, len(cnts)):
        if length < cv2.arcLength(cnts[counts], 1):
            length = cv2.arcLength(cnts[counts], 1)
            k = cnts[counts]
        for j in cnts[counts]:
            if j[0][1] > lowestpt:
                lowestpt = j[0][1]
                midx = j[0][0]
                lowestptcoordinate = j[0]

    minx = 10000
    maxy = lowestpt

    # min x coordinate
    for i in k:
        minx = min([minx, i[0][0]])

    # max x coordinate
    radius = midx - minx
    maxx = minx + 2 * radius

    # crop
    cropped1 = canny[0:maxy, minx:maxx]
    cropped2 = imgg[0:maxy, minx:maxx]
    return (cropped1,cropped2,lowestptcoordinate)

# getting slope with 2 points
def slope(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    if x2 - x1 > 0:
        return ((y2 - y1) / (x2 - x1))
    else:
        return 'NA'

# length between two points
def length(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return (((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)


# Choose stratification line in detected lines.
def chooseLines(lines, img1):

    # Height and width of the image
    height = (img1.shape)[0]
    width = (img1.shape)[1]
    # print("height", height)

    # Return array which records each group of edges
    output = np.array([0,0,0,0])

    # Traverse through all lines and get lines that satisfy requirement
    for x1, y1, x2, y2 in lines[:, 0]:


        # detect horizontal lines with enough length
        if abs(y1 - y2) < 3 and length((x1,y1), (x2,y2)) > 20 and height - y1 > 5:
            left = 0
            right = 0

            # If:
            # 1. current vertical lines are close enough to both sides of the image, it is the edge
            # 2. current horizontal line is between two edges
            # 3. the horizontal line is far from any one of two edges.
            # then current group of line is interfering light
            for x3, y3, x4, y4 in lines[:, 0]:

                # get the slope of the edge and find current x coordinate
                k = slope((x3,y3), (x4,y4))
                if(k == 'NA'):
                    x5 = x4
                elif (k == 0):
                    continue
                else:
                    b = y3 - k * x3
                    x5 = (y1 - b) / k

                # Mark the horizontal line if it's too far from the vertical edge
                if y3 < y1 and y4 > y1 and (x3 < 10 or x4 < 10) and abs(x1 - x5) > 5:
                    left = 1
                    #print("left error",x1 - x3, " ", x3)
                    #cv2.line(img, (x3, y3), (x4, y4), (150, 100, 300), 2)
                    #return img
                    #cv2.circle(img, (x3, y3), 4, (183, 15, 245), -1)
                if y3 < y1 and y4 > y1 and  (width - x3 < 10 or width - x4 < 10) and (x5 - x1) > 5:
                    right = 1
                    #print("right error", x3 - x1, x3)

            # If the horizontal line is marked as interfering light, do not output it
            if left > 0 or right > 0 or height - y1 < 10 or height - y2 < 10:
                continue

            # merge the array
            output = np.row_stack((output, np.array([x1, y1, x2, y2])))
            # cv2.line(img1, (x1, y1), (x2, y2), (150, 100, 300), 2)
            # print(x1, " ", y1, " ", x2, " ", y2)

    return output


# merge lines close enough
def merge(lines):
    lines = sorted(lines, key = lambda x: x[1])
    i = 0
    while i < len(lines) - 1:
        if abs(lines[i][1] - lines[i + 1][1]) < 5 and abs(lines[i][3] - lines[i + 1][3]) < 5:
            lines[i][0] = min([lines[i][0], lines[i + 1][0]])
            lines[i][2] = max([lines[i][2], lines[i + 1][2]])
            lines = np.delete(lines, i + 1, axis = 0)
            continue
        i = i + 1

    return lines




def detect():
    path = sys.argv[1]
    save_path = sys.argv[2]
    im0 = cv2.imread(path)
    height = (im0.shape)[0]
    width = (im0.shape)[1]


    # crop the img
    cropped = crop(im0)

    # detect lines
    lines = cv2.HoughLinesP(cropped[0], 1, np.pi / 360, 10, minLineLength=20, maxLineGap=20)

    # choose horizontal lines
    outputlines = chooseLines(lines, cropped[0])
    outputlines = np.delete(outputlines, 0, axis=0)
    # merge close lines
    outputlines = merge(outputlines)

    print(outputlines)

    # Draw lines in the picture and output the result
    highestptcoordinate = [0, width // 2]
    length = (outputlines[0][1] + outputlines[0][1]) // 2
    print(length)

    for i in range(0, len(outputlines) - 1):

        length = abs((outputlines[i][1] + outputlines[i][3] - outputlines[i - 1][1] - outputlines[i - 1][3])) // 2
        #outputx = (min(outputlines[i][1], outputlines[i - 1][1]) + max(outputlines[i][3], outputlines[i - 1][3])) //2
        #outputy = (outputlines[i][1] + outputlines[i][3]) // 2 + length
        cv2.line(cropped[1], (outputlines[i][0], outputlines[i][1]), (outputlines[i][2], outputlines[i][3]), (150, 100, 300), 2, cv2.LINE_AA)
        outputtext = str(length)
        if i == 0:
            continue
        print(outputtext)
        #cv2.putText(cropped[1], outputtext, (outputx - 5, outputy - 3), cv2.FONT_HERSHEY_COMPLEX, 0.5, (150, 100, 300), 1)

    lowestptcoordinate = cropped[2]
    length = lowestptcoordinate[1] - (outputlines[len(outputlines) - 1][1] + outputlines[len(outputlines) - 1][1]) // 2
    #outputx = lowestptcoordinate[0]
    #outputy = lowestptcoordinate[1] - length // 2
    #cv2.putText(cropped[1], outputtext, (outputx - 5, outputy - 3), cv2.FONT_HERSHEY_COMPLEX, 0.5, (150, 100, 300), 1)
    print(length)


    outputimg = cropped[1]
    cv2.imwrite(save_path, outputimg)


if __name__ == '__main__':
    detect()
