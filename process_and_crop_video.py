import cv2
import os
import numpy as np
from PIL import Image


def keep_main_center_component(mask):
    """
    只保留最像主体猫猫的连通区域：
    面积大、且靠近画面中心。
    """
    h, w = mask.shape
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    if num_labels <= 1:
        return mask

    cx, cy = w / 2, h / 2
    best_label = 0
    best_score = -1

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        x, y = centroids[i]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # 面积越大越好，离中心越近越好
        score = area - dist * 8

        if score > best_score:
            best_score = score
            best_label = i

    return (labels == best_label).astype(np.uint8) * 255


def remove_black_background_keep_cat(
    bgr_img,
    bg_threshold=25,
    protect_threshold=18,
    close_size=15,
    dilate_size=35,
    dilate_iter=2,
    feather=1
):
    """
    抠除黑色背景，但保留猫猫内部的黑色区域。

    核心思路：
    1. 找到明显不是黑背景的像素，作为猫猫主体种子。
    2. 通过形态学膨胀生成“猫猫保护区”。
    3. 只从图像四周开始搜索黑色区域，只有和边界连通的黑色才认为是背景。
    4. 猫猫内部的黑色不会被扣掉。
    """

    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]

    max_channel = rgb.max(axis=2)

    # 1. 明显不是黑色背景的区域，作为猫猫主体种子
    fg_seed = (max_channel > protect_threshold).astype(np.uint8) * 255

    # 2. 闭运算 + 膨胀，让保护区覆盖猫猫的黑色毛发、帽子、身体
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (close_size, close_size)
    )
    fg_seed = cv2.morphologyEx(fg_seed, cv2.MORPH_CLOSE, close_kernel, iterations=2)

    dilate_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (dilate_size, dilate_size)
    )
    protected_cat = cv2.dilate(fg_seed, dilate_kernel, iterations=dilate_iter)

    # 只保留画面中心最大的主体，避免误把水印、噪声当成猫
    protected_cat = keep_main_center_component(protected_cat)

    # 再做一次闭运算，让保护区更连续
    protected_cat = cv2.morphologyEx(protected_cat, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    # 3. 找到黑色区域
    dark_area = (max_channel <= bg_threshold).astype(np.uint8) * 255

    # 黑色区域中，被猫猫保护区覆盖的部分不允许被当成背景
    passable_bg = cv2.bitwise_and(dark_area, cv2.bitwise_not(protected_cat))

    # 4. 只从边界 flood fill，找真正的背景黑色
    flood = passable_bg.copy()

    for x in range(w):
        if flood[0, x] == 255:
            mask = np.zeros((h + 2, w + 2), np.uint8)
            cv2.floodFill(flood, mask, (x, 0), 128)

        if flood[h - 1, x] == 255:
            mask = np.zeros((h + 2, w + 2), np.uint8)
            cv2.floodFill(flood, mask, (x, h - 1), 128)

    for y in range(h):
        if flood[y, 0] == 255:
            mask = np.zeros((h + 2, w + 2), np.uint8)
            cv2.floodFill(flood, mask, (0, y), 128)

        if flood[y, w - 1] == 255:
            mask = np.zeros((h + 2, w + 2), np.uint8)
            cv2.floodFill(flood, mask, (w - 1, y), 128)

    background_mask = (flood == 128)

    # 5. 生成 alpha 通道
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[background_mask] = 0

    # 边缘轻微羽化，避免透明边缘太硬
    if feather > 0:
        k = feather * 2 + 1
        alpha = cv2.GaussianBlur(alpha, (k, k), 0)
        alpha[alpha < 8] = 0
        alpha[alpha > 247] = 255

    rgba = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = alpha

    return Image.fromarray(rgba)


def crop_center_square(frame):
    """
    保持你原来的逻辑：
    9:16 视频中，以宽度 W 为边长，从纵向中心裁剪 1:1 正方形。
    """
    h, w = frame.shape[:2]

    if h >= w:
        left = 0
        right = w
        top = (h - w) // 2
        bottom = top + w
    else:
        top = 0
        bottom = h
        left = (w - h) // 2
        right = left + h

    return frame[top:bottom, left:right]


def process_and_crop_video(
    video_path,
    output_dir,
    bg_threshold=25,
    protect_threshold=18,
    close_size=15,
    dilate_size=35,
    dilate_iter=2,
    feather=1
):
    """
    抠除黑色背景、保留猫猫内部黑色区域、切除上下空白和右下角水印，
    输出紧凑透明 PNG 序列帧。
    """

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    frame_count = 0

    print(f"正在处理视频: {video_path}...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. 先居中裁剪正方形，逻辑和你原代码一致
        cropped_frame = crop_center_square(frame)

        # 2. 抠除黑色背景，但保护猫猫内部黑色
        result_img = remove_black_background_keep_cat(
            cropped_frame,
            bg_threshold=bg_threshold,
            protect_threshold=protect_threshold,
            close_size=close_size,
            dilate_size=dilate_size,
            dilate_iter=dilate_iter,
            feather=feather
        )

        # 3. 保存 PNG
        frame_name = os.path.join(output_dir, f"frame_{frame_count:04d}.png")
        result_img.save(frame_name, "PNG")

        frame_count += 1

    cap.release()

    print(f"✨ 处理完成！共生成 {frame_count} 张透明 PNG -> {output_dir}\n")


if __name__ == "__main__":
    process_and_crop_video(
        r"C:\Users\admin\Desktop\pet\Idle.mp4",
        r"C:\Users\admin\Desktop\pet\idle",
        bg_threshold=25,
        protect_threshold=18,
        close_size=15,
        dilate_size=21,
        dilate_iter=2,
        feather=1
    )

    process_and_crop_video(
        r"C:\Users\admin\Desktop\pet\Interact.mp4",
        r"C:\Users\admin\Desktop\pet\interact",
        bg_threshold=25,
        protect_threshold=18,
        close_size=15,
        dilate_size=21,
        dilate_iter=2,
        feather=1
    )

    process_and_crop_video(
        r"C:\Users\admin\Desktop\pet\Scroll.mp4",
        r"C:\Users\admin\Desktop\pet\scroll",
        bg_threshold=25,
        protect_threshold=18,
        close_size=15,
        dilate_size=21,
        dilate_iter=2,
        feather=1
    )