import pathlib
import itertools
import logging

import ffmpeg
import numpy as np


png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\\r\xa8f\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\x0fa\x00\x00\x0fa\x01\xa8?\xa7i\x00\x00\x01\x15IDATx\x9c\xed\xc11\x01\x00\x00\x00\xc2\xa0\xf5O\xedk\x08\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00x\x03\x01<\x00\x01<\xedS\t\x00\x00\x00\x00IEND\xaeB`\x82'

def stack_2x2(input_dir, zoom, col, row, frame_pattern='%05d', **kwargs):
    """create an ffmpeg path that stacks four streams of images of 256x256 and generates a video of 512x512"""
    assert zoom >= 1, 'zoom level 0 does not have 4 images'
    assert col % 2 == 0,  'col should  be even'
    assert row % 2 == 0,  'row should  be even'
    # define 4  streams
    input_dir = pathlib.Path(input_dir)
    inputs = [
        ffmpeg.input(str(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col, row=row)), **kwargs),
        ffmpeg.input(str(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col+1, row=row)), **kwargs),
        ffmpeg.input(str(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col, row=row+1)), **kwargs),
        ffmpeg.input(str(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col+1, row=row+1)), **kwargs),
    ]
    # stack
    stacked = ffmpeg.filter(
        inputs,
        'xstack',
        inputs=4,
        layout='0_0|w0_0|0_h0|w0_h0'
    )
    return stacked


# postprocessing
def interpolate(stream, mode='blend'):
    """create  interpolation function that  blends between frames"""
    options = dict(fps=24)
    if mode == 'blend':
        options.update(dict(
            mi_mode='blend'
        ))
    elif mode == 'flow':
        options.update(dict(
            mi_mode='mci',
            mc_mode='aobmc',
            me_mode='bilat',
            vsbmc=0,
            mb_size=8
        ))
    filter_ = ffmpeg.filter(stream, 'minterpolate', **options)
    return filter_

def alpha_output(stream, video_path, fps):
    output_options = dict(
        vcodec='libvpx',
        pix_fmt='yuva420p',
        keyint_min=fps,
        cluster_size_limit='10M',
        cluster_time_limit=2100,
        g=fps,
        qmin=0,
        qmax=30,
        crf=5,
    )

    # output_options = dict(
    #    vcodec='libvpx',
    #    pix_fmt='yuva420p',
    #    keyint_min=1,
    #    qmin=0,
    #    qmax=30,
    #    crf=5,
    #)

    # alternate or constructed reference frame, needed for alpha channel
    output_options['auto-alt-ref'] = '0'

    output = ffmpeg.output(stream, str(video_path), **output_options).overwrite_output()
    return output

def debug_output(stream, video_path):
    return ffmpeg.output(stream, str(video_path)).overwrite_output()

# stack inputs


def make_stream(frames_dir, result_dir,  zoom, col, row, blend=False, frame_size=256):
    """generate a stream for 2x2 png into a 512 video"""

    if blend:
        framerate = 1
        fps = 24
    else:
        framerate = 10
        fps = 1

    if frame_size == 512:
        stream = stack_2x2(frames_dir, zoom, col, row, framerate=framerate)
        col=int(col/2)
        row=int(row/2)
    else:
        input_path = (frames_dir / '%05d' / str(zoom) / str(col) / str(row)).with_suffix('.png')
        stream = ffmpeg.input(str(input_path), framerate=framerate)

    if blend:
        stream = interpolate(stream, mode='blend')
    
    result_path = pathlib.Path('{result_dir}/{zoom}/{col}/{row}.webm'.format(
        result_dir=result_dir,
        zoom=zoom-1,
        col=col,
        row=row
    ))
    result_path.parent.mkdir(parents=True, exist_ok=True)

    stream = alpha_output(stream, result_path, fps)

    return stream

def fill_missing_pngs(frames_dir, zoom, col, row):
    frames = list(frames_dir.glob('*[0-9]'))
    count = 0
    for frame, r, c in itertools.product(
        frames,
        [row, row + 1],
        [col, col + 1]
    ):
        path = pathlib.Path(frame / str(zoom) /  str(c) / (str(r) + '.png'))
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # create an empty png
            with path.open('wb') as f:
                f.write(png_bytes)
            count += 1
    if count > 0:
        logging.debug('filled {} frames in {}'.format(count, frames_dir))
