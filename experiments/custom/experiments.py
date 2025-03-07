"""
DeepLabStream
© J.Schweihoff, M. Loshakov
University Bonn Medical Faculty, Germany
https://github.com/SchwarzNeuroconLab/DeepLabStream
Licensed under GNU General Public License v3.0
"""
import numpy as np
import random
import time
from functools import partial
from collections import Counter
from experiments.custom.stimulus_process import (
    ClassicProtocolProcess,
    SimpleProtocolProcess,
    Timer,
    ExampleProtocolProcess,
)
from experiments.custom.triggers import (
    ScreenTrigger,
    RegionTrigger,
    OutsideTrigger,
    DirectionTrigger,
    SpeedTrigger,
    SimbaThresholdBehaviorPoolTrigger,
    BsoidClassBehaviorPoolTrigger,
    SocialInteractionTrigger,
)

from utils.plotter import plot_triggers_response,plot_dots,plot_angle,plot_angle_value,plot_absolute_angle, plot_bodyparts, plot_distance_traveled
from utils.analysis import angle_between_vectors, absolute_angle, calculate_distance
from experiments.custom.stimulation import show_visual_stim_img, laser_switch, serial_laser_switch
from experiments.custom.classifier import FeatBsoidProcessPool, FeatSimbaProcessPool


import copy
import serial
from utils.configloader import THRESHOLD, POOL_SIZE, TRIGGER



""" experimental classification experiment using Simba trained classifiers in a pool which are converted using the pure-predict package"""

class SimbaBehaviorPoolExperiment:
    """
    Test experiment for Simba classification
    Simple class to contain all of the experiment properties and includes classification
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependant
    """

    def __init__(self):
        """Classifier process and initiation of behavior trigger"""
        self.experiment_finished = False
        self._process_experiment = ExampleProtocolProcess()
        # this process has feature extraction and classification in one process
        # simplifies everything if the feature extraction script is within the parallel process
        self._process_pool = FeatSimbaProcessPool(POOL_SIZE)
        # pass classifier to trigger, so that check_skeleton is the only function that passes skeleton
        # initiate in experiment, so that process can be started with start_experiment
        self._behaviortrigger = SimbaThresholdBehaviorPoolTrigger(
            prob_threshold=THRESHOLD, class_process_pool=self._process_pool, debug=False
        )
        self._event = None
        # is not fully utilized in this experiment but is useful to keep for further adaptation
        self._current_trial = None
        self._max_reps = 999
        self._trial_count = {trial: 0 for trial in self._trials}
        self._trial_timers = {trial: Timer(0) for trial in self._trials}
        self._exp_timer = Timer(9999)
    def check_skeleton(self, frame, skeleton):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeleton: skeleton, consisting of multiple joints of an animal
        """
        self.check_exp_timer()  # checking if experiment is still on
        for trial in self._trial_count:
            # checking if any trial hit a predefined cap
            if self._trial_count[trial] >= self._max_reps:
                self.stop_experiment()

        if not self.experiment_finished:
            for trial in self._trials:
                # check for all trials if condition is met
                # this passes the skeleton to the trigger, where the feature extraction is done and the extracted features
                # are passed to the classifier process
                result, response = self._trials[trial]["trigger"](
                    skeleton, target_prob=self._trials[trial]["target_prob"]
                )
                plot_triggers_response(frame, response)
                # if the trigger is reporting back that the behavior is found: do something
                # currently nothing is done, expect counting the occurances
                if result:
                    if self._current_trial is None:
                        if not self._trial_timers[trial].check_timer():
                            self._current_trial = trial
                            self._trial_timers[trial].reset()
                            self._trial_count[trial] += 1
                            print(trial, self._trial_count[trial])
                else:
                    if self._current_trial == trial:
                        self._current_trial = None
                        self._trial_timers[trial].start()

            self._process_experiment.set_trial(self._current_trial)

    @property
    def _trials(self):
        """
        Defining the trials
        """
        trials = {
            "DLStream_test": dict(
                trigger=self._behaviortrigger.check_skeleton, target_prob=None, count=0
            )
        }
        return trials

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        self._process_experiment.start()
        self._process_pool.start()
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        self._process_experiment.end()
        self._process_pool.end()
        print("Experiment completed!")
        self._exp_timer.reset()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = self._behaviortrigger.get_last_prob()
        return info


""" experimental classification experiment using BSOID trained classifiers in a pool"""


class BsoidBehaviorPoolExperiment:
    """
    Test experiment for BSOID classification
    Simple class to contain all of the experiment properties and includes classification
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependant
    """

    def __init__(self):
        """Classifier process and initiation of behavior trigger"""
        self.experiment_finished = False
        self._process_experiment = ExampleProtocolProcess()
        self._process_pool = FeatBsoidProcessPool(POOL_SIZE)
        # pass classifier to trigger, so that check_skeleton is the only function that passes skeleton
        # initiate in experiment, so that process can be started with start_experiment
        self._behaviortrigger = BsoidClassBehaviorPoolTrigger(
            target_class=TRIGGER, class_process_pool=self._process_pool, debug=False
        )
        self._event = None
        # is not fully utilized in this experiment but is usefull to keep for further adaptation
        self._current_trial = None
        self._trial_count = {trial: 0 for trial in self._trials}
        self._trial_timers = {trial: Timer(10) for trial in self._trials}
        self._exp_timer = Timer(600)

    def check_skeleton(self, frame, skeleton):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeleton: skeleton, consisting of multiple joints of an animal
        """
        self.check_exp_timer()  # checking if experiment is still on
        for trial in self._trial_count:
            # checking if any trial hit a predefined cap
            if self._trial_count[trial] >= 10:
                self.stop_experiment()

        if not self.experiment_finished:
            for trial in self._trials:
                # check for all trials if condition is met
                # this passes the skeleton to the trigger, where the feature extraction is done and the extracted features
                # are passed to the classifier process
                result, response = self._trials[trial]["trigger"](
                    skeleton, target_class=self._trials[trial]["target_class"]
                )
                plot_triggers_response(frame, response)
                # if the trigger is reporting back that the behavior is found: do something
                # currently nothing is done, expect counting the occurances
                if result:
                    if self._current_trial is None:
                        if not self._trial_timers[trial].check_timer():
                            self._current_trial = trial
                            self._trial_timers[trial].reset()
                            self._trial_count[trial] += 1
                            print(trial, self._trial_count[trial])
                else:
                    if self._current_trial == trial:
                        self._current_trial = None
                        self._trial_timers[trial].start()
            self._process_experiment.set_trial(self._current_trial)
        else:
            pass
        return result, response

    @property
    def _trials(self):
        """
        Defining the trials
        Target class is the cluster of interest and can be changed with every call of check_skeleton
        """
        trials = {
            "DLStream_test": dict(
                trigger=self._behaviortrigger.check_skeleton, target_class=None, count=0
            )
        }
        return trials

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        self._process_pool.start()
        self._process_experiment.start()
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        self._process_experiment.end()
        self._process_pool.end()
        print("Experiment completed!")
        self._exp_timer.reset()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = self._behaviortrigger.get_last_prob()
        return info


