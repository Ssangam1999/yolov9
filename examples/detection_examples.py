from mdetect import yolov9

if __name__ == "__main__":
    obj = yolov9(conf_thres=0.25, iou_thres=0.25)
    # path = "0"
    path = '/home/sangam/Pictures/2.jpg'
    obj.run(view_img=True,nosave=True,webcam=False,source=path)

    # run method should have 3 parameters
    # 1st is webcam.
    # if webcam is set to true, it should automatically open a webcam and start to do the object detection
    # if webcam is false, we should by default provide an image to do the OD.
    # 2nd is save_file, is save_file is true, go and save in the user given directory.
    # 3rd visualize is true and we are sending an image then the detected object on that given image should be
    # draw with the bounding box, class_name and confidence


