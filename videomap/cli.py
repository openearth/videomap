# -*- coding: utf-8 -*-

"""Console script for videomap."""
import re
import sys
import pathlib

import click
import pandas as pd
import ffmpeg


frame_pattern = re.compile(
    r'(?P<frame>\d+)/(?P<zoom>\d+)/(?P<column>\d+)/(?P<row>\d+)\.(png|jpg)$'
)

@click.group()
def cli():
    pass

@cli.command()
@click.argument('frames_dir', type=click.Path(exists=True))
@click.argument('result_dir', type=click.Path(exists=False), default='result')
def convert(frames_dir, result_dir):
    """Console script for videomap."""
    frames_path = pathlib.Path(frames_dir)
    result_path = pathlib.Path(result_dir)

    tile_paths = list(frames_path.glob('**/*.png'))
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
    tiles_df.head()

    # Convert all images per frame
    for (zoom, column, row), frames in tiles_df.groupby(['zoom', 'column', 'row']):
        # define the path of the  videos
        video_path = (result_path / str(zoom) / str(column) / str(row)).with_suffix('.webm')

        # create an input string that reflects all images per tile
        input_path = (frames_path / '%d' / str(zoom) / str(column) / str(row)).with_suffix('.png')

        # create parents
        video_path.parent.mkdir(parents=True, exist_ok=True)

        # cmd = 'ffmpeg -framerate 10 -i "{0}/{1}/%03d.png" -c:v libvpx -keyint_min 1 -cluster_size_limit 10M -cluster_time_limit 2100 -g 1 -an -qmin 0 -qmax 30 -crf 5 -auto-alt-ref 0 {2}/{1}.webm -y'.format(tile_x_dir, tile_y, new_path)

        output_options = dict(
            vcodec='libvpx',
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

        chain = (
            ffmpeg
                .input(str(input_path), framerate=10)
                .output(str(video_path),  **output_options)
                .overwrite_output()
        )
        click.echo(chain.get_args())
        chain.run()


    return 0


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
