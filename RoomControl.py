import cv2
import mediapipe as mp
import math
import subprocess
import time
import requests

# Initialize the Mediapipe Hands model
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Start capturing video from the webcam
cap = cv2.VideoCapture(0)

# flag turned on or off to allow a measurement to change some value, e.g., changing volume or light level
length_measurement_boolean_sound = False

length_measurement_boolean_light = False

length_measurement_boolean_brightness = False

url = "http://10.0.0.88:5000"

# Last time the volume was updated
last_volume_update = 0
update_interval = 0.5  # interval in seconds


def rgb_scalar(value):
    """
    Scales a value between 0 and 30 to an RGB color between (0, 0, 0) and (255, 255, 255).

    Parameters:
    value (int): An integer between 0 and 30.

    Returns:
    tuple: A tuple of (R, G, B) values, each between 0 and 255.
    """
    # Ensure value is within the range [0, 30]
    if value < 0:
        value = 0
    elif value > 32:
        value = 32
    rgb_value1, rgb_value2, rgb_value3 = 0,0,0
    # Calculate the scaling factor (from 0 to 1)
    # Scale each RGB component from 0 to 255
    if value <= 8:
       scaleR = value / 8
       scaleGB = value / 32
       rgb_value1,rgb_value2,rgb_value3 = int(255 * scaleR), int(scaleGB * 255), int(255*scaleGB)
    elif value <= 16:
        scaleG = value / 16
        scaleRB = value / 32
        rgb_value1, rgb_value2, rgb_value3 = int(255 * scaleRB), int(scaleG * 255), int(255 * scaleRB)
    elif value <= 24:
        scaleB = value / 24
        scaleRG = value / 90
        rgb_value1, rgb_value2, rgb_value3 = int(255 * scaleRG), int(scaleRG * 255), int(255 * scaleB)
    elif value <= 32:
        scale = value / 32
        rgb_value1, rgb_value2, rgb_value3 = int(255 * scale), int(scale * 255), int(255 * scale)


    return [rgb_value1, rgb_value2, rgb_value3]

