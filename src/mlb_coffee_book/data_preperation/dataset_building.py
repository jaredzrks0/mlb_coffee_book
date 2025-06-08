import pickle as pkl
import polars as pl

from pathlib import Path



class DatasetBuilder():

    def __init__(self, path_to_transcripts: str = 'data/processed_data'):
        self.path_to_transcripts = path_to_transcripts

        if not Path(self.path_to_transcripts).exists():
            raise ValueError('Path to downloaded transcripts does not exist')
        if not Path(self.path_to_transcripts).is_dir():
            raise ValueError('Path to transcripts is not a directory')
        if not any(Path(self.path_to_transcripts).iterdir()):
            raise ValueError('Path to transcripts does not contain any transcript files')

        # Read in the transcripts to a polars DataFrame
        folder = Path(self.path_to_transcripts)
        files = list(folder.glob("*"))  # adjust glob pattern if needed

        transcripts = []
        file_names = []


        for file in files:
            try:
                text = file.read_text(encoding='utf-8')
                transcripts.append(text)
                file_names.append(file.name)
            except Exception as e:
                print(f"Could not read {file.name}: {e}")
        self.transcripts = pl.DataFrame(transcripts, schema=['transcript'])
        self.files = pl.DataFrame(file_names, schema=['filename'])

    def build_dataset(self):
        dataset, files = self.build_dataset_chunks(), self.files
        with open('data/transcript_text_chunks/chunks.pkl', 'wb') as path:
            pkl.dump(dataset, path)
        with open('data/transcript_text_chunks/chunk_map.pkl', 'wb') as path:
            pkl.dump(files, path)

        return dataset, files


    def build_dataset_chunks(self, col_name: str = 'transcript'):
        return self.transcripts.select(
                pl.col(col_name).map_elements(lambda x: self._split_into_sliding_windows(x, window_size=30, step=15))
        ).explode(col_name)


    def _split_into_sliding_windows(self, text: str, window_size: int = 50, step: int = 20) -> list[str]:
        words = text.split()
        return [
            ' '.join(words[i:i+window_size])
            for i in range(0, max(len(words) - window_size + 1, 1), step)
        ]





