holidayLightPatternDefault = "on"
holidayLightAnimationDefault = "solid"

import time
import threading
import random
from homealone import *

def randomPattern(length=1, colors=3):
    pattern = [0]*length
    for i in range(length):
        pattern[i] = int(16777215 * random.random()) # random number between 0 and 256**3-1
    return pattern

# define a segment of a string of lights
class Segment(object):
    def __init__(self, start, length, pattern=None, animation=None):
        self.name = "segment"
        self.start = start
        self.length = length
        if pattern:
            self.pattern = pattern
        else:
            self.pattern = [0]
        self.animation = animation
        debug("debugHolidayLights", "segment", self.name, start, length, self.pattern, self.animation)
        self.pixels = [0]*length
        self.frame = 0

    # fill the segment with a pattern
    def fill(self, pattern=None):
        if not pattern:
            pattern = self.pattern
        if isinstance(pattern[0], list):
            pattern = pattern[0]
        debug("debugHolidayLights", "segment", self.name, "fill", pattern)
        for l in range(self.length):
            self.pixels[l] = pattern[l%len(pattern)]

    # display the segment
    def display(self, strip):
        for l in range(self.length):
            strip.write(self.start+l, self.pixels[l])

    # animate the segment
    def animate(self):
        if self.animation:
            self.animation.animate(self)

    # shift the pattern by the specified number of pixels in the specified direction
    def shift(self, n, direction):
        debug("debugHolidayLightsAnimation", "segment", self.name, "shift", n, direction)
        if direction > 0:   # shift out
            pixels = self.pixels[-n:]
            self.pixels = pixels+self.pixels[:-n]
        else:       # shift in
            pixels = self.pixels[n:]
            self.pixels = pixels+self.pixels[:n]

    # turn off random pixels based on a culling frequency between 0 and 1
    def decimate(self, factor):
        debug("debugHolidayLightsAnimation", "segment", self.name, "decimate", factor)
        for p in range(len(self.pixels)):
            if random.random() < factor:
                self.pixels[p] = 0

    # dim the pattern by a specified factor
    def dim(self, factor):
        for p in range(len(self.pixels)):
            pixel = self.pixels[p]
            r = int(factor * ((pixel>>16)&0xff))
            g = int(factor * ((pixel>>8)&0xff))
            b = int(factor * (pixel&0xff))
            self.pixels[p] = (r<<16)+(g<<8)+b

# define an animation for a segment
class Animation(object):
    def __init__(self, name, rate):
        self.name = name
        self.rate = rate
        self.animationCount = 0

    # define an animation cycle
    def animate(self, segment):
        self.segment = segment
        if self.animationCount == 0:
            self.cycle()
        self.animationCount += 1
        if self.animationCount == self.rate:
            self.animationCount = 0

class RandomColorAnimation(Animation):
    def __init__(self, name="randomcolor", rate=3):
        Animation.__init__(self, name, rate)

    def cycle(self):
        self.segment.fill(randomPattern(len(self.segment.pixels)))

class CrawlAnimation(Animation):
    def __init__(self, name="crawl", rate=3, direction=1):
        Animation.__init__(self, name, rate)
        self.direction = direction

    def cycle(self):
        self.segment.shift(1, self.direction)

class SparkleAnimation(Animation):
    def __init__(self, name="sparkle", rate=3, factor=.7):
        Animation.__init__(self, name, rate)
        self.factor = factor

    def cycle(self):
        self.segment.fill()
        self.segment.decimate(self.factor)

class FlickerAnimation(Animation):
    def __init__(self, name="flicker", rate=1, factor=.7):
        Animation.__init__(self, name, rate)
        self.factor = factor

    def cycle(self):
        if random.random() < self.factor:
            self.segment.fill()
        else:
            self.segment.fill([0])

class BlinkAnimation(Animation):
    def __init__(self, name="blink", rate=15):
        Animation.__init__(self, name, rate)
        self.state = True

    def cycle(self):
        if self.state:
            self.segment.fill([off])
            self.state = False
        else:
            self.segment.fill()
            self.state = True

class FadeAnimation(Animation):
    def __init__(self, name="fade", rate=6):
        Animation.__init__(self, name, rate)
        self.fadeFactor = 10
        self.fadeIncr = -1

    def cycle(self):
        self.segment.fill()
        self.segment.dim(float(self.fadeFactor)/10)
        self.fadeFactor += self.fadeIncr
        if (self.fadeFactor == 0) or (self.fadeFactor == 10):
            self.fadeIncr = -self.fadeIncr

class MovieAnimation(Animation):
    def __init__(self, name="movie", rate=6):
        Animation.__init__(self, name, rate)

    def cycle(self):
        self.segment.fill(self.segment.pattern[self.segment.frame])
        self.segment.frame += 1
        if self.segment.frame == len(self.segment.pattern):
            self.segment.frame = 0

class HolidayLightControl(Control):
    def __init__(self, name, interface, patterns, patternControl, delay=0,
                 **kwargs):
        Control.__init__(self, name, interface, **kwargs)
        self.className = "Control"
        self.patterns = patterns                # list of patterns
        self.patternControl = patternControl    # a Control whose state specifies which pattern is active
        self.patternControl.stateSet = self.setPattern  # callback for pattern changes
        self.pattern = ""                       # name of the active pattern
        self.delay = delay                      # optional delay between animation cycles
        self.runState = off                     # current state of the control
        self.run = False                        # signal to start and stop animation thread
        self.running = False                    # animation thread is running

    def getState(self, missing=None):
        return self.runState

    def setState(self, value):
        debug("debugHolidayLights", self.name, "setState", "value:", value)
        if value:
            self.runState = on
            self.setPattern(self.patternControl, self.patternControl.getState())
        else:
           self.run = False
           self.runState = off

    # set the pattern based on the pattern control
    def setPattern(self, control, state):
        debug('debugHolidayLights', "setPattern", control.name, state)
        # stop the animation thread if it is running
        if self.running:
            self.run = False
            # wait for it to finish
            while self.running:
                time.sleep(.1)
        self.pattern = state
        self.segments = self.patterns[self.pattern]
        # compute segment positions if not explicitly specified
        pos = 0
        for segment in self.segments:
            if segment.start == 0:
                segment.start = pos
            debug("debugHolidayLights", self.name, "segment", segment.start, segment.length, segment.pattern)
            pos += segment.length
        # run the animations if the control is on
        if self.runState:
            displayThread = LogThread(name="displayThread", target=self.runDisplay)
            displayThread.start()

    # thread to run the animations
    def runDisplay(self):
        debug("debugHolidayLights", self.name, "runDisplay started")
        self.run = True
        self.running = True
        for segment in self.segments:
            segment.fill()
            segment.display(self.interface)
        self.interface.show()
        # run the animations
        while self.run:
            time.sleep(self.delay)
            for segment in self.segments:
                segment.animate()
                segment.display(self.interface)
            self.interface.show()
        # turn all lights off
        for segment in self.segments:
            segment.fill([off])
            segment.display(self.interface)
        self.interface.show()
        self.running = False
        debug("debugHolidayLights", self.name, "runDisplay terminated")
