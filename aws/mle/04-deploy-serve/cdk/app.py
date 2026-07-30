from __future__ import annotations

import aws_cdk as cdk

from stack import DeployServeStack


app = cdk.App()
DeployServeStack(app, "MleLab04DeployServeStack")
app.synth()
