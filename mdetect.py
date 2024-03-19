import argparse
import os
import platform
import sys
import json
from pathlib import Path

import torch

# FILE = Path(__file__).resolve()
# ROOT = FILE.parents[0]  # YOLO root directory
# if str(ROOT) not in sys.path:
#     sys.path.append(str(ROOT))  # add ROOT to PATH
# ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode

BASEDIR = os.path.dirname(__file__)


class yolov9:

    def __init__(self, conf_thres, iou_thres, device='cpu'):
        self.weights = os.path.join(BASEDIR, 'weights', 'human_monkey2.pt')
        self.imgsz = (320, 320)
        self.iou_thres = iou_thres
        self.conf_thres = conf_thres
        self.data = os.path.join(BASEDIR, 'data', 'coco.yaml')
        self.device = select_device(device)
        self.max_det = 1000

    @smart_inference_mode()
    def run(self, source, view_img=False, project=os.path.join(BASEDIR, 'runs', 'detect'), nosave=False,
            dnn=False, half=False, vid_stride=1, name='exp', exist_ok=False, augment=False,
            save_txt=True, classes=None, agnostic_nms=False, save_crop=False, line_thickness=3,
            save_conf=False, hide_labels=False, hide_conf=False, update=False, visualize=False,webcam=True,save_json=True
            ):
        detections_summary = {}
        if webcam:
            source = '0'  # Default webcam
        elif source is None:
            print("You must either enable webcam or provide path of an image")
            sys.exit(1)
            #source = '/home/sangam/Pictures/1.jpg'
        source = str(source)
        save_img = not nosave and not source.endswith('.txt')  # save inference images
        is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)


        is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
        webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
        screenshot = source.lower().startswith('screen')
        if is_url and is_file:
            source = check_file(source)  # download

        # Directories
        save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
        (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

        # Load Model
        device = self.device
        model = DetectMultiBackend(self.weights, device=device, dnn=dnn, data=self.data, fp16=half)
        stride, names, pt = model.stride, model.names, model.pt
        imgsz = check_img_size(self.imgsz, s=stride)  # check image size

        # Dataloader
        bs = 1  # batch_size
        if webcam:
            view_img = check_imshow(warn=True)
            dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
            bs = len(dataset)
        elif screenshot:
            dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
        else:
            dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        vid_path, vid_writer = [None] * bs, [None] * bs

        # Run inference
        model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
        seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
        for path, im, im0s, vid_cap, s in dataset:
            with dt[0]:
                im = torch.from_numpy(im).to(model.device)
                im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
                im /= 255  # 0 - 255 to 0.0 - 1.0
                if len(im.shape) == 3:
                    im = im[None]  # expand for batch dim

            # Inference
            with dt[1]:
                visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
                pred = model(im, augment=augment, visualize=visualize)

            # NMS
            with dt[2]:
                pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, classes, agnostic_nms,
                                           max_det=self.max_det)

            # Process predictions
            for i, det in enumerate(pred):  # per image
                seen += 1
                if webcam:  # batch_size >= 1
                    p, im0, frame = path[i], im0s[i].copy(), dataset.count
                    s += f'{i}: '
                else:
                    p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

                p = Path(p)  # to Path
                #Changes for json
                file_name = p.name
                if file_name not in detections_summary:
                    detections_summary[file_name] = {}
                #changes_upto_here

                save_path = str(save_dir / p.name)  # im.jpg
                txt_path = str(save_dir / 'labels' / p.stem) + (
                    '' if dataset.mode == 'image' else f'_{frame}')  # im.txt
                s += '%gx%g ' % im.shape[2:]  # print string
                gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                imc = im0.copy() if save_crop else im0  # for save_crop
                annotator = Annotator(im0, line_width=line_thickness, example=str(names))
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                    # Print results
                    for c in det[:, 5].unique():
                        n = (det[:, 5] == c).sum()  # detections per class
                        s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                    # Write results
                    for *xyxy, conf, cls in reversed(det):
                        if save_txt:  # Write to file
                            xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                            line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                            with open(f'{txt_path}.txt', 'a') as f:
                                f.write(('%g ' * len(line)).rstrip() % line + '\n')

                        if save_img or save_crop or view_img:  # Add bbox to image
                            c = int(cls)  # integer class
                            label = None if hide_labels else (names[c] if hide_conf else f'{names[c]} {conf:.2f}')
                            annotator.box_label(xyxy, label, color=colors(c, True))
                        if save_crop:
                            save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)
                        #changes for json
                        class_name = names[int(cls)]
                        if class_name not in detections_summary[file_name]:
                            detections_summary[file_name][class_name] = {'count': 0, 'frames': []}
                        detections_summary[file_name][class_name]['count'] += 1
                        if webcam or vid_cap:  # If it's a video or webcam, add the frame number
                            detections_summary[file_name][class_name]['frames'].append(frame)
                        #end

                    # Stream results
                    im0 = annotator.result()
                    if webcam:
                        if view_img:
                            if platform.system() == 'Linux' and p not in windows:
                                windows.append(p)
                                cv2.namedWindow(str(p),
                                                cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                                cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                            cv2.imshow(str(p), im0)
                            cv2.waitKey(1)  # 1 millisecond
                    else:
                        if view_img:
                            if platform.system() == 'Linux' and p not in windows:
                                windows.append(p)
                                cv2.namedWindow(str(p),
                                                cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                                cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                            cv2.imshow(str(p), im0)
                            cv2.waitKey(1)  # 1 millisecond

                    # Save results (image with detections)

                    if save_img:
                        if dataset.mode == 'image':
                            cv2.imwrite(save_path, im0)
                        else:  # 'video' or 'stream'
                            if vid_path[i] != save_path:  # new video
                                vid_path[i] = save_path
                                if isinstance(vid_writer[i], cv2.VideoWriter):
                                    vid_writer[i].release()  # release previous video writer
                                if vid_cap:  # video
                                    fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                    w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                    h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                else:  # stream
                                    fps, w, h = 30, im0.shape[1], im0.shape[0]
                                save_path = str(
                                    Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                                vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                            vid_writer[i].write(im0)

            # Print time (inference-only)
            LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")

        t = tuple(x.t / seen * 1E3 for x in dt)  # speeds per image
        LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
        if save_txt or save_img:
            s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
            LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
        if update:
            strip_optimizer(self.weights[0])  # update model (to fix SourceChangeWarning)

        if save_json:
            json_path = str(save_dir / "detections.json")  # Define the JSON file path
            with open(json_path, 'w') as f:
                json.dump(detections_summary, f,indent=4)  # Save the detections summary to a JSON file

            LOGGER.info(f"Detections saved to {json_path}")