"""Social or multiple animal experiments in combination with SLEAP or non-flattened maDLC pose estimation"""


class ExampleSocialInteractionExperiment:
    """
    In this experiment the skeleton/instance of each animal will be considers for the trigger,
    any animal can trigger the stimulation (the first one to result in TRUE).

    Simple class to contain all of the experiment properties
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependent
    """

    def __init__(self):
        self.experiment_finished = False
        self._process = ExampleProtocolProcess()
        self._proximity_threshold = 30
        self._min_animals = 2
        self._event = None
        self._current_trial = None
        self._max_reps = 999
        self._trial_count = {trial: 0 for trial in self._trials}
        self._trial_timers = {trial: Timer(10) for trial in self._trials}
        self._exp_timer = Timer(600)

    def check_skeleton(self, frame, skeletons):
        """
        Checking passed animal skeletons for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeletons: skeletons, consisting of multiple joints of an animal
        """
        self.check_exp_timer()  # checking if experiment is still on
        for trial in self._trial_count:
            # checking if any trial hit a predefined cap
            if self._trial_count[trial] >= self._max_reps:
                self.stop_experiment()

        if not self.experiment_finished:
            result, response = False, None
            # checking if enough animals were detected
            if len(skeletons) >= self._min_animals:
                for trial in self._trials:
                    # check if social interaction trigger is true
                    result, response = self._trials[trial]["trigger"](
                        skeletons=skeletons
                    )
                    plot_triggers_response(frame, response)
                    if result:
                        if self._current_trial is None:
                            if not self._trial_timers[trial].check_timer():
                                self._current_trial = trial
                                self._trial_timers[trial].reset()
                                self._trial_count[trial] += 1
                                print(trial, self._trial_count[trial])
                    else:
                        if self._current_trial == trial:
                            self._current_trial = None
                            self._trial_timers[trial].start()

                self._process.set_trial(self._current_trial)
            else:
                pass
            return result, response

    @property
    def _trials(self):
        """
        Defining the trials
        """
        identification_dict = dict(
            active={"animal": 1, "bp": ["bp0"]}, passive={"animal": 0, "bp": ["bp2"]}
        )

        interaction_trigger = SocialInteractionTrigger(
            threshold=self._proximity_threshold,
            identification_dict=identification_dict,
            interaction_type="proximity",
            debug=True,
        )

        trials = {
            "DLStream_test": dict(trigger=interaction_trigger.check_skeleton, count=0)
        }
        return trials

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        self._process.start()
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        print("Experiment completed!")
        self._exp_timer.reset()
        # don't forget to end the process!
        self._process.end()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._current_trial


