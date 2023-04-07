import os
import subprocess
from pathlib import Path

os.environ["AWS_CBOR_DISABLE"] = "true"  # Required because we're using kinesalite

# We require java 11
java_home = (
    subprocess.run(["/usr/libexec/java_home", "-v 11"], capture_output=True)
    .stdout.decode("utf-8")
    .strip()
)

from pyflink.table import EnvironmentSettings, TableEnvironment  # noqa

stream_name = "telemetry"
config_stream_name = "config"

# create a batch TableEnvironment
table_env = TableEnvironment.create(EnvironmentSettings.in_streaming_mode())
table_env.get_config().set("parallelism.default", "1")
table_env.get_config().set("env.java.home", java_home)

# Get jar dependencies

all_jars = ";".join([f"file://{p.resolve()}" for p in Path("jars").glob("*.jar")])
table_env.get_config().set("pipeline.jars", all_jars)

table_env.execute_sql(
    f"""
CREATE TABLE kinesis_table (
  `serial_no` string,
  `sensor_value` float,
  `event_ts` timestamp(3),
  WATERMARK FOR event_ts AS event_ts
  )
  WITH (
    'connector' = 'kinesis',
    'stream' = '{stream_name}',
    'aws.endpoint' = 'http://localhost:4567',
    'aws.trust.all.certificates' = 'true',
    'scan.stream.initpos' = 'TRIM_HORIZON',
    'format' = 'json',
    'json.timestamp-format.standard' = 'ISO-8601'
);
"""
)
table_env.execute_sql(
    f"""
CREATE TABLE config (
  `serial_no` string,
  `config` bigint,
  `update_ts` timestamp(3),
  WATERMARK FOR update_ts AS update_ts
  )
  WITH (
    'connector' = 'kinesis',
    'stream' = '{config_stream_name}',
    'aws.endpoint' = 'http://localhost:4567',
    'aws.trust.all.certificates' = 'true',
    'scan.stream.initpos' = 'TRIM_HORIZON',
    'format' = 'json',
    'json.timestamp-format.standard' = 'ISO-8601'
);
"""
)

table_env.execute_sql(
    """
CREATE VIEW versioned_config AS
SELECT serial_no, config, update_ts
  FROM (
      SELECT *,
      ROW_NUMBER() OVER (PARTITION BY serial_no ORDER BY update_ts DESC) AS rownum
      FROM config)
WHERE rownum = 1;
"""
)

table_env.execute_sql(
    """
CREATE TABLE print_table (
  `serial_no` string,
  `sensor_value` float,
  `config` bigint,
  `event_ts` timestamp(3),
  `update_ts` timestamp(3)
)
WITH ('connector' = 'print');
"""
)

table_env.execute_sql(
    """
INSERT INTO print_table
  SELECT kinesis_table.serial_no, sensor_value, config, event_ts, update_ts
  FROM kinesis_table
  LEFT JOIN versioned_config FOR SYSTEM_TIME AS OF kinesis_table.event_ts
    ON kinesis_table.serial_no = versioned_config.serial_no;
"""
).wait()
