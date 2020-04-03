---

# Creating frontend bucket pipeline

Follow the following guide to setup pipelines for github/bitbucket repositories:

###Github Repository

In github console, generate a new Personal access token (https://github.com/settings/tokens/new) ensuring
to provide access to the desired github organization. In AWS secrets manager, store the access key as secret entry 
with name of`GithubCreds`.

Run the following cloudformation stack replacing the parameter values with appropriate values; 
Note: Service name can only contain alphanummeric & hyphen characters.
```
aws cloudformation create-stack --stack-name covid19-et-pipeline \
--template-body file://frontend-s3-pipeline.yml \
--parameters ParameterKey=ServiceName,ParameterValue="<<the service name>>" \
             ParameterKey=ThirdPartyRepositoryName,ParameterValue="<<your github repository>>" \
             ParameterKey=ThirdPartyOrgName,ParameterValue="<<the github org name>>" \
             ParameterKey=ThirdPartyVCSProvider,ParameterValue="GitHub" \
--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --profile covid
```

###BitBucket Cloud

In bitbucket console, generate a new access token ensuring to provide access to the desired team. 
In AWS secrets manager, store the access token as secret entry with name of`BitBucketCreds`.

Run the following cloudformation stack replacing the parameter values with appropriate values; 
Note: Service name can only contain alphanummeric & hyphen characters.
```
aws cloudformation create-stack --stack-name covid19-et-pipeline \
--template-body file://frontend-s3-pipeline.yml \
--parameters ParameterKey=ServiceName,ParameterValue="<<the service name>>" \
             ParameterKey=ThirdPartyRepositoryName,ParameterValue="<<your bitbucket repository>>" \
             ParameterKey=ThirdPartyOrgName,ParameterValue="<<the bitbucket project name>>" \
             ParameterKey=ThirdPartyVCSProvider,ParameterValue="BitBucket" \
--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --profile covid
```

Here is an example forhttps://github.com/Ethiopia-COVID19/Covid19.ET.git repo:

```
aws cloudformation update-stack --stack-name covid19-et-pipeline \
--template-body file://frontend-s3-pipeline.yml \
--parameters ParameterKey=ServiceName,ParameterValue="Covid19-ET" \
             ParameterKey=ThirdPartyRepositoryName,ParameterValue="Covid19.ET" \
             ParameterKey=ThirdPartyOrgName,ParameterValue="Ethiopia-COVID19" \
             ParameterKey=ThirdPartyVCSProvider,ParameterValue="GitHub" \
--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --profile covid
```