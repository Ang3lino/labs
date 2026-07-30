from __future__ import annotations

import aws_cdk as cdk

from stack import ModelTrainingStack


app = cdk.App()
ModelTrainingStack(app, "MleLab02ModelTrainingStack")
app.synth()