def calculate_distance(point1, point2):
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Flip the frame to avoid mirrored effect
    frame = cv2.flip(frame, 1)

    # Convert the BGR frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame to find hands
    results = hands.process(frame_rgb)

    # Variables to store the pointer finger coordinates and lengths for both hands
    left_pointer = None
    right_pointer = None
    left_finger_length = None
    right_finger_length = None
    left_thumb = None
    right_thumb = None
    left_pinky = None
    left_middle = None

    # If hands are detected, find the index finger landmarks
    if results.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            # Get the hand label (LEFT or RIGHT)
            hand_label = results.multi_handedness[idx].classification[0].label

            # Extract index finger tip coordinates (landmark 8)
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]

            # Convert to pixel coordinates
            index_finger_tip_coord = (
            int(index_finger_tip.x * frame.shape[1]), int(index_finger_tip.y * frame.shape[0]))
            index_finger_mcp_coord = (
            int(index_finger_mcp.x * frame.shape[1]), int(index_finger_mcp.y * frame.shape[0]))

            # Calculate the length of the index finger (from MCP to tip)
            finger_length = calculate_distance(index_finger_tip_coord, index_finger_mcp_coord)

            # Left Pinky
            index_pinky_left = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
            index_pinky_left_coord = (
            int(index_pinky_left.x * frame.shape[1]), int(index_pinky_left.y * frame.shape[0]))

            # Left and Right Thumbs
            index_thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_thumb_coord = (int(index_thumb.x * frame.shape[1]), int(index_thumb.y * frame.shape[0]))

            # Left Middle Finger
            index_middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            index_middle_coord = (int(index_middle.x * frame.shape[1]), int(index_middle.y * frame.shape[0]))
            # Assign to the appropriate hand
            if hand_label == 'Left':
                left_pointer = index_finger_tip_coord
                left_finger_length = finger_length
                left_pinky = index_pinky_left_coord
                left_thumb = index_thumb_coord
                left_middle = index_middle_coord
            elif hand_label == 'Right':
                right_pointer = index_finger_tip_coord
                right_finger_length = finger_length
                right_thumb = index_thumb_coord

            # Draw hand landmarks on the original frame
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            #Check if left thumb and left middle are touching
            if left_middle and left_thumb and left_finger_length and right_finger_length and not (length_measurement_boolean_sound or length_measurement_boolean_light or length_measurement_boolean_brightness):
                middle_thumb_distance = calculate_distance(left_thumb, left_middle)
                mean_finger_length = (left_finger_length + right_finger_length) / 2
                middle_thumb_distance /= mean_finger_length

                if middle_thumb_distance <= 0.3:
                    length_measurement_boolean_brightness = True
            # Check if left thumb and left pointer are touching
            if left_thumb and left_pointer and left_finger_length and right_finger_length and not (length_measurement_boolean_sound or length_measurement_boolean_light or length_measurement_boolean_brightness):
                thumb_pointer_distance = calculate_distance(left_thumb, left_pointer)
                mean_finger_length = (left_finger_length + right_finger_length) / 2  # optimize
                thumb_pointer_distance /= mean_finger_length

                if thumb_pointer_distance <= 0.3:
                    length_measurement_boolean_light = True

        # Check if left thumb and left pinky are touching
        if left_thumb and left_pinky and left_finger_length and right_finger_length and not (length_measurement_boolean_sound or length_measurement_boolean_light or length_measurement_boolean_brightness):
            thumb_pinky_distance = calculate_distance(left_thumb, left_pinky)
            mean_finger_length = (left_finger_length + right_finger_length) / 2  # optimize
            thumb_pinky_distance /= mean_finger_length

            if thumb_pinky_distance <= 0.3:
                length_measurement_boolean_sound = True

        # Check if right pointer and right thumb are no longer touching
        if right_thumb and right_pointer and left_finger_length and right_finger_length and (length_measurement_boolean_sound or length_measurement_boolean_light or length_measurement_boolean_brightness):
            pointer_thumb_distance = calculate_distance(right_pointer, right_thumb)
            mean_finger_length = (left_finger_length + right_finger_length) / 2
            pointer_thumb_distance /= mean_finger_length

            if pointer_thumb_distance > 0.6:
                length_measurement_boolean_sound = False
                length_measurement_boolean_light = False
                length_measurement_boolean_brightness = False

        # If both left and right pointer fingers are detected, calculate distance
        if left_pointer and right_pointer and (length_measurement_boolean_sound or length_measurement_boolean_light or length_measurement_boolean_brightness):
            # Draw a line between the left and right index fingers
            cv2.line(frame, left_pointer, right_pointer, (0, 255, 0), 3)

            # Calculate the Euclidean distance between the two points (pointer fingers)
            pointer_distance = calculate_distance(left_pointer, right_pointer)

            # Calculate the mean of the lengths of both index fingers
            if left_finger_length and right_finger_length:
                mean_finger_length = (left_finger_length + right_finger_length) / 2
                if length_measurement_boolean_sound:
                    # Scale the distance by the inverse of the mean finger length
                    scaled_distance = pointer_distance / mean_finger_length
                    volume = min(100, int(100.0 * (scaled_distance / 20)))

                    # Check if 0.5 seconds have passed since the last volume update
                    current_time = time.time()
                    if current_time - last_volume_update > update_interval:
                        subprocess.run(["osascript", "-e", f"set volume output volume {volume}"])
                        last_volume_update = current_time  # Update the time of the last volume change
                elif length_measurement_boolean_light:
                    current_time = time.time()
                    if current_time - last_volume_update > 0.5:
                        scaled_distance = pointer_distance / mean_finger_length
                        rgb_values = rgb_scalar(scaled_distance)
                        payload = {
                            "rgb": rgb_values
                        }
                        response = requests.post(url + '/set_color', json=payload)
                        last_volume_update = current_time
                elif length_measurement_boolean_brightness:
                    current_time = time.time()
                    if current_time - last_volume_update > 0.5:
                        scaled_distance = pointer_distance / mean_finger_length
                        light_level = 0
                        if scaled_distance >= 30:light_level = 254
                        else: light_level = int((scaled_distance / 30) * 254)
                        payload = {
                            "brightness": light_level
                        }
                        response = requests.post(url + '/set_brightness', json=payload)
                        last_volume_update = current_time


                # Display the scaled distance on the screen above the line
                midpoint = ((left_pointer[0] + right_pointer[0]) // 2, (left_pointer[1] + right_pointer[1]) // 2 - 10)
                cv2.putText(frame, f'{scaled_distance:.2f}', midpoint, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Display the output frame
    cv2.imshow('Hand Detection - Scaled Distance Between Pointer Fingers', frame)

    # Exit on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
