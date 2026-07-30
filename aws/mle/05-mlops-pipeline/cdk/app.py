from __future__ import annotations

import aws_cdk as cdk

from stack import MlopsPipelineStack


app = cdk.App()
MlopsPipelineStack(app, "MleLab05MlopsPipelineStack")
app.synth()
