"""
DeepLabStream
© J.Schweihoff, M. Loshakov
University Bonn Medical Faculty, Germany
https://github.com/SchwarzNeuroconLab/DeepLabStream
Licensed under GNU General Public License v3.0
"""

import cv2
import numpy as np
import math

def plot_dots(image, coordinates, color, cond=False):
    """
    Takes the image and positional arguments from pose to plot corresponding dot
    Returns the resulting image
    """
    cv2.circle(image, coordinates, 3, color, -1)
    if cond:
        cv2.circle(image, (10, 10), 10, (0, 255, 0), -1)
    return image

def plot_angle(image,pointa,pointb,pointc,event):
    """
    Takes the image and coordinates from 3 points to draw the angle between them.
    Note: convert to int because opencv sucks
    """
    pta = ( int(pointa[0]), int(pointa[1]) )
    ptb = ( int(pointb[0]), int(pointb[1]) )
    ptc = ( int(pointc[0]), int(pointc[1]) )
    
    
    if event:
        color = (0,0,255)
    else:
        color = (255,0,0)
    
    cv2.line(image,pta,ptb,color,thickness=2)
    cv2.line(image,ptb,ptc,color,thickness=2)
    return image
    

def plot_absolute_angle(image,pointa,pointb,stim_angle,event):
    """
    Takes the image and
    Note: convert to int because opencv sucks
    """
    pta = ( int(pointa[0]), int(pointa[1]) )
    ptb = ( int(pointb[0]), int(pointb[1]) )
    ptc = (int(ptb[0] + np.cos(stim_angle*np.pi/180)*80) , int(ptb[1] - np.sin(stim_angle*np.pi/180)*80))
    
    if event:
        color = (255,0,0)
    else:
        color = (0,0,255)
        
    #Draw neck->nose vector
    cv2.line(image,pta,ptb,color,thickness=2)
    
    #Draw target angle reference vector
    cv2.line(image,ptb,ptc,(0,0,0),thickness=2)
    
    return image    

def plot_angle_value(image,angle_value,plot_position,event):
    """
    Takes the image and plots the angle value next to the mouse. The color
    changes, depending on if condition is met.
    """
    #Convert to int for opencv2 to not freak out
    position = ( int(plot_position[0]), int(plot_position[1]) )
    
    
    # NOTE : opencv colors is BGR not RGB!!!
    if event:
        color = (0,0,255)
    else:
        color = (0,0,0)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1
    thickness = 2
    
    image = cv2.putText(image, "%.1fdg" %angle_value, position, font, 
                   fontScale, color, thickness)
    
    return image


def plot_distance_traveled(image,distance,position,event):
    """
    Takes the image and plots the angle value next to the mouse. The color
    changes, depending on if condition is met.
    """
    # make sure integer for opencv2!
    
    
    # NOTE : opencv colors is BGR not RGB!!!# NOTE : opencv colors is BGR not RGB!!!
    if event: # plot in red when under threshold
        color = (0,0,255)
    else: # plot in blue when over threshold
        color = (0,0,0)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1
    thickness = 2
    
    image = cv2.putText(image, "%3.0f" %distance, position, font, 
                   fontScale, color, thickness)
    
    return image


def plot_bodyparts(image, skeletons):
    
    
    """
    Takes the image and skeletons list to plot them
    :return: resulting image
    """
    res_image = image.copy()
    # predefined colors list
    colors_list = [
        (0, 0, 255),
        (0, 255, 0),
        (0, 255, 255),
        (255, 0, 0),
        (255, 0, 255),
        (255, 255, 0),
        (255, 255, 128),
        (0, 0, 128),
        (0, 128, 0),
        (0, 128, 128),
        (0, 128, 255),
        (0, 255, 128),
        (128, 0, 0),
        (128, 0, 128),
        (128, 0, 255),
        (128, 128, 0),
        (128, 128, 128),
        (128, 128, 255),
        (128, 255, 0),
        (128, 255, 128),
        (128, 255, 255),
        (255, 0, 128),
        (255, 128, 0),
        (255, 128, 128),
        (255, 128, 255),
    ]
    # color = (255, 0, 0)

    for num, animal in enumerate(skeletons):
        bodyparts = animal.keys()
        bp_count = len(bodyparts)
        # colors = dict(zip(bodyparts, colors_list[:bp_count]))
        for part in animal:
            # check for NaNs and skip
            if not any(np.isnan(animal[part])):
                plot_dots(res_image, tuple(map(int, animal[part])), colors_list[num])
                # plot_dots(res_image, tuple(animal[part]), colors[part])
            else:
                pass
    return res_image


def plot_metadata_frame(
    image, frame_width, frame_height, current_fps, current_elapsed_time
):
    """
    Takes the image and plots metadata
    :return: resulting image
    """
    res_image = image.copy()
    font = cv2.FONT_HERSHEY_PLAIN

    cv2.putText(
        res_image,
        "Time: " + str(round(current_elapsed_time, 2)),
        (int(frame_width * 0.8), int(frame_height * 0.9)),
        font,
        1,
        (255, 255, 0),
    )
    cv2.putText(
        res_image,
        "FPS: " + str(round(current_fps, 1)),
        (int(frame_width * 0.8), int(frame_height * 0.94)),
        font,
        1,
        (255, 255, 0),
    )
    return res_image


def plot_dlc_bodyparts(image, bodyparts):
    """
    Plots dlc bodyparts on given image
    adapted from plotter
    """

    for bp in bodyparts:
        center = tuple(bp.astype(int))
        cv2.circle(image, center=center, radius=3, color=(255, 0, 0), thickness=2)
    return image


def plot_triggers_response(image, response):
    """
    Plots trigger response on given image
    """
    if "plot" in response:
        plot = response["plot"]
        if "line" in plot:
            #make sure they are int for openCV. No half pixels there...

            plot['line']["pt1"] = tuple([int(i) for i in plot['line']["pt1"]])
            plot['line']["pt2"] = tuple([int(i) for i in plot['line']["pt2"]])
            cv2.line(image, **plot["line"], thickness=4)
        if "text" in plot:
            #make sure they are int for openCV. No half pixels there...
            plot['text']["org"] = tuple([int(i) for i in plot['text']["org"]])
            font = cv2.FONT_HERSHEY_PLAIN
            cv2.putText(image, **plot["text"], fontFace=font, fontScale=1)
        if "circle" in plot:
            #make sure they are int for openCV. No half pixels there...
            plot['circle']["center"] = tuple([int(i) for i in plot['circle']["center"]])
            plot['circle']["radius"] = int(plot['circle']["radius"])

            cv2.circle(image, **plot["circle"], thickness=2)
        if "square" in plot:
            #make sure they are int for openCV. No half pixels there...
            plot['square']["pt1"] = tuple([int(i) for i in plot['square']["pt1"]])
            plot['square']["pt2"] = tuple([int(i) for i in plot['square']["pt2"]])

            cv2.rectangle(image, **plot["square"], thickness=2)
