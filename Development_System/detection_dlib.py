import utils.logging_data as LOG
import cv2
from imutils import face_utils
import dlib
from keras.models import load_model
from scipy.spatial import distance as dist
import imutils
import os
import sys
import threading
import numpy as np
import re
import time
import datetime

'''
Dlib detection
This file contains a dlib detection implementation
Make sure 68 face landmark model is reachable!
'''

#Detection
# Class that handle detection in own thread
class Detection(threading.Thread):
    pnet = None
    rnet = None
    onet = None
    landmarks_model_path = '../../model/shape_predictor_68_face_landmarks.dat'
    face_detector = None
    landmarks_predictor = None

    #face_cascade_path = 'model/haarcascade_frontalface_alt.xml'

    # Flipp testing camera
    flipp_test_nr = 1
    flipp_test_degree = 90
    do_flipp_test = False
    flipp_test_long_intervall = 6

    # Calculate time
    start_time = None
    end_time = None


    # Thread sleep times
    sleep_time = 0.1
    LONG_SLEEP = 2
    SHORT_SLEEP = 0.5

    # Number of detection fails to start energy save
    no_face_count = 0
    NO_FACE_MAX = 4
    Loaded_model = False
    index = 0

    # Initiate thread
    # parameters name, and shared_variables reference
    def __init__(self, name=None,  shared_variables = None):
        threading.Thread.__init__(self)
        self.name = name
        self.shared_variables = shared_variables
        self.sleep_time = self.SHORT_SLEEP
        self.index = int(name)
        LOG.info("Create dlib detection" + str(self.index), "SYSTEM-"+self.shared_variables.name)

    # Convert_dlib_box_to_OpenCV_box(box)
    # @param takes in a dlib box
    # @return returns a box for OpenCV
    def convert_dlib_box_to_openCV_box(self, box):
        return (int(box.left()), int(box.top()), int(box.right() - box.left()),
                         int(box.bottom() - box.top()) )

    # Object_detection
    # @ returns True if detections successful
    # @ returns False if no face found
    #
    # This function uses dlib to make a face detection.
    # Then transform the result to OpenCV
    #
    def object_detection(self, frame):

        #image = imutils.resize(image, width=500)
       # gray = cv2.cvtColor(self.shared_variables.frame, cv2.COLOR_BGR2GRAY)

        # detect faces in the grayscale image
        box_arr = self.face_detector(frame, 1)


        # No face
        if(not len(box_arr) ):
            face_found = False
            return face_found, None, None, None

        # determine the facial landmarks for the face region
        shape = self.landmarks_predictor(frame, box_arr[0])
        landmarks = face_utils.shape_to_np(shape)

        # convert box
        face_box = self.convert_dlib_box_to_openCV_box(box_arr[0])
        face_found = True

        # Fix score later!
        score = 100
        #success, face_box, landmarks, score
        return face_found, face_box, landmarks, score


    #Run
    #Detection function
    def run(self):
        if not self.Loaded_model:
            LOG.info("Loading Dlib model" + str(self.index),"SYSTEM-"+self.shared_variables.name)

                # Load model
            self.face_detector = dlib.get_frontal_face_detector()
            self.landmarks_predictor = dlib.shape_predictor(self.landmarks_model_path)

                #face_cascade = cv2.CascadeClassifier(face_cascade_path)
            self.Loaded_model = True

        LOG.info("Start dlib detections" + str(self.index),"SYSTEM-"+self.shared_variables.name)

        #wait for first cam frame
        while self.shared_variables.frame[self.index] is None:
            pass

            # Start Loop
        while self.shared_variables.system_running:
            self.start_time = datetime.datetime.now()

            frame = self.shared_variables.frame[self.index]

            if self.do_flipp_test:
                frame = imutils.rotate(frame, self.flipp_test_degree*self.flipp_test_nr)

                # Do detection
            success, face_box, landmarks, score = self.object_detection(frame)

                # if found faces
            if success:


                self.shared_variables.detection_score[self.index] = score

                self.no_face_count = 0

                    # Save landmark
                #self.shared_variables.landmarks[self.index] = landmarks
                self.shared_variables.set_landmarks(landmarks, self.index)

                    # Save boxes
                self.shared_variables.face_box[self.index] = [face_box]
                self.shared_variables.set_detection_box([face_box], self.index)

                self.shared_variables.face_found[self.index] = True
                    # Do flipp test on detection
                if self.shared_variables.flipp_test[self.index] and self.do_flipp_test:
                            # save flipp as success
                        degree = self.shared_variables.flipp_test_degree[self.index] + self.flipp_test_nr*self.flipp_test_degree

                        degree = degree - (degree % 360)*360

                        self.shared_variables.flipp_test_degree[self.index] = degree

                            # log frame change
                        LOG.info("Flipp test successful add degree :" + str(self.flipp_test_nr*self.flipp_test_degree),self.shared_variables.name)

                            # end flipp test
                        self.do_flipp_test = False
                        self.flipp_test_nr = 1

                    # Wake tracking thread

                #if not self.shared_variables.tracking_running[self.index]:
                #    self.sleep_time = self.SHORT_SLEEP

            else:
                    # No face
                self.shared_variables.face_found[self.index] = False

                    # if max face misses has been done, do less detections
                if self.no_face_count >= self.NO_FACE_MAX:

                        # do flipp test
                    if self.shared_variables.flipp_test[self.index]:

                            # doing flipp test
                        if self.do_flipp_test:
                            self.flipp_test_nr = self.flipp_test_nr + 1

                                # flipp test did not find anything
                            if self.flipp_test_nr*self.flipp_test_degree >= 360:
                                self.do_flipp_test = False
                                self.flipp_test_nr = 1

                                if self.sleep_time == self.SHORT_SLEEP:
                                    #LOG.log("Initiate energy save",self.shared_variables.name)
                                    #self.sleep_time = self.LONG_SLEEP
                                    pass
                        else:
                            self.do_flipp_test = True

                    else:
                        #self.sleep_time = self.LONG_SLEEP
                        #self.shared_variables.tracking_running[self.index] = False
                        #LOG.log("Initiate energy save",self.shared_variables.name)
                        pass

                else:
                    self.no_face_count = self.no_face_count + 1

                if self.no_face_count >= self.flipp_test_long_intervall and self.shared_variables.flipp_test[self.index]:
                    self.no_face_count = 0

            self.end_time = datetime.datetime.now()

                # Debug detection time
            if  self.shared_variables.debug:
                LOG.debug('Dlib Detection time:' + str(self.end_time - self.start_time),self.shared_variables.name)

            time.sleep(self.sleep_time) # sleep if wanted

        LOG.info("Ending dlib detection " + str(self.index), "SYSTEM-"+self.shared_variables.name )
