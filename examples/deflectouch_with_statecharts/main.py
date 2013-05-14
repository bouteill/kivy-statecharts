'''
-----------------------------------------------------------------
PORT to STATECHART Treatment

Deflectouch-with-Statecharts has changes needed to move code to
a statechart treatment. The port is meant as an example for
comparison to a full Kivy app with and without statecharts.

See Cyril Stoller's Deflectouch repo for the original code:

    https://github.com/stocyr/Deflectouch

As of August 7, 2012, this port is a work-in-progress ...
-----------------------------------------------------------------

Deflectouch

Copyright (C) 2012  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of Deflectouch.

Deflectouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Deflectouch is distributed in the hope that it will be fun,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Deflectouch.  If not, see <http://www.gnu.org/licenses/>.
'''

# For including for ios, etc.
#
#import sys, os; sys.path += [os.path.join(os.path.dirname(__file__), 'lib')]

import kivy
kivy.require('1.0.9')

from kivy.config import Config
# for making screenshots with F12:
#Config.set('modules', 'keybinding', '')
#Config.set('modules', 'inspector', '')

from kivy.app import App
from kivy.factory import Factory
from kivy.utils import boundary
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
from kivy.base import EventLoop
from kivy.vector import Vector
from kivy.graphics.transformation import Matrix
from kivy.graphics import Line, Color

from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import ListProperty

from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter

from math import tan
from math import sin
from math import cos
from math import pi
from math import radians
from math import atan2

from random import randint

from kivy_statecharts.system.state import State
from kivy_statecharts.system.statechart import StatechartManager

# For debugging memory leaks and other investigations:
#
#import gc
#import objgraph

#
#  Constants
#

VERSION = '1.0'

LEVEL_WIDTH = 16
LEVEL_HEIGHT = 16

MIN_DEFLECTOR_LENGTH = 100

GRAB_RADIUS = 30


#
#  Background
#
class Background(Image):
    def on_touch_down(self, touch):
        # [statechart port] check if moving deflector:
        for deflector in self.parent.app.deflector_list:
            if deflector.collide_grab_point(*touch.pos):
                # pass the touch to the deflector scatter
                return super(Background, self).on_touch_down(touch)

        self.parent.app.statechart.send_event('background_touch_down', touch)

#
#  Bullet
#
class Bullet(Image):
    angle = NumericProperty(0)  # in radians!
    exploding = False

    def __init__(self, **kwargs):
        super(Bullet, self).__init__(**kwargs)


#
#  Stockbar
#
class Stockbar(Image):
    max_stock = NumericProperty(0)


#
#  Tank
#
class Tank(Widget):
    tank_tower_scatter = ObjectProperty(None)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        else:
            touch.ud['tank_touch'] = True
            return True

    def on_touch_move(self, touch):
        ud = touch.ud

        if not 'tank_touch' in ud:
            return False

        if 'rotation_mode' in ud:
            # if the current touch is already in the 'rotate' mode, rotate the tower.
            dx = touch.x - self.center_x
            dy = touch.y - self.center_y
            angle = boundary(atan2(dy, dx) * 360 / 2 / pi, -60, 60)

            angle_change = self.tank_tower_scatter.rotation - angle
            rotation_matrix = Matrix().rotate(-radians(angle_change), 0, 0, 1)
            self.tank_tower_scatter.apply_transform(rotation_matrix, post_multiply=True, anchor=(105, 15))

        elif touch.x > self.right:
            # if the finger moved too far to the right go into rotation mode
            ud['rotation_mode'] = True

        else:
            # if the user wants only to drag the tank up and down, let him do it!
            self.y += touch.dy


