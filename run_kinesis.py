import json
import random
import signal
import time
from contextlib import contextmanager, suppress

import boto3
import docker
import pandas

port = 4567


@contextmanager
def kinesalite():
    client = docker.from_env()
    container = client.containers.run(
        "instructure/kinesalite", ports={f"{port}/tcp": port}, detach=True
    )
    yield container
    container.stop()


class Kinesis:
    def __init__(self):
        self.service = boto3.Session().client(
            "kinesis", endpoint_url=f"http://localhost:{port}"
        )

        self.shutdown = False
        signal.signal(signal.SIGINT, self.should_shutdown)
        signal.signal(signal.SIGTERM, self.should_shutdown)

    def should_shutdown(self, *args):
        self.shutdown = True

    def check_and_create_stream(self, name: str):
        with suppress(self.service.exceptions.ResourceNotFoundException):
            self.service.delete_stream(StreamName=name, EnforceConsumerDeletion=True)

        waiter = self.service.get_waiter("stream_not_exists")
        waiter.wait(StreamName=name, WaiterConfig=dict(Delay=1))

        self.service.create_stream(StreamName=name, ShardCount=2)

    def put_record(self, **kwargs):
        return self.service.put_record(**kwargs)


telemetry_stream = "telemetry"
config_stream = "config"

with kinesalite():
    service = Kinesis()
    print("Creating Streams")
    for s in [telemetry_stream, config_stream]:
        service.check_and_create_stream(s)

    print("Beginning streaming")
    counter = -1
    while not service.shutdown:
        time.sleep(1)
        service.put_record(
            StreamName=telemetry_stream,
            Data=json.dumps(
                dict(
                    serial_no="VA01",
                    sensor_value=random.random(),
                    event_ts=f"{pandas.Timestamp.now().isoformat()}",
                )
            )
            + "\n",
            PartitionKey="serial_no",
        )
        service.put_record(
            StreamName=telemetry_stream,
            Data=json.dumps(
                dict(
                    serial_no="VA02",
                    sensor_value=random.random(),
                    event_ts=f"{pandas.Timestamp.now().isoformat()}",
                )
            )
            + "\n",
            PartitionKey="serial_no",
        )
        counter += 1
        if counter % 5 != 0:
            continue

        service.put_record(
            StreamName=config_stream,
            Data=json.dumps(
                dict(
                    serial_no="VA01",
                    config=counter,
                    update_ts=f"{pandas.Timestamp.now().isoformat()}",
                )
            )
            + "\n",
            PartitionKey="serial_no",
        )
