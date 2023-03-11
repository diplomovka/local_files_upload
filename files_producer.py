# created based on: https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/avro_producer.py

import os
from uuid import uuid4
from hashlib import sha256
import time
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka import SerializingProducer
from fastcdc import fastcdc
from serialization_classes.file_data import FileData
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, wait
import settings


def file_data_to_dict(file_data, ctx):
    return dict(file_name=file_data.file_name, chunk=file_data.chunk,
                chunk_hash=file_data.chunk_hash, chunk_serial_num=file_data.chunk_serial_num,
                end_of_file=file_data.end_of_file, experiment_name=file_data.experiment_name)


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


def send_data(file_name, min_size, avg_size, max_size, counter):
    producer = set_up_producer()

    producer.poll(0.0)

    file = open(f'./experiments_input_data/{file_name}', 'rb')
    content = file.read()
    file.close()

    start = time.perf_counter_ns()
    results = list(fastcdc(content, min_size=min_size, avg_size=avg_size, max_size=max_size, fat=True, hf=sha256))
    end = time.perf_counter_ns()
    
    total_chunks = len(results)

    for i, res in enumerate(results):
        end_of_file = i == (total_chunks - 1)
        file_data = FileData(file_name=file_name, chunk=res.data, chunk_hash=res.hash,
                            chunk_serial_num=i, end_of_file=end_of_file, experiment_name=settings.EXPERIMENT_NAME)
        producer.produce(topic=settings.FILES_TOPIC, key=str(uuid4()), value=file_data,
                        on_delivery=delivery_report)
        
    producer.flush()

    if counter % 1000 == 0:
        print(counter)

    with open(f'experiments_data/{settings.EXPERIMENT_NAME}.csv', 'a') as f:
        f.write(f'{file_name};{(end-start) / 1000000}\n')


if __name__ == '__main__':
    # time.sleep(settings.WAIT_BEFORE_START)

    files_names = os.listdir('./experiments_input_data')

    max_size = int(1024)
    avg_size = int(256)
    min_size = int(64)

    with ProcessPoolExecutor(max_workers=8) as executor:
        future_results = []
        
        counter = 0
        for file_name in files_names:
            future = executor.submit(send_data, file_name, min_size, avg_size, max_size, counter)
            future_results.append(future)
            counter += 1

        wait(future_results)