#
#  Deflector
#
class Deflector(Scatter):
    statechart = ObjectProperty(None)

    touch1 = ObjectProperty(None)
    touch2 = ObjectProperty(None)

    point1 = ObjectProperty(None)
    point2 = ObjectProperty(None)

    deflector_line = ObjectProperty(None)

    length = NumericProperty(0)
    length_origin = 0

    point_pos_origin = []

    def __init__(self, **kwargs):
        super(Deflector, self).__init__(**kwargs)

        # DEFLECTOR LINE:
        # Here I rotate and translate the deflector line so that it lays exactly under the two fingers
        # and can be moved and scaled by scatter from now on. Thus I also have to pass the touches to scatter.
        # First i create the line perfectly horizontal but with the correct length. Then i add the two
        # drag points at the beginning and the end.

        self.length_origin = self.length

        with self.canvas.before:
            Color(.8, .8, .8)
            self.deflector_line = Line(points=(self.touch1.x, self.touch1.y - 1, self.touch1.x + self.length, self.touch1.y - 1))
            self.deflector_line2 = Line(points=(self.touch1.x, self.touch1.y + 1, self.touch1.x + self.length, self.touch1.y + 1))

        '''
        self.deflector_line = Image(source='graphics/beta/deflector_blue_beta2.png',
                                    allow_stretch=True,
                                    keep_ratio=False,
                                    size=(self.length, 20),
                                    center_y=(self.touch1.y),
                                    x=self.touch1.x)
        '''

        # set the right position for the two points:
        self.point1.center = self.touch1.pos
        self.point2.center = self.touch1.x + self.length, self.touch1.y
        self.point_pos_origin = [self.point1.x, self.point1.y, self.point2.x, self.point2.y]

        # rotation:
        dx = self.touch2.x - self.touch1.x
        dy = self.touch2.y - self.touch1.y
        angle = atan2(dy, dx)

        rotation_matrix = Matrix().rotate(angle, 0, 0, 1)
        self.apply_transform(rotation_matrix, post_multiply=True, anchor=self.to_local(self.touch1.x, self.touch1.y))

        # We have to adjust the bounding box of ourself to the dimension of all the canvas objects (Do we have to?)
        #self.size = (abs(self.touch2.x - self.touch1.x), abs(self.touch2.y - self.touch1.y))
        #self.pos = (min(self.touch1.x, self.touch2.x), min(self.touch1.y, self.touch2.y))

        # Now we finally add both touches we received to the _touches list of the underlying scatter class structure.
        self.touch1.grab(self)
        self._touches.append(self.touch1)
        self._last_touch_pos[self.touch1] = self.touch1.pos

        self.touch2.grab(self)
        self._touches.append(self.touch2)
        self._last_touch_pos[self.touch2] = self.touch2.pos

        self.point1.bind(size=self.size_callback)

    def size_callback(self, instance, size):
        self.statechart.send_event('resize_deflector', self, size)

    def collide_widget(self, wid):
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])

        if max(point1_parent[0], point2_parent[0]) < wid.x:
            return False
        if min(point1_parent[0], point2_parent[0]) > wid.right:
            return False
        if max(point1_parent[1], point2_parent[1]) < wid.y:
            return False
        if min(point1_parent[1], point2_parent[1]) > wid.top:
            return False
        return True

    def collide_point(self, x, y):
        # this function is used exclusively by the underlying scatter functionality.
        # therefor i can control when a touch will be dispatched from here.
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])

        return min(point1_parent[0], point2_parent[0]) - GRAB_RADIUS <= x <= max(point1_parent[0], point2_parent[0]) + GRAB_RADIUS \
           and min(point1_parent[1], point2_parent[1]) - GRAB_RADIUS <= y <= max(point1_parent[1], point2_parent[1]) + GRAB_RADIUS

    def collide_grab_point(self, x, y):
        point1_parent = self.to_parent(self.point1.center[0], self.point1.center[1])
        point2_parent = self.to_parent(self.point2.center[0], self.point2.center[1])

        return point1_parent[0] - GRAB_RADIUS <= x <= point1_parent[0] + GRAB_RADIUS and point1_parent[1] - GRAB_RADIUS <= y <= point1_parent[1] + GRAB_RADIUS \
            or point2_parent[0] - GRAB_RADIUS <= x <= point2_parent[0] + GRAB_RADIUS and point2_parent[1] - GRAB_RADIUS <= y <= point2_parent[1] + GRAB_RADIUS

    def on_touch_down(self, touch):
        self.statechart.send_event('deflector_touch_down')

        return super(Deflector, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        # if the deflector want's to be removed (touches too close to each other):
        # [statechart port] context could normally be a class of some sort,
        #                   but probably could be anything. Setting to string here.
        context = 'deflector_touch_up'

        if self.parent != None and self.collide_grab_point(*touch.pos):
            self.statechart.send_event('deflector_touch_up', self, context)

        return super(Deflector, self).on_touch_up(touch)


############################
#
#  Application Statechart
#
class AppStatechart(StatechartManager):
    app = ObjectProperty(None)

    def __init__(self, app, **kwargs):
        kwargs['app'] = app
        kwargs['trace'] = True
        kwargs['root_state_class'] = self.RootState
        super(AppStatechart, self).__init__(**kwargs)

    #  RootState of statechart
    #
    class RootState(State):
        def __init__(self, **kwargs):
            kwargs['initial_substate_key'] = 'ShowingGameScreen'
            super(AppStatechart.
                  RootState, self).__init__(**kwargs)

        def enter_state(self, context=None):
            print 'RootState/enter_state'

        def exit_state(self, context=None):
            print 'RootState/exit_state'

        # ShowingGameScreen
        #
        class ShowingGameScreen(State):
            settings_popup = None

            def __init__(self, **kwargs):
                super(AppStatechart.
                      RootState.
                      ShowingGameScreen, self).__init__(**kwargs)

            def enter_state(self, context=None):
                print 'ShowingGameScreen/enter_state'

                # create the root widget and give it a reference of the application instance (so it can access the application settings)
                self.statechart.app.game_screen = self.statechart.app.root

                # start the background music:
                self.statechart.app.music = SoundLoader.load('sound/deflectouch.ogg')
                self.statechart.app.music.volume = self.statechart.app.config.getint('General', 'Music') / 100.0
                self.statechart.app.music.bind(on_stop=self.sound_replay)
                self.statechart.app.music.play()

                # load all other sounds:
                self.statechart.app.sound['switch'] = SoundLoader.load('sound/switch.ogg')
                self.statechart.app.sound['select'] = SoundLoader.load('sound/select.ogg')
                self.statechart.app.sound['reset'] = SoundLoader.load('sound/reset.ogg')
                self.statechart.app.sound['beep'] = SoundLoader.load('sound/beep.ogg')

                self.statechart.app.sound['bullet_start'] = SoundLoader.load('sound/bullet_start.ogg')
                self.statechart.app.sound['explosion'] = SoundLoader.load('sound/explosion.ogg')
                self.statechart.app.sound['accomplished'] = SoundLoader.load('sound/accomplished.ogg')

                self.statechart.app.sound['no_deflector'] = SoundLoader.load('sound/no_deflector.ogg')
                self.statechart.app.sound['deflector_new'] = SoundLoader.load('sound/deflector_new.ogg')
                self.statechart.app.sound['deflector_touch_down'] = SoundLoader.load('sound/deflector_touch_down.ogg')
                self.statechart.app.sound['deflector_touch_up'] = SoundLoader.load('sound/deflector_touch_up.ogg')
                self.statechart.app.sound['deflector_delete'] = SoundLoader.load('sound/deflector_delete.ogg')
                self.statechart.app.sound['deflection'] = SoundLoader.load('sound/deflection.ogg')

                sound_volume = self.statechart.app.config.getint('General', 'Sound') / 100.0
                print 'sound_volume is', sound_volume
                for item in self.statechart.app.sound:
                    self.statechart.app.sound[item].volume = sound_volume

                # [statechart port] Changed up this section to set current_level, instead
                #                   of calling load_level() -- this is now the enter_state
                #                   of the ShowingLevel state. Also, added a way to put up
                #                   the help screen then goto ShowingLevel, vs. directly
                #                   from here.

                # continue on the last level which wasn't finished
                unfinished_level_found = False
                for counter, char in enumerate(self.statechart.app.config.get('GamePlay', 'Levels')):
                    # if I found a level not yet done, continue with that
                    if char == '0':
                        self.statechart.app.current_level = counter + 1
                        unfinished_level_found = True
                        break

                # if all levels were completed, just open the last one.
                if unfinished_level_found is False:
                    self.statechart.app.current_level = 40

                # if the user started the game the first time, display quick start guide
                if self.statechart.app.config.get('General', 'FirstStartup') == 'Yes':
                    Clock.schedule_once(self.show_help_first_time, 2)
                    self.statechart.app.config.set('General', 'FirstStartup', 'No')
                    self.statechart.app.config.write()
                else:
                    self.go_to_state('ShowingLevel')

            def show_help_first_time(self, *args):
                self.go_to_state('ShowingWelcomePopup')

            def exit_state(self, context=None):
                print 'ShowingGameScreen/exit_state'

            def sound_replay(self, instance):
                if self.statechart.app.music.status != 'play':
                    self.statechart.app.music.play()

            # ShowingLevelsPopup
            #
            class ShowingLevelsPopup(State):
                popup = ObjectProperty(None)

                def __init__(self, **kwargs):
                    super(AppStatechart.
                          RootState.
                          ShowingGameScreen.
                          ShowingLevelsPopup, self).__init__(**kwargs)

                def enter_state(self, context=None):
                    print 'ShowingLevelsPopup/enter_state'

                    # create a popup with all the levels
                    grid_layout = GridLayout(cols=8, rows=5, spacing=10, padding=10)

                    enable_next_row = True
                    row_not_complete = False
                    for row in range(5):
                        for column in range(8):
                            button = Button(text=str(row * 8 + (column + 1)), bold=True, font_size=30)

                            if enable_next_row is True:
                                # if this row is already enabled:
                                button.bind(on_press=self.select_level)

                                if self.statechart.app.config.get('GamePlay', 'Levels')[row * 8 + column] == '1':
                                    # if level was already done, green button
                                    button.background_color = (0, 1, 0, 1)
                                else:
                                    # if level not yet done but enabled though, red button
                                    button.background_color = (1, 0, 0, 0.5)

                                    # and do NOT enable the next row then:
                                    row_not_complete = True

                            else:
                                # if not yet enabled:
                                button.background_color = (0.1, 0.05, 0.05, 1)

                            grid_layout.add_widget(button)

                        if row_not_complete is True:
                            enable_next_row = False

                    self.popup = Popup(title='Level List (if you finished a row, the next row will get enabled!)',
                                       content=grid_layout,
                                       size_hint=(0.5, 0.5))
                    self.popup.open()

                # [statechart port] See context of select_level binding above for how text of level buttons are set.
                #                   This is a new action function, simplifying the code in what was the reset_level()
                #                   function, but now is in ShowingLevel state's enter_state() setup code.
                def select_level(self, level_button, *args):
                    level = int(level_button.text)
                    self.statechart.app.current_level = level
                    self.statechart.app.sound['select'].play()
                    self.go_to_state('ShowingLevel')

                def exit_state(self, context=None):
                    print 'ShowingLevelsPopup/exit_state'
                    self.popup.dismiss()

                def cancel(self, context):
                    self.go_to_state(self.parent_state)

            # ShowingSettingsPopup
            #
            class ShowingSettingsPopup(State):
                popup = ObjectProperty(None)

                def __init__(self, **kwargs):
                    super(AppStatechart.
                          RootState.
                          ShowingGameScreen.
                          ShowingSettingsPopup, self).__init__(**kwargs)

                def enter_state(self, context=None):
                    print 'ShowingSettingsPopup/enter_state'

                    # the first time the setting dialog is called, initialize its content.
                    if self.popup is None:

                        self.popup = Popup(attach_to=self.statechart.app.game_screen,
                                           title='DeflecTouch Settings',
                                           size_hint=(0.3, 0.5))

                        class SettingsDialog(BoxLayout):
                            statechart = ObjectProperty(None)

                            music_slider = ObjectProperty(None)
                            sound_slider = ObjectProperty(None)
                            speed_slider = ObjectProperty(None)

                            def __init__(self, statechart, **kwargs):
                                self.statechart = statechart
                                super(SettingsDialog, self).__init__(**kwargs)

                        settings_dialog = SettingsDialog(statechart=self.statechart)

                        self.popup.content = settings_dialog

                        settings_dialog.music_slider.bind(value=self.update_music_volume)
                        settings_dialog.sound_slider.bind(value=self.update_sound_volume)
                        settings_dialog.speed_slider.bind(value=self.update_speed)

                        settings_dialog.music_slider.value = boundary(self.statechart.app.config.getint('General', 'Music'), 0, 100)
                        settings_dialog.sound_slider.value = boundary(self.statechart.app.config.getint('General', 'Sound'), 0, 100)
                        settings_dialog.speed_slider.value = boundary(self.statechart.app.config.getint('GamePlay', 'BulletSpeed'), 1, 10)

                    self.popup.open()

                def exit_state(self, context=None):
                    print 'ShowingSettingsPopup/exit_state'
                    self.popup.dismiss()

                def update_music_volume(self, instance, value):
                    # write to app configs
                    self.statechart.app.config.set('General', 'Music', str(int(value)))
                    self.statechart.app.config.write()
                    self.statechart.app.music.volume = value / 100.0

                def update_sound_volume(self, instance, value):
                    # write to app configs
                    self.statechart.app.config.set('General', 'Sound', str(int(value)))
                    self.statechart.app.config.write()
                    for item in self.statechart.app.sound:
                        self.statechart.app.sound[item].volume = value / 100.0

                def update_speed(self, instance, value):
                    # write to app configs
                    self.statechart.app.config.set('GamePlay', 'BulletSpeed', str(int(value)))
                    self.statechart.app.config.write()

                def show_help(self, *args):
                    self.go_to_state('ShowingHelpPopup')

                def close(self, *args):
                    self.go_to_state(self.parent_state)

            # ShowingHelpPopup
            #
            class ShowingHelpPopup(State):
                popup = ObjectProperty(None)

                def __init__(self, **kwargs):
                    super(AppStatechart.
                          RootState.
                          ShowingGameScreen.
                          ShowingHelpPopup, self).__init__(**kwargs)

                def enter_state(self, context=None):
                    print 'ShowingHelpPopup/enter_state'

                    # display the help screen on a Popup
                    image = Image(source='graphics/help_screen.png')

                    self.popup = Popup(title='Quick Guide through DEFLECTOUCH',
                                       attach_to=self.statechart.app.game_screen,
                                       size_hint=(0.98, 0.98),
                                       content=image)
                    image.bind(on_touch_down=self.dismiss)
                    self.popup.open()

                def exit_state(self, context=None):
                    print 'ShowingHelpPopup/exit_state'
                    self.popup.dismiss()

                def dismiss(self, *args):
                    self.go_to_state(self.parent_state)

            # [statechart port] Note reuse of ShowingHelpPopup through subclassing.
            #                   Only difference is that dismiss fires to ShowingLevel
            #                   (See statechart drawing).

            # ShowingWelcomePopup
            #
            class ShowingWelcomePopup(ShowingHelpPopup):
                def __init__(self, **kwargs):
                    super(AppStatechart.
                          RootState.
                          ShowingGameScreen.
                          ShowingWelcomePopup, self).__init__(**kwargs)

                def dismiss(self, *args):
                    self.go_to_state('ShowingLevel')

            # ShowingLevelAccomplished (transient state)
            #
            class ShowingLevelAccomplished(State):
                animation = None

                def enter_state(self, context):
                    print 'ShowingLevelAccomplished/enter_state'
                    self.statechart.app.sound['accomplished'].play()

                    # store score in config: (i have to convert the string to a list to do specific char writing)
                    levels_before = list(self.statechart.app.config.get('GamePlay', 'Levels'))
                    levels_before[self.statechart.app.level - 1] = '1'
                    self.statechart.app.config.set('GamePlay', 'Levels', "".join(levels_before))
                    self.statechart.app.config.write()

                    # show up a little image with animation: size*2 and out_bounce and the wait 1 sec
                    image = Image(source='graphics/accomplished.png', size_hint=(None, None), size=(200, 200))
                    image.center = self.statechart.app.game_screen.center
                    self.animation = Animation(size=(350, 416), duration=1, t='out_bounce')
                    self.animation &= Animation(center=self.statechart.app.game_screen.center, duration=1, t='out_bounce')
                    self.animation += Animation(size=(350, 416), duration=1)  # little hack to sleep for 1 sec

                    self.statechart.app.game_screen.add_widget(image)
                    self.animation.start(image)
                    self.animation.bind(on_complete=self.accomplished_animation_complete)

                def accomplished_animation_complete(self, animation, widget):
                    self.animation.unbind(on_complete=self.accomplished_animation_complete)
                    self.statechart.app.game_screen.remove_widget(widget)

                    if self.statechart.app.level != 40:
                        if self.statechart.app.level % 8 == 0:
                            Popup(title='New levels unlocked!',
                                  content=Label(text='Next 8 levels unlocked!',
                                                font_size=18),
                                                size_hint=(0.3, 0.15)).open()

                        self.statechart.app.current_level += 1
                        self.go_to_state('ShowingLevel')

                def exit_state(self, context):
                    print 'ShowingLevelAccomplished/exit_state'

            # ResettingLevel
            #
            class ResettingLevel(State):
                def enter_state(self, context=None):
                    print 'ResettingLevel/enter_state'
                    self.statechart.app.sound['reset'].play()

                    self.go_to_state('ShowingLevel')

                def exit_state(self, context=None):
                    print 'ResettingLevel/exit_state'

            # ShowingLevel
            #
            class ShowingLevel(State):
                level_image = ObjectProperty(None)

                def __init__(self, **kwargs):
                    kwargs['initial_substate_key'] = 'ShowingBackground'
                    super(AppStatechart.
                            RootState.
                            ShowingGameScreen.
                            ShowingLevel, self).__init__(**kwargs)

                def enter_state(self, context=None):
                    print 'ShowingLevel/enter_state'
                    #print gc.get_count()
                    #print gc.get_objects()
                    #print gc.get_referrers(gc.get_objects())
                    #objgraph.show_backrefs([self], filename='showing-level-backrefs.png')
                    BRICK_WIDTH = self.statechart.app.game_screen.height / 17.73
                    LEVEL_OFFSET = [self.statechart.app.game_screen.center_x - (LEVEL_WIDTH / 2) * BRICK_WIDTH, self.statechart.app.game_screen.height / 12.5]

                    # [statechart port] Now have a select_level action function in ShowingLevelsPopup that plays the select sound, then go_to_state ShowingLevel
                    # i have to check if the function is called by a level button in the level popup OR with an int as argument:
                    #if not isinstance(level, int):
                    #    level = int(level.text)
                    #    # and if the function was called by a button, play a sound
                    #    self.statechart.app.sound['select'].play()

                    level = self.statechart.app.current_level

                    # try to load the level image
                    try:
                        # per https://github.com/stocyr/Deflectouch/commit/18d4cc2d98b922d932af9febc4fd9cb5d2fc3ee7,
                        # app directory added to path.
                        #self.level_image = kivy.core.image.Image.load('levels/level%02d.png' % level, keep_data=True)
                        self.level_image = kivy.core.image.Image.load(self.statechart.app.directory + '/levels/level%02d.png' % level, keep_data=True)
                    except Exception, e:
                        error_text = 'Unable to load Level %d!\n\nReason: %s' % (level, e)
                        Popup(title='Level loading error:', content=Label(text=error_text, font_size=18), size_hint=(0.3, 0.2)).open()
                        return

                    # [statechart port] Should the following bullet killing and deflector delecting
                    #                   sections be done? Originally was call to this code in reset_level(),
                    #                   which is now in enter_state of ShowingLevel state.
                    #
                    #    *** moved to exit_state ***

                    # The user begins with 3 lives:
                    self.statechart.app.lives = 3

                    for obstacle in self.statechart.app.obstacle_list:
                        self.statechart.app.game_screen.background.remove_widget(obstacle)
                    self.statechart.app.obstacle_list = []

                    for goal in self.statechart.app.goal_list:
                        self.statechart.app.game_screen.background.remove_widget(goal)
                    self.statechart.app.goal_list = []

                    # set level initial state
                    self.statechart.app.lives = 3
                    self.statechart.app.level = level

                    for y in range(LEVEL_HEIGHT, 0, -1):
                        for x in range(LEVEL_WIDTH):
                            color = self.level_image.read_pixel(x, y)
                            if len(color) > 3:
                                # if there was transparency stored in the image, cut it.
                                color.pop()

                            if color == [0, 0, 0]:
                                # create obstacle brick on white pixels
                                image = Image(source=('graphics/brick%d.png' % randint(1, 4)),
                                              x = LEVEL_OFFSET[0] + x * BRICK_WIDTH,
                                              y = LEVEL_OFFSET[1] + (y - 1) * BRICK_WIDTH,
                                              size = (BRICK_WIDTH, BRICK_WIDTH),
                                              allow_stretch = True)
                                self.statechart.app.obstacle_list.append(image)
                                # These two lines were commented out in the original:
                                # the actual widget adding is done in build_level()
                                #self.statechart.app.game_screen.background.add_widget(image)

                            elif color == [0, 0, 1]:
                                # create a goal brick on blue pixels
                                image = Image(source=('graphics/goal%d.png' % randint(1, 4)),
                                              x = LEVEL_OFFSET[0] + x * BRICK_WIDTH,
                                              y = LEVEL_OFFSET[1] + (y - 1) * BRICK_WIDTH,
                                              size = (BRICK_WIDTH, BRICK_WIDTH),
                                              allow_stretch = True)
                                self.statechart.app.goal_list.append(image)
                                # These two lines were commented out in the original:
                                # the actual widget adding is done in build_level()
                                #self.statechart.app.game_screen.background.add_widget(image)

                    # now start to build up the level:
                    self.statechart.app.level_build_index = 0
                    if len(self.statechart.app.obstacle_list) != 0:
                        Clock.schedule_interval(self.build_level, 0.01)

                def build_level(self, instance):
                    #if self.statechart.app.level_build_index % int(0.02 / (0.5 / (len(self.statechart.app.obstacle_list) + len(self.statechart.app.goal_list)))) == 0:
                    # play a sound every now and then:
                    self.statechart.app.sound['beep'].play()

                    if self.statechart.app.level_build_index < len(self.statechart.app.obstacle_list):
                        self.statechart.app.game_screen.background.add_widget(self.statechart.app.obstacle_list[self.statechart.app.level_build_index])
                    else:
                        if self.statechart.app.level_build_index - len(self.statechart.app.obstacle_list) != len(self.statechart.app.goal_list):
                            self.statechart.app.game_screen.background.add_widget(self.statechart.app.goal_list[self.statechart.app.level_build_index - len(self.statechart.app.obstacle_list)])
                        else:
                            # we're done. Disable the schedule
                            return False
                    self.statechart.app.level_build_index += 1

                def exit_state(self, context):
                    print 'ShowingLevel/exit_state'

                    self.statechart.app.game_screen.remove_widget(self.statechart.app.stockbar)
                    self.statechart.app.stockbar = None

                    self.delete_all_deflectors()

                def delete_all_deflectors(self):
                    for deflector in self.statechart.app.deflector_list:
                        self.statechart.app.game_screen.remove_widget(deflector)

                    self.statechart.app.deflector_list = []

                    self.go_to_state('ShowingBackground')

                # ShowingBackground == ShowingBackground
                #
                class ShowingBackground(State):
                    def __init__(self, **kwargs):
                        kwargs['initial_substate_key'] = 'ShowingStockbar'
                        super(AppStatechart.
                              RootState.
                              ShowingGameScreen.
                              ShowingLevel.
                              ShowingBackground, self).__init__(**kwargs)

                    def enter_state(self, context=None):
                        print 'ShowingBackground/enter_state'

                    def exit_state(self, context=None):
                        print 'ShowingBackground/exit_state'

                    def fire(self, *args):
                        # If there is already a bullet existing (which means
                        # its flying around or exploding somewhere) don't fire.
                        if self.statechart.app.bullet is None:
                            self.go_to_state('BulletMoving')

                    def show_levels(self, *args):
                        self.statechart.app.sound['switch'].play()
                        self.go_to_state('ShowingLevelsPopup')

                    def show_settings(self, *args):
                        self.statechart.app.sound['switch'].play()
                        self.go_to_state('ShowingSettingsPopup')

                    def show_help(self, *args):
                        self.go_to_state('ShowingHelpPopup')

                    def stop(self, *args):
                        self.statechart.app.stop()

                    # ShowingStockbar
                    #
                    class ShowingStockbar(State):
                        def __init__(self, **kwargs):
                            kwargs['initial_substate_key'] = 'WaitingForTouches'
                            super(AppStatechart.
                                  RootState.
                                  ShowingGameScreen.
                                  ShowingLevel.
                                  ShowingBackground.
                                  ShowingStockbar, self).__init__(**kwargs)

                        def enter_state(self, context=None):
                            print 'ShowingStockbar/enter_state'

                            if self.statechart.app.stockbar is None:
                                self.statechart.app.max_stock = 0

                                # in the lowermost row there is also stored the value for the maximum stock
                                for x in range(LEVEL_WIDTH):
                                    # Original deflectouch has x,0 here, but Kivy changed a fundamental thing about
                                    # images -- it used to flip images, but now it only flips the gl co-ordinates.
                                    color = self.parent_state.parent_state.level_image.read_pixel(x, LEVEL_HEIGHT)
                                    color = [int(c) for c in color]
                                    if len(color) > 3:
                                        # if there was transparency stored in the image, cut it.
                                        color.pop()
                                    if color == [1, 0, 0]:
                                        self.statechart.app.max_stock += 1

                                # now i set up the stockbar widget:
                                self.statechart.app.max_stock = self.statechart.app.max_stock * self.statechart.app.game_screen.width / 1.4 / LEVEL_WIDTH

                                self.statechart.app.stockbar = Stockbar(max_stock=self.statechart.app.max_stock,
                                                         x=self.statechart.app.game_screen.center_x - self.statechart.app.max_stock / 2,
                                                         center_y=self.statechart.app.game_screen.height / 16 + 20)

                                self.statechart.app.game_screen.add_widget(self.statechart.app.stockbar)

                        def exit_state(self, context=None):
                            print 'ShowingStockbar/exit_state'

                        # WaitingForTouches
                        #
                        class WaitingForTouches(State):
                            touches = ListProperty([])

                            def __init__(self, **kwargs):
                                super(AppStatechart.
                                      RootState.
                                      ShowingGameScreen.
                                      ShowingLevel.
                                      ShowingBackground.
                                      ShowingStockbar.
                                      WaitingForTouches, self).__init__(**kwargs)

                            def enter_state(self, context=None):
                                print 'WaitingForTouches/enter_state'

                                self.recalculate_stockbar()

                            def exit_state(self, context=None):
                                print 'WaitingForTouches/exit_state'

                            def recalculate_stockbar(self):
                                # done every time a deflector size is changing
                                # first sum up all the deflectors on screen
                                length_sum = 0

                                if not len(self.statechart.app.deflector_list) == 0:
                                    for deflector in self.statechart.app.deflector_list:
                                        length_sum += deflector.length

                                self.statechart.app.stockbar.width = self.statechart.app.max_stock - length_sum

                                if self.statechart.app.stockbar.width < MIN_DEFLECTOR_LENGTH:
                                    # if the stock material doesn't suffice for a new deflector, disable new deflectors
                                    self.statechart.app.stockbar.source = 'graphics/deflector_red.png'
                                    self.statechart.app.new_deflectors_allowed = False
                                elif self.statechart.app.stockbar.width <= 0:
                                    # if all the stock material was used up, disable new deflectors
                                    self.statechart.app.new_deflectors_allowed = False
                                else:
                                    self.statechart.app.stockbar.source = 'graphics/deflector_blue.png'
                                    self.statechart.app.new_deflectors_allowed = True

                                print 'MIN_DEFLECTOR_LENGTH', MIN_DEFLECTOR_LENGTH
                                print 'recalculated: stockbar.width, new_deflectors_allowed, stockbar.source', self.statechart.app.stockbar.width, self.statechart.app.new_deflectors_allowed, self.statechart.app.stockbar.source

                                if self.statechart.app.current_deflector_and_vector is not None:
                                    deflector,deflector_vector = self.statechart.app.current_deflector_and_vector

                                    # get the current stock from the root widget:
                                    current_stock = self.statechart.app.stockbar.width
                                    stock_for_deflector = current_stock + deflector.length

                                    # now set the limitation for scaling:
                                    deflector.scale_max = stock_for_deflector / deflector.length_origin

                                    if deflector.length < MIN_DEFLECTOR_LENGTH:
                                        deflector.point1.color = (1, 0, 0, 1)
                                        deflector.point2.color = (1, 0, 0, 1)
                                    else:
                                        deflector.point1.color = (0, 0, 1, 1)
                                        deflector.point2.color = (0, 0, 1, 1)

                                    self.statechart.app.current_deflector_and_vector = None

                            @State.event_handler(['background_touch_down', 'background_touch_up'])
                            def analyze_touches(self, event, touch, context):
                                print 'analyze_touches'
                                user_data = touch.ud

                                # if a bullet has been fired and is flying now, don't allow ANY change!
                                if self.statechart.app.bullet is None:
                                    # if i didn't wanted to move / scale a deflector and but rather create a new one:
                                    # search for other 'lonely' touches
                                    creating_new_deflector = False
                                    #for search_touch in EventLoop.touches[:]:
                                    # Not sure why, but EventLoop.touches is getting reset, so making a
                                    # local self.touches ListProperty to contain touches.
                                    for search_touch in self.touches:
                                        if 'lonely' in search_touch.ud:
                                            print 'lonely'
                                            self.touches.remove(search_touch)
                                            #del search_touch.ud['lonely']
                                            # so here we have a second touch: try to create a deflector:
                                            if self.statechart.app.new_deflectors_allowed is True:
                                                length = Vector(search_touch.pos).distance(touch.pos)
                                                print 'MIN_DEFLECTOR_LENGTH', MIN_DEFLECTOR_LENGTH
                                                print 'length =', length
                                                # create only a new one if he's not too big and not too small
                                                print self.statechart.app.stockbar.width
                                                if MIN_DEFLECTOR_LENGTH <= length <= self.statechart.app.stockbar.width:
                                                    self.statechart.app.new_deflector_touch1 = touch
                                                    self.statechart.app.new_deflector_touch2 = search_touch
                                                    self.statechart.app.new_deflector_length = length
                                                    creating_new_deflector = True

                                    if creating_new_deflector == True:
                                        self.go_to_state('CreatingDeflector')
                                    else:
                                        # no second touch was found: tag the current one as a 'lonely' touch
                                        touch.ud['lonely'] = True
                                        self.touches.append(touch)
                                        self.statechart.app.sound['no_deflector'].play()

                            def resize_deflector(self, deflector, size):
                                print 'resize_deflector'

                                # problem: if the points are resized (scatter resized them, kv-rule resized them back),
                                # their center isn't on the touch point anymore.
                                deflector.point1.pos = deflector.point_pos_origin[0] + (40 - size[0])/2, deflector.point_pos_origin[1] + (40 - size[0])/2
                                deflector.point2.pos = deflector.point_pos_origin[2] + (40 - size[0])/2, deflector.point_pos_origin[3] + (40 - size[0])/2

                                # feedback to the stockbar: reducing of the deflector material stock:
                                #deflector.length = Vector(deflector.touch1.pos).distance(deflector.touch2.pos)
                                print 'deflector.length_origin', deflector.length_origin
                                print 'deflector.scale', deflector.scale
                                deflector.length = deflector.length_origin * deflector.scale

                                deflector_point1 = Vector(deflector.to_parent(deflector.point1.center[0], deflector.point1.center[1]))
                                deflector_point2 = Vector(deflector.to_parent(deflector.point2.center[0], deflector.point2.center[1]))

                                deflector_vector = Vector(deflector_point2 - deflector_point1)

                                self.statechart.app.current_deflector_and_vector = (deflector, deflector_vector)

                                self.recalculate_stockbar()

                            def deflector_touch_down(self, deflector, context):
                                print 'deflector_touch_down'
                                if self.statechart.app.sound['deflector_touch_down'].status != 'play':
                                    self.statechart.app.sound['deflector_touch_down'].play()

                            def deflector_touch_up(self, deflector, context):
                                print 'deflector_touch_up'
                                if self.statechart.app.sound['deflector_touch_up'].status != 'play':
                                    self.statechart.app.sound['deflector_touch_up'].play()

                                print 'deflector.length', deflector.length
                                print 'MIN_DEFLECTOR_LENGTH', MIN_DEFLECTOR_LENGTH
                                if deflector.length < MIN_DEFLECTOR_LENGTH and deflector.parent != None:
                                    self.statechart.app.current_deflector_and_vector = (deflector, None)
                                    self.statechart.go_to_state('DeletingDeflector')

                                self.go_to_state('ShowingStockbar')

                # CreatingDeflector (transient)
                #
                class CreatingDeflector(State):
                    def __init__(self, **kwargs):
                        super(AppStatechart.
                              RootState.
                              ShowingGameScreen.
                              ShowingLevel.
                              CreatingDeflector, self).__init__(**kwargs)

                    def enter_state(self, context=None):
                        print 'CreatingDeflector/enter_state'
                        self.statechart.app.sound['deflector_new'].play()

                        deflector = Deflector(statechart=self.statechart,
                                              touch1=self.statechart.app.new_deflector_touch1,
                                              touch2=self.statechart.app.new_deflector_touch2,
                                              length=self.statechart.app.new_deflector_length)

                        self.statechart.app.deflector_list.append(deflector)
                        self.statechart.app.game_screen.add_widget(deflector)

                        self.statechart.app.stockbar.width -= self.statechart.app.new_deflector_length

                        print 'have new deflector', deflector
                        print 'new stockbar width', self.statechart.app.stockbar.width

                        self.statechart.app.new_deflector_touch1 = None
                        self.statechart.app.new_deflector_touch2 = None
                        self.statechart.app.new_deflector_length = 0

                        self.go_to_state('ShowingBackground')

                    def exit_state(self, context=None):
                        print 'CreatingDeflector/exit_state'


                # DeletingDeflector (transient)
                #
                class DeletingDeflector(State):
                    def __init__(self, **kwargs):
                        super(AppStatechart.
                              RootState.
                              ShowingGameScreen.
                              ShowingLevel.
                              DeletingDeflector, self).__init__(**kwargs)

                    def enter_state(self, context=None):
                        print 'DeletingDeflector/enter_state'
                        self.deflector,self.deflector_vector = self.statechart.app.current_deflector_and_vector

                        self.statechart.app.sound['deflector_delete'].play()
                        self.deflector_deleted(deflector.length)

                        self.statechart.app.game_screen.remove_widget(deflector)
                        self.statechart.app.deflector_list.remove(deflector)

                        self.go_to_state('ShowingBackground')

                    def exit_state(self, context=None):
                        print 'DeletingDeflector/exit_state'

                    #@State.event_handler(['delete_deflector'])
                    #def delete_deflector_handler(self, event, deflector, context):
                        #self.statechart.app.sound['deflector_delete'].play()
                        #self.deflector_deleted(deflector.length)

                        #self.statechart.app.game_screen.remove_widget(deflector)
                        #self.statechart.app.deflector_list.remove(deflector)

                    def deflector_deleted(self, length):
                        self.statechart.app.stockbar.width += length

                # BulletMoving
                #
                class BulletMoving(State):
                    def __init__(self, **kwargs):
                        kwargs['initial_substate_key'] = 'EstablishingTrajectory'
                        super(AppStatechart.
                              RootState.
                              ShowingGameScreen.
                              ShowingLevel.
                              BulletMoving, self).__init__(**kwargs)

                    def enter_state(self, context=None):
                        print 'BulletMoving/enter_state'
                        self.statechart.app.sound['bullet_start'].play()
                        self.statechart.app.bullet = Bullet()
                        self.statechart.app.game_screen.add_widget(self.statechart.app.bullet)

                    def exit_state(self, context=None):
                        print 'BulletMoving/exit_state'
                        self.statechart.app.game_screen.remove_widget(self.statechart.app.bullet)
                        self.statechart.app.bullet = None

                    # EstablishingTrajectory (transient state)
                    #
                    class EstablishingTrajectory(State):
                        def __init__(self, **kwargs):
                            super(AppStatechart.RootState.ShowingGameScreen.ShowingLevel.BulletMoving.EstablishingTrajectory, self).__init__(**kwargs)

                        def enter_state(self, context=None):
                            print 'EstablishingTrajectory/enter_state'
                            # Calculate bullet start position.
                            tower_angle = radians(self.statechart.app.game_screen.tank.tank_tower_scatter.rotation)
                            tower_position = self.statechart.app.game_screen.tank.pos
                            bullet_position = (tower_position[0] + 48 + cos(tower_angle) * 130, tower_position[1] + 70 + sin(tower_angle) * 130)

                            self.statechart.app.bullet.angle = tower_angle
                            self.statechart.app.bullet.center = bullet_position

                            self.statechart.go_to_state('OnTrajectory')

                        def exit_state(self, context=None):
                            print 'EstablishingTrajectory/exit_state'

                    # ChangingTrajectory (transient state)
                    #
                    class ChangingTrajectory(State):
                        deflector_vector = None

                        def __init__(self, **kwargs):
                            super(AppStatechart.
                                  RootState.
                                  ShowingGameScreen.
                                  ShowingLevel.
                                  BulletMoving.
                                  ChangingTrajectory, self).__init__(**kwargs)

                        def enter_state(self, context=None):
                            print 'ChangingTrajectory/enter_state'

                            self.deflector,self.deflector_vector = self.statechart.app.current_deflector_and_vector

                            # calculate deflection angle
                            impact_angle = (radians(self.deflector_vector.angle(Vector(1, 0))) % pi) - (self.statechart.app.bullet.angle % pi)
                            self.statechart.app.bullet.angle = (self.statechart.app.bullet.angle + 2 * impact_angle) % (2 * pi)

                            self.statechart.go_to_state('OnTrajectory')

                        def exit_state(self, context=None):
                            print 'ChangingTrajectory/exit_state'

                    # OnTrajectory
                    #
                    class OnTrajectory(State):
                        bullet_animation = None

                        def __init__(self, **kwargs):
                            super(AppStatechart.
                                  RootState.
                                  ShowingGameScreen.
                                  ShowingLevel.
                                  BulletMoving.
                                  OnTrajectory, self).__init__(**kwargs)

                        def enter_state(self, context=None):
                            print 'OnTrajectory/enter_state'

                            # start the animation
                            destination = self.calc_bullet_destination_at_edge(self.statechart.app.bullet.angle)
                            speed = boundary(self.statechart.app.config.getint('GamePlay', 'BulletSpeed'), 1, 10)

                            self.bullet_animation = self.create_bullet_animation(speed, destination)

                            self.bullet_animation.start(self.statechart.app.bullet)
                            self.bullet_animation.bind(on_complete=self.collide_with_edge)

                            # start to track the position changes
                            self.statechart.app.bullet.bind(pos=self.bullet_pos_callback)

                        def exit_state(self, context=None):
                            print 'OnTrajectory/exit_state'
                            self.statechart.app.bullet.unbind(pos=self.bullet_pos_callback)
                            self.bullet_animation.unbind(on_complete=self.collide_with_edge)
                            self.bullet_animation.stop(self.statechart.app.bullet)

                        def create_bullet_animation(self, speed, destination):
                            # create the animation
                            # t = s/v -> v from 1 to 10 / unit-less
                            # NOTE: THE DIFFERENCE BETWEEN TWO RENDERED ANIMATION STEPS
                            # MUST *NOT* EXCESS THE RADIUS OF THE BULLET! OTHERWISE I
                            # HAVE PROBLEMS DETECTING A COLLISION WITH A DEFLECTOR!!
                            time = Vector(self.statechart.app.bullet.center).distance(destination) / (speed * 30)
                            return Animation(pos=destination, duration=time)

                        def calc_bullet_destination_at_edge(self, angle):
                            # calculate the path until the bullet hits the edge of the screen
                            win = self.statechart.app.bullet.get_parent_window()
                            left = 150.0 * win.width / 1920.0
                            right = win.width - 236.0 * win.width / 1920.0
                            top = win.height - 50.0 * win.height / 1920.0
                            bottom = 96.0 * win.height / 1920.0

                            bullet_x_to_right = right - self.statechart.app.bullet.center_x
                            bullet_x_to_left = left - self.statechart.app.bullet.center_x
                            bullet_y_to_top = top - self.statechart.app.bullet.center_y
                            bullet_y_to_bottom = bottom - self.statechart.app.bullet.center_y

                            destination_x = 0
                            destination_y = 0

                            # this is a little bit ugly, but i couldn't find a nicer way in the hurry
                            if 0 <= self.statechart.app.bullet.angle < pi / 2:
                                # 1st quadrant
                                if self.statechart.app.bullet.angle == 0:
                                    destination_x = bullet_x_to_right
                                    destination_y = 0
                                else:
                                    destination_x = boundary(bullet_y_to_top / tan(self.statechart.app.bullet.angle), bullet_x_to_left, bullet_x_to_right)
                                    destination_y = boundary(tan(self.statechart.app.bullet.angle) * bullet_x_to_right, bullet_y_to_bottom, bullet_y_to_top)

                            elif pi / 2 <= self.statechart.app.bullet.angle < pi:
                                # 2nd quadrant
                                if self.statechart.app.bullet.angle == pi / 2:
                                    destination_x = 0
                                    destination_y = bullet_y_to_top
                                else:
                                    destination_x = boundary(bullet_y_to_top / tan(self.statechart.app.bullet.angle), bullet_x_to_left, bullet_x_to_right)
                                    destination_y = boundary(tan(self.statechart.app.bullet.angle) * bullet_x_to_left, bullet_y_to_bottom, bullet_y_to_top)

                            elif pi <= self.statechart.app.bullet.angle < 3 * pi / 2:
                                # 3rd quadrant
                                if self.statechart.app.bullet.angle == pi:
                                    destination_x = bullet_x_to_left
                                    destination_y = 0
                                else:
                                    destination_x = boundary(bullet_y_to_bottom / tan(self.statechart.app.bullet.angle), bullet_x_to_left, bullet_x_to_right)
                                    destination_y = boundary(tan(self.statechart.app.bullet.angle) * bullet_x_to_left, bullet_y_to_bottom, bullet_y_to_top)

                            elif self.statechart.app.bullet.angle >= 3 * pi / 2:
                                # 4th quadrant
                                if self.statechart.app.bullet.angle == 3 * pi / 2:
                                    destination_x = 0
                                    destination_y = bullet_y_to_bottom
                                else:
                                    destination_x = boundary(bullet_y_to_bottom / tan(self.statechart.app.bullet.angle), bullet_x_to_left, bullet_x_to_right)
                                    destination_y = boundary(tan(self.statechart.app.bullet.angle) * bullet_x_to_right, bullet_y_to_bottom, bullet_y_to_top)

                            # because all of the calculations above were relative, add the bullet position to it.
                            destination_x += self.statechart.app.bullet.center_x
                            destination_y += self.statechart.app.bullet.center_y

                            return (destination_x, destination_y)

                        def check_deflector_collision(self, deflector):
                            # Here we have a collision Bullet <--> Deflector-bounding-box. But that doesn't mean
                            # that there's a collision with the deflector LINE yet. So here's some math stuff
                            # for the freaks :) It includes vector calculations, distance problems and trigonometry

                            # first thing to do is: we need a vector describing the bullet. Length isn't important.
                            bullet_position = Vector(self.statechart.app.bullet.center)
                            bullet_direction = Vector(1, 0).rotate(self.statechart.app.bullet.angle * 360 / (2 * pi))
                            deflector_point1 = Vector(deflector.to_parent(deflector.point1.center[0], deflector.point1.center[1]))
                            deflector_point2 = Vector(deflector.to_parent(deflector.point2.center[0], deflector.point2.center[1]))

                            # then we need a vector describing the deflector line.
                            deflector_vector = Vector(deflector_point2 - deflector_point1)

                            # now we do a line intersection with the deflector line:
                            intersection = Vector.line_intersection(bullet_position, bullet_position + bullet_direction, deflector_point1, deflector_point2)

                            # now we want to proof if the bullet comes from the 'right' side.
                            # Because it's possible that the bullet is colliding with the deflectors bounding box but
                            # would miss / has already missed the deflector line.
                            # We do that by checking if the expected intersection point is BEHIND the bullet position.
                            # ('behind' means the bullets direction vector points AWAY from the vector
                            # [bullet -> intersection]. That also means the angle between these two vectors is not 0
                            # -> due to some math-engine-internal inaccuracies, i have to check if the angle is greater than one:
                            if abs(bullet_direction.angle(intersection - bullet_position)) > 1:
                                # if the bullet missed the line already - NO COLLISION
                                return False

                            # now we finally check if the bullet is close enough to the deflector line:
                            distance = abs(sin(radians(bullet_direction.angle(deflector_vector)) % (pi / 2))) * Vector(intersection - bullet_position).length()
                            if distance < (self.statechart.app.bullet.width / 2):
                                self.collide_with_deflector(deflector, deflector_vector)

                        def bullet_pos_callback(self, instance, pos):
                            if self.statechart.app.bullet is None:
                                return

                            # check here if the bullet collides with a deflector, an obstacle or the goal
                            # (edge collision detection is irrelevant - the edge is where the bullet animation ends
                            # and therefor a callback is raised then)

                            # first check if there's a collision with deflectors:
                            if not len(self.statechart.app.deflector_list) == 0:
                                for deflector in self.statechart.app.deflector_list:
                                    if deflector.collide_widget(self.statechart.app.bullet):
                                        self.check_deflector_collision(deflector)
                                        return

                            # [statechart port] Moved the check for obstacle before the check for goal.

                            # then check if there's a collision with obstacles:
                            if not len(self.statechart.app.obstacle_list) == 0:
                                for obstacle in self.statechart.app.obstacle_list:
                                    if self.statechart.app.bullet.collide_widget(obstacle):
                                        self.collide_with_obstacle()
                                        return

                            # then check if there's a collision with the goal:
                            if not len(self.statechart.app.goal_list) == 0:
                                for goal in self.statechart.app.goal_list:
                                    if self.statechart.app.bullet.collide_widget(goal):
                                        self.collide_with_goal()
                                        return

                        def collide_with_deflector(self, deflector, deflector_vector):
                            self.statechart.app.current_deflector_and_vector = (deflector, deflector_vector)
                            self.go_to_state('CollisionWithDeflector')

                        def collide_with_obstacle(self, *args):
                            print 'collide_with_obstacle'
                            self.go_to_state('CollisionWithObstacle')

                        def collide_with_edge(self, *args):
                            print 'collide_with_edge'
                            self.go_to_state('CollisionWithEdge')

                        def collide_with_goal(self, *args):
                            print 'collide_with_goal'
                            # [statechart port] Hopefully fixed by rearrangements.
                            # i still have some strange exceptions because of multiple function calls:
                            #if self.statechart.app.game_screen is None:
                                #return

                            #self.parent.level_accomplished()
                            self.go_to_state('CollisionWithGoal')

                    # Collision
                    #
                    class Collision(State):
                        bullet_exploding_animation = None

                        def __init__(self, **kwargs):
                            super(AppStatechart.
                                  RootState.
                                  ShowingGameScreen.
                                  ShowingLevel.
                                  BulletMoving.
                                  Collision, self).__init__(**kwargs)

                        def enter_state(self, context=None):
                            print 'Collision/enter_state'
                            self.statechart.app.sound['explosion'].play()

                        def exit_state(self, context=None):
                            print 'Collision/exit_state'

                        # [statechart port] The solution used here for CollisionWithObject and substates
                        #                   CollisionWithEdge and CollisionWithObstacle, is to have these
                        #                   substates as transient substates that decide whether there
                        #                   are lives left to keep_playing_level() or, if not, to
                        #                   reset_level().
                        #
                        #                   Alternatively, through a subclassing scheme, one could have
                        #                   two states, CollisionWithEdge(CollisionWithObject) and
                        #                   CollisionWithObstacle(CollisionWithObject), that through a
                        #                   combination of method overriding could accomplish the same
                        #                   thing, no? Merits?

                        # CollisionWithObject
                        #
                        class CollisionWithObject(State):
                            def __init__(self, **kwargs):
                                super(AppStatechart.
                                      RootState.
                                      ShowingGameScreen.
                                      ShowingLevel.
                                      BulletMoving.
                                      Collision.
                                      CollisionWithObject, self).__init__(**kwargs)

                            def enter_state(self, context=None):
                                print 'CollisionWithObject/enter_state'
                                self.statechart.app.lives -= 1

                            def exit_state(self, context=None):
                                print 'CollisionWithObject/exit_state'

                            # CollisionWithObjectState(transient state)
                            #
                            class CollisionWithObjectState(State):
                                def __init__(self, **kwargs):
                                    super(AppStatechart.
                                          RootState.
                                          ShowingGameScreen.
                                          ShowingLevel.
                                          BulletMoving.
                                          Collision.
                                          CollisionWithObject.
                                          CollisionWithObjectState, self).__init__(**kwargs)

                                def enter_state(self, context=None):
                                    print 'CollisionWithObjectState/enter_state'
                                    # [statechart port] These should call statechart.send_event('some_action'),
                                    #                   and not self.parent_state.some_action() directly, in this
                                    #                   case, because we want the statechart machinery to figure
                                    #                   out the sequence of state transitions that should happen
                                    #                   for the action in the current context.
                                    #
                                    # Ah, but, there could be a problem with state transitions fired within an
                                    # enter_state() firing immediately.
                                    #
                                    if self.statechart.app.lives == 0:
                                        #self.statechart.send_event('reset_level')
                                        self.reset_level()
                                    else:
                                        #self.statechart.send_event('keep_playing_level')
                                        self.keep_playing_level()

                                def reset_level(self, *args):
                                    #self.go_to_state('ResettingLevel')
                                    self.go_to_state('ShowingGameScreen')

                                def keep_playing_level(self, *args):
                                    self.go_to_state('ShowingBackground')

                            # CollisionWithEdge (transient state)
                            #
                            class CollisionWithEdge(CollisionWithObjectState):
                                pass

                            # CollisionWithObstacle (transient state)
                            #
                            class CollisionWithObstacle(CollisionWithObjectState):
                                pass

                        # CollisionWithDeflector (transient state)
                        #
                        class CollisionWithDeflector(State):
                            deflector = None

                            def __init__(self, **kwargs):
                                super(AppStatechart.
                                      RootState.
                                      ShowingGameScreen.
                                      ShowingLevel.
                                      BulletMoving.
                                      Collision.
                                      CollisionWithDeflector, self).__init__(**kwargs)

                            def enter_state(self, context=None):
                                print 'CollisionWithDeflector/enter_state'
                                self.statechart.app.sound['deflection'].play()

                                self.deflector,self.deflector_vector = self.statechart.app.current_deflector_and_vector

                                self.flash_deflector()

                                # [statechart port] See note below about send_event() vs. direct call.
                                #self.statechart.send_event('change_trajectory')
                                self.change_trajectory()

                            def flash_deflector(self, *args):
                                # flash up the deflector
                                Animation.stop_all(self.deflector.point1, 'color')
                                Animation.stop_all(self.deflector.point2, 'color')
                                self.deflector.point1.color = (1, 1, 1, 1)
                                self.deflector.point2.color = (1, 1, 1, 1)
                                animation = Animation(color=(0, 0, 1, 1), duration=3, t='out_expo')
                                animation.start(self.deflector.point1)
                                animation.start(self.deflector.point2)

                            def exit_state(self, context=None):
                                print 'CollisionWithDeflector/exit_state'

                                # Do not remove the bullet widget nor set bullet = None here.
                                # (Bullet only changes trajectory).

                            def change_trajectory(self, *args):
                                self.go_to_state('ChangingTrajectory')

                        # CollisionWithGoal (transient state)
                        #
                        class CollisionWithGoal(State):
                            def __init__(self, **kwargs):
                                super(AppStatechart.
                                      RootState.
                                      ShowingGameScreen.
                                      ShowingLevel.
                                      BulletMoving.
                                      Collision.
                                      CollisionWithGoal, self).__init__(**kwargs)

                            def enter_state(self, context=None):
                                print 'CollisionWithGoal/enter_state'

                                # [statechart port] Direct call to self.show_level_accomplished() OK here?
                                #                   Or is it a bad habit to ever call go_to_state() from
                                #                   enter_state() or exit_state()? Efficiency of action lookup
                                #                   a factor, no? Could show_level_accomplished() live in
                                #
                                #self.statechart.send_event('show_level_accomplished')
                                self.show_level_accomplished()

                            def exit_state(self, context=None):
                                print 'CollisionWithObject/exit_state'

                            def show_level_accomplished(self, *args):
                                self.go_to_state('ShowingLevelAccomplished')


class GameScreen(Widget):
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)


