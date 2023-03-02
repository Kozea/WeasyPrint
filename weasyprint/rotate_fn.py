from PIL import ImageOps, Image


def rotate_pillow_image(pillow_image: Image.Image, orientation) -> Image.Image:
    """
    Returns either absolute same image if orientation was not changed.
    or its copy with modified orientation.
    """
    image_format = pillow_image.format
    if orientation == 'from-image':
        if 'exif' in pillow_image.info:
            pillow_image = ImageOps.exif_transpose(
                pillow_image)
    elif orientation != 'none':
        angle, flip = orientation
        if angle > 0:
            rotation = getattr(
                Image.Transpose, f'ROTATE_{angle}')
            pillow_image = pillow_image.transpose(rotation)
        if flip:
            pillow_image = pillow_image.transpose(
                Image.Transpose.FLIP_LEFT_RIGHT)
    pillow_image.format = image_format
    return pillow_image
