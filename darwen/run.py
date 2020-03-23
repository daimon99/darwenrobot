#!/usr/bin/env python3
"""
戴成功送药机器人
v1.0
@Darwen
"""

import io
import json
import sys
import time
from enum import Enum

import anki_vector
from anki_vector import annotate
from anki_vector import util
from lib import flask_helpers

try:
    from flask import Flask, request, render_template
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install --user flask` to install")

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


def create_default_image(image_width, image_height, do_gradient=False):
    """Create a place-holder PIL image to use until we have a live feed from Vector"""
    image_bytes = bytearray([0x70, 0x70, 0x70]) * image_width * image_height

    if do_gradient:
        i = 0
        for y in range(image_height):
            for x in range(image_width):
                image_bytes[i] = int(255.0 * (x / image_width))  # R
                image_bytes[i + 1] = int(255.0 * (y / image_height))  # G
                image_bytes[i + 2] = 0  # B
                i += 3

    image = Image.frombytes('RGB', (image_width, image_height), bytes(image_bytes))
    return image


flask_app = Flask(__name__)
_default_camera_image = create_default_image(320, 240)
_is_mouse_look_enabled_by_default = False


def remap_to_range(x, x_min, x_max, out_min, out_max):
    """convert x (in x_min..x_max range) to out_min..out_max range"""
    if x < x_min:
        return out_min
    if x > x_max:
        return out_max
    ratio = (x - x_min) / (x_max - x_min)
    return out_min + ratio * (out_max - out_min)


class DebugAnnotations(Enum):
    DISABLED = 0
    ENABLED_VISION = 1
    ENABLED_ALL = 2


class RemoteControlVector:

    def __init__(self, robot):
        self.vector = robot

        # don't send motor messages if it matches the last setting
        self.last_lift = None
        self.last_head = None
        self.last_wheels = None

        self.drive_forwards = 0
        self.drive_back = 0
        self.turn_left = 0
        self.turn_right = 0
        self.lift_up = 0
        self.lift_down = 0
        self.head_up = 0
        self.head_down = 0

        self.go_fast = 0
        self.go_slow = 0

        self.is_mouse_look_enabled = _is_mouse_look_enabled_by_default
        self.mouse_dir = 0

        self.action_queue = []
        self.text_to_say = "Hi I'm Vector"

    def handle_mouse(self, mouse_x, mouse_y):
        """Called whenever mouse moves
            mouse_x, mouse_y are in in 0..1 range (0,0 = top left, 1,1 = bottom right of window)
        """
        if self.is_mouse_look_enabled:
            mouse_sensitivity = 1.5  # higher = more twitchy
            self.mouse_dir = remap_to_range(mouse_x, 0.0, 1.0, -mouse_sensitivity, mouse_sensitivity)
            self.update_mouse_driving()

            desired_head_angle = remap_to_range(mouse_y, 0.0, 1.0, 45, -25)
            head_angle_delta = desired_head_angle - util.radians(self.vector.head_angle_rad).degrees
            head_vel = head_angle_delta * 0.03
            if self.last_head and head_vel == self.last_head:
                return
            self.last_head = head_vel
            self.vector.motors.set_head_motor(head_vel)

    def set_mouse_look_enabled(self, is_mouse_look_enabled):
        was_mouse_look_enabled = self.is_mouse_look_enabled
        self.is_mouse_look_enabled = is_mouse_look_enabled
        if not is_mouse_look_enabled:
            # cancel any current mouse-look turning
            self.mouse_dir = 0
            if was_mouse_look_enabled:
                self.update_mouse_driving()
                self.update_head()

    def update_drive_state(self, key_code, is_key_down, speed_changed):
        """Update state of driving intent from keyboard, and if anything changed then call update_driving"""
        update_driving = True
        if key_code == ord('W'):
            self.drive_forwards = is_key_down
        elif key_code == ord('S'):
            self.drive_back = is_key_down
        elif key_code == ord('A'):
            self.turn_left = is_key_down
        elif key_code == ord('D'):
            self.turn_right = is_key_down
        else:
            if not speed_changed:
                update_driving = False
        return update_driving

    def update_lift_state(self, key_code, is_key_down, speed_changed):
        """Update state of lift move intent from keyboard, and if anything changed then call update_lift"""
        update_lift = True
        if key_code == ord('R'):
            self.lift_up = is_key_down
        elif key_code == ord('F'):
            self.lift_down = is_key_down
        else:
            if not speed_changed:
                update_lift = False
        return update_lift

    def update_head_state(self, key_code, is_key_down, speed_changed):
        """Update state of head move intent from keyboard, and if anything changed then call update_head"""
        update_head = True
        if key_code == ord('T'):
            self.head_up = is_key_down
        elif key_code == ord('G'):
            self.head_down = is_key_down
        else:
            if not speed_changed:
                update_head = False
        return update_head

    def handle_key(self, key_code, is_shift_down, is_alt_down, is_key_down):
        """Called on any key press or release
           Holding a key down may result in repeated handle_key calls with is_key_down==True
        """

        # Update desired speed / fidelity of actions based on shift/alt being held
        was_go_fast = self.go_fast
        was_go_slow = self.go_slow

        self.go_fast = is_shift_down
        self.go_slow = is_alt_down

        speed_changed = (was_go_fast != self.go_fast) or (was_go_slow != self.go_slow)

        update_driving = self.update_drive_state(key_code, is_key_down, speed_changed)

        update_lift = self.update_lift_state(key_code, is_key_down, speed_changed)

        update_head = self.update_head_state(key_code, is_key_down, speed_changed)

        # Update driving, head and lift as appropriate
        if update_driving:
            self.update_mouse_driving()
        if update_head:
            self.update_head()
        if update_lift:
            self.update_lift()

        # Handle any keys being released (e.g. the end of a key-click)
        if not is_key_down:
            if ord('9') >= key_code >= ord('0'):
                anim_name = self.key_code_to_anim_name(key_code)
                self.queue_action((self.vector.anim.play_animation, anim_name))
            elif key_code == ord(' '):
                self.queue_action((self.vector.behavior.say_text, self.text_to_say))
            elif key_code == ord('X'):
                self.queue_action((self.vector.anim.play_animation_trigger, self.selected_anim_trigger_name))

    def key_code_to_anim_name(self, key_code):
        key_num = key_code - ord('0')
        anim_num = self.anim_index_for_key[key_num]
        anim_name = self.anim_names[anim_num]
        return anim_name

    def func_to_name(self, func):
        if func == self.vector.behavior.say_text:
            return "say_text"
        if func == self.vector.anim.play_animation:
            return "play_anim"
        return "UNKNOWN"

    def action_to_text(self, action):
        func, args = action
        return self.func_to_name(func) + "( " + str(args) + " )"

    def action_queue_to_text(self, action_queue):
        out_text = ""
        i = 0
        for action in action_queue:
            out_text += "[" + str(i) + "] " + self.action_to_text(action)
            i += 1
        return out_text

    def queue_action(self, new_action):
        if len(self.action_queue) > 10:
            self.action_queue.pop(0)
        self.action_queue.append(new_action)

    def update(self):
        """Try and execute the next queued action"""
        if self.action_queue:
            queued_action, action_args = self.action_queue[0]
            if queued_action(action_args):
                self.action_queue.pop(0)

    def pick_speed(self, fast_speed, mid_speed, slow_speed):
        if self.go_fast:
            if not self.go_slow:
                return fast_speed
        elif self.go_slow:
            return slow_speed
        return mid_speed

    def update_lift(self):
        lift_speed = self.pick_speed(8, 4, 2)
        lift_vel = (self.lift_up - self.lift_down) * lift_speed
        if self.last_lift and lift_vel == self.last_lift:
            return
        self.last_lift = lift_vel
        self.vector.motors.set_lift_motor(lift_vel)

    def update_head(self):
        if not self.is_mouse_look_enabled:
            head_speed = self.pick_speed(2, 1, 0.5)
            head_vel = (self.head_up - self.head_down) * head_speed
            if self.last_head and head_vel == self.last_head:
                return
            self.last_head = head_vel
            self.vector.motors.set_head_motor(head_vel)

    def update_mouse_driving(self):
        drive_dir = (self.drive_forwards - self.drive_back)

        turn_dir = (self.turn_right - self.turn_left) + self.mouse_dir
        if drive_dir < 0:
            # It feels more natural to turn the opposite way when reversing
            turn_dir = -turn_dir

        forward_speed = self.pick_speed(150, 75, 50)
        turn_speed = self.pick_speed(100, 50, 30)

        l_wheel_speed = (drive_dir * forward_speed) + (turn_speed * turn_dir)
        r_wheel_speed = (drive_dir * forward_speed) - (turn_speed * turn_dir)

        wheel_params = (l_wheel_speed, r_wheel_speed, l_wheel_speed * 4, r_wheel_speed * 4)
        if self.last_wheels and wheel_params == self.last_wheels:
            return
        self.last_wheels = wheel_params
        self.vector.motors.set_wheel_motors(*wheel_params)


@flask_app.route("/")
def handle_index_page():
    return render_template('index.html')


def get_annotated_image():
    image = flask_app.remote_control_vector.vector.camera.latest_image
    if flask_app.display_debug_annotations != DebugAnnotations.DISABLED.value:
        return image.annotate_image()
    return image.raw_image


def streaming_video():
    """Video streaming generator function"""
    while True:
        if flask_app.remote_control_vector:
            image = get_annotated_image()

            img_io = io.BytesIO()
            image.save(img_io, 'PNG')
            img_io.seek(0)
            yield (b'--frame\r\n'
                   b'Content-Type: image/png\r\n\r\n' + img_io.getvalue() + b'\r\n')
        else:
            time.sleep(.1)


def serve_single_image():
    if flask_app.remote_control_vector:
        image = get_annotated_image()
        if image:
            return flask_helpers.serve_pil_image(image)

    return flask_helpers.serve_pil_image(_default_camera_image)


def is_microsoft_browser(req):
    agent = req.user_agent.string
    return 'Edge/' in agent or 'MSIE ' in agent or 'Trident/' in agent


@flask_app.route("/vectorImage")
def handle_vectorImage():
    if is_microsoft_browser(request):
        return serve_single_image()
    return flask_helpers.stream_video(streaming_video)


@flask_app.route('/tts', methods=['POST'])
def http_tts():
    message = json.loads(request.data.decode("utf-8"))
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.vector.audio.stream_wav_file(tts(message['textEntered']))
    return ""


def handle_key_event(key_request, is_key_down):
    message = json.loads(key_request.data.decode("utf-8"))
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.handle_key(key_code=(message['keyCode']), is_shift_down=message['hasShift'],
                                                   is_alt_down=message['hasAlt'], is_key_down=is_key_down)
    return ""


@flask_app.route('/mousemove', methods=['POST'])
def handle_mousemove():
    """Called from Javascript whenever mouse moves"""
    message = json.loads(request.data.decode("utf-8"))
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.handle_mouse(mouse_x=(message['clientX']), mouse_y=message['clientY'])
    return ""


@flask_app.route('/setMouseLookEnabled', methods=['POST'])
def handle_setMouseLookEnabled():
    """Called from Javascript whenever mouse-look mode is toggled"""
    message = json.loads(request.data.decode("utf-8"))
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.set_mouse_look_enabled(is_mouse_look_enabled=message['isMouseLookEnabled'])
    return ""


@flask_app.route('/setAreDebugAnnotationsEnabled', methods=['POST'])
def handle_setAreDebugAnnotationsEnabled():
    """Called from Javascript whenever debug-annotations mode is toggled"""
    message = json.loads(request.data.decode("utf-8"))
    flask_app.display_debug_annotations = message['areDebugAnnotationsEnabled']
    if flask_app.remote_control_vector:
        if flask_app.display_debug_annotations == DebugAnnotations.ENABLED_ALL.value:
            flask_app.remote_control_vector.vector.camera.image_annotator.enable_annotator('robotState')
        else:
            flask_app.remote_control_vector.vector.camera.image_annotator.disable_annotator('robotState')
    return ""


@flask_app.route('/setFreeplayEnabled', methods=['POST'])
def handle_setFreeplayEnabled():
    """Called from Javascript whenever freeplay mode is toggled on/off"""
    message = json.loads(request.data.decode("utf-8"))
    isFreeplayEnabled = message['isFreeplayEnabled']
    if flask_app.remote_control_vector:
        connection = flask_app.remote_control_vector.vector.conn
        if isFreeplayEnabled:
            connection.release_control()
        else:
            connection.request_control()
    return ""


@flask_app.route('/keydown', methods=['POST'])
def handle_keydown():
    """Called from Javascript whenever a key is down (note: can generate repeat calls if held down)"""
    return handle_key_event(request, is_key_down=True)


@flask_app.route('/keyup', methods=['POST'])
def handle_keyup():
    """Called from Javascript whenever a key is released"""
    return handle_key_event(request, is_key_down=False)


@flask_app.route('/dropDownSelect', methods=['POST'])
def handle_dropDownSelect():
    """Called from Javascript whenever an animSelector dropdown menu is selected (i.e. modified)"""
    message = json.loads(request.data.decode("utf-8"))

    item_name_prefix = "animSelector"
    item_name = message['itemName']

    if flask_app.remote_control_vector and item_name.startswith(item_name_prefix):
        item_name_index = int(item_name[len(item_name_prefix):])
        flask_app.remote_control_vector.set_anim(item_name_index, message['selectedIndex'])

    return ""


@flask_app.route('/animTriggerDropDownSelect', methods=['POST'])
def handle_animTriggerDropDownSelect():
    """Called from Javascript whenever the animTriggerSelector dropdown menu is selected (i.e. modified)"""
    message = json.loads(request.data.decode("utf-8"))
    selected_anim_trigger_name = message['animTriggerName']
    flask_app.remote_control_vector.selected_anim_trigger_name = selected_anim_trigger_name
    return ""


@flask_app.route('/sayText', methods=['POST'])
def handle_sayText():
    """Called from Javascript whenever the saytext text field is modified"""
    message = json.loads(request.data.decode("utf-8"))
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.text_to_say = message['text']
    return ""


@flask_app.route('/updateVector', methods=['POST'])
def handle_updateVector():
    return ""
    if flask_app.remote_control_vector:
        flask_app.remote_control_vector.update()
        action_queue_text = ""
        i = 1
        for action in flask_app.remote_control_vector.action_queue:
            action_queue_text += str(i) + ": " + flask_app.remote_control_vector.action_to_text(action) + "<br>"
            i += 1

        return "Action Queue:<br>" + action_queue_text + "\n"
    return ""


def tts(text):
    print('tts', text)
    import requests
    import tempfile
    import pydub
    url = 'https://tts.taijihuabao.com/api/v1/ai/tts/'
    headers = {'Authorization': f'Bearer <KEY>'}
    payload = {'text': text, 'voice_name': 2, 'param_name': 'auto', 'audio_format': 'mp3'}
    response = requests.post(url, headers=headers, json=payload)
    temp_mp3 = tempfile.mktemp(suffix='.mp3')
    with open(temp_mp3, 'wb') as fout:
        fout.write(response.content)
    temp_wav = tempfile.mktemp(suffix='.wav')
    pydub.AudioSegment.from_mp3(temp_mp3).apply_gain(15).export(temp_wav, format='wav')
    return temp_wav


def run():
    args = util.parse_command_args()

    with anki_vector.AsyncRobot(args.serial, enable_face_detection=True, enable_custom_object_detection=True) as robot:
        flask_app.remote_control_vector = RemoteControlVector(robot)
        flask_app.display_debug_annotations = DebugAnnotations.ENABLED_ALL.value

        robot.camera.init_camera_feed()
        robot.behavior.drive_off_charger()

        flask_helpers.run_flask(flask_app, '0.0.0.0', '80')


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt as e:
        pass
    except anki_vector.exceptions.VectorConnectionException as e:
        sys.exit("A connection error occurred: %s" % e)