class ExampleMultipleAnimalExperiment:
    """
    In this experiment the skeleton/instance of each animal will be considers for the trigger,
    any animal can trigger the stimulation (the first one to result in TRUE).

    Simple class to contain all of the experiment properties
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependent
    """

    def __init__(self):
        self.experiment_finished = False
        self._process = ExampleProtocolProcess()
        self._green_point = (550, 163)
        self._radius = 40
        self._dist_threshold = 80
        self._event = None
        self._current_trial = None
        self._max_reps = 10
        self._trial_count = {trial: 0 for trial in self._trials}
        self._trial_timers = {trial: Timer(10) for trial in self._trials}
        self._exp_timer = Timer(600)

    def check_skeleton(self, frame, skeletons):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeletons: skeletons, consisting of multiple joints of an animal
        """
        self.check_exp_timer()  # checking if experiment is still on
        for trial in self._trial_count:
            # checking if any trial hit a predefined cap
            if self._trial_count[trial] >= self._max_reps:
                self.stop_experiment()

        if not self.experiment_finished:
            result, response = False, None
            for trial in self._trials:
                # check for all trials if condition is met
                result_list = []
                for skeleton in skeletons:
                    # checking each skeleton for trigger success
                    result, response = self._trials[trial]["trigger"](skeleton=skeleton)
                    # if one of the triggers is true, break the loop and continue (the first True)
                    if result:
                        break
                plot_triggers_response(frame, response)
                if result:
                    if self._current_trial is None:
                        if not self._trial_timers[trial].check_timer():
                            self._current_trial = trial
                            self._trial_timers[trial].reset()
                            self._trial_count[trial] += 1
                            print(trial, self._trial_count[trial])
                else:
                    if self._current_trial == trial:
                        self._current_trial = None
                        self._trial_timers[trial].start()

            self._process.set_trial(self._current_trial)
            return result, response

    @property
    def _trials(self):
        """
        Defining the trials
        """
        green_roi = RegionTrigger(
            "circle", self._green_point, self._radius * 2 + 7.5, "bp1"
        )
        trials = {"Greenbar_whiteback": dict(trigger=green_roi.check_skeleton, count=0)}
        return trials

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        self._process.start()
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        print("Experiment completed!")
        self._exp_timer.reset()
        # don't forget to end the process!
        self._process.end()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._current_trial


"""Single animal or flattened multi animal pose estimation experiments (e.g. different fur color) 
or by use of the FLATTEN_MA parameter in advanced settings"""


class ExampleExperiment:
    """
    Simple class to contain all of the experiment properties
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependent
    """

    def __init__(self):
        self.experiment_finished = False
        self._process = ExampleProtocolProcess()
        self._green_point = (550, 163)
        self._blue_point = (372, 163)
        self._radius = 40
        self._event = None
        self._current_trial = None
        self._trial_count = {trial: 0 for trial in self._trials}
        self._trial_timers = {trial: Timer(10) for trial in self._trials}
        self._exp_timer = Timer(600)

    def check_skeleton(self, frame, skeleton):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeleton: skeleton, consisting of multiple joints of an animal
        """
        
        
        print(skeleton)
        
        self.check_exp_timer()  # checking if experiment is still on
        for trial in self._trial_count:
            # checking if any trial hit a predefined cap
            if self._trial_count[trial] >= 10:
                self.stop_experiment()

        if not self.experiment_finished:
            result, response = False, None
            for trial in self._trials:
                # check for all trials if condition is met
                result, response = self._trials[trial]["trigger"](skeleton=skeleton)
                plot_triggers_response(frame, response)
                if result:
                    if self._current_trial is None:
                        if not self._trial_timers[trial].check_timer():
                            self._current_trial = trial
                            self._trial_timers[trial].reset()
                            self._trial_count[trial] += 1
                            print(trial, self._trial_count[trial])
                else:
                    if self._current_trial == trial:
                        self._current_trial = None
                        self._trial_timers[trial].start()

            self._process.set_trial(self._current_trial)
            return result, response

    @property
    def _trials(self):
        """
        Defining the trials
        """
        green_roi = RegionTrigger(
            "circle", self._green_point, self._radius * 2 + 7.5, "neck"
        )
        blue_roi = RegionTrigger(
            "circle", self._blue_point, self._radius * 2 + 7.5, "neck"
        )
        trials = {
            "Greenbar_whiteback": dict(trigger=green_roi.check_skeleton, count=0),
            "Bluebar_whiteback": dict(trigger=blue_roi.check_skeleton, count=0),
        }
        return trials

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        self._process.start()
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        print("Experiment completed!")
        self._exp_timer.reset()
        # don't forget to end the process!
        self._process.end()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._current_trial


"""The following is the original experiments we used for our experiments! If you are interested in using this, 
you will need to adapt the stimulation to your system! Otherwise I recommend looking at them for ideas how to incorporate
your own experiment into DLStream!"""

# local config

GREEN_POINT = (550, 63)
BLUE_POINT = (372, 63)

INTERTRIAL_TIME = 40
PENALTY_TIME = 5
POINT = (300,600)

"""For FLiCRE CA1 experiment: tag freezing or no freezing, but with a high tolerance (i.e moving vs no moving)."""

#local config

#   0 degrees   : horizontal left
#  90 degrees   : vertical up
# -90 degrees   : vertical down
#+-180 degrees  : horizontal right
# STIM_ANGLE = int(input('Stim angle (-180 to 180degrees):'))

# EXP_LENGTH = 40
# EXP_TIME = 3600
# EXP_COMPLETION = 10
# ARDUINO = serial.Serial('COM3',9600,timeout=1)



