import cv2
cap = cv2.VideoCapture(0)
print("相机可用:", cap.isOpened())
cap.release()
