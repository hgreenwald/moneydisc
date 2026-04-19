PYTHON ?= python
GDRIVE_FOLDER_URL ?=
RAW_DATA_DIR ?= data/raw
PROCESSED_DATA_DIR ?= data/processed

.PHONY: pull-data compute-stats

pull-data:
	$(PYTHON) -m moneydisc.data_ingestion.download_google_drive --folder-url "$(GDRIVE_FOLDER_URL)" --output-dir "$(RAW_DATA_DIR)"

compute-stats:
	$(PYTHON) -m moneydisc.analysis.compute_stats --input-dir "$(RAW_DATA_DIR)" --output-dir "$(PROCESSED_DATA_DIR)"
