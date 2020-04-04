# ECS Infrastructure setup

# Background

We need a way to flexibly deploy services in a quick and cost efficient manner. This project is a semi automated way of
initializing an aws infrastructure to enable ECS deployment. 

# Features

- Script to Create S3 bucket and CodeBuild project used to execute this project
- Initializing cluster (Auto Scaling Group, ECS cluster)
- Based on parameters, the ability to create ECS Services
- For each ECS service (look at buildspec.yml), it creates
    - Code build project
    - ECS Service
    - ECR Repository
    - Target Group which is associated with `service_name` sub-domain of the chosen domain
    
# Improvements

- The configurations for each service reside in this repository, it might grow 
- Parameterize the build project to have more control of some items. 
- Deploying in a different region in the same account is not supported 

# Procedure

## (First time only) init.sh
When deploying in a new account, the first thing to do is to to run init.sh. This script will generate the following.

#### An S3 bucket. 
   This is used by terraform to manage the states of the infrastructure managed by it. The contents of this bucket should
   not be removed or edited manually. This could put potentially screw up the ability to further use this project
   to manage infrastructure. (Unless you really know what you are doing.)
#### Infra-Builder CodeBuild project
   This project will create the buildspec.yml in this folder. The buildspec defines steps that will initialize
   and update the resources in the account.r
    
   If you need to deploy new services, you only need to add a new section to the build spec with a new tfvar file
   (Needs more explanation here)
   
### Running the script
Running this script requires, 
 - AWS Cli installed
 - AWS Credentials set up
 - Permissions to Create S3 bucket, create CodeBuild project and Create IAM Role
 
   
    $ ./init.sh --region us-east-1 --s3-bucket-name moh-tf-state-files --domain example.com 
    
This will initialize the S3 bucket an the infra-builder project. 
  
## Run Infra-Builder

After running the initialization script, you will find a CodeBuild project in you account. The next step is to run this build.
(Please, make sure the S3 bucket was created)