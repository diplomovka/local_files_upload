# created based on: https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/avro_producer.py

import os
from uuid import uuid4
from hashlib import sha256, sha1, md5
import time
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka import SerializingProducer
from serialization_classes.file_data import FileData
from concurrent.futures import ProcessPoolExecutor, wait
from typing import List
import settings


hash_functions = {
    'SHA256': sha256,
    'SHA1': sha1,
    'MD5': md5
}


class DataAndHash:
    def __init__(self, data, hash):
        self.data = data
        self.hash = hash


def create_directory(directory_name):
    if not os.path.exists(directory_name) or not os.path.isdir(directory_name):
        os.mkdir(directory_name)


def file_data_to_dict(file_data, ctx):
    return dict(file_name=file_data.file_name, data=file_data.data,
                chunk_hash=file_data.data_hash, experiment_name=file_data.experiment_name)


def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print(f'Message delivery failed: {err}')


def set_up_producer():
    schema_registry_conf = {'url': settings.SCHEMA_REGISTRY_URL}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    with open(settings.FILES_SCHEMA_PATH, 'r', encoding=settings.AVRO_FILES_ENCODING) as f:
        schema_str = f.read()

    avro_serializer = AvroSerializer(schema_registry_client,
                                     schema_str,
                                     file_data_to_dict)

    producer_conf = {
        'bootstrap.servers': settings.BOOTSTRAP_SERVERS,
        'key.serializer': StringSerializer(settings.ENCODING),
        'value.serializer': avro_serializer
    }

    return SerializingProducer(producer_conf)


def chunk_data(file_name, hf):
    file = open(f'./experiments_input_data/{file_name}', 'rb')
    content = file.read()
    file.close()

    results = []

    start = time.perf_counter_ns()
    hash_object = hf(content)
    results.append(DataAndHash(content, hash_object.hexdigest()))
    end = time.perf_counter_ns()

    with open(f'experiments_data/{settings.EXPERIMENT_NAME}/{settings.EXPERIMENT_NAME}_chunking_time.csv', 'a') as f:
        f.write(f'{file_name};{(end-start) / 1000000}\n')

    return results


if __name__ == '__main__':
    time.sleep(settings.WAIT_BEFORE_START)

    hash_function = hash_functions[settings.HASH_FUNCTION]

    print(f'Hashing with {settings.HASH_FUNCTION}')

    create_directory(f'{settings.EXPERIMENTS_DATA_DIR}/{settings.EXPERIMENT_NAME}')

    start_time = time.time()

    f_names = os.listdir('./experiments_input_data')
    total_f_names = len(f_names)
    categories = [f_names[i:i+settings.CATEGORY_LENGTH]
                   for i in range(0, total_f_names, settings.CATEGORY_LENGTH)]
    
    counter = 1
    for files_names in categories:
        with ProcessPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
            future_results = []
            
            producer = set_up_producer()

            producer.poll(0.0)

            for file_name in files_names:
                future = executor.submit(chunk_data, file_name, hash_function)
                future_results.append(future)

            wait(future_results)

            for (future, file_name) in zip(future_results, files_names):
                results = future.result()

                for i, res in enumerate(results):
                    file_data = FileData(file_name=file_name, chunk=res.data, chunk_hash=res.hash,
                                        experiment_name=settings.EXPERIMENT_NAME)
                    producer.produce(topic=settings.FILES_TOPIC, key=str(uuid4()),
                                     value=file_data, on_delivery=delivery_report)

                if counter % 1000 == 0:
                    print(counter)
                
                counter += 1

            print('Flushing...')

            producer.flush()

            print('Flushed...')

    end_time = time.time()

    with open(f'experiments_data/{settings.EXPERIMENT_NAME}/{settings.EXPERIMENT_NAME}_upload_time.txt', 'a') as f:
        f.write(f'Total execution time in seconds: {end_time - start_time}')
