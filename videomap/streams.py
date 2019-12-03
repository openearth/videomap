import pathlib

import ffmpeg
import numpy as np

def stack_2x2(input_dir, zoom, col, row, frame_pattern='%05d', **kwargs):
    """create an ffmpeg path that stacks four streams of images of 256x256 and generates a video of 512x512"""
    assert zoom >= 1, 'zoom level 0 does not have 4 images'
    assert col % 2 == 0,  'col should  be even'
    assert row % 2 == 0,  'row should  be even'
    # define 4  streams
    input_dir = pathlib.Path(input_dir)
    inputs = [
        ffmpeg.input(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col, row=row), **kwargs),
        ffmpeg.input(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col+1, row=row), **kwargs),
        ffmpeg.input(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col, row=row+1), **kwargs),
        ffmpeg.input(input_dir / frame_pattern / '{zoom}/{col}/{row}.png'.format(zoom=zoom, col=col+1, row=row+1), **kwargs),
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

def alpha_output(stream, video_path):
    output_options = dict(
        vcodec='libvpx',
        pix_fmt='yuva420p',
        keyint_min=1,
        qmin=0,
        qmax=30,
        crf=5,
    )
    # add unusual format option (to allow for alpha channel)
    output_options['auto-alt-ref'] = '0'
    output = ffmpeg.output(stream, str(video_path), **output_options).overwrite_output()
    return output

def debug_output(stream, video_path):
    return ffmpeg.output(stream, str(video_path)).overwrite_output()

# stack inputs


def make_stream(frames_dir, result_dir,  zoom, col, row):
    """generate a stream for 2x2 png into a 512 video"""
    stream = stack_2x2(frames_dir, zoom, col, row, framerate=1)
    stream = interpolate(stream, mode='blend')
    result_path = pathlib.Path('{result_dir}/{zoom}/{col}/{row}.webm'.format(
        result_dir=result_dir,
        zoom=zoom-1,
        col=col,
        row=row
    ))
    result_path.parent.mkdir(parents=True, exist_ok=True)
    stream = alpha_output(stream, result_path)
    return stream

def make_stream_256(frames_dir, result_dir, zoom, col, row):
    video_path = (result_dir / str(zoom) / str(col) / str(row)).with_suffix('.webm')

    # create an input string that reflects all images per tile
    # this  asserts the frame are in the format %05d.
    input_path = (frames_dir / '%05d' / str(zoom) / str(col) / str(row)).with_suffix('.png')

    # create parents
    video_path.parent.mkdir(parents=True, exist_ok=True)

    # cmd = 'ffmpeg -framerate 10 -i "{0}/{1}/%03d.png" -c:v libvpx -keyint_min 1 -cluster_size_limit 10M -cluster_time_limit 2100 -g 1 -an -qmin 0 -qmax 30 -crf 5 -auto-alt-ref 0 {2}/{1}.webm -y'.format(tile_x_dir, tile_y, new_path)

    output_options = dict(
        vcodec='libvpx',
        pix_fmt='yuva420p',
        keyint_min=1,
        cluster_size_limit='10M',
        cluster_time_limit=2100,
        g=1,
        qmin=0,
        qmax=30,
        crf=5,
    )
    # add unusual format option (to allow for alpha channel)
    output_options['auto-alt-ref'] = '0'

    stream = (
        ffmpeg
            .input(str(input_path), framerate=1)
            .filter('minterpolate',  mi_mode='blend', fps=24)
            .output(str(video_path),  **output_options)
            .overwrite_output()
    )
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
        if not path.exists():
            # create an empty png
            with path.open('wb') as f:
                f.write(png_bytes)
            count += 1
    if count > 0:
        logging.debug('filled {} frames in {}'.format(count, frames_dir))
