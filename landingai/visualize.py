import logging
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from landingai.common import (
    ClassificationPrediction,
    ObjectDetectionPrediction,
    Prediction,
    SegmentationPrediction,
)

_LOGGER = logging.getLogger(__name__)


def overlay_predictions(
    predictions: list[Prediction], image: np.ndarray, options: dict[str, Any] = None
) -> Image.Image:
    """Overlay the prediction results on the input image and return the image with overlaid."""
    if len(predictions) == 0:
        _LOGGER.warning("No predictions to overlay, returning original image")
        return Image.fromarray(image)
    types = {type(pred) for pred in predictions}
    assert len(types) == 1, f"Expecting only one type of prediction, got {types}"
    overlay_func = _OVERLAY_FUNC_MAP[types.pop()]
    return overlay_func(predictions, image, options)


def overlay_bboxes(
    predictions: list[ObjectDetectionPrediction],
    image: np.ndarray,
    options: dict[str, Any] = None,
) -> Image.Image:
    "Draw bounding boxes on the input image and return the image with bounding boxes drawn."
    import bbox_visualizer as bbv

    if options is None:
        options = {}
    label_type = options.get("label_type", "default")
    for pred in predictions:
        bbox = pred.bboxes
        label = f"{pred.label_name} | {pred.score:.4f}"
        if label_type == "flag":
            image = bbv.draw_flag_with_label(image, label, bbox)
        else:
            draw_bg = options.get("draw_bg", True)
            label_at_top = options.get("top", True)
            image = bbv.draw_rectangle(image, pred.bboxes)
            if label_type == "default":
                image = bbv.add_label(
                    image, label, bbox, draw_bg=draw_bg, top=label_at_top
                )
            elif label_type == "t-label":
                image = bbv.add_T_label(image, label, bbox, draw_bg=draw_bg)
    return Image.fromarray(image)


def overlay_colored_masks(
    predictions: list[SegmentationPrediction],
    image: np.ndarray,
    options: dict[str, Any] = None,
) -> Image.Image:
    from segmentation_mask_overlay import overlay_masks

    if options is None:
        options = {}
    image = Image.fromarray(image).convert(mode="L")
    masks = [pred.decoded_boolean_mask.astype(np.bool_) for pred in predictions]
    return overlay_masks(image, masks, mask_alpha=0.5, return_pil_image=True)


def overlay_predicted_class(
    predictions: list[ClassificationPrediction],
    image: np.ndarray,
    options: dict[str, Any] = None,
    text_position: tuple[int, int] = (10, 25),
) -> Image.Image:
    if options is None:
        options = {}
    assert len(predictions) == 1
    prediction = predictions[0]
    image = Image.fromarray(image)
    text = f"{prediction.label_name} {prediction.score:.4f}"
    draw = ImageDraw.Draw(image)
    font = _get_pil_font()
    xy = (text_position[0], image.size[1] - text_position[1])
    box = draw.textbbox(xy=xy, text=text, font=font)
    box = (box[0] - 10, box[1] - 5, box[2] + 10, box[3] + 5)
    draw.rounded_rectangle(box, radius=15, fill="#333333")
    draw.text(xy=xy, text=text, fill="white", font=font)
    return image


def _get_pil_font(font_size: int = 18):
    from matplotlib import font_manager

    font = font_manager.FontProperties(family="sans-serif", weight="bold")
    file = font_manager.findfont(font)
    assert file, f"Cannot find font file for {font} at {file}"
    return ImageFont.truetype(file, font_size)


_OVERLAY_FUNC_MAP = {
    ObjectDetectionPrediction: overlay_bboxes,
    SegmentationPrediction: overlay_colored_masks,
    ClassificationPrediction: overlay_predicted_class,
}
