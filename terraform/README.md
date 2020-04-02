############################
## Terraform installation ##
############################

## Get terraform package
wget https://releases.hashicorp.com/terraform/0.11.13/terraform_0.11.13_linux_amd64.zip
 
## Unzip the package
unzip terraform_0.11.13_linux_amd64.zip
 
## Move the package to /usr/local/bin
sudo mv terraform /usr/local/bin/ && rm terraform_0.11.13_linux_amd64.zip
 
## Check if terraform working properly
terraform --version
 
