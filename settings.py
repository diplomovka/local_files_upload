import os

MAX_SIZE = int(os.getenv('MAX_SIZE') or 1024)
AVG_SIZE = int(os.getenv('AVG_SIZE') or 256)
MIN_SIZE = int(os.getenv('MIN_SIZE') or 64)

CATEGORY_LENGTH = int(os.getenv('CATEGORY_LENGTH') or 1000)
MAX_WORKERS = int(os.getenv('MAX_WORKERS') or 4)

FILES_TOPIC = str(os.getenv('FILES_TOPIC') or 'FILES_TOPIC')
FILES_SCHEMA_PATH = str(os.getenv('FILES_SCHEMA_PATH') or './avro_files/files_array.avsc')

BOOTSTRAP_SERVERS = str(os.getenv('BOOTSTRAP_SERVERS') or 'localhost:9092')
SCHEMA_REGISTRY_URL = str(os.getenv('SCHEMA_REGISTRY_URL') or 'http://localhost:8085')
ENCODING = str(os.getenv('ENCODING') or 'utf_8')
AVRO_FILES_ENCODING = str(os.getenv('AVRO_FILES_ENCODING') or 'utf-8')

EXPERIMENTS_DATA_DIR = 'experiments_data'
EXPERIMENT_NAME = str(os.getenv('EXPERIMENT_NAME') or 'test1')

WAIT_BEFORE_START = int(os.getenv('WAIT_BEFORE_START') or 30)