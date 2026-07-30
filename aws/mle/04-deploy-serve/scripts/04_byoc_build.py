from __future__ import annotations

import argparse
import base64
import subprocess

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and push BYOC image to ECR")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--repository", default="mle-lab-04-serve", help="ECR repository name")
    parser.add_argument("--tag", default="latest", help="Image tag")
    parser.add_argument("--docker-dir", default="aws/mle/04-deploy-serve/docker", help="Path to docker context")
    return parser


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    args = _build_parser().parse_args()
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    ecr = session.client("ecr")
    sts = session.client("sts")
    region = session.region_name or ecr.meta.region_name

    try:
        repository = ecr.create_repository(repositoryName=args.repository)["repository"]
        repository_uri = repository["repositoryUri"]
    except ecr.exceptions.RepositoryAlreadyExistsException:
        repository_uri = ecr.describe_repositories(repositoryNames=[args.repository])["repositories"][0]["repositoryUri"]

    authorization_data = ecr.get_authorization_token()["authorizationData"][0]
    token = base64.b64decode(authorization_data["authorizationToken"]).decode("utf-8")
    _username, password = token.split(":", maxsplit=1)
    account_id = sts.get_caller_identity()["Account"]
    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"

    _run(["docker", "build", "-t", f"{args.repository}:{args.tag}", args.docker_dir])
    _run(["docker", "login", "--username", "AWS", "--password", password, registry])
    image_uri = f"{repository_uri}:{args.tag}"
    _run(["docker", "tag", f"{args.repository}:{args.tag}", image_uri])
    _run(["docker", "push", image_uri])

    print(f"ECR image URI: {image_uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
