#!/bin/bash

# TODO: Print out the authenticated user and ask for confirmation
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -b|--bucket-name)
    BUCKET_NAME="$2"
    shift # past argument
    shift # past value
    ;;
    -r|--region)
    REGION="$2"
    shift # past argument
    shift # past value
    ;;
esac
done

region=${REGION:="us-east-1"}

if [ "$BUCKET_NAME" == "" ]; then
  echo "Bucket name is required"
  exit 1
fi

bucket_name="${BUCKET_NAME}"
key_prefix ="${region}""
echo "Region=$region and Bucket Name=$bucket_name"
aws s3 ls "s3://$bucket_name" || aws s3 mb --region $region "s3://$bucket_name"

role_policy=$(cat <<END
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "codebuild.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
END
)

role_perms=$(cat <<END
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }
END
)

role_arn

aws iam create-role --role-name "infra_builder_${region}" --assume-role-policy-document $role_policy

exit 1

envs=$(cat <<END
{
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:2.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "environmentVariables": [
              {
                "name": "AWS_REGION",
                "value": "$region"
              },
              {
                "name": "STATE_BUCKET_NAME",
                "value": "$bucket_name"
              },
              {
                "name": "KEY_PREFIX",
                "value": "$key_prefix"
              }
            ],
            "privilegedMode": false
          }
END
)

echo $envs

aws codebuild create-project --name "infra-builder for $region" \
                             --source type=GITHUB,location=https://github.com/Ethiopia-COVID19/aws-infrastructure \
                             --source-version master \
                             --artifacts "type=NO_ARTIFACTS"
                             --environment $envs