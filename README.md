# moneydisc
A repository designed to calculate and analyze statistics for ultimate frisbee teams from pass logs. Originally developed on top of outputs from the Statto App.

## Project structure

- `src/moneydisc/data_ingestion/`: data download utilities
- `src/moneydisc/analysis/`: analysis entrypoints
- `data/raw/`: downloaded source files
- `data/processed/`: computed outputs
- `tests/`: unit tests

## Make targets

- `make pull-data GDRIVE_FOLDER_URL="<google-drive-folder-url>"`
  - Downloads files from a Google Drive folder into `data/raw`.
- `make compute-stats`
  - Loads files from `data/raw` and writes a summary artifact to `data/processed/summary.txt`.