class TestExperiment:
    """
    Simple class to contain all of the experiment properties
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependent
    """

    def __init__(self):
        
        
        # basic stuff to get it to run
        self.experiment_finished = False
        self._exp_timer = Timer(30)
        self._event = None
        self._current_trial = None
        
        # max total stim time
        self._MAX_TOTAL_STIM_TIME = 10
        
        # min number of bodyparts "immobile" to start stim
        self._BP_THRESHOLD = 3
        
        # threshold distance to consider if bp is moving or not, in px.
        self._DISTANCE_THRESHOLD = 5
        
        # init total stim time up until now
        self._total_stim_time = 0
        
        # init current event start point
        self._event_start = 0
        
        # init last frame position of animal to 0s.
        self._last_frame_skeleton = {"nose" : (0,0), "left_ear" : (0,0), "right_ear" : (0,0), "neck" : (0,0), "left_side" : (0,0), "body_center" : (0,0), "right_side" : (0,0), "left_hip" : (0,0), "right_hip" : (0,0), "tail_base" : (0,0), "tail_tip" : (0,0)}
        
        # init distance list where we compute distance for each point between current frame and last frame.
        self._distance = np.array([])
        
        # init speed list where we compute speed for each point between current frame and last frame.
        self._speed = []

        
    def check_skeleton(self, frame, skeleton):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeleton: skeleton, consisting of multiple joints of an animal
        """
        
        # compute distance travelled for each tracked point.
        self._distance = np.array([calculate_distance(self._last_frame_skeleton["nose"],skeleton["nose"]), calculate_distance(self._last_frame_skeleton["left_ear"],skeleton["left_ear"]), calculate_distance(self._last_frame_skeleton["right_ear"],skeleton["right_ear"]), calculate_distance(self._last_frame_skeleton["neck"],skeleton["neck"]), calculate_distance(self._last_frame_skeleton["left_side"],skeleton["left_side"]), calculate_distance(self._last_frame_skeleton["body_center"],skeleton["body_center"]), calculate_distance(self._last_frame_skeleton["right_side"],skeleton["right_side"]), calculate_distance(self._last_frame_skeleton["left_hip"],skeleton["left_hip"]), calculate_distance(self._last_frame_skeleton["right_hip"],skeleton["right_hip"]), calculate_distance(self._last_frame_skeleton["tail_base"],skeleton["tail_base"]), calculate_distance(self._last_frame_skeleton["tail_tip"],skeleton["tail_tip"])])
        
        
        
        print(sum( self._distance <= self._DISTANCE_THRESHOLD ))
        
        
        # show each point's distance travelled on the image to make it clear.
        for n in range(len(self._distance)-1): # except for tail tip which is not tracked correctly.
            # make sure int for opencv2
            position = (int(50),int((n+1)*50))
            plot_distance_traveled(frame,self._distance[n],position, self._distance[n] <= self._DISTANCE_THRESHOLD)
        
        
        
        
        # check if total stim time reached
        if self._total_stim_time >= self._MAX_TOTAL_STIM_TIME:
            # if so, turn off laser and end experiment.
            print("Ending experiment, total event time ran out")
            """"ARDUINO : TURN OFF LASER"""
            print('Laser OFF')
            self.stop_experiment()
            
        # else, check if animal is moving or not.
        # How many body parts are under the moving threshold ? We made _distance a numpy array for this. So you know, enjoy
        elif sum( self._distance <= self._DISTANCE_THRESHOLD )>=self._BP_THRESHOLD:
            
            # if already in stim:
            if self._event == True:
                
                # don't do shit, exept if we are over self._MAX_TOTAL_STIM_TIME.
                if self._total_stim_time + ( time.time() - self._event_start ) >= self._MAX_TOTAL_STIM_TIME:
                    
                    # in that case, turn off laser and end experiment.
                    print("Ending experiment, total event time ran out")
                    """"ARDUINO : TURN OFF LASER"""
                    self.stop_experiment()
                    
            
            # else if not already in stim:
            elif self._event == False:
                
                 # set event to True.
                 self._event = True
                 
                 # record start of stim time so that when event end we can add to total stim.
                 self._event_start = time.time()
                 
                 # turn ON laser
                 """"ARDUINO : TURN ON LASER"""
                 print('Laser ON')
         
        # else (i.e the animal is considered moving):
        else:
            
            # if in stim, stop stim:
            if self._event == True:
                
                # stop event
                self._event = False
                
                # add event time to total stim time
                self._total_stim_time += time.time() - self._event_start
                
                # turn OFF laser
                """"ARDUINO : TURN OFF LASER"""
                print('Laser OFF')
            
         
        # prep next loop:
            
        # replace last frame skeleton for next loop
        self._last_frame_skeleton = copy.deepcopy(skeleton) 
        
        
        
        return self._event
    


    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        print("Experiment completed!")
        self._exp_timer.reset()

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._current_trial
    
    
    
    
    

