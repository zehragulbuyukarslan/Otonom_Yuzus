#main.py

from yolov7_detector import detect_objects
from mav_controller import MavController
from pid_controller import PID
from utils.vision_utils import get_cable_offset
import cv2
import time

# MAVLink bağlantısı kur
mav = MavController('/dev/ttyACM0')  # Pixhawk USB portu
mav.arm()
mav.set_mode("STABILIZE")

# PID kontrolcü
pid = PID(Kp=0.5, Ki=0, Kd=0.2)

# Kamera başlat
cap = cv2.VideoCapture(0)
frame_width = 640
dt = 0.1

if not cap.isOpened():
    print("Kamera açılamadı.")
    exit()


while True:
    ret, frame = cap.read()
    if not ret:
        continue

    detections = detect_objects(frame)
    offset = get_cable_offset(detections, frame_width)
    error = offset / (frame_width / 2)  # normalize
    yaw_cmd = int(pid.compute(error, dt) * 1000)
    yaw_cmd = max(min(yaw_cmd, 1000), -1000)

    if offset is None:
        # Kablo yok, araç için alternatif hareket kararı ver
        print("Kablo algılanamadı! Farklı bir hareket yapılıyor.")
        # Örnek: dur ya da geri dön, sağa kay vb.
        mav.send_manual_control(0, 0, 0, 0)
    else:
        error = offset / (frame_width / 2)
        yaw_cmd = int(pid.compute(error, dt) * 1000)
        yaw_cmd = max(min(yaw_cmd, 1000), -1000)
        mav.send_manual_control(x=500, y=0, z=500, r=yaw_cmd)

    # Aracı yönlendir
    mav.send_manual_control(x=500, y=0, z=500, r=yaw_cmd)

    # Şekil algılandı mı?
    for det in detections:
        if det['class'] in ['circle', 'square', 'triangle']:
            print("Şekil bulundu. Duruluyor.")
            mav.send_manual_control(0, 0, 500, 0)
            break
        if det['class'] in ['circle', 'square', 'triangle']:
            mav.send_manual_control(0, 0, 500, 0)
            print(f"{det['class']} bulundu.")
            time.sleep(2)


    time.sleep(dt)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
