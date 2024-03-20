from modal import Stub, Volume
import subprocess

stub = Stub()

vol = Volume.from_name("my-test-volume")

@stub.function(volumes={"/data": vol})
def run():
    subprocess.run("AWS_ACCESS_KEY_ID=AKIA2J37CALYGP54WYS7 AWS_SECRET_ACCESS_KEY=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 aws s3 sync s3://jubbamodel/ ./")
    vol.commit()  # Needed to make sure all changes are persisted

