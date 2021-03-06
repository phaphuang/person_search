import argparse
import logging
import os.path as osp
from glob import glob

import coloredlogs
import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch

import _init_paths  # noqa: F401
from models.network import Network
from utils.config import cfg_from_file


def parse_args():
    parser = argparse.ArgumentParser(description="A demo of person search")
    parser.add_argument(
        "--gpu", default=-1, type=int, help="GPU device id to use. Default: -1, means using CPU"
    )
    parser.add_argument("--checkpoint", help="The checkpoint to be used. Default: None")
    parser.add_argument(
        "--threshold",
        default=0.75,
        type=float,
        help="The threshold used to remove those bounding boxes with low scores. Default: 0.75",
    )
    parser.add_argument("--cfg", help="Optional config file. Default: None")
    return parser.parse_args()


def visualize_result(img_path, detections, similarities):
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.imshow(plt.imread(img_path))
    plt.axis("off")
    for detection, sim in zip(detections, similarities):
        x1, y1, x2, y2, _ = detection
        ax.add_patch(
            plt.Rectangle(
                (x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="#4CAF50", linewidth=3.5
            )
        )
        ax.add_patch(
            plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="white", linewidth=1)
        )
        ax.text(
            x1 + 5,
            y1 - 18,
            "{:.2f}".format(sim),
            bbox=dict(facecolor="#4CAF50", linewidth=0),
            fontsize=20,
            color="white",
        )
    #plt.tight_layout()
    fig.savefig(img_path.replace("gallery", "result"))
    #plt.show()
    #plt.close(fig)

def visualize_video(frame, detections, similarities):
    out_frame = frame.copy()
    for detection, sim in zip(detections, similarities):
        x1, y1, x2, y2, _ = detection
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        print(x1, x2, y1, y2)
        cv2.rectangle(out_frame, (x1, y1), (x2, y2), (255,0,0), 1)
        cv2.putText(out_frame, "{:.2f}".format(sim), ((x1+5), (y1-18)), cv2.FONT_HERSHEY_SIMPLEX, color=(0,0,0), fontScale=1)
    
    return out_frame


if __name__ == "__main__":
    args = parse_args()

    coloredlogs.install(level="INFO", fmt="%(asctime)s %(filename)s %(levelname)s %(message)s")

    logging.info("Called with args: " + str(args))

    if args.cfg:
        cfg_from_file(args.cfg)

    net = Network()
    checkpoint = torch.load(osp.abspath(args.checkpoint))
    net.load_state_dict(checkpoint["model"])
    logging.info("Loaded checkpoint from: %s" % args.checkpoint)
    net.eval()
    device = torch.device("cuda:%s" % args.gpu if args.gpu != -1 else "cpu")
    net.to(device)

    """
    # Extract feature of the query person
    query_img = cv2.imread("imgs/query.jpg")
    query_roi = np.array([0, 0, 466, 943])  # [x1, y1, x2, y2]
    query_feat = net.inference(query_img, query_roi).view(-1, 1)

    # Get gallery images
    gallery_imgs = sorted(glob("imgs/gallery*.jpg"))

    for gallery_img in gallery_imgs:
        logging.info("Detecting %s" % gallery_img)
        detections, features = net.inference(cv2.imread(gallery_img))

        # Compute pairwise cosine similarities,
        # which equals to inner-products, as features are already L2-normed
        similarities = features.mm(query_feat).squeeze()

        # Visualize the results
        visualize_result(gallery_img, detections, similarities)
    """

    #### For video file
    cap = cv2.VideoCapture("data/dataset/video/handmovewhite.mp4")

    #### For video camera
    #cap = cv2.VideoCapture(0)

    query_img = cv2.imread("data/dataset/video/query.png")
    query_roi = np.array([0, 0, 313, 733])
    query_feat = net.inference(query_img, query_roi).view(-1, 1)

    scale_percent = 50
    width = int(cap.get(3) * scale_percent / 100)
    height = int(cap.get(4) * scale_percent / 100)
    dim = (width, height)

    output_video = cv2.VideoWriter("output/output_video.avi", cv2.VideoWriter_fourcc('M','J','P','G'), 20.0, (width, height))

    no_frame = 1
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")

        frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

        #cv2.imshow("Input video", frame)
        
        
        logging.info("Detecting Frame %d" % no_frame)
        detections, features = net.inference(frame)

        # Compute pairwise cosine similarities,
        # which equals to inner-products, as features are already L2-normed
        similarities = features.mm(query_feat).squeeze()

        print(detections.tolist(), similarities.tolist())

        # Visualize the results
        out_frame = visualize_video(frame, detections.tolist(), [similarities.tolist()])

        output_video.write(out_frame)
        cv2.imshow("Output video", out_frame)
        
        if cv2.waitKey(1) == ord('q'):
            break
        
        no_frame += 1
    
    cap.release()
    output_video.release()
    cv2.destroyAllWindows()
        
        
        
