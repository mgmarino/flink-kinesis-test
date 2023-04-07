## Flink usage with Kinesis

Setup:

1. Install environment:
    ```bash
    pipenv install --dev
    ```
1. Ensure you have a Java (JDK) 11 installed. I've used Temurin/Open JDK.
1. Pull down jar files using maven (install maven with `brew install mvn` if necessary):
    ```bash
    mvn dependency:copy-dependencies -DoutputDirectory=jars
    ```
1. Run kinesis emulator in one terminal.  This spins up a docker container
   running `kinesalite` and begins to populate two kinesis treams.  `CTRL-C`
   allows graceful stopping, which will shutdown the container.
    ```bash
    pipenv run python run_kinesis.py
    ```
1. Run flink job in other terminal.  At the moment, this does a simple temporal join between the two streams:
    ```bash
    pipenv run python run_flink.py
    ```

You should see output like:

```bash
> pipenv run python run_flink.py
+I[VA01, 0.7258213, null, 2023-04-07T12:33:11.598, null]
+I[VA02, 0.20517807, null, 2023-04-07T12:33:11.616, null]
+I[VA01, 0.32209012, 0, 2023-04-07T12:33:12.633, 2023-04-07T12:33:11.623]
+I[VA01, 0.9628723, 0, 2023-04-07T12:33:13.658, 2023-04-07T12:33:11.623]
+I[VA01, 0.21753427, 0, 2023-04-07T12:33:14.676, 2023-04-07T12:33:11.623]
+I[VA01, 0.20549107, 0, 2023-04-07T12:33:15.710, 2023-04-07T12:33:11.623]
+I[VA01, 0.93291366, 0, 2023-04-07T12:33:16.737, 2023-04-07T12:33:11.623]
+I[VA02, 0.34070176, null, 2023-04-07T12:33:12.646, null]
...
```
