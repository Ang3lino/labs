from __future__ import annotations

import os

import boto3
import sagemaker


# ponytail: just convenience wrappers, not an abstraction layer — boto3 is already simple
def get_session(region: str | None = None, profile: str | None = None) -> boto3.Session:
    session_kwargs: dict[str, str] = {}
    if region is not None:
        session_kwargs["region_name"] = region
    if profile is not None:
        session_kwargs["profile_name"] = profile
    return boto3.Session(**session_kwargs)


def get_sagemaker_role() -> str:
    env_role = (
        os.getenv("SAGEMAKER_ROLE_ARN")
        or os.getenv("SAGEMAKER_EXECUTION_ROLE_ARN")
        or os.getenv("AWS_SAGEMAKER_ROLE_ARN")
    )
    if env_role:
        return env_role

    try:
        from sagemaker import get_execution_role

        return get_execution_role()
    except Exception as error:
        raise RuntimeError(
            "Could not resolve SageMaker execution role from environment or default context."
        ) from error


def get_default_bucket(session: boto3.Session | None = None) -> str:
    boto_session = session if session is not None else get_session()
    sm_session = sagemaker.session.Session(boto_session=boto_session)
    return sm_session.default_bucket()