Factory.register("Tank", Tank)
Factory.register("Background", Background)
Factory.register("Stockbar", Stockbar)


class Deflectouch(App):
    game_screen = ObjectProperty(None)

    title = 'Deflectouch'
    icon = 'icon.png'

    version = StringProperty(VERSION)
    level = NumericProperty(1)
    lives = NumericProperty(3)

    bullet = None

    deflector_list = []
    obstacle_list = []
    goal_list = []

    stockbar = None
    max_stock = 0

    new_deflectors_allowed = True
    new_deflector_touch1 = None
    new_deflector_touch2 = None
    new_deflector_length = 0

    level_build_index = 0

    sound = {}
    music = None

    # [statechart port] These are akin to object controllers linked to
    #                   list controllers. Maybe this should be formalized
    #                   with new class types?
    current_level = NumericProperty(0)
    current_deflector_and_vector = None

    def build(self):
        # print the application informations
        print '\nDeflectouch v%s  Copyright (C) 2012  Cyril Stoller' % VERSION
        print 'This program comes with ABSOLUTELY NO WARRANTY'
        print 'This is free software, and you are welcome to redistribute it'
        print 'under certain conditions; see the source code for details.\n'

        # create the root widget and give it a reference of the application instance (so it can access the application settings)
        self.root = GameScreen(app=self)
        self.game_screen = self.root

    def build_config(self, config):
        config.adddefaultsection('General')
        config.setdefault('General', 'Music', '40')
        config.setdefault('General', 'Sound', '100')
        config.setdefault('General', 'FirstStartup', 'Yes')

        config.adddefaultsection('GamePlay')
        config.setdefault('GamePlay', 'BulletSpeed', '10')
        config.setdefault('GamePlay', 'Levels', '0000000000000000000000000000000000000000')

    def on_start(self):
        self.statechart = AppStatechart(app=self)
        self.statechart.init_statechart()

if __name__ in ('__main__', '__android__'):
    Deflectouch().run()
