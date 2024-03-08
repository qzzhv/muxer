import luigi
from collections import defaultdict
import ffmpeg
from pathlib import Path
from itertools import chain
from loguru import logger
import os
import hashlib

INPUT_FOLDER = os.environ.get("INPUT_FOLDER", "input")
OUTPUT_FOLDER = os.environ.get("OUTPUT_FOLDER", "output")
INGORE_EXTENSIONS = ['!qB']


class MuxPack(luigi.Task):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)
    pack = luigi.ListParameter()

    @property
    def output_log_path(self):
        data = "\n".join(sorted(self.pack))
        stem = Path(self.pack[0]).stem
        md5 = hashlib.md5(data.encode()).hexdigest()
        return self.output_folder / f"{stem[:255-33]}_{md5}"

    def output(self):
        return luigi.LocalTarget(self.output_log_path)

    def get_streams(self):
        input_streams = defaultdict(list)

        for path in self.pack:
            path = Path(path)
            try:
                inp = ffmpeg.input(path)
                streams = ffmpeg.probe(path)["streams"]
            except ffmpeg.Error:
                logger.warning(f"Can't use file as input: {path}")
                continue

            for stream in streams:
                input_streams[stream["codec_type"]].append(inp[str(stream["index"])])

        return input_streams

    def mux_streams(self, streams, output):
        (
            ffmpeg.output(
                *chain.from_iterable(streams.values()),
                str(output.absolute()),
                acodec="copy",
                vcodec="copy",
            ).run(
                overwrite_output=True,
            )
        )

    def run(self):
        streams = self.get_streams()

        if (cnt := len(streams["video"])) > 1:
            logger.warning(f"Video streams error: except 1 stream, but get {cnt}: {streams['video']}")
        elif cnt == 0:
            logger.info("No video stream")
            with self.output().open("w") as outfile:
                outfile.write("No video stream")
            return

        video_path = streams["video"][0].node.kwargs["filename"]
        output = self.output_folder / video_path.relative_to(self.input_folder)

        self.mux_streams(streams, output=output)
        with self.output().open("w") as outfile:
            pass


class MuxSeriesFolder(luigi.WrapperTask):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)

    def get_packs(self):
        packs = defaultdict(list)
        ignored = set(f'.{ext.lower()}' for ext in INGORE_EXTENSIONS)
        for path in [p for p in self.input_folder.glob("**/*") if p.is_file() and p.suffix.lower() not in ignored]:
            packs[path.stem].append(path)
        return list(packs.values())

    def requires(self):
        packs = self.get_packs()
        for pack in packs:
            pack = [str(path.absolute()) for path in pack]
            yield MuxPack(
                input_folder=self.input_folder,
                output_folder=self.output_folder,
                pack=pack,
            )


class MuxTvFolder(luigi.WrapperTask):
    input_folder = luigi.PathParameter(exists=True)
    output_folder = luigi.PathParameter(exists=True)

    def requires(self):
        series_folders = [path for path in self.input_folder.glob("*") if path.is_dir()]
        for series_folder in series_folders:
            output_folder = self.output_folder / series_folder.relative_to(
                self.input_folder
            )

            output_folder.mkdir(mode=777, exist_ok=True)

            yield MuxSeriesFolder(
                input_folder=series_folder,
                output_folder=output_folder,
            )


BUILD_KWARGS = dict(
        tasks=[
            MuxTvFolder(
                input_folder=Path(INPUT_FOLDER).absolute(),
                output_folder=Path(OUTPUT_FOLDER).absolute(),
            )
        ],
        workers=1,
        local_scheduler=True,
)


if __name__ == "__main__":
    luigi.build(**BUILD_KWARGS)