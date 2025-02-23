import hashlib
import os
from collections import defaultdict
from itertools import chain
from pathlib import Path

import ffmpeg
import luigi
from loguru import logger
from ..utils import add_luigi_task
import schedule


DEFAULT_INPUT_FOLDER = 'input'
DEFAULT_OUTPUT_FOLDER = 'output'
INPUT_FOLDER = os.environ.get('INPUT_FOLDER')
OUTPUT_FOLDER = os.environ.get('OUTPUT_FOLDER')
INGORE_EXTENSIONS = os.environ.get('INGORE_EXTENSIONS', '!qB')


if not INPUT_FOLDER:
    Path(DEFAULT_INPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    INPUT_FOLDER = DEFAULT_INPUT_FOLDER
INPUT_FOLDER = Path(INPUT_FOLDER)

if not OUTPUT_FOLDER:
    Path(DEFAULT_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    OUTPUT_FOLDER = DEFAULT_OUTPUT_FOLDER
OUTPUT_FOLDER = Path(OUTPUT_FOLDER)


INGORE_EXTENSIONS = set(INGORE_EXTENSIONS.split(','))


class MuxPack(luigi.Task):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)
    stem = luigi.Parameter()
    pack = luigi.ListParameter()

    def output_log_path(self):
        data = '\n'.join(sorted(self.pack))
        h = hashlib.sha1(data.encode()).hexdigest()
        suffix = f'.{h[:8]}.mux'
        return self.output_folder / f'{self.stem[:255-len(suffix)]}{suffix}'

    def output(self):
        return luigi.LocalTarget(self.output_log_path())

    def get_streams(self):
        input_streams = defaultdict(list)

        for path in sorted(self.pack):
            path = Path(path)
            try:
                inp = ffmpeg.input(path)
                streams = ffmpeg.probe(path)['streams']
            except ffmpeg.Error:
                logger.warning(f'Can\'t use file as input: {path}')
                continue

            for stream in streams:
                input_streams[stream['codec_type']].append(inp[str(stream['index'])])

        return input_streams

    def mux_streams(self, streams, output):
        return ffmpeg.output(
            *chain.from_iterable(streams.values()),
            str(output.absolute()),
            acodec='copy',
            vcodec='copy',
            max_interleave_delta=0,
            avoid_negative_ts='make_zero',
        ).run(
            overwrite_output=True,
        )

    def run(self):
        streams = self.get_streams()

        if (cnt := len(streams['video'])) != 1:
            logger.warning(f'Video streams error: except 1 stream, but get {cnt}: {streams['video']}')
            if cnt == 0:
                with self.output().open('w') as outfile:
                    pass
                return

        video_path = streams['video'][0].node.kwargs['filename']
        output = self.output_folder / video_path.relative_to(self.input_folder)

        self.mux_streams(streams, output=output)

        with self.output().open('w') as outfile:
            for path in self.pack:
                print(Path(path).relative_to(self.input_folder), file=outfile)


class MuxSeriesFolder(luigi.WrapperTask):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)

    def get_packs(self):
        packs = defaultdict(list)
        ignored = set(f'.{ext.lower()}' for ext in INGORE_EXTENSIONS)
        for path in [p for p in self.input_folder.glob('**/*') if p.is_file() and p.suffix.lower() not in ignored]:

            has_video = False
            try:
                has_video = any(stream.get('codec_type') == 'video' for stream in ffmpeg.probe(path)['streams'])
            except ffmpeg.Error as e:
                if 'Invalid data found' not in e.stderr.decode():
                    raise

            if has_video:
                pack = [p for p in path.parent.glob('**/*') if p.stem.startswith(path.stem)]
                packs[path.stem] = pack

        return packs

    def requires(self):
        packs = self.get_packs()
        for stem, pack in packs.items():
            pack = [str(path.absolute()) for path in pack]
            yield MuxPack(
                input_folder=self.input_folder,
                output_folder=self.output_folder,
                stem=stem,
                pack=pack,
            )


class MuxTvFolder(luigi.WrapperTask):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)

    def requires(self):
        item_folder = [path for path in self.input_folder.glob('*') if path.is_dir()]
        for series_folder in item_folder:
            output_folder = self.output_folder / series_folder.relative_to(self.input_folder)

            output_folder.mkdir(exist_ok=True)

            yield MuxSeriesFolder(
                input_folder=series_folder,
                output_folder=output_folder,
            )


task = MuxTvFolder(
    input_folder=INPUT_FOLDER.absolute(),
    output_folder=OUTPUT_FOLDER.absolute(),
)


add_luigi_task(schedule.every(1).minutes, task)
