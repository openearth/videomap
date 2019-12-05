# -*- coding: utf-8 -*-

"""Console script for videomap."""
import re
import sys
import pathlib
import logging

import click
import pandas as pd
import ffmpeg
import numpy as np

import videomap.streams


frame_pattern = re.compile(
    r'(?P<frame>\d+)/(?P<zoom>\d+)/(?P<column>\d+)/(?P<row>\d+)\.(png|jpg)$'
)

# setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass

@cli.command()
@click.argument('frames_dir', type=click.Path(exists=True))
@click.argument('result_dir', type=click.Path(exists=False))
@click.option('--frame-size', type=click.Choice([512, 256]), default=512, help='Generate tiles with custom framesize (e.g. 512).')
@click.option('--blend', is_flag=True, default=False, help='Generate interpolated videos.')
def convert(frames_dir, result_dir, frame_size, blend):
    """Console script for videomap."""
    # convert to path
    frames_dir = pathlib.Path(frames_dir)
    result_dir = pathlib.Path(result_dir)

    tile_paths = list(frames_dir.glob('**/*.png'))
    rows = []
    for tile in tile_paths:
        match = frame_pattern.search(tile.as_posix())
        match_dict = match.groupdict()
        row = {
            "match": match,
            "tile": tile,
            "column": int(match_dict["column"]),
            "frame": int(match_dict["frame"]),
            "row": int(match_dict["row"]),
            "zoom": int(match_dict["zoom"])
        }
        rows.append(row)

    # Overview of tiles
    tiles_df = pd.DataFrame(rows).infer_objects()

    # if we do 512 frames we only need the even  frames
    if frame_size == 512:
        # we need the rows and columns one level up
        # the row,column number 1 level up is modulo 2
        # jump to the even tile coordinate, representing the 2x2 quad
        tiles_df['row'] = tiles_df['row'] - tiles_df['row'] % 2
        tiles_df['column'] = tiles_df['column'] - tiles_df['column'] % 2
        # now we have double tiles,  drop them
        tiles_df = tiles_df[['frame', 'row', 'column', 'zoom']].drop_duplicates()
        # drop level 0
        idx_512 = np.logical_and.reduce([
            tiles_df.zoom > 0
        ])
        tiles_df = tiles_df[idx_512]

    # Convert all images per frame
    for (zoom, col, row), frames in tiles_df.groupby(['zoom', 'column', 'row']):
        # define the path of the  videos
        videomap.streams.fill_missing_pngs(frames_dir, zoom, col, row)
        stream = videomap.streams.make_stream(frames_dir, result_dir,  zoom, col, row, frame_size=frame_size, blend=blend)
        logger.debug('running %s', stream.compile())
        stream.run()


    return 0


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
