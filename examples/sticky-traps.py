####################################################################
# The python code for analysing sticky traps (on command line).    #
# This code is created for Naturalis Biodiversity Center, Leiden.  #
# Latest update 1-7-18.                                            #
####################################################################


# Importing useful packages.
import logging
import mimetypes
import os
import common
import cv2
import numpy as np
import yaml
import imgpheno


# List to hold the images.
image_list = []


# Start of program, it creates parser to obtain the path to images to analyse. Uses the settings in the YAML file to
# create a result file and write the headers, in normal size classes or detailed size classes, or to not create a
# result file at all. It adds the images to a global list.
def main():
    path = "images"

	# write header
    if yml.detailed_size_classes is True:
        print("File \t Total number of insects \t Average area \t Between 0 and 1mm \t Between 1 and 4mm \t Between 4 and 7mm \t Between 7 and 12mm \t Larger than 12mm \n")
    else:
        print("File \t Total number of insects \t Average area \t Smaller than 4mm \t Between 4 and 10mm \t Larger than 10mm \n")

	# scan path for images
    image_files = get_image_paths(path)
    for img in image_files:
        contours, trap, message = find_insects(img)
        run_analysis(contours, img, message)

# Returns a list of all images present in the directory 'path'. Returns an error message when no images are found.
def get_image_paths(path):
    if not os.path.exists(path):
        logging.error("Cannot open %s (No such file or directory)", path)
        return 1

    images = []

    for item in os.listdir(path):
        imgpath = os.path.join(path, item)
        if os.path.isfile(imgpath):
            mime = mimetypes.guess_type(imgpath)[0]
            if mime and mime.startswith('image'):
                images.append(imgpath)

    if len(images) == 0:
        logging.error("No images found in %s", path)
        return 1
    return images


# Calls in different functions to analyse the image. It transforms the perspective of the image and draws the contours
# of the insects on the image. When analysis of an image is not possible it will return a string with an error message
# as a result for that particular image.
def find_insects(img_file):
    img = read_img(img_file)
    # Converts to HSV colourspace for trap roi selection.
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Calls the function that detects the trap based on the HSV image.
    mask = hsv_threshold(hsv)
    # Finds the four corners based on an approximation of the contour of the mask.
    corners = imgpheno.find_corners(mask)
    width = 4 * yml.trap_dimensions.Trap_width
    height = 4 * yml.trap_dimensions.Trap_height
    try:
        points_new = np.array([[0, 0], [width, 0], [0, height], [width, height]], np.float32)
        # Resizes the image.
        trap = imgpheno.perspective_transform(img, corners, points_new)
    except:
        message = "Analyis not possible of file " + img_file.replace("images/", "") + "\n"
        trap = None
    # This code returns None for the contours, in case not exactly 4 were returned.
    if trap is None:
        contours = None
        trap = None
        message = "Analysis not possible of file " + img_file.replace("images/", "") + "\n"
    # Now the program finds the insects present on the trap.
    else:
        if yml.edges_to_crop:
            trap = crop_image(trap)
        # Selects the channel with the highest contrast.
        r_channel = trap[:, :, 2]
        contours = find_contours(r_channel)

        contour_img = trap.copy()
        cv2.drawContours(contour_img, contours, -1, [0, 0, 255], -1)
        image_list.append(contour_img)
        message = ""

    return contours, trap, message


# Reads the images into an array generated by opencv2, the image is also resized if it is to large.
def read_img(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    perim = sum(img.shape[:2])
    if perim > 1000:
        ref = float(1000) / perim
        img = cv2.resize(img, None, fx=ref, fy=ref)
    return img


# Uses the colour of the trap to detect the outer contour of the trap.
def hsv_threshold(img):
    # Knowing which HSV colour code to use can be calculated below by giving a BGR colour code, this will return a
    # HSV colour code. Specified below is the colour blue. To specify the lower and upper HSV colour codes use lower =
    # [-10, 100, 100] and upper = [+10, 255, 255] respectively.
    #
    # colour = np.uint8([[[255, 0, 0]]])
    # hsv_colour= cv2.cvtColor(colour, cv2.COLOR_BGR2HSV)
    # print(hsv_colour)
    # This will give [120, 255, 255]

    lower = np.array(yml.trap_colours.trap_lower)
    upper = np.array(yml.trap_colours.trap_upper)
    mask = cv2.inRange(img, lower, upper)
    return mask


# Returns all contours found in an image using findContours using adaptive thresholding and a tree retrieval mode.
def find_contours(image):
    thresh = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 22)
    # Finds the contours in the mask of the thresholded image.
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return contours


# Crops the image if set in the YAML file.
def crop_image(img):
    short_edge = yml.cropping_width.along_short_edges * 4
    long_edge = yml.cropping_width.along_long_edges * 4
    width, height = img.shape[0:2]
    roi = img[short_edge: width - short_edge, long_edge: height - long_edge]
    return roi


# Uses the detected contours of the insects to determine the size and count the number of insects found for each size
# class. Writes the results in a result file, for normal size classes or detailed size classes, if set in the YAML file.
def run_analysis(contours, filename, message):
    filename = filename.replace("images\\", "").replace("images/", "")
    if message != "":
        results = message
        print(str(results))
    else:
        properties = imgpheno.contour_properties(contours, ('Area', 'MajorAxisLength',))
        if properties is None:
            pass
        else:
            properties = imgpheno.contour_properties(contours, ('Area', 'MajorAxisLength',))
            major_axes = [i['MajorAxisLength'] for i in properties]

            if yml.detailed_size_classes is True:
                b_0_1 = [i for i in major_axes if i < 4]
                b_1_4 = [i for i in major_axes if 4 <= i < 15]
                b_4_7 = [i for i in major_axes if 15 <= i < 26]
                b_7_12 = [i for i in major_axes if 26 <= i < 45]
                larger_12 = [i for i in major_axes if i >= 45]

                areas = [i['Area'] for i in properties]
                average_area = np.mean(areas)
                number_of_insects = (len(b_0_1) + len(b_1_4) + len(b_4_7) + len(b_7_12) + len(larger_12))

                results = """%s \t %s \t %f \t %s \t %s \t %s \t %s \t %s
            """ % (filename, number_of_insects, (average_area / 4), len(b_0_1),
                   len(b_1_4), len(b_4_7), len(b_7_12), len(larger_12))

                print(str(results.replace("    ", "")))

            else:
                smaller_than_4 = [i for i in major_axes if 4 <= i < 15]
                between_4_and_10 = [i for i in major_axes if 15 <= i < 38]
                larger_than_10 = [i for i in major_axes if 38 <= i < 45]

                areas = [i['Area'] for i in properties]
                average_area = np.mean(areas)
                number_of_insects = (len(smaller_than_4) + len(between_4_and_10) + len(larger_than_10))

                results = """%s \t %s \t %d \t %s \t %s \t %s
            """ % (filename, number_of_insects, (average_area / 4),
                   len(smaller_than_4),
                   len(between_4_and_10), len(larger_than_10))

                print(str(results.replace("    ", "")))


# Opens the YAML file to create a DictObject of the settings that were set in the YAML file. Returns an error message if
# the YAML file cannot be found.
def open_yaml(path):
    if not os.path.isfile(path):
        logging.error("Cannot open %s (no such file)" % path)
        return None

    f = open(path, 'r')
    yml = yaml.load(f)
    yml = common.DictObject(yml)
    f.close()

    return yml


# Variable creation for the YAML file.
yml = open_yaml(r'./sticky-traps.yml')


if __name__ == "__main__":
    main()
