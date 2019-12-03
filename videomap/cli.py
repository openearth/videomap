# -*- coding: utf-8 -*-

"""Console script for videomap."""
import re
import sys
import pathlib

import click
import pandas as pd
import ffmpeg
import numpy as np

import videomap.streams


png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\\r\xa8f\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\x0fa\x00\x00\x0fa\x01\xa8?\xa7i\x00\x00\x01\x15IDATx\x9c\xed\xc11\x01\x00\x00\x00\xc2\xa0\xf5O\xedk\x08\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00x\x03\x01<\x00\x01<\xedS\t\x00\x00\x00\x00IEND\xaeB`\x82'


frame_pattern = re.compile(
    r'(?P<frame>\d+)/(?P<zoom>\d+)/(?P<column>\d+)/(?P<row>\d+)\.(png|jpg)$'
)

@click.group()
def cli():
    pass

@cli.command()
@click.argument('frames_dir', type=click.Path(exists=True))
@click.argument('result_dir', type=click.Path(exists=False))
@click.option('--to512/--no-to512', is_flag=True, default=True, help='Generate tiles in 512x512 size.')
def convert(frames_dir, result_dir, to512):
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
    if to512:
        idx_512 = np.logical_and.reduce([
            tiles_df.column % 2 == 0,
            tiles_df.row % 2 == 0,
            tiles_df.zoom > 0
        ])
        tiles_df = tiles_df[idx_512]

    # Convert all images per frame
    for (zoom, col, row), frames in tiles_df.groupby(['zoom', 'column', 'row']):
        # define the path of the  videos
        if to512:
            stream = videomap.streams.make_stream(frames_dir, result_dir,  zoom, col, row)
        else:
            stream = videomap.streams.make_stream_256(frames_dir, result_dir,  zoom, col, row)

        stream.run()


    return 0


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