class TagFreezingExperiment:
    
    """This experiment is designed to activate blue LASER for FLiCRE tagging of
    cells whenever the animal is not moving. We do this so that we tag all
    freezing cells, even freezing start (if we actually used freezing as a
    trigger it would start 0.5s after starting freezing, so we would miss
    them). 
    """
    
    def __init__(self):
        
        self.experiment_finished = False
        
        # init current time
        self._cur_time = 0
        
        # init last frame time
        self._last_frame_time = 0
        
        # self._ser = arduino
        # serial_laser_switch(self._ser,False)
        
        # init last frame position of animal to 0s.
        self._last_frame_skeleton = {"nose" : (0,0), "left_ear" : (0,0), "right_ear" : (0,0), "neck" : (0,0), "left_side" : (0,0), "body_center" : (0,0), "right_center" : (0,0), "left_hip" : (0,0), "right_hip" : (0,0), "tail_base" : (0,0), "tail_tip" : (0,0)}
        
        # init distance list where we compute distance for each point between current frame and last frame.
        self._distance = []
        
        # init speed list where we compute speed for each point between current frame and last frame.
        self._speed = []

    def check_skeleton(self, frame, skeleton):
        # Get angle between mouse head and object, and set the 0 
        xc,yc = skeleton["neck"][0] + np.cos(self._stim_angle*np.pi/180), skeleton["neck"][1] - np.sin(self._stim_angle*np.pi/180)
        _, angle_point = angle_between_vectors(xc,yc,*skeleton["neck"],*skeleton["nose"])
        """"Answer is angle from -180° to 180 ° compared to stim direction"""
        
        # Plot absolute angle.
        plot_absolute_angle(frame,skeleton["nose"],skeleton["neck"],self._stim_angle,self._event)
        

        #Show absolute angle value (0 to 180° compared to stim direction).
        plotting_position = (skeleton["nose"][0]+20 , skeleton["nose"][1]-20)
        plot_angle_value(frame,abs(angle_point),plotting_position,self._event)
        
        
        if self._experiment_timer.check_timer():
            if self._total_time >= self._max_total_time:
                # check if total time to stimulate per experiment is reached
                print("Ending experiment, total event time ran out")
                self.stop_experiment()
            else:
                # if not continue
                if not self._intertrial_timer.check_timer():
                    # check if there is an intertrial time running right now, if not continue
                    # check if the headdirection angle is within limits

                    if self._start_angle <= angle_point <= self._end_angle:
                        if not self._event:
                            # if a stimulation event wasn't started already, start one
                            print("Starting Stimulation")
                            self._event = True
                            # and activate the laser, start the timer and reset the intertrial timer
                            serial_laser_switch(self._ser,True)
                            self._event_start = time.time()
                            self._intertrial_timer.reset()
                        else:
                            if time.time() - self._event_start <= self._max_trial_time:
                                # if the total event time has not reached the maximum time per event
                                # self._trial_time = time.time() - self._event_start
                                pass
                            else:
                                # if the maximum event time was reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, Stimulation time ran out")
                                self._event = False
                                # laser_toggle(False)
                                serial_laser_switch(self._ser,False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
                    else:
                        # if the headdirection is not within the parameters
                        if self._event:
                            # but the stimulation is still going
                            if time.time() - self._event_start < self._min_trial_time:
                                # check if the minimum event time was not reached, then pass
                                pass
                            else:
                                # if minumum event time has been reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, angle not in range")
                                self._event = False
                                # laser_toggle(False)
                                serial_laser_switch(self._ser,False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
        else:
            # if maximum experiment time was reached, stop experiment
            print("Ending experiment, timer ran out")
            self.stop_experiment()

        return self._event

    def start_experiment(self):
        # not necessary as this experiment is not needing any multiprocessing
        self._experiment_timer.start()

    def stop_experiment(self):
        self.experiment_finished = True
        print("Experiment completed!")
        print("Total event duration", sum(self._results))
        print(self._results)

    def get_trial(self):
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = None
        return info



class SpeedExperiment:
    """
    Simple class to contain all of the experiment properties
    Uses multiprocess to ensure the best possible performance and
        to showcase that it is possible to work with any type of equipment, even timer-dependent
    """

    def __init__(self):
        self.experiment_finished = False
        self._threshold = 10
        self._event = None
        self._current_trial = None
        self._event_count = 0
        self._trigger = SpeedTrigger(
            threshold=self._threshold, bodypart="tailroot", timewindow_len=5
        )
        self._exp_timer = Timer(600)

    def check_skeleton(self, frame, skeleton):
        """
        Checking each passed animal skeleton for a pre-defined set of conditions
        Outputting the visual representation, if exist
        Advancing trials according to inherent logic of an experiment
        :param frame: frame, on which animal skeleton was found
        :param skeleton: skeleton, consisting of multiple joints of an animal
        """
        self.check_exp_timer()  # checking if experiment is still on

        if not self.experiment_finished:
            result, response = self._trigger.check_skeleton(skeleton=skeleton)
            plot_triggers_response(frame, response)
            if result:
                laser_switch(True)
                self._event_count += 1
                print(self._event_count)
                print("Light on")

            else:
                laser_switch(False)
                print("Light off")

            return result, response

    def check_exp_timer(self):
        """
        Checking the experiment timer
        """
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        """
        Start the experiment
        """
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        """
        Stop the experiment and reset the timer
        """
        self.experiment_finished = True
        print("Experiment completed!")
        self._exp_timer.reset()
        # don't forget to stop the laser for safety!
        laser_switch(False)

    def get_trial(self):
        """
        Check which trial is going on right now
        """
        return self._current_trial


class FirstExperiment:
    def __init__(self):
        self.experiment_finished = False
        self._point = POINT
        self._start_angle, self._end_angle = ANGLE_WINDOW
        self._intertrial_timer = Timer(15)
        self._experiment_timer = Timer(1800)
        self._event = False
        self._event_start = None
        self._results = []
        self._max_trial_time = 5
        self._min_trial_time = 1
        self._max_total_time = 600
        self._total_time = 0
        self._trial_time = 0
        self._test= 1
    def check_skeleton(self, frame, skeleton):
        
        # Get angle between mouse head and object
        _, angle_point = angle_between_vectors(
            *skeleton["nose"],*skeleton["neck"], *self._point
        )     
        print(angle_point)
        #Show object's XY coordinates
        plot_dots(frame,self._point,(255, 0, 0))
        
        #Show angle between mice head and object
        plot_angle(frame,skeleton["nose"], skeleton["neck"], self._point,(255, 0, 0))
        
        if self._experiment_timer.check_timer():
            if self._total_time >= self._max_total_time:
                # check if total time to stimulate per experiment is reached
                print("Ending experiment, total event time ran out")
                self.stop_experiment()
            else:
                # if not continue
                if not self._intertrial_timer.check_timer():
                    # check if there is an intertrial time running right now, if not continue
                    # check if the headdirection angle is within limits
                    if self._start_angle <= angle_point <= self._end_angle:
                        if not self._event:
                            # if a stimulation event wasn't started already, start one
                            print("Starting Stimulation")
                            self._event = True
                            # and activate the laser, start the timer and reset the intertrial timer
                            # laser_switch(True)
                            self._event_start = time.time()
                            self._intertrial_timer.reset()
                        else:
                            if time.time() - self._event_start <= self._max_trial_time:
                                # if the total event time has not reached the maximum time per event
                                # self._trial_time = time.time() - self._event_start
                                pass
                            else:
                                # if the maximum event time was reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, Stimulation time ran out")
                                self._event = False
                                # laser_toggle(False)
                                # laser_switch(False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
                    else:
                        # if the headdirection is not within the parameters
                        if self._event:
                            # but the stimulation is still going
                            if time.time() - self._event_start < self._min_trial_time:
                                # check if the minimum event time was not reached, then pass
                                pass
                            else:
                                # if minumum event time has been reached, reset the event,
                                # turn of the laser and start intertrial time
                                print("Ending Stimulation, angle not in range")
                                self._event = False
                                # laser_toggle(False)
                                # laser_switch(False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
        else:
            # if maximum experiment time was reached, stop experiment
            print("Ending experiment, timer ran out")
            self.stop_experiment()

        return self._event

    def start_experiment(self):
        # not necessary as this experiment is not needing any multiprocessing
        self._experiment_timer.start()

    def stop_experiment(self):
        self.experiment_finished = True
        print("Experiment completed!")
        print("Total event duration", sum(self._results))
        print(self._results)

    def get_trial(self):
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = None
        return info

class SecondExperiment:
    def __init__(self):
        self.experiment_finished = False
        self._green_point = GREEN_POINT
        self._blue_point = BLUE_POINT
        self._radius = 20.5
        self._event = None
        self._stage = 3
        self._count = {trial: 0 for trial in self._trials}
        self._exp_timer = Timer(600)

        # For automatic switches between stages:
        # self._stages = 2
        # self._completion_counter = {stage: False for stage in range(1, self._stages+1)}

    def check_skeleton(self, frame, skeleton):
        # if not all(self._completion_counter.values()):
        # if not all stages are completed
        for trial in self._trials:
            # check for all trials if condition is met
            result, response = self._trials[trial]["trigger"](skeleton=skeleton)
            if self._event is None:
                # if there is no current trial as event already
                if result:
                    # if condition is met set current trial as event
                    self._event = trial
                    self._count[trial] += 1
            else:
                # if there is a current trial set as event
                if not result and self._event == trial:
                    # if the condition for current trial is not met, reset event
                    self._event = None
                elif result and self._event != trial:
                    # if condition is met but event is not current trial(but last trial), set current trial as event
                    self._event = trial
                    self._count[trial] += 1
            # plot_triggers_response(frame, response)
        print(self._event)
        print("green: {}".format(self._count["Greenbar_whiteback"]))
        print("blue: {}".format(self._count["Bluebar_whiteback"]))
        if self._event is not None:
            # if there is a trial set as event, show stimulus
            print("I am not none!")
            show_visual_stim_img(type=self._event, name="inside")
        elif self._event is None:
            # if there is no trial set as event, show background
            show_visual_stim_img(name="inside")
        if all(trials >= EXP_COMPLETION for trials in self._count.values()):
            # if all trials reached number of repeats of completion criterion, set stage as completed and go higher
            # self._completion_counter[self._stage] = True
            # finish the experiment if stage is completed
            print("Stage " + str(self._stage) + " completed!")
            self.stop_experiment()
        self.check_exp_timer()
        #       self._stage += 1
        # else:
        #     # finish the experiment if all stages are completed
        #     self.stop_experiment()

    @property
    def _trials(self):

        orientation_angle = 30
        orientation_bodyparts = ["neck", "nose"]

        region_bodyparts = "nose"
        if self._stage == 1:
            green_roi = RegionTrigger(
                "circle", self._green_point, self._radius * 2 + 7.5, region_bodyparts
            )
            blue_roi = RegionTrigger(
                "circle", self._blue_point, self._radius * 2 + 7.5, region_bodyparts
            )
            trials = {
                "Greenbar_whiteback": dict(trigger=green_roi.check_skeleton, count=0),
                "Bluebar_whiteback": dict(trigger=blue_roi.check_skeleton, count=0),
            }
        elif self._stage == 2:
            green_roi = RegionTrigger(
                "circle",
                self._green_point,
                self._radius * 2 + 7.5 * 5,
                region_bodyparts,
            )
            blue_roi = RegionTrigger(
                "circle", self._blue_point, self._radius * 2 + 7.5 * 5, region_bodyparts
            )
            green_dir = DirectionTrigger(
                self._green_point, orientation_angle, orientation_bodyparts, True
            )
            blue_dir = DirectionTrigger(
                self._blue_point, orientation_angle, orientation_bodyparts, True
            )

            def res_func(roi, direct, skeleton):
                res_roi, response_roi = roi.check_skeleton(skeleton)
                res_dir, response_dir = direct.check_skeleton(skeleton)
                final_result = all([res_roi, res_dir])
                response_roi["plot"].update(response_dir["plot"])
                return final_result, response_roi

            trials = {
                "Greenbar_whiteback": dict(
                    trigger=partial(res_func, roi=green_roi, direct=green_dir), count=0
                ),
                "Bluebar_whiteback": dict(
                    trigger=partial(res_func, roi=blue_roi, direct=blue_dir), count=0
                ),
            }
        elif self._stage == 3:
            green_roi = RegionTrigger(
                "circle",
                self._green_point,
                self._radius * 2 + 7.5 * 10,
                region_bodyparts,
            )
            blue_roi = RegionTrigger(
                "circle",
                self._blue_point,
                self._radius * 2 + 7.5 * 10,
                region_bodyparts,
            )
            green_dir = DirectionTrigger(
                self._green_point, orientation_angle, orientation_bodyparts, True
            )
            blue_dir = DirectionTrigger(
                self._blue_point, orientation_angle, orientation_bodyparts, True
            )

            def res_func(roi, direct, skeleton):
                res_roi, response_roi = roi.check_skeleton(skeleton)
                res_dir, response_dir = direct.check_skeleton(skeleton)
                final_result = all([res_roi, res_dir])
                response_roi["plot"].update(response_dir["plot"])
                return final_result, response_roi

            trials = {
                "Greenbar_whiteback": dict(
                    trigger=partial(res_func, roi=green_roi, direct=green_dir), count=0
                ),
                "Bluebar_whiteback": dict(
                    trigger=partial(res_func, roi=blue_roi, direct=blue_dir), count=0
                ),
            }

            # green_dir = DirectionTrigger(self._green_point, orientation_angle, orientation_bodyparts, True)
            # blue_dir = DirectionTrigger(self._blue_point, orientation_angle, orientation_bodyparts, True)
            #
            # trials = {'Greenbar_whiteback': dict(trigger=green_dir.check_skeleton,
            #                                      count=0),
            #           'Bluebar_whiteback': dict(trigger=blue_dir.check_skeleton,
            #                                     count=0)}

        return trials

    def check_exp_timer(self):
        if not self._exp_timer.check_timer():
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        # not necessary as this experiment is not needing any multiprocessing
        if not self.experiment_finished:
            self._exp_timer.start()

    def stop_experiment(self):
        self.experiment_finished = True
        print("Experiment completed!")

    def get_trial(self):
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = None
        return info
    
class OptogenExperiment:
    def __init__(self):
        self.experiment_finished = False
        self._point = POINT
        self._start_angle, self._end_angle = ANGLE_WINDOW
        self._intertrial_timer = Timer(15)
        self._experiment_timer = Timer(1800)
        self._event = False
        self._event_start = None
        self._results = []
        self._max_trial_time = 5
        self._min_trial_time = 1
        self._max_total_time = 600
        self._total_time = 0
        self._trial_time = 0
    def check_skeleton(self, frame, skeleton):
        
        if self._experiment_timer.check_timer():
            if self._total_time >= self._max_total_time:
                # check if total time to stimulate per experiment is reached
                print("Ending experiment, total event time ran out")
                self.stop_experiment()
            else:
                # if not continue
                if not self._intertrial_timer.check_timer():
                    # check if there is an intertrial time running right now, if not continue
                    # check if the headdirection angle is within limits
                    _, angle_point = angle_between_vectors(
                        *skeleton["nose"],*skeleton["neck"], *self._point
                    )     

                    if self._start_angle <= angle_point <= self._end_angle:
                        if not self._event:
                            # if a stimulation event wasn't started already, start one
                            print("Starting Stimulation")
                            self._event = True
                            # and activate the laser, start the timer and reset the intertrial timer
                            laser_switch(True)
                            self._event_start = time.time()
                            self._intertrial_timer.reset()
                        else:
                            if time.time() - self._event_start <= self._max_trial_time:
                                # if the total event time has not reached the maximum time per event
                                # self._trial_time = time.time() - self._event_start
                                pass
                            else:
                                # if the maximum event time was reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, Stimulation time ran out")
                                self._event = False
                                # laser_toggle(False)
                                laser_switch(False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
                    else:
                        # if the headdirection is not within the parameters
                        if self._event:
                            # but the stimulation is still going
                            if time.time() - self._event_start < self._min_trial_time:
                                # check if the minimum event time was not reached, then pass
                                pass
                            else:
                                # if minumum event time has been reached, reset the event,
                                # turn of the laser and start intertrial time
                                print("Ending Stimulation, angle not in range")
                                self._event = False
                                # laser_toggle(False)
                                laser_switch(False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
        else:
            # if maximum experiment time was reached, stop experiment
            print("Ending experiment, timer ran out")
            self.stop_experiment()

        return self._event

    def start_experiment(self):
        # not necessary as this experiment is not needing any multiprocessing
        self._experiment_timer.start()

    def stop_experiment(self):
        self.experiment_finished = True
        print("Experiment completed!")
        print("Total event duration", sum(self._results))
        print(self._results)

    def get_trial(self):
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = None
        return info

class C4TeamOptoG:
    def __init__(self):
        self.experiment_finished = False
        self._start_angle, self._end_angle = ANGLE_WINDOW
        self._stim_angle = STIM_ANGLE
        self._intertrial_timer = Timer(0)
        self._experiment_timer = Timer(1800)
        self._event = False
        self._event_start = None
        self._results = []
        self._max_trial_time = 100
        self._min_trial_time = 0
        self._max_total_time = 600
        self._total_time = 0
        self._trial_time = 0
        self._ser = arduino
        serial_laser_switch(self._ser,False)
        
        
    def check_skeleton(self, frame, skeleton):
        
        # Get angle between mouse head and object, and set the 0 
        xc,yc = skeleton["neck"][0] + np.cos(self._stim_angle*np.pi/180), skeleton["neck"][1] - np.sin(self._stim_angle*np.pi/180)
        _, angle_point = angle_between_vectors(xc,yc,*skeleton["neck"],*skeleton["nose"])
        """"Answer is angle from -180° to 180 ° compared to stim direction"""
        
        # Plot absolute angle.
        plot_absolute_angle(frame,skeleton["nose"],skeleton["neck"],self._stim_angle,self._event)
        

        #Show absolute angle value (0 to 180° compared to stim direction).
        plotting_position = (skeleton["nose"][0]+20 , skeleton["nose"][1]-20)
        plot_angle_value(frame,abs(angle_point),plotting_position,self._event)
        
        
        if self._experiment_timer.check_timer():
            if self._total_time >= self._max_total_time:
                # check if total time to stimulate per experiment is reached
                print("Ending experiment, total event time ran out")
                self.stop_experiment()
            else:
                # if not continue
                if not self._intertrial_timer.check_timer():
                    # check if there is an intertrial time running right now, if not continue
                    # check if the headdirection angle is within limits

                    if self._start_angle <= angle_point <= self._end_angle:
                        if not self._event:
                            # if a stimulation event wasn't started already, start one
                            print("Starting Stimulation")
                            self._event = True
                            # and activate the laser, start the timer and reset the intertrial timer
                            serial_laser_switch(self._ser,True)
                            self._event_start = time.time()
                            self._intertrial_timer.reset()
                        else:
                            if time.time() - self._event_start <= self._max_trial_time:
                                # if the total event time has not reached the maximum time per event
                                # self._trial_time = time.time() - self._event_start
                                pass
                            else:
                                # if the maximum event time was reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, Stimulation time ran out")
                                self._event = False
                                # laser_toggle(False)
                                serial_laser_switch(self._ser,False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
                    else:
                        # if the headdirection is not within the parameters
                        if self._event:
                            # but the stimulation is still going
                            if time.time() - self._event_start < self._min_trial_time:
                                # check if the minimum event time was not reached, then pass
                                pass
                            else:
                                # if minumum event time has been reached, reset the event,
                                # turn off the laser and start intertrial time
                                print("Ending Stimulation, angle not in range")
                                self._event = False
                                # laser_toggle(False)
                                serial_laser_switch(self._ser,False)
                                # self._trial_time = time.time() - self._event_start
                                trial_time = time.time() - self._event_start
                                self._total_time += trial_time
                                self._results.append(trial_time)
                                print("Stimulation duration", trial_time)
                                self._intertrial_timer.start()
        else:
            # if maximum experiment time was reached, stop experiment
            print("Ending experiment, timer ran out")
            self.stop_experiment()

        return self._event

    def start_experiment(self):
        # not necessary as this experiment is not needing any multiprocessing
        self._experiment_timer.start()

    def stop_experiment(self):
        self.experiment_finished = True
        print("Experiment completed!")
        print("Total event duration", sum(self._results))
        print(self._results)

    def get_trial(self):
        return self._event

    def get_info(self):
        """ returns optional info"""
        info = None
        return info

class Reward_PreTraining:
    
    
    def __init__(self):
        self.experiment_finished = False
        self._trials_list = self.generate_trials_list(self._trials, 30)
        self._iti_list = self.generate_iti_list(30)
        self._iti_duration = 10
        self._intertrial_timer = Timer(self._iti_duration)
        self._process = SimpleProtocolProcess(self._trials)
        self._chosen_trial = None
        self._exp_timer = Timer(1800)
        self._trial_counter = 0
        self._print_check = False

    def check_skeleton(self, frame, skeleton):
        status, trial = self._process.get_status()

        if status:
            result = self._process.get_result()
            if result is not None:
                # if trial is finished, takes new ITI.
                self._iti_duration = next(self._iti_list, False)
                self._intertrial_timer = Timer(self._iti_duration)

        elif self.check_triggers(skeleton) and not self._intertrial_timer.check_timer():
            # check trial end trigger and starts Timer
            self._intertrial_timer.start()
            if not self._print_check:
                print(
                    "Reward was taken. Going into InterTrialTime for "
                    + str(self._iti_duration)
                    + " sec."
                )
                self._print_check = True
            # resets chosen_trial
            self._chosen_trial = None
        elif not self._intertrial_timer.check_timer():
            # if the timer ran out or was not started yet again
            self._print_check = False
            if self._chosen_trial is None:
                # if the chosen_trial was reset or first time
                self._chosen_trial = next(self._trials_list, False)
                if not self._chosen_trial:
                    # if no more trials exist in iter
                    print("Experiment is finished due to max. trial number.")
                    exp_time = self._exp_timer.return_time()
                    print("Experiment took " + str(exp_time) + " sec")
                    self.stop_experiment()
                self._trial_counter += 1
                print("Stimulation: #", str(self._trial_counter))
                self._process.set_trial(self._chosen_trial)
        self.check_end_time()

    def check_triggers(self, skeleton):
        """
        checks stage dependent trigger dict
        :param skeleton: bodypart coordinates
        :return: returns whether all triggers were true
        """
        result_list = []
        result = False
        for trigger in self._triggers.values():
            trigger_result, _ = trigger.check_skeleton(skeleton)
            result_list.append(trigger_result)
        if all(result_list):
            result = True

        return result

    @property
    def _trials(self):
        """this is a dummy version of the more complex experiments to keep the general flow"""
        trials = {"Pretraining": dict(stimulus_timer=None, count=0)}
        return trials

    @property
    def _triggers(self):
        """
        creates trial start condition triggers depending on the experimental stage"
        :return: dict of triggers
        """
        triggers = dict(region=RegionTrigger("circle", (648, 38), 30, "nose"))

        return triggers

    @staticmethod
    def generate_trials_list(trials: dict, length: int):
        trials_list = []
        for trial in range(length):
            trials_list.append(random.choice(list(trials.keys())))
        return iter(trials_list)

    @staticmethod
    def generate_iti_list(length: int, min: int = 0):
        iti_list = []
        for i in range(length):
            iti = random.randint(min, 30 + 1)
            iti_list.append(iti)
        return iter(iti_list)

    def check_end_time(self):
        if not self._exp_timer.check_timer():
            # if experimental time ran out, finish experiments
            print("Experiment is finished")
            print("Time ran out.")
            self.stop_experiment()

    def start_experiment(self):
        if not self.experiment_finished:
            self._intertrial_timer.start()
            self._exp_timer.start()
            self._process.start()

    def stop_experiment(self):
        # stopping the experiment
        self._process.end()
        self.experiment_finished = True

    def get_trial(self):
        return self._chosen_trial

    def get_info(self):
        """ returns optional info"""
        info = None
        return info
    
    
    
