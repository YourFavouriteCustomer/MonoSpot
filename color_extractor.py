from typing import Any

from sklearn.cluster import MeanShift, estimate_bandwidth
import numpy as np
import cv2
import colorsys


def convert_to_rgb(color: tuple[float, float, float]) -> tuple[float, float, float]:
    h, s, v = color
    h, s, v = h / 360.0, s / 1000.0, v / 1000.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    r, g, b = round(r * 255), round(g * 255), round(b * 255)

    return r, g, b


def merge_colors(colors, counts, threshold):
    merged_colors = []
    merged_counts = []

    for i, color in enumerate(colors):
        if len(merged_colors) == 0:
            merged_colors.append(color)
            merged_counts.append(counts[i])
        else:
            # Calculate Euclidean distance between the current color and all merged colors
            distances = np.linalg.norm(np.array(merged_colors) - color, axis=1)
            closest = np.argmin(distances)

            # If the closest color is within the threshold, merge them
            if distances[closest] < threshold:
                merged_colors[closest] = (merged_colors[closest] * merged_counts[closest] + color * counts[i]) / (
                            merged_counts[closest] + counts[i])
                merged_counts[closest] += counts[i]
            else:
                # Otherwise, add as a new color
                merged_colors.append(color)
                merged_counts.append(counts[i])

    return np.array(merged_colors), np.array(merged_counts)


def get_palette(filename: str) -> list[list[int | float | Any]]:
    image = cv2.imread(filename)
    if image is None:
        raise ValueError(f"Failed to load image: {filename}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (200, 200))

    pixels = image.reshape(-1, 3)

    bandwidth = estimate_bandwidth(pixels, quantile=0.1, n_samples=500)
    if bandwidth < 0.1:
        bandwidth = 0.1

    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
    ms.fit(pixels)

    labels = ms.labels_
    cluster_centers = ms.cluster_centers_

    unique_labels, counts = np.unique(labels, return_counts=True)
    cluster_centers, counts = merge_colors(cluster_centers, counts, 60)

    colors_and_area = list()
    for count, color in zip(counts, cluster_centers):
        r, g, b = [x / 255.0 for x in color]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        colors_and_area.append([h * 360, s * 1000, v * 1000, count / len(pixels) * 100])

    return colors_and_area