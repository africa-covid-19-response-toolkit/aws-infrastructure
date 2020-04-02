---

# Creating frontend bucket pipeline

Note: Service name can only contain alphanummeric & hyphen.
```
aws cloudformation create-stack --stack-name covid19-et-pipeline \
--template-body file://frontend-s3-pipeline.yml \
--parameters ParameterKey=ServiceName,ParameterValue="Covid19-ET" \
             ParameterKey=ThirdPartyRepositoryName,ParameterValue="Covid19.ET" \
--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --profile covid
```
